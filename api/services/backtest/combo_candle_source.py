"""Candle acquisition for the combo backtests.

The session backtests ask "what does this definition see on this day?".
A combo backtest holds positions across days, so it asks for one
contiguous series covering the whole run - plus enough candles before it
to define the indicator on the run's very first candle (FR-C13).

Like `CandleSource`, this is the only module here that performs I/O, and
it inherits that module's failure policy verbatim because it is a
correctness rule rather than an optimization: a genuine "Saxo has nothing
for this day" is cached, a transient fetch failure is never cached, and a
cache outage in either direction degrades to going to Saxo.
"""

import datetime
import logging
from typing import List, Optional

from api.services.backtest.calendar import (
    is_today_not_yet_closed,
    paris_session_end_utc,
    paris_session_start_utc,
    session_key,
)
from api.services.backtest.candles import candle_date
from client.aws_client import DynamoDBClient, DynamoDBOperationError
from model import BacktestDefinition, Candle, UnitTime
from services.candles_service import CandlesService
from utils.exception import SaxoException

# Minutes per candle for each timeframe a combo backtest can run on.
HORIZONS = {
    UnitTime.M5: 5,
    UnitTime.M15: 15,
    UnitTime.H1: 60,
}

# Candles of warm-up before the run's first candle. Matches what the live
# alerting path feeds combo (alerting.py::_build_candles fetches 250), and
# clears the 235 that indicator_service.COMBO_MIN_CANDLES requires. It
# matters beyond the minimum because macd0lag is a recursive EMA: a
# shorter window would give the backtest a different MACD than the live
# engine saw on the same candle.
WARM_UP_CANDLES = 250

# How far back the warm-up may reach. Generous enough for H1 over the
# 20-hour DAX CFD session (250 candles is ~13 trading days) with room for
# holidays, and bounded so a dead instrument cannot walk backwards
# forever.
MAX_WARM_UP_CALENDAR_DAYS = 30

CACHE_SCHEMA_VERSION = 1


def cache_key(definition: BacktestDefinition, ut: UnitTime) -> str:
    """What the fetch depends on and nothing else: the instrument, the
    session window, the timeframe and the schema version. Deliberately
    not the definition code - two definitions on the same instrument,
    session and timeframe read identical candles."""
    return (
        f"{definition.instrument}:{session_key(definition.market)}"
        f":{ut.value}:v{CACHE_SCHEMA_VERSION}"
    )


def horizon_for(ut: UnitTime) -> int:
    horizon = HORIZONS.get(ut)
    if horizon is None:
        raise SaxoException(
            f"no candle horizon for {ut} - the combo backtests run on "
            f"{', '.join(u.value for u in HORIZONS)}"
        )
    return horizon


class ComboCandleSource:
    """Serves one chronological candle series spanning a run."""

    def __init__(
        self,
        candles_service: CandlesService,
        dynamodb_client: DynamoDBClient,
        logger: logging.Logger,
    ):
        self.candles_service = candles_service
        self.dynamodb_client = dynamodb_client
        self.logger = logger

    async def series(
        self,
        definition: BacktestDefinition,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> List[Candle]:
        """Every candle of the definition's timeframe from the warm-up
        lead-in through end_date, oldest first."""
        ut = definition.unit_time
        if ut is None:
            raise SaxoException(
                "a combo definition must carry a unit_time "
                f"(definition {definition.code!r})"
            )
        warm_up = await self._warm_up(definition, ut, start_date)
        run = await self._range(definition, ut, start_date, end_date)
        return warm_up + run

    async def _range(
        self,
        definition: BacktestDefinition,
        ut: UnitTime,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> List[Candle]:
        candles: List[Candle] = []
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:
                candles.extend(await self._day(definition, ut, current))
            current += datetime.timedelta(days=1)
        return candles

    async def _warm_up(
        self,
        definition: BacktestDefinition,
        ut: UnitTime,
        start_date: datetime.date,
    ) -> List[Candle]:
        """Trading days before start_date, walked backwards until the
        indicator has enough history or the lookback is exhausted.

        Returned oldest-first like the rest of the series. A short
        warm-up is not an error: the strategy simply takes no entry until
        the window fills, which is FR-C13.
        """
        collected: List[List[Candle]] = []
        total = 0
        current = start_date - datetime.timedelta(days=1)
        floor = start_date - datetime.timedelta(days=MAX_WARM_UP_CALENDAR_DAYS)
        while total < WARM_UP_CANDLES and current >= floor:
            if current.weekday() < 5:
                day = await self._day(definition, ut, current)
                if day:
                    collected.append(day)
                    total += len(day)
            current -= datetime.timedelta(days=1)

        if total < WARM_UP_CANDLES:
            self.logger.warning(
                f"only {total} warm-up candles for {definition.instrument} "
                f"at {ut.value} before {start_date}; the run starts with "
                "candles the indicator cannot be evaluated on"
            )
        return [candle for day in reversed(collected) for candle in day]

    async def _day(
        self,
        definition: BacktestDefinition,
        ut: UnitTime,
        trading_date: datetime.date,
    ) -> List[Candle]:
        """One trading day's candles, chronological, from the cache when
        possible and from Saxo otherwise. Empty for a day with no data
        (holiday) or a fetch that failed.

        The two empties are not stored the same way: a genuine empty day
        is cached as such, while a SaxoException is left uncached so one
        bad minute does not poison every later run over that day.
        """
        key = cache_key(definition, ut)
        cached = await self.load(key, trading_date)
        if cached is not None:
            return cached

        try:
            candles = self._fetch(definition, ut, trading_date)
        except SaxoException as e:
            self.logger.warning(
                f"Candle fetch failed for {definition.instrument} at "
                f"{ut.value} on {trading_date}, not caching: {e}"
            )
            return []

        candles = sorted(candles, key=candle_date)
        if is_today_not_yet_closed(trading_date, definition.market):
            # A day still trading is a partial answer, and this cache has
            # no TTL. Storing it would freeze a truncated day into the
            # *warm-up* of every later run on this instrument, not just
            # into one day's result.
            self.logger.debug(
                f"not caching {trading_date} for {definition.instrument}: "
                "the session has not closed yet"
            )
            return candles
        await self.store(key, trading_date, candles)
        return candles

    def _fetch(
        self,
        definition: BacktestDefinition,
        ut: UnitTime,
        trading_date: datetime.date,
    ) -> List[Candle]:
        start_utc = paris_session_start_utc(trading_date, definition.market)
        end_utc = paris_session_end_utc(trading_date, definition.market)
        return self.candles_service.get_candles_in_window(
            definition.instrument,
            ut,
            horizon_for(ut),
            start_utc,
            end_utc,
        )

    async def load(
        self, key: str, trading_date: datetime.date
    ) -> Optional[List[Candle]]:
        """The cached series for (key, trading_date), or None on a miss,
        a DynamoDB failure or a malformed item - in every such case the
        caller falls back to Saxo, so a cache problem never breaks a
        run. An empty list is a cached "Saxo has nothing for this day"
        and is distinct from None."""
        try:
            item = await self.dynamodb_client.get_cached_backtest_series(
                key, trading_date.isoformat()
            )
        except (DynamoDBOperationError, RuntimeError) as e:
            self.logger.warning(
                f"Combo candle cache lookup failed for "
                f"{key}/{trading_date}: {e}"
            )
            return None
        if item is None:
            return None
        try:
            if not bool(item["has_data"]):
                return []
            return [Candle.from_dict(c) for c in item.get("candles", [])]
        except (KeyError, ValueError, TypeError) as e:
            self.logger.warning(
                f"Malformed combo cache item for {key}/{trading_date}: {e}"
            )
            return None

    async def store(
        self, key: str, trading_date: datetime.date, candles: List[Candle]
    ) -> None:
        """Cache a day's series. A DynamoDB failure (including no active
        resource - local/dev without AWS) degrades to "not cached this
        time"; caching is a cost optimization, not a correctness
        requirement."""
        try:
            await self.dynamodb_client.store_backtest_series(
                key,
                trading_date.isoformat(),
                bool(candles),
                [c.to_dict() for c in candles],
            )
        except (DynamoDBOperationError, RuntimeError) as e:
            self.logger.warning(
                f"Combo candle cache store failed for "
                f"{key}/{trading_date}: {e}"
            )
