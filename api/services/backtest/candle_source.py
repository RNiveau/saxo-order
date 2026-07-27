"""Raw candle acquisition for the backtests: Saxo fetches fronted by the
DynamoDB raw-candle cache (FR-036-FR-040).

This is the only module in the package that performs I/O. It answers one
question - "what candles does this definition see on this day?" - and never
looks at the strategy, with one exception: on a definition carrying a
minimum H1 range, a day that fails the filter skips the 5-minute fetch
entirely (FR-033), because no 5-minute candle can change the outcome.

Failure policy: a genuine "Saxo has nothing for this day" is cached as
such, but a transient fetch failure (expired token, rate limit, network
blip) is never written to the cache - otherwise one bad minute would
poison every later run over that day. A cache outage in either direction
degrades to going to Saxo, never to a failed request.
"""

import datetime
import logging
from typing import List, Optional

from api.services.backtest.calendar import (
    paris_reference_window_utc,
    paris_session_end_utc,
)
from api.services.backtest.candles import candle_date
from api.services.backtest.definitions import is_below_min_range
from client.aws_client import DynamoDBClient, DynamoDBOperationError
from model import BacktestDefinition, CachedDayCandles, Candle, UnitTime
from services.candles_service import CandlesService
from utils.exception import SaxoException

# Candle horizons for the two Saxo fetches. Unlike the strategy thresholds
# (tunable via BacktestParameters), these describe the fixed shape of the
# "Bougie de 9h" setup - a 1-hour reference window scanned with 5-minute
# candles - and are not exposed as parameters.
FIVE_MINUTE_HORIZON = 5
H1_HORIZON = 60

# Bump whenever a change to a BacktestDefinition's instrument, 9h reference
# window, or session windows would change what candles are fetched under
# the same code (e.g. re-pointing a definition at a different instrument).
# Without this, an edited definition would otherwise keep serving cache
# entries fetched under its old shape forever - there is no TTL on the
# candle cache (FR-040).
CACHE_SCHEMA_VERSION = 1


def cache_key(definition: BacktestDefinition) -> str:
    """Cache key for the raw-candle cache (FR-036), covering not just the
    definition's code but also its instrument and the schema version, so a
    definition edit or a strategy-shape change can invalidate old entries
    just by bumping CACHE_SCHEMA_VERSION."""
    return f"{definition.code}:{definition.instrument}:v{CACHE_SCHEMA_VERSION}"


class CandleSource:
    """Serves a day's H1 reference candle and 5-minute session candles,
    from the cache when possible and from Saxo otherwise."""

    def __init__(
        self,
        candles_service: CandlesService,
        dynamodb_client: DynamoDBClient,
        logger: logging.Logger,
    ):
        self.candles_service = candles_service
        self.dynamodb_client = dynamodb_client
        self.logger = logger

    async def day_candles(
        self, definition: BacktestDefinition, trading_date: datetime.date
    ) -> Optional[CachedDayCandles]:
        """The day's candles, or None when the day has no usable data
        (nothing from Saxo, or a fetch that failed). A returned value
        always carries an h1_candle."""
        cached = await self._cache_hit(definition, trading_date)
        if cached is not None:
            return None if not cached.has_data else cached
        return await self._fetch_and_store(definition, trading_date)

    async def _cache_hit(
        self, definition: BacktestDefinition, trading_date: datetime.date
    ) -> Optional[CachedDayCandles]:
        """The cached entry for this day, or None to go to Saxo. An entry
        claiming data but carrying no H1 candle is unusable, so it is
        treated as a miss rather than failing the request."""
        cached = await self._load(cache_key(definition), trading_date)
        if cached is None:
            return None
        if cached.has_data and cached.h1_candle is None:
            self.logger.warning(
                f"Cached backtest entry for {cache_key(definition)}/"
                f"{trading_date} has has_data=True but no h1_candle; "
                "treating as a miss"
            )
            return None
        return cached

    async def _fetch_and_store(
        self, definition: BacktestDefinition, trading_date: datetime.date
    ) -> Optional[CachedDayCandles]:
        h1_start_utc, h1_end_utc = paris_reference_window_utc(
            trading_date, definition.market
        )
        try:
            h1_candle = self._fetch_h1_reference_candle(
                definition.instrument, h1_start_utc, h1_end_utc
            )
        except SaxoException as e:
            self.logger.warning(
                f"H1 fetch failed for {definition.instrument} on "
                f"{trading_date}, not caching: {e}"
            )
            return None

        if h1_candle is None:
            await self._store(
                cache_key(definition), trading_date, has_data=False
            )
            return None

        # Wide-range variant (FR-033): a day whose H1 range doesn't clear
        # the threshold is a NO_TRADE whatever the 5-minute candles hold,
        # so don't pay for the second fetch.
        if is_below_min_range(definition, h1_candle.higher, h1_candle.lower):
            await self._store(
                cache_key(definition),
                trading_date,
                has_data=True,
                h1_candle=h1_candle,
                m5_candles=[],
            )
            return CachedDayCandles(
                has_data=True, h1_candle=h1_candle, m5_candles=[]
            )

        session_end_utc = paris_session_end_utc(
            trading_date, definition.market
        )
        try:
            m5_candles = self._fetch_five_minute_candles(
                definition.instrument, h1_end_utc, session_end_utc
            )
        except SaxoException as e:
            self.logger.warning(
                f"5-minute fetch failed for {definition.instrument} on "
                f"{trading_date}, not caching: {e}"
            )
            m5_candles = []
        else:
            await self._store(
                cache_key(definition),
                trading_date,
                has_data=True,
                h1_candle=h1_candle,
                m5_candles=m5_candles,
            )

        return CachedDayCandles(
            has_data=True, h1_candle=h1_candle, m5_candles=m5_candles
        )

    def _fetch_h1_reference_candle(
        self,
        instrument: str,
        h1_start_utc: datetime.datetime,
        h1_end_utc: datetime.datetime,
    ) -> Optional[Candle]:
        """Returns None only when Saxo genuinely has no H1 candle for this
        window (a real "no data" day, safe to cache as such). A
        SaxoException is a transient fetch failure, not "no data" - it
        propagates so the caller never confuses the two."""
        candles = self.candles_service.get_candles_in_window(
            instrument, UnitTime.H1, H1_HORIZON, h1_start_utc, h1_end_utc
        )
        if not candles:
            return None
        return sorted(candles, key=candle_date)[0]

    def _fetch_five_minute_candles(
        self,
        instrument: str,
        start_utc: datetime.datetime,
        end_utc: datetime.datetime,
    ) -> List[Candle]:
        """An empty result is a genuine (cacheable) "no candles"; a
        SaxoException is a transient fetch failure and propagates - see
        _fetch_h1_reference_candle."""
        return self.candles_service.get_candles_in_window(
            instrument, UnitTime.M5, FIVE_MINUTE_HORIZON, start_utc, end_utc
        )

    async def _load(
        self, key: str, trading_date: datetime.date
    ) -> Optional[CachedDayCandles]:
        """The cached entry for (key, trading_date), or None on a miss, a
        DynamoDB failure, or a malformed item. In every such case the
        caller falls back to Saxo, so a cache problem never breaks a run."""
        try:
            item = await self.dynamodb_client.get_cached_backtest_candles(
                key, trading_date.isoformat()
            )
        except (DynamoDBOperationError, RuntimeError) as e:
            self.logger.warning(
                f"Backtest candle cache lookup failed for "
                f"{key}/{trading_date}: {e}"
            )
            return None
        if item is None:
            return None

        try:
            if not bool(item["has_data"]):
                return CachedDayCandles(has_data=False)
            return CachedDayCandles(
                has_data=True,
                h1_candle=Candle.from_dict(item["h1_candle"]),
                m5_candles=[
                    Candle.from_dict(c) for c in item.get("m5_candles", [])
                ],
            )
        except (KeyError, ValueError, TypeError) as e:
            # An item written under an earlier schema (or otherwise
            # malformed) is treated as a miss, the same as if nothing
            # were cached.
            self.logger.warning(
                f"Malformed backtest cache item for "
                f"{key}/{trading_date}: {e}"
            )
            return None

    async def _store(
        self,
        key: str,
        trading_date: datetime.date,
        has_data: bool,
        h1_candle: Optional[Candle] = None,
        m5_candles: Optional[List[Candle]] = None,
    ) -> None:
        """Store the day's raw candles (FR-037/FR-038). A DynamoDB failure
        (including no active resource - local/dev without AWS) degrades to
        "not cached this time": caching is a cost optimization, not a
        correctness requirement."""
        try:
            await self.dynamodb_client.store_backtest_candles(
                key,
                trading_date.isoformat(),
                has_data,
                h1_candle.to_dict() if h1_candle is not None else None,
                (
                    [c.to_dict() for c in m5_candles]
                    if m5_candles is not None
                    else None
                ),
            )
        except (DynamoDBOperationError, RuntimeError) as e:
            self.logger.warning(
                f"Backtest candle cache store failed for "
                f"{key}/{trading_date}: {e}"
            )
