"""The MM50 direction filter (spec 025 addendum 5, FR-G36-FR-G45).

The two filtered variants are `G9HIC` with one rule added: the 9:00-10:00
reference candle's close against an MA50 decides, once and for the whole
session, which single direction may open a position.

Every day here runs against the 8000-8100 H1 range the impulsive variant
needs, with the reference candle closing at 8030 (h1_candle()'s default).
The MA50 is therefore steered by the filter series' constant close: 8000
puts the reference candle above it (long-only), 8100 below it
(short-only), 8030 exactly on it.
"""

import datetime

import pytest

from api.services.backtest.direction_filter import (
    H1_CANDLES_LEAD_IN,
    MA50_PERIOD,
    allowed_side,
)
from api.services.backtest.side import LONG
from model import BacktestDefinition, Candle, EUMarket, UnitTime
from model.enum import DayStatus, Direction, ExitReason
from tests.api.services.backtest.helpers import (
    GER_PARAMS,
    H1_LOW,
    IMPULSIVE_DEFINITION,
    IMPULSIVE_H1_HIGH,
    MM50_DAILY_DEFINITION,
    MM50_H1_DEFINITION,
    TRADING_DATE,
    daily_filter_series,
    ger_entry_candles,
    h1_candle,
    h1_filter_series,
    m5_candle,
    make_service,
    run_impulsive,
    run_mm50,
    short_entry_candles,
)

ABOVE_MA50 = 8000.0  # series close: reference candle (8030) sits above
BELOW_MA50 = 8100.0  # series close: reference candle sits below
ON_MA50 = 8030.0


class TestAllowedDirection:
    """FR-G37: strictly above the MA50 is long-only, strictly below is
    short-only, exactly on it is neither."""

    async def test_above_the_ma50_only_a_long_opens(self):
        result = await run_mm50(
            ger_entry_candles(), series=h1_filter_series(ABOVE_MA50)
        )

        assert result.status == DayStatus.TRADED
        assert len(result.trades) == 1
        assert result.trades[0].direction == Direction.BUY

    async def test_above_the_ma50_a_confirmed_short_is_refused(self):
        result = await run_mm50(
            short_entry_candles(), series=h1_filter_series(ABOVE_MA50)
        )

        assert result.status == DayStatus.NO_TRADE
        assert result.trades == []

    async def test_below_the_ma50_only_a_short_opens(self):
        result = await run_mm50(
            short_entry_candles(), series=h1_filter_series(BELOW_MA50)
        )

        assert result.status == DayStatus.TRADED
        assert len(result.trades) == 1
        assert result.trades[0].direction == Direction.SELL

    async def test_below_the_ma50_a_confirmed_long_is_refused(self):
        result = await run_mm50(
            ger_entry_candles(), series=h1_filter_series(BELOW_MA50)
        )

        assert result.status == DayStatus.NO_TRADE
        assert result.trades == []

    async def test_exactly_on_the_ma50_no_direction_is_allowed(self):
        """Vanishingly rare on floats, specified so the outcome is
        deterministic rather than accidental."""
        result = await run_mm50(
            ger_entry_candles(), series=h1_filter_series(ON_MA50)
        )

        assert result.status == DayStatus.NO_TRADE
        assert result.trades == []

    async def test_the_day_keeps_its_h1_levels_when_no_direction_opens(self):
        """A filtered-out day is a NO_TRADE like any other, not a hole:
        the day export still shows the levels it was judged on."""
        result = await run_mm50(
            ger_entry_candles(), series=h1_filter_series(BELOW_MA50)
        )

        assert result.h1_high == IMPULSIVE_H1_HIGH
        assert result.h1_low == H1_LOW
        assert result.h1_open == 8020.0


class TestUnchangedInTheAllowedDirection:
    """SC-G20 / FR-G41: the filter refuses entries, it never re-prices or
    re-times the ones it allows."""

    async def test_an_allowed_long_matches_the_unfiltered_variant(self):
        candles = ger_entry_candles() + [
            m5_candle(3, 8015, 8095, 8010, 8090),  # take-profit at 8090
        ]

        filtered = await run_mm50(candles, series=h1_filter_series(ABOVE_MA50))
        unfiltered = await run_impulsive(candles)

        assert filtered.trades == unfiltered.trades
        assert filtered.trades[0].entry_price == 8015.0
        assert filtered.trades[0].exit_reason == ExitReason.TAKE_PROFIT

    async def test_an_allowed_short_matches_the_unfiltered_variant(self):
        candles = short_entry_candles() + [
            m5_candle(3, 8080, 8085, 8005, 8010),  # take-profit at 8010
        ]

        filtered = await run_mm50(candles, series=h1_filter_series(BELOW_MA50))
        unfiltered = await run_impulsive(candles)

        assert filtered.trades == unfiltered.trades
        assert filtered.trades[0].direction == Direction.SELL
        assert filtered.trades[0].exit_reason == ExitReason.TAKE_PROFIT

    async def test_a_second_entry_in_the_allowed_direction_still_opens(self):
        """FR-G41/scenario 7: the filter caps direction, not the number of
        positions a day may take."""
        candles = (
            ger_entry_candles()
            + [m5_candle(3, 8015, 8095, 8010, 8090)]  # take-profit
            + [
                m5_candle(4, 8090, 8092, 7990, 7995),  # breach again
                m5_candle(5, 8000, 8015, 7995, 8010),  # candidate
                m5_candle(6, 8010, 8020, 8005, 8015),  # entry @8015
            ]
        )

        result = await run_mm50(candles, series=h1_filter_series(ABOVE_MA50))

        assert len(result.trades) == 2
        assert all(trade.direction == Direction.BUY for trade in result.trades)


class TestBothSearchesStillFed:
    """FR-G42: refusing an entry is not the same as not looking. The
    refused side's state machine must keep advancing, and refusing it must
    not reset the *other* side's pending candidate."""

    # The long confirms on candle 2 (trading above the 8015 candidate
    # high) and is refused; that same candle closes at 8110, above the
    # 8100 H1 high, which is what breaches the short side. If the refusal
    # reset the searches - as an actual entry does - that breach would be
    # lost and the short could not confirm two candles later.
    INTERLEAVED = [
        m5_candle(0, 8005, 8010, 7990, 7995),  # long breach
        m5_candle(1, 8000, 8015, 7995, 8010),  # long candidate @8015
        m5_candle(2, 8010, 8120, 8005, 8110),  # long confirms; short breach
        m5_candle(3, 8110, 8112, 8085, 8095),  # short candidate @8085
        m5_candle(4, 8090, 8092, 8080, 8082),  # short confirms -> @8085
    ]

    async def test_a_refused_long_does_not_reset_the_short_search(self):
        result = await run_mm50(
            self.INTERLEAVED, series=h1_filter_series(BELOW_MA50)
        )

        assert result.status == DayStatus.TRADED
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.direction == Direction.SELL
        assert trade.entry_price == 8085.0

    async def test_the_unfiltered_variant_takes_the_long_instead(self):
        """The contrast: without the filter the long opens on candle 2 and
        holds the one position slot for the rest of the day."""
        result = await run_impulsive(self.INTERLEAVED)

        assert len(result.trades) == 1
        assert result.trades[0].direction == Direction.BUY


class TestUnavailableMa50:
    """FR-G40: a day whose MA50 cannot be computed is not traded, in
    either direction - never silently unfiltered."""

    async def test_too_few_candles_is_a_no_trade(self):
        result = await run_mm50(
            ger_entry_candles(),
            series=h1_filter_series(ABOVE_MA50, count=MA50_PERIOD - 1),
        )

        assert result.status == DayStatus.NO_TRADE
        assert result.trades == []

    async def test_exactly_fifty_candles_is_enough(self):
        result = await run_mm50(
            ger_entry_candles(),
            series=h1_filter_series(ABOVE_MA50, count=MA50_PERIOD),
        )

        assert result.status == DayStatus.TRADED

    async def test_an_empty_series_is_a_no_trade(self):
        """What a failed fetch degrades to: visibly nothing, rather than a
        run that quietly took every trade unfiltered."""
        result = await run_mm50(ger_entry_candles(), series=[])

        assert result.status == DayStatus.NO_TRADE

    async def test_a_series_that_only_starts_after_10am_is_a_no_trade(self):
        """Candles exist, but none of them at or before the decision
        point - the count that matters is of usable candles, not of
        fetched ones."""
        series = [
            candle
            for candle in h1_filter_series(ABOVE_MA50)
            if candle.date is not None
        ]
        for candle in series:
            candle.date = candle.date + datetime.timedelta(days=1)

        result = await run_mm50(ger_entry_candles(), series=series)

        assert result.status == DayStatus.NO_TRADE


class TestLookaheadBoundary:
    """FR-G38/FR-G39: the H1 MA50 ends *with* the reference candle - which
    has closed by 10:00 - and reads nothing after it. The daily MA50 stops
    strictly before the day."""

    def test_the_h1_ma50_includes_the_reference_candle(self):
        # Exactly 50 candles, the newest being the reference candle
        # itself: excluding it would leave 49 - too few for an MA50 at
        # all - so getting a direction back at all proves it is counted.
        series = h1_filter_series(ABOVE_MA50, count=MA50_PERIOD)
        series[0].close = 8500.0

        side = allowed_side(
            MM50_H1_DEFINITION, series, TRADING_DATE, reference_close=8030.0
        )

        assert side == LONG  # 8030 > (49 * 8000 + 8500) / 50 = 8010

    def test_the_h1_ma50_ignores_candles_after_the_reference_hour(self):
        """The afternoon's candles exist in the series a range run
        fetched; a day must not be judged on hours it had not reached."""
        series = h1_filter_series(ABOVE_MA50, count=60)
        after = [
            Candle(
                lower=8500,
                higher=8500,
                open=8500,
                close=8500,
                ut=UnitTime.H1,
                date=series[0].date + datetime.timedelta(hours=offset),
            )
            for offset in range(1, 6)
        ]

        with_afternoon = allowed_side(
            MM50_H1_DEFINITION,
            after + series,
            TRADING_DATE,
            reference_close=8030.0,
        )
        without = allowed_side(
            MM50_H1_DEFINITION, series, TRADING_DATE, reference_close=8030.0
        )

        assert with_afternoon == without == LONG

    def test_the_daily_ma50_excludes_the_trading_day_itself(self):
        """The day's own daily candle closes at 22:00 - eleven hours of
        information the 10:00 decision could not have had."""
        series = daily_filter_series(ABOVE_MA50, count=50)
        today = Candle(
            lower=8500,
            higher=8500,
            open=8500,
            close=8500,
            ut=UnitTime.D,
            date=datetime.datetime(
                TRADING_DATE.year, TRADING_DATE.month, TRADING_DATE.day
            ),
        )

        side = allowed_side(
            MM50_DAILY_DEFINITION,
            [today] + series,
            TRADING_DATE,
            reference_close=8030.0,
        )

        # Counting today would make the MA50 (49*8000 + 8500)/50 = 8010
        # and flip the day short; excluding it leaves 8000 and a long.
        assert side == LONG


class TestDailyVariant:
    """FR-G38: same rule, daily candles."""

    async def test_above_the_daily_ma50_only_a_long_opens(self):
        result = await run_mm50(
            ger_entry_candles(),
            definition=MM50_DAILY_DEFINITION,
            series=daily_filter_series(ABOVE_MA50),
        )

        assert result.status == DayStatus.TRADED
        assert result.trades[0].direction == Direction.BUY

    async def test_below_the_daily_ma50_a_long_is_refused(self):
        result = await run_mm50(
            ger_entry_candles(),
            definition=MM50_DAILY_DEFINITION,
            series=daily_filter_series(BELOW_MA50),
        )

        assert result.status == DayStatus.NO_TRADE

    async def test_the_two_timeframes_can_disagree_on_the_same_day(self):
        """The whole point of shipping the pair: the day's allowed
        direction is attributable to the timeframe alone."""
        h1_result = await run_mm50(
            ger_entry_candles(),
            definition=MM50_H1_DEFINITION,
            series=h1_filter_series(ABOVE_MA50),
        )
        daily_result = await run_mm50(
            ger_entry_candles(),
            definition=MM50_DAILY_DEFINITION,
            series=daily_filter_series(BELOW_MA50),
        )

        assert h1_result.status == DayStatus.TRADED
        assert daily_result.status == DayStatus.NO_TRADE


class TestFilterOrdering:
    """FR-G43: the minimum-range filter is cheaper and needs no series, so
    it still decides first."""

    async def test_a_narrow_day_is_rejected_without_fetching_the_series(self):
        service = make_service(
            [h1_candle(higher=8050.0, lower=H1_LOW)], ger_entry_candles()
        )
        service.candles_service.build_candles.return_value = h1_filter_series(
            ABOVE_MA50
        )

        result = await service.evaluate_day(
            MM50_H1_DEFINITION, TRADING_DATE, GER_PARAMS
        )

        assert result.status == DayStatus.NO_TRADE
        service.candles_service.build_candles.assert_not_called()


class TestSeriesFetch:
    """The series is fetched once per range run, on the cash session."""

    async def test_the_h1_series_is_built_on_the_cash_session(self):
        """Not the definition's own 9:00-22:00 CFD session: a 50-period MA
        would span four sessions instead of six and stop being comparable
        with the daily variant."""
        service = make_service([h1_candle()], [])
        service.candles_service.build_candles.return_value = []

        await service.run_range(MM50_H1_DEFINITION, TRADING_DATE, TRADING_DATE)

        h1_calls = [
            call
            for call in service.candles_service.build_candles.call_args_list
            if call.args[1] == UnitTime.H1
        ]
        assert len(h1_calls) == 1
        assert isinstance(h1_calls[0].args[2], EUMarket)

    async def test_the_h1_series_reaches_past_the_first_day(self):
        service = make_service([h1_candle()], [])
        service.candles_service.build_candles.return_value = []
        start = datetime.date(2026, 5, 4)

        await service.run_range(MM50_H1_DEFINITION, start, TRADING_DATE)

        h1_call = [
            call
            for call in service.candles_service.build_candles.call_args_list
            if call.args[1] == UnitTime.H1
        ][0]
        assert h1_call.args[3] >= H1_CANDLES_LEAD_IN
        # The anchor must sit past the last day, or its own 9:00-10:00
        # candle - the one the decision is taken on - is not in the series.
        assert h1_call.args[4].date() > TRADING_DATE

    async def test_the_daily_variant_reuses_the_regime_series(self):
        """The daily candles the run already fetches for mm50_slope /
        adx14 / overnight_gap are the same series the filter needs."""
        service = make_service([h1_candle()], [])
        service.candles_service.build_candles.return_value = (
            daily_filter_series(ABOVE_MA50, count=80)
        )

        await service.run_range(
            MM50_DAILY_DEFINITION, TRADING_DATE, TRADING_DATE
        )

        assert service.candles_service.build_candles.call_count == 1

    async def test_a_definition_without_the_filter_fetches_no_h1_series(self):
        service = make_service([h1_candle()], [])
        service.candles_service.build_candles.return_value = []

        await service.run_range(
            IMPULSIVE_DEFINITION, TRADING_DATE, TRADING_DATE
        )

        h1_calls = [
            call
            for call in service.candles_service.build_candles.call_args_list
            if call.args[1] == UnitTime.H1
        ]
        assert h1_calls == []


class TestDefinitionValidation:
    """FR-G38: only two timeframes have a series the filter can build."""

    @pytest.mark.parametrize(
        "ut", [UnitTime.M5, UnitTime.M15, UnitTime.H4, UnitTime.W]
    )
    def test_an_unsupported_timeframe_is_rejected(self, ut):
        with pytest.raises(ValueError, match="ma50_direction_filter"):
            BacktestDefinition(
                code="X",
                name="x",
                display_name="x",
                instrument="GER40.I",
                ma50_direction_filter=ut,
            )

    @pytest.mark.parametrize("ut", [UnitTime.H1, UnitTime.D])
    def test_the_two_supported_timeframes_are_accepted(self, ut):
        definition = BacktestDefinition(
            code="X",
            name="x",
            display_name="x",
            instrument="GER40.I",
            ma50_direction_filter=ut,
        )

        assert definition.ma50_direction_filter == ut

    def test_a_definition_without_the_filter_keeps_both_directions(self):
        assert IMPULSIVE_DEFINITION.ma50_direction_filter is None
