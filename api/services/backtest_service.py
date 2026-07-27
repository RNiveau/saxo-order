import datetime
from typing import List, Optional
from zoneinfo import ZoneInfo

from client.aws_client import DynamoDBClient, DynamoDBOperationError
from model import (
    BacktestDefinition,
    BacktestParameters,
    BacktestRunResult,
    BacktestSummary,
    CachedDayCandles,
    Candle,
    DayResult,
    DayResultSummary,
    EUMarket,
    Market,
    Strategy,
    Trade,
    UnitTime,
)
from model.enum import DayStatus, Direction, ExitReason
from services.candles_service import CandlesService
from services.indicator_service import (
    adx,
    mobile_average,
    slope_percentage,
)
from utils.exception import SaxoException
from utils.helper import market_in_utc
from utils.logger import Logger

PARIS_TZ = ZoneInfo("Europe/Paris")

# Daily MA50 slope regime measure: MA50 needs 50 daily closes and the
# slope is taken over a 10-candle lookback, so at least 60 prior daily
# candles are required before a day can be scored.
MM50_MIN_DAILY_CANDLES = 60
MM50_SLOPE_LOOKBACK = 10

# Daily ADX regime measure: Wilder's double smoothing needs period * 3
# prior daily candles (matches services.indicator_service.adx).
ADX_PERIOD = 14
ADX_MIN_DAILY_CANDLES = ADX_PERIOD * 3

BACKTEST_DEFINITIONS: List[BacktestDefinition] = [
    BacktestDefinition(
        code="B9H",
        name=Strategy.B9H.value,
        display_name="CAC40 Bougie de 9h",
        instrument="FRA40.I",
    ),
    BacktestDefinition(
        code="B9HTC",
        name=Strategy.B9HTC.value,
        display_name="CAC40 Bougie de 9h (time cut)",
        instrument="FRA40.I",
        time_cut_minutes=30,
        time_cut_min_favorable_points=5.0,
    ),
    BacktestDefinition(
        code="G9H",
        name=Strategy.G9H.value,
        display_name="GER40 Bougie de 9h",
        instrument="GER40.I",
        default_parameters=BacktestParameters(
            stop_loss_points=150,
            take_profit_offset_points=10,
            break_even_trigger_points=50,
            max_entry_distance_points=40,
        ),
        double_take_profit=True,
        first_target_fraction=0.5,
        stop_from_reference_level=True,
    ),
    # Control run for G9H: the same GER40 setup and the same 150-point
    # stop measured from the H1 reference level, but a single lot and a
    # single take-profit. Isolates what the double take-profit overlay
    # itself contributes. Note it also drops the TP1 entry filter (a
    # midpoint that only exists under double_take_profit), so it takes
    # entries G9H rejects rather than the same entries at half size.
    BacktestDefinition(
        code="G9HSL",
        name=Strategy.G9HSL.value,
        display_name="GER40 Bougie de 9h (lot unique)",
        instrument="GER40.I",
        default_parameters=BacktestParameters(
            stop_loss_points=150,
            take_profit_offset_points=10,
            break_even_trigger_points=50,
            max_entry_distance_points=40,
        ),
        stop_from_reference_level=True,
    ),
    BacktestDefinition(
        code="B9HWS",
        name=Strategy.B9HWS.value,
        display_name="CAC40 Bougie de 9h (wide-range structural stop)",
        instrument="FRA40.I",
        min_h1_range_points=40.0,
        structural_stop=True,
    ),
]

# Bump whenever a change to a BacktestDefinition's instrument, 9h
# reference window, or session windows would change what candles are
# fetched under the same code (e.g. re-pointing a definition at a
# different instrument). Without this, an edited definition would
# otherwise keep serving cache entries fetched under its old shape
# forever - there is no TTL on the candle cache (FR-040).
CACHE_SCHEMA_VERSION = 1


def _cache_key(definition: BacktestDefinition) -> str:
    """Cache key for the raw-candle cache (FR-036), covering not just
    the definition's code but also its instrument and the schema
    version, so a definition edit or a strategy-shape change can
    invalidate old entries just by bumping CACHE_SCHEMA_VERSION."""
    return f"{definition.code}:{definition.instrument}:v{CACHE_SCHEMA_VERSION}"


# Candle horizons for the two Saxo fetches. Unlike the strategy
# thresholds (now tunable via BacktestParameters), these describe the
# fixed shape of the "CAC40 Bougie de 9h" setup - a 1-hour reference
# window scanned with 5-minute candles - and are not exposed as
# parameters.
FIVE_MINUTE_HORIZON = 5
H1_HORIZON = 60

# Default thresholds, kept in one place so the free-function unit tests
# and the dataclass agree on what "unparametrized" means.
_DEFAULTS = BacktestParameters()


def resolve_parameters(
    definition: BacktestDefinition,
    stop_loss_points: Optional[float] = None,
    take_profit_offset_points: Optional[float] = None,
    break_even_trigger_points: Optional[float] = None,
    max_entry_distance_points: Optional[float] = None,
) -> BacktestParameters:
    """Merge per-run overrides onto the definition's default thresholds.
    An omitted (None) override falls back to definition.default_parameters,
    so each definition keeps its own defaults - CAC40 50/10/20/20, GER40
    150/10/50/40."""
    defaults = definition.default_parameters
    return BacktestParameters(
        stop_loss_points=(
            stop_loss_points
            if stop_loss_points is not None
            else defaults.stop_loss_points
        ),
        take_profit_offset_points=(
            take_profit_offset_points
            if take_profit_offset_points is not None
            else defaults.take_profit_offset_points
        ),
        break_even_trigger_points=(
            break_even_trigger_points
            if break_even_trigger_points is not None
            else defaults.break_even_trigger_points
        ),
        max_entry_distance_points=(
            max_entry_distance_points
            if max_entry_distance_points is not None
            else defaults.max_entry_distance_points
        ),
    )


def _is_valid_long_entry(
    entry_price: float,
    h1_low: float,
    take_profit_level: float,
    max_entry_distance: float = _DEFAULTS.max_entry_distance_points,
    first_target: Optional[float] = None,
) -> bool:
    """A long breakout entry only produces a trade when it still leaves
    room to work: within max_entry_distance points of the H1 low, and
    below the take-profit level (H1 high minus the take-profit offset).
    An entry too far above the low, or already at/above take-profit, is
    not valid - it would exit on the very next candle for little or no
    favorable move despite being labeled a take-profit.

    For a double take-profit setup, first_target (the H1 midpoint, TP1)
    is also required to sit strictly above the entry: on a narrow H1
    range an otherwise-valid entry (within max_entry_distance of the low)
    can open past the midpoint, which would fire TP1 immediately, bank a
    loss as a take-profit, and discard the structural stop - so such an
    entry is rejected, mirroring the take_profit_level guard."""
    valid = (
        entry_price - h1_low <= max_entry_distance
        and entry_price < take_profit_level
    )
    if first_target is not None:
        valid = valid and entry_price < first_target
    return valid


def _is_valid_short_entry(
    entry_price: float,
    h1_high: float,
    take_profit_level: float,
    max_entry_distance: float = _DEFAULTS.max_entry_distance_points,
    first_target: Optional[float] = None,
) -> bool:
    """Mirror of _is_valid_long_entry for the short side: a short
    breakdown entry is only valid when it is within max_entry_distance
    points below the H1 high, and above the take-profit level (H1 low
    plus the take-profit offset). For a double take-profit setup,
    first_target (TP1) must also sit strictly below the entry."""
    valid = (
        h1_high - entry_price <= max_entry_distance
        and entry_price > take_profit_level
    )
    if first_target is not None:
        valid = valid and entry_price > first_target
    return valid


def _eu_market_in_utc(trading_date: datetime.date) -> Market:
    reference = datetime.datetime(
        trading_date.year,
        trading_date.month,
        trading_date.day,
        tzinfo=PARIS_TZ,
    )
    return market_in_utc(EUMarket(), reference)


def paris_reference_window_utc(
    trading_date: datetime.date,
) -> tuple[datetime.datetime, datetime.datetime]:
    """9:00-10:00 Paris local time for trading_date, as naive UTC bounds."""
    utc_market = _eu_market_in_utc(trading_date)
    start = datetime.datetime(
        trading_date.year,
        trading_date.month,
        trading_date.day,
        utc_market.open_hour,
        utc_market.open_minutes,
    )
    end = start + datetime.timedelta(hours=1)
    return (start, end)


def paris_session_end_utc(trading_date: datetime.date) -> datetime.datetime:
    """End of FRA40.I's regular trading session (Euronext Paris close,
    17:30 local, from EUMarket.close_hour/end_minute), as a naive UTC
    datetime."""
    utc_market = _eu_market_in_utc(trading_date)
    return datetime.datetime(
        trading_date.year,
        trading_date.month,
        trading_date.day,
        utc_market.close_hour,
        utc_market.end_minute,
    )


def is_future_paris_date(
    d: datetime.date, now: Optional[datetime.datetime] = None
) -> bool:
    current = (now or datetime.datetime.now(PARIS_TZ)).astimezone(PARIS_TZ)
    return d > current.date()


def is_today_not_yet_closed(
    d: datetime.date, now: Optional[datetime.datetime] = None
) -> bool:
    """True if d is today (Paris) and the regular session hasn't ended
    yet - the backtest only operates on already-closed historical days,
    and Saxo won't return a complete H1/5-minute series for a session
    still in progress."""
    current = (now or datetime.datetime.now(PARIS_TZ)).astimezone(PARIS_TZ)
    if d != current.date():
        return False
    market = EUMarket()
    session_end_local = datetime.datetime(
        d.year,
        d.month,
        d.day,
        market.close_hour,
        market.end_minute,
        tzinfo=PARIS_TZ,
    )
    return current < session_end_local


def _candle_date(candle: Candle) -> datetime.datetime:
    """Candles from get_candles_in_window always carry a date (it is
    part of that method's window filter); raise rather than assert so
    a violation surfaces as a normal exception instead of silently
    passing through under `-O` or crashing with a bare AssertionError."""
    if candle.date is None:
        raise SaxoException(
            "Candle from get_candles_in_window is missing a date"
        )
    return candle.date


class _OpenPosition:
    def __init__(
        self,
        entry_time: datetime.datetime,
        entry_price: float,
        direction: Direction,
        take_profit_level: float,
        stop_loss_points: float,
        time_cut_minutes: Optional[int] = None,
        time_cut_min_favorable_points: Optional[float] = None,
        double: bool = False,
        first_target_level: Optional[float] = None,
        initial_stop_price: Optional[float] = None,
        h1_high: Optional[float] = None,
        h1_low: Optional[float] = None,
        structural_stop: bool = False,
    ):
        self.entry_time = entry_time
        self.entry_price = entry_price
        self.direction = direction
        self.take_profit_level = take_profit_level
        self.stop_loss_points = stop_loss_points
        self.be_armed = False
        self.time_cut_minutes = time_cut_minutes
        self.time_cut_min_favorable_points = time_cut_min_favorable_points
        self.max_favorable_points = 0.0
        # Double take-profit / two-lot state (GER40). double gates the
        # split-exit path; first_target_level is TP1 (H1 midpoint); once
        # the first lot fills, first_target_taken flips and banked_points
        # holds lot A's realised P&L, added to the runner's leg at close.
        self.double = double
        self.first_target_level = first_target_level
        self.first_target_taken = False
        self.banked_points = 0.0
        # Absolute initial stop level. When set (GER40, stop measured from
        # the H1 reference level) it overrides the entry-relative stop; both
        # lots share it until break-even moves the stop to entry.
        self.initial_stop_price = initial_stop_price
        # Wide-range structural-stop variant (spec 021, US1d): the H1
        # reference levels and the flag enabling the close-beyond-level stop.
        self.h1_high = h1_high
        self.h1_low = h1_low
        self.structural_stop = structural_stop

    @property
    def time_cut_enabled(self) -> bool:
        return (
            self.time_cut_minutes is not None
            and self.time_cut_min_favorable_points is not None
        )

    @property
    def is_long(self) -> bool:
        return self.direction == Direction.BUY

    @property
    def stop_level(self) -> float:
        if self.be_armed:
            return self.entry_price
        if self.initial_stop_price is not None:
            return self.initial_stop_price
        if self.is_long:
            return self.entry_price - self.stop_loss_points
        return self.entry_price + self.stop_loss_points


class _DirectionSearch:
    """Tracks the breakout/reversal candidate search for a single
    direction while no position is open.

    LONG watches for a candle closing below the H1 low, then a reversal
    candle closing back at/above it, confirmed by a later candle trading
    above that reversal candle's high. SHORT is the mirror image around
    the H1 high: a candle closing above the high, a reversal candle
    closing back at/below it, confirmed by a later candle trading below
    that candle's low. The breach is measured on the close (a confirmed
    candle outside the H1 range), not an intrabar wick. The two
    directions are searched independently and concurrently; the engine
    (see _evaluate_trades) enforces that only one may open a position at
    a time.
    """

    def __init__(
        self,
        direction: Direction,
        h1_high: float,
        h1_low: float,
        take_profit_level: float,
        max_entry_distance: float,
        first_target_level: Optional[float] = None,
    ):
        self.direction = direction
        self.h1_high = h1_high
        self.h1_low = h1_low
        self.take_profit_level = take_profit_level
        self.max_entry_distance = max_entry_distance
        # TP1 (H1 midpoint) for double take-profit definitions; None for
        # single-lot ones. When set, a valid entry must sit on the
        # favorable side of it (see _is_valid_long_entry / _short).
        self.first_target_level = first_target_level
        self.breached = False
        self.candidate: Optional[Candle] = None

    @property
    def is_long(self) -> bool:
        return self.direction == Direction.BUY

    def reset(self) -> None:
        self.breached = False
        self.candidate = None

    def feed(self, candle: Candle) -> Optional[float]:
        """Advance the search by one candle. Returns a valid entry price
        when this candle confirms a tradeable breakout, otherwise None
        (updating the internal breach/candidate state)."""
        if self.is_long:
            return self._feed_long(candle)
        return self._feed_short(candle)

    def _feed_long(self, candle: Candle) -> Optional[float]:
        if self.candidate is None:
            if not self.breached:
                if candle.close < self.h1_low:
                    self.breached = True
                return None
            if candle.close >= self.h1_low:
                self.candidate = candle
                self.breached = False
            return None

        # candidate is the reversal candle awaiting breakout
        # confirmation: only a later candle trading above its high
        # confirms the reversal has momentum.
        if candle.higher > self.candidate.higher:
            entry_price = max(self.candidate.higher, candle.open)
            self.candidate = None
            if _is_valid_long_entry(
                entry_price,
                self.h1_low,
                self.take_profit_level,
                self.max_entry_distance,
                self.first_target_level,
            ):
                return entry_price
            return None
        if candle.close < self.h1_low:
            self.candidate = None
            self.breached = True
            return None
        self.candidate = candle
        return None

    def _feed_short(self, candle: Candle) -> Optional[float]:
        if self.candidate is None:
            if not self.breached:
                if candle.close > self.h1_high:
                    self.breached = True
                return None
            if candle.close <= self.h1_high:
                self.candidate = candle
                self.breached = False
            return None

        # mirror of _feed_long: a later candle trading below the
        # reversal candle's low confirms the downside breakout.
        if candle.lower < self.candidate.lower:
            entry_price = min(self.candidate.lower, candle.open)
            self.candidate = None
            if _is_valid_short_entry(
                entry_price,
                self.h1_high,
                self.take_profit_level,
                self.max_entry_distance,
                self.first_target_level,
            ):
                return entry_price
            return None
        if candle.close > self.h1_high:
            self.candidate = None
            self.breached = True
            return None
        self.candidate = candle
        return None


class BacktestService:
    """Runs the hardcoded backtests exposed by the Backtest menu."""

    def __init__(
        self,
        candles_service: CandlesService,
        dynamodb_client: DynamoDBClient,
    ):
        self.logger = Logger.get_logger("backtest_service")
        self.candles_service = candles_service
        self.dynamodb_client = dynamodb_client

    def list_definitions(self) -> List[BacktestDefinition]:
        return BACKTEST_DEFINITIONS

    def get_definition(self, code: str) -> Optional[BacktestDefinition]:
        for definition in BACKTEST_DEFINITIONS:
            if definition.code == code:
                return definition
        return None

    async def evaluate_day(
        self,
        definition: BacktestDefinition,
        trading_date: datetime.date,
        params: Optional[BacktestParameters] = None,
    ) -> DayResult:
        """Run the "CAC40 Bougie de 9h" rules for a single trading day.

        Before fetching from Saxo, checks the raw-candle cache for this
        (definition, trading_date) pair (FR-036); on a miss, fetches as
        before and stores the result under that key (FR-037/FR-038) so a
        later request for the same pair skips Saxo entirely. The
        strategy evaluation (_evaluate_from_candles) always runs fresh
        against those candles, cached or not (FR-039). A transient Saxo
        fetch failure (as opposed to a genuine "no data") is never
        written to the cache, so it doesn't permanently poison later
        runs over the same day."""
        params = params or BacktestParameters()
        cached = await self._get_cached_candles(
            _cache_key(definition), trading_date
        )

        if cached is not None and cached.has_data and cached.h1_candle is None:
            # _get_cached_candles already guards against this, but a
            # cache problem must never break a backtest - fall through
            # to a fresh fetch instead of failing the request.
            self.logger.warning(
                f"Cached backtest entry for {_cache_key(definition)}/"
                f"{trading_date} has has_data=True but no h1_candle; "
                "treating as a miss"
            )
            cached = None

        if cached is not None:
            if not cached.has_data:
                return DayResult(date=trading_date, status=DayStatus.NO_DATA)
            cached_h1_candle = cached.h1_candle
            if cached_h1_candle is not None:
                return self._evaluate_from_candles(
                    definition,
                    trading_date,
                    params,
                    cached_h1_candle,
                    cached.m5_candles,
                )

        h1_start_utc, h1_end_utc = paris_reference_window_utc(trading_date)
        try:
            fetched_h1_candle = self._fetch_h1_reference_candle(
                definition.instrument, h1_start_utc, h1_end_utc
            )
        except SaxoException as e:
            self.logger.warning(
                f"H1 fetch failed for {definition.instrument} on "
                f"{trading_date}, not caching: {e}"
            )
            return DayResult(date=trading_date, status=DayStatus.NO_DATA)
        if fetched_h1_candle is None:
            await self._store_candles(
                _cache_key(definition), trading_date, has_data=False
            )
            return DayResult(date=trading_date, status=DayStatus.NO_DATA)

        # Wide-range variant (FR-033): skip the 5-minute fetch entirely
        # on a day whose H1 range doesn't clear the threshold - the day
        # is a NO_TRADE regardless of what the 5-minute candles hold.
        if self._is_below_min_range(
            definition, fetched_h1_candle.higher, fetched_h1_candle.lower
        ):
            await self._store_candles(
                _cache_key(definition),
                trading_date,
                has_data=True,
                h1_candle=fetched_h1_candle,
                m5_candles=[],
            )
            return self._evaluate_from_candles(
                definition, trading_date, params, fetched_h1_candle, []
            )

        session_end_utc = paris_session_end_utc(trading_date)
        try:
            five_min_candles = self._fetch_five_minute_candles(
                definition.instrument, h1_end_utc, session_end_utc
            )
        except SaxoException as e:
            self.logger.warning(
                f"5-minute fetch failed for {definition.instrument} on "
                f"{trading_date}, not caching: {e}"
            )
            five_min_candles = []
        else:
            await self._store_candles(
                _cache_key(definition),
                trading_date,
                has_data=True,
                h1_candle=fetched_h1_candle,
                m5_candles=five_min_candles,
            )

        return self._evaluate_from_candles(
            definition,
            trading_date,
            params,
            fetched_h1_candle,
            five_min_candles,
        )

    @staticmethod
    def _is_below_min_range(
        definition: BacktestDefinition, h1_high: float, h1_low: float
    ) -> bool:
        """Wide-range variant (FR-033): whether the day's H1 range fails
        to clear the definition's threshold. Always False for
        definitions without one (min_h1_range_points is None)."""
        return (
            definition.min_h1_range_points is not None
            and h1_high - h1_low <= definition.min_h1_range_points
        )

    def _evaluate_from_candles(
        self,
        definition: BacktestDefinition,
        trading_date: datetime.date,
        params: BacktestParameters,
        h1_candle: Candle,
        five_min_candles: List[Candle],
    ) -> DayResult:
        """Shared tail of evaluate_day once the day's H1/5-minute candles
        are known, whether from the cache or a fresh Saxo fetch: applies
        the wide-range filter (FR-033) then runs the strategy. Pure/no
        I/O, so it's reused unchanged by both the cache-hit and
        cache-miss paths."""
        h1_high = h1_candle.higher
        h1_low = h1_candle.lower
        if self._is_below_min_range(definition, h1_high, h1_low):
            return DayResult(
                date=trading_date,
                status=DayStatus.NO_TRADE,
                h1_high=h1_high,
                h1_low=h1_low,
                h1_open=h1_candle.open,
            )

        chronological = sorted(five_min_candles, key=_candle_date)
        trades = self._evaluate_trades(
            chronological, h1_high, h1_low, params, definition
        )

        status = DayStatus.TRADED if trades else DayStatus.NO_TRADE
        return DayResult(
            date=trading_date,
            status=status,
            h1_high=h1_high,
            h1_low=h1_low,
            h1_open=h1_candle.open,
            candles=chronological,
            trades=trades,
        )

    async def run_range(
        self,
        definition: BacktestDefinition,
        start_date: datetime.date,
        end_date: datetime.date,
        params: Optional[BacktestParameters] = None,
    ) -> BacktestRunResult:
        """Run the backtest across every day in [start_date, end_date]."""
        params = params or BacktestParameters()
        day_summaries: List[DayResultSummary] = []
        all_trades: List[Trade] = []

        daily_candles = self._fetch_daily_candles(
            definition.instrument, start_date, end_date
        )

        current = start_date
        while current <= end_date:
            if current.weekday() >= 5:
                # Saturday/Sunday: FRA40.I never trades, so skip the
                # H1/5-minute fetches that would only resolve to
                # NO_DATA - avoids two wasted Saxo calls per weekend day.
                current += datetime.timedelta(days=1)
                continue
            day_result = await self.evaluate_day(definition, current, params)
            if day_result.status != DayStatus.NO_DATA:
                day_points = round(
                    sum(trade.points for trade in day_result.trades), 4
                )
                day_summaries.append(
                    DayResultSummary(
                        date=day_result.date,
                        status=day_result.status,
                        trade_count=len(day_result.trades),
                        points=day_points,
                        h1_high=day_result.h1_high,
                        h1_low=day_result.h1_low,
                        mm50_slope=self._mm50_slope_before(
                            daily_candles, day_result.date
                        ),
                        adx14=self._adx_before(daily_candles, day_result.date),
                        h1_open=day_result.h1_open,
                        overnight_gap=self._overnight_gap(
                            daily_candles,
                            day_result.date,
                            day_result.h1_open,
                        ),
                    )
                )
                all_trades.extend(day_result.trades)
            current += datetime.timedelta(days=1)

        summary = self._build_summary(
            definition, start_date, end_date, all_trades, len(day_summaries)
        )
        return BacktestRunResult(summary=summary, days=day_summaries)

    @staticmethod
    def _build_summary(
        definition: BacktestDefinition,
        start_date: datetime.date,
        end_date: datetime.date,
        trades: List[Trade],
        number_of_days: int,
    ) -> BacktestSummary:
        winning: List[Trade] = []
        losing: List[Trade] = []
        be_trades: List[Trade] = []
        for trade in trades:
            if definition.double_take_profit:
                # Two-lot positions are classified by the sign of their
                # net points (FR-G08): a TP1-then-break-even runner closes
                # BREAK_EVEN but banks a net gain, so it counts as a win;
                # only a genuinely flat position (net 0) is a break-even.
                if trade.points > 0:
                    winning.append(trade)
                elif trade.points < 0:
                    losing.append(trade)
                else:
                    be_trades.append(trade)
            elif trade.exit_reason == ExitReason.BREAK_EVEN:
                be_trades.append(trade)
            elif trade.points > 0:
                winning.append(trade)
            else:
                losing.append(trade)

        average_win = (
            round(sum(t.points for t in winning) / len(winning), 4)
            if winning
            else None
        )
        average_loss = (
            round(-sum(t.points for t in losing) / len(losing), 4)
            if losing
            else None
        )
        final_result = round(sum(t.points for t in trades), 4)

        return BacktestSummary(
            definition_code=definition.code,
            start_date=start_date,
            end_date=end_date,
            number_of_days=number_of_days,
            number_of_trades=len(trades),
            number_of_winning_positions=len(winning),
            number_of_losing_positions=len(losing),
            number_of_be=len(be_trades),
            average_win=average_win,
            average_loss=average_loss,
            final_result=final_result,
        )

    def _fetch_h1_reference_candle(
        self,
        instrument: str,
        h1_start_utc: datetime.datetime,
        h1_end_utc: datetime.datetime,
    ) -> Optional[Candle]:
        """Returns None only when Saxo genuinely has no H1 candle for this
        window (a real "no data" day, safe to cache as such). A
        SaxoException (expired token, rate limit, network blip) is a
        transient fetch failure, not "no data" - it propagates so the
        caller never mistakes one for the other and caches it
        permanently."""
        candles = self.candles_service.get_candles_in_window(
            instrument,
            UnitTime.H1,
            H1_HORIZON,
            h1_start_utc,
            h1_end_utc,
        )
        if not candles:
            return None
        return sorted(candles, key=_candle_date)[0]

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
            instrument,
            UnitTime.M5,
            FIVE_MINUTE_HORIZON,
            start_utc,
            end_utc,
        )

    def _fetch_daily_candles(
        self,
        instrument: str,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> List[Candle]:
        """Daily (newest-first) candle series covering the run range plus
        enough lead-in to compute a 50-day MA slope on the first day.
        Fetched once per run_range. A failure degrades to an empty series
        (blank mm50_slope column) rather than aborting the whole export."""
        # Daily candles are fetched counting backward from end_date, so
        # count must reach ~60 trading days before start_date for the
        # first day's MA50 slope. Calendar days is a safe upper bound on
        # the range's trading days (build_candles caps at available data),
        # so no need to exclude weekends/holidays precisely.
        count = (
            (end_date - start_date).days
            + MM50_MIN_DAILY_CANDLES
            + MM50_SLOPE_LOOKBACK
            + 5
        )
        reference = datetime.datetime(
            end_date.year, end_date.month, end_date.day, tzinfo=PARIS_TZ
        )
        try:
            return self.candles_service.build_candles(
                instrument, UnitTime.D, EUMarket(), count, reference
            )
        except SaxoException as e:
            self.logger.warning(
                f"No daily candles for {instrument} regime measure: {e}"
            )
            return []

    @staticmethod
    def _mm50_slope_before(
        daily_candles: List[Candle], trading_date: datetime.date
    ) -> Optional[float]:
        """Daily MA50 slope (%) as of the last close strictly before
        trading_date (lookahead-safe: today's daily candle is never in the
        window). Mirrors the MA50 slope used by the MM50 alert (spec 019).
        Returns None when fewer than MM50_MIN_DAILY_CANDLES prior daily
        candles are available."""
        prior = [
            candle
            for candle in daily_candles
            if candle.date is not None and candle.date.date() < trading_date
        ]
        if len(prior) < MM50_MIN_DAILY_CANDLES:
            return None
        prior.sort(key=_candle_date, reverse=True)
        ma50_last = mobile_average(prior, 50)
        ma50_first = mobile_average(prior[MM50_SLOPE_LOOKBACK:], 50)
        return slope_percentage(0, ma50_first, MM50_SLOPE_LOOKBACK, ma50_last)

    @staticmethod
    def _adx_before(
        daily_candles: List[Candle], trading_date: datetime.date
    ) -> Optional[float]:
        """Daily ADX(14) as of the last close strictly before trading_date
        (lookahead-safe, same window discipline as _mm50_slope_before).
        Returns None when fewer than ADX_MIN_DAILY_CANDLES prior daily
        candles are available."""
        prior = [
            candle
            for candle in daily_candles
            if candle.date is not None and candle.date.date() < trading_date
        ]
        if len(prior) < ADX_MIN_DAILY_CANDLES:
            return None
        prior.sort(key=_candle_date, reverse=True)
        return adx(prior, ADX_PERIOD)

    @staticmethod
    def _overnight_gap(
        daily_candles: List[Candle],
        trading_date: datetime.date,
        h1_open: Optional[float],
    ) -> Optional[float]:
        """Overnight gap = 9h open - the prior daily close. A same-day,
        pre-trade shock signal (the 9h open is known at 09:00, before any
        entry). Lookahead-safe: the prior close is the latest daily candle
        strictly before trading_date. None when the 9h open or a prior
        daily candle is missing."""
        if h1_open is None:
            return None
        prior = [
            candle
            for candle in daily_candles
            if candle.date is not None and candle.date.date() < trading_date
        ]
        if not prior:
            return None
        prior_close = max(prior, key=_candle_date).close
        return round(h1_open - prior_close, 4)

    def _evaluate_trades(
        self,
        candles: List[Candle],
        h1_high: float,
        h1_low: float,
        params: BacktestParameters,
        definition: BacktestDefinition,
    ) -> List[Trade]:
        """Evaluate both directions concurrently, with at most one
        position open at any time. The H1 high/low reference levels are
        shared: a long trades the reversal off the H1 low, a short the
        reversal off the H1 high. Whichever direction confirms a valid
        breakout first opens the position and holds it until it closes;
        the search for both directions only resumes once flat again."""
        trades: List[Trade] = []
        position: Optional[_OpenPosition] = None
        long_take_profit = h1_high - params.take_profit_offset_points
        short_take_profit = h1_low + params.take_profit_offset_points

        # Double take-profit / two-lot setup (GER40). first_target is the
        # H1 midpoint (TP1); the stop, when measured from the reference
        # level, sits stop_loss_points beyond the H1 low/high (shared by
        # both lots). Both stay None on the single-lot CAC40 backtests.
        double = definition.double_take_profit
        first_target: Optional[float] = None
        if double and definition.first_target_fraction is not None:
            first_target = h1_low + definition.first_target_fraction * (
                h1_high - h1_low
            )
        long_stop_price: Optional[float] = None
        short_stop_price: Optional[float] = None
        if definition.stop_from_reference_level:
            long_stop_price = h1_low - params.stop_loss_points
            short_stop_price = h1_high + params.stop_loss_points

        long_search = _DirectionSearch(
            Direction.BUY,
            h1_high,
            h1_low,
            long_take_profit,
            params.max_entry_distance_points,
            first_target,
        )
        short_search = _DirectionSearch(
            Direction.SELL,
            h1_high,
            h1_low,
            short_take_profit,
            params.max_entry_distance_points,
            first_target,
        )

        for candle in candles:
            candle_date = _candle_date(candle)
            if position is None:
                long_entry = long_search.feed(candle)
                short_entry = short_search.feed(candle)
                # One position at a time, either side: whichever
                # direction confirms first opens. On the rare candle
                # that would confirm both (opposing candidates pending,
                # an engulfing candle), the long entry takes precedence
                # as a deterministic tiebreak.
                if long_entry is not None:
                    position = _OpenPosition(
                        entry_time=candle_date,
                        entry_price=long_entry,
                        direction=Direction.BUY,
                        take_profit_level=long_take_profit,
                        stop_loss_points=params.stop_loss_points,
                        time_cut_minutes=definition.time_cut_minutes,
                        time_cut_min_favorable_points=(
                            definition.time_cut_min_favorable_points
                        ),
                        double=double,
                        first_target_level=first_target,
                        initial_stop_price=long_stop_price,
                        h1_high=h1_high,
                        h1_low=h1_low,
                        structural_stop=definition.structural_stop,
                    )
                elif short_entry is not None:
                    position = _OpenPosition(
                        entry_time=candle_date,
                        entry_price=short_entry,
                        direction=Direction.SELL,
                        take_profit_level=short_take_profit,
                        stop_loss_points=params.stop_loss_points,
                        time_cut_minutes=definition.time_cut_minutes,
                        time_cut_min_favorable_points=(
                            definition.time_cut_min_favorable_points
                        ),
                        double=double,
                        first_target_level=first_target,
                        initial_stop_price=short_stop_price,
                        h1_high=h1_high,
                        h1_low=h1_low,
                        structural_stop=definition.structural_stop,
                    )
                if position is not None:
                    long_search.reset()
                    short_search.reset()
                continue

            closed = self._resolve_exit(position, candle, candle_date, params)
            if closed is not None:
                trades.append(closed)
                position = None
                long_search.reset()
                short_search.reset()

        if position is not None and candles:
            last_candle = candles[-1]
            close = (
                self._close_double_trade
                if position.double
                else self._close_trade
            )
            trades.append(
                close(
                    position,
                    _candle_date(last_candle),
                    last_candle.close,
                    ExitReason.END_OF_DAY,
                )
            )

        return trades

    def _resolve_exit(
        self,
        position: _OpenPosition,
        candle: Candle,
        candle_date: datetime.datetime,
        params: BacktestParameters,
    ) -> Optional[Trade]:
        """Resolve the exit conditions for an open position on a single
        candle. Checks stop-loss (or break-even) before take-profit
        (FR-009), and only arms the break-even stop when neither exit
        triggered. Returns the closed Trade, or None if the position
        stays open."""
        if position.double:
            return self._resolve_exit_double(
                position, candle, candle_date, params
            )
        if position.structural_stop and not position.be_armed:
            return self._resolve_structural_exit(
                position, candle, candle_date, params
            )
        stop_level = position.stop_level
        take_profit_level = position.take_profit_level

        if position.is_long:
            stop_hit = candle.lower <= stop_level
            take_profit_hit = candle.higher >= take_profit_level
        else:
            stop_hit = candle.higher >= stop_level
            take_profit_hit = candle.lower <= take_profit_level

        if stop_hit:
            exit_price = self._stop_fill(position, candle, stop_level)
            reason = (
                ExitReason.BREAK_EVEN
                if position.be_armed
                else ExitReason.STOP_LOSS
            )
            return self._close_trade(position, candle_date, exit_price, reason)

        if take_profit_hit:
            return self._take_profit_exit(position, candle, candle_date)

        if position.time_cut_enabled:
            time_cut = self._resolve_time_cut(position, candle, candle_date)
            if time_cut is not None:
                return time_cut

        self._arm_break_even(position, candle, params)
        return None

    def _resolve_exit_double(
        self,
        position: _OpenPosition,
        candle: Candle,
        candle_date: datetime.datetime,
        params: BacktestParameters,
    ) -> Optional[Trade]:
        """Exit resolution for a two-lot / double-take-profit position
        (GER40). While both lots are open they share one stop; a stop hit
        closes both (the "SL is x2" loss). The first lot takes profit at
        the H1 midpoint (TP1); when it fills, the runner's stop moves to
        break-even and the runner then targets the full take-profit (TP2)
        or that break-even stop. Stop is checked before take-profit on the
        same candle (conservative, FR-009/FR-G05)."""
        stop_level = position.stop_level
        first_target = position.first_target_level

        if position.is_long:
            stop_hit = candle.lower <= stop_level
            tp1_hit = (
                first_target is not None and candle.higher >= first_target
            )
            tp2_hit = candle.higher >= position.take_profit_level
        else:
            stop_hit = candle.higher >= stop_level
            tp1_hit = first_target is not None and candle.lower <= first_target
            tp2_hit = candle.lower <= position.take_profit_level

        if stop_hit:
            exit_price = self._stop_fill(position, candle, stop_level)
            reason = (
                ExitReason.BREAK_EVEN
                if position.be_armed
                else ExitReason.STOP_LOSS
            )
            return self._close_double_trade(
                position, candle_date, exit_price, reason
            )

        if (
            not position.first_target_taken
            and tp1_hit
            and first_target is not None
        ):
            tp1_fill = self._target_fill(position, candle, first_target)
            leg = (
                tp1_fill - position.entry_price
                if position.is_long
                else position.entry_price - tp1_fill
            )
            position.banked_points += leg
            position.first_target_taken = True
            position.be_armed = True
            if tp2_hit:
                tp2_fill = self._target_fill(
                    position, candle, position.take_profit_level
                )
                return self._close_double_trade(
                    position, candle_date, tp2_fill, ExitReason.TAKE_PROFIT
                )
            return None

        if position.first_target_taken and tp2_hit:
            tp2_fill = self._target_fill(
                position, candle, position.take_profit_level
            )
            return self._close_double_trade(
                position, candle_date, tp2_fill, ExitReason.TAKE_PROFIT
            )

        self._arm_break_even(position, candle, params)
        return None

    def _resolve_structural_exit(
        self,
        position: _OpenPosition,
        candle: Candle,
        candle_date: datetime.datetime,
        params: BacktestParameters,
    ) -> Optional[Trade]:
        """Exit resolution for the wide-range structural-stop variant while
        break-even is unarmed (FR-034/FR-035). Take-profit is reached
        intrabar (before the candle's close), so it is resolved first; the
        structural stop then fires when the candle *closes* beyond the H1
        level on the losing side (below the H1 low for a long, above the H1
        high for a short), filling at that close with a stop-loss reason (no
        gap-fill - it is a market/close exit). Break-even arms as usual;
        once armed, _resolve_exit routes to the base logic instead."""
        if position.is_long:
            take_profit_hit = candle.higher >= position.take_profit_level
        else:
            take_profit_hit = candle.lower <= position.take_profit_level
        if take_profit_hit:
            return self._take_profit_exit(position, candle, candle_date)

        if position.is_long:
            structural_hit = (
                position.h1_low is not None and candle.close < position.h1_low
            )
        else:
            structural_hit = (
                position.h1_high is not None
                and candle.close > position.h1_high
            )
        if structural_hit:
            return self._close_trade(
                position, candle_date, candle.close, ExitReason.STOP_LOSS
            )

        self._arm_break_even(position, candle, params)
        return None

    @staticmethod
    def _take_profit_exit(
        position: _OpenPosition,
        candle: Candle,
        candle_date: datetime.datetime,
    ) -> Trade:
        """Close a position at take-profit, applying the FR-010 gap-fill
        convention (fill at the candle open when it gapped past the level)."""
        exit_price = BacktestService._target_fill(
            position, candle, position.take_profit_level
        )
        return BacktestService._close_trade(
            position, candle_date, exit_price, ExitReason.TAKE_PROFIT
        )

    @staticmethod
    def _arm_break_even(
        position: _OpenPosition,
        candle: Candle,
        params: BacktestParameters,
    ) -> None:
        """Arm the break-even stop the first time a candle reaches entry ±
        the break-even trigger (FR-008a); takes effect on later candles."""
        if position.be_armed:
            return
        arm_threshold = params.break_even_trigger_points
        if position.is_long:
            if candle.higher >= position.entry_price + arm_threshold:
                position.be_armed = True
        elif candle.lower <= position.entry_price - arm_threshold:
            position.be_armed = True

    @staticmethod
    def _stop_fill(
        position: _OpenPosition, candle: Candle, level: float
    ) -> float:
        """Gap-fill for a stop-type exit: the candle open when it gapped
        through the level, else the level itself (FR-010)."""
        if position.is_long:
            return candle.open if candle.open <= level else level
        return candle.open if candle.open >= level else level

    @staticmethod
    def _target_fill(
        position: _OpenPosition, candle: Candle, level: float
    ) -> float:
        """Gap-fill for a take-profit-type exit (mirror of _stop_fill),
        for an arbitrary target level (TP1 midpoint or the full TP)."""
        if position.is_long:
            return candle.open if candle.open >= level else level
        return candle.open if candle.open <= level else level

    @staticmethod
    def _resolve_time_cut(
        position: _OpenPosition,
        candle: Candle,
        candle_date: datetime.datetime,
    ) -> Optional[Trade]:
        """Time-based cut for the "Bougie de 9h (time cut)" variant.

        Tracks the position's max favorable excursion candle by candle.
        Once time_cut_minutes have elapsed since entry, if the trade has
        never moved more than time_cut_min_favorable_points in its favor,
        it is closed at market (this candle's close). "Never been higher
        than N points" means the cut also fires when the best move was
        exactly N points, so the comparison is <=.
        """
        threshold = position.time_cut_min_favorable_points
        minutes = position.time_cut_minutes
        if threshold is None or minutes is None:
            return None

        favorable = (
            candle.higher - position.entry_price
            if position.is_long
            else position.entry_price - candle.lower
        )
        if favorable > position.max_favorable_points:
            position.max_favorable_points = favorable

        deadline = position.entry_time + datetime.timedelta(minutes=minutes)
        if (
            candle_date >= deadline
            and position.max_favorable_points <= threshold
        ):
            return BacktestService._close_trade(
                position, candle_date, candle.close, ExitReason.TIME_CUT
            )
        return None

    @staticmethod
    def _close_trade(
        position: _OpenPosition,
        exit_time: datetime.datetime,
        exit_price: float,
        exit_reason: ExitReason,
    ) -> Trade:
        if position.is_long:
            points = exit_price - position.entry_price
        else:
            points = position.entry_price - exit_price
        return Trade(
            entry_time=position.entry_time,
            entry_price=position.entry_price,
            exit_time=exit_time,
            exit_price=round(exit_price, 4),
            exit_reason=exit_reason,
            direction=position.direction,
            points=round(points, 4),
        )

    @staticmethod
    def _close_double_trade(
        position: _OpenPosition,
        exit_time: datetime.datetime,
        exit_price: float,
        exit_reason: ExitReason,
    ) -> Trade:
        """Aggregate a two-lot position into one Trade whose points is the
        sum of both lots (FR-G07). Before the first lot takes profit both
        lots exit at exit_price (2x the leg - the "SL is x2" loss);
        afterwards only the runner remains, added to the first lot's
        banked points. exit_price/exit_reason reflect the runner's final
        exit, so points need not equal exit_price - entry_price here."""
        leg = (
            exit_price - position.entry_price
            if position.is_long
            else position.entry_price - exit_price
        )
        if position.first_target_taken:
            points = position.banked_points + leg
        else:
            points = 2 * leg
        return Trade(
            entry_time=position.entry_time,
            entry_price=position.entry_price,
            exit_time=exit_time,
            exit_price=round(exit_price, 4),
            exit_reason=exit_reason,
            direction=position.direction,
            points=round(points, 4),
        )

    async def _get_cached_candles(
        self, cache_key: str, trading_date: datetime.date
    ) -> Optional[CachedDayCandles]:
        """Look up the raw-candle cache for (cache_key, trading_date)
        (FR-036). Returns None on a cache miss, or on a DynamoDB failure
        (including no active resource - local/dev without AWS, see
        get_dynamodb_client_best_effort) - in every such case the caller
        falls back to fetching from Saxo, so a cache outage never
        breaks a backtest run."""
        try:
            item = await self.dynamodb_client.get_cached_backtest_candles(
                cache_key, trading_date.isoformat()
            )
        except (DynamoDBOperationError, RuntimeError) as e:
            self.logger.warning(
                f"Backtest candle cache lookup failed for "
                f"{cache_key}/{trading_date}: {e}"
            )
            return None
        if item is None:
            return None

        try:
            has_data = bool(item["has_data"])
            if not has_data:
                return CachedDayCandles(has_data=False)
            return CachedDayCandles(
                has_data=True,
                h1_candle=Candle.from_dict(item["h1_candle"]),
                m5_candles=[
                    Candle.from_dict(c) for c in item.get("m5_candles", [])
                ],
            )
        except (KeyError, ValueError, TypeError) as e:
            # A cache problem must never break a backtest: an item
            # written under an earlier schema (or otherwise malformed)
            # is treated as a miss, the same as if nothing were cached.
            self.logger.warning(
                f"Malformed backtest cache item for "
                f"{cache_key}/{trading_date}: {e}"
            )
            return None

    async def _store_candles(
        self,
        cache_key: str,
        trading_date: datetime.date,
        has_data: bool,
        h1_candle: Optional[Candle] = None,
        m5_candles: Optional[List[Candle]] = None,
    ) -> None:
        """Store the raw candles fetched for (cache_key, trading_date)
        so a later request for the same pair is served from the cache
        (FR-037/FR-038). A DynamoDB failure (including no active
        resource - local/dev without AWS) degrades to "not cached this
        time" rather than failing the backtest - caching is a cost
        optimization, not a correctness requirement."""
        try:
            await self.dynamodb_client.store_backtest_candles(
                cache_key,
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
                f"{cache_key}/{trading_date}: {e}"
            )
