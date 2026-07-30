"""The combo engine, one test per acceptance scenario of spec 026 US1.

The band levels are patched rather than shaped out of real candles: the
strategy's job is what it does *with* a target, and driving the mm20 to a
chosen price through 20 synthetic closes would obscure every test with
arithmetic that `test_bands.py` already covers.
"""

import datetime
from unittest.mock import MagicMock

import pytest

from api.services.backtest.bands import BandLevels
from api.services.backtest.combo_strategy import ComboStrategy
from api.services.backtest.side import LONG, SHORT
from api.services.backtest.signals import Entry
from client.aws_client import DynamoDBClient
from model import (
    BacktestDefinition,
    BacktestParameters,
    Candle,
    DaxCfdMarket,
    UnitTime,
)
from model.enum import ExitReason
from services.candles_service import CandlesService

BANDS = "api.services.backtest.combo_strategy.levels"
BANDS_STRICT = "api.services.backtest.combo_strategy.levels_or_raise"
SEARCH = "api.services.backtest.combo_strategy.ComboEntrySearch"

DEFINITION = BacktestDefinition(
    code="C15M",
    name="Combo GER40 15m",
    display_name="GER40 Combo 15m",
    instrument="GER40.I",
    market=DaxCfdMarket(),
    unit_time=UnitTime.M15,
    combo_entry=True,
    double_take_profit=True,
    default_parameters=BacktestParameters(stop_loss_points=50),
)
PARAMS = BacktestParameters(stop_loss_points=50)

# mm20 at 8060 (TP1), upper band at 8120 (TP2 for a long), lower at 7940.
LEVELS = BandLevels(mm20=8060.0, upper=8120.0, bottom=7940.0)


def strategy():
    return ComboStrategy(
        MagicMock(spec=CandlesService), MagicMock(spec=DynamoDBClient)
    )


def candle(lower, higher, open_, close, day=2, hour=10, minute=0):
    return Candle(
        lower=lower,
        higher=higher,
        open=open_,
        close=close,
        ut=UnitTime.M15,
        date=datetime.datetime(2026, 6, day, hour, minute),
    )


class FixedSearch:
    """Yields a prepared entry on a chosen candle index and nothing
    after, standing in for the signal state machine."""

    entries: dict = {}

    def __init__(self):
        self.index = -1

    def reset(self):
        pass

    def feed(self, candle, window):
        self.index += 1
        return type(self).entries.get(self.index)


def run(mocker, candles, entries, levels=LEVELS, definition=DEFINITION):
    FixedSearch.entries = entries
    mocker.patch(SEARCH, FixedSearch)
    mocker.patch(BANDS, return_value=levels)
    mocker.patch(BANDS_STRICT, return_value=levels)
    return strategy()._run(definition, PARAMS, candles)


def long_entry(signal_candle, price=8000.0):
    return Entry(price=price, side=LONG, signal_candle=signal_candle)


class TestEntryAndStop:
    def test_the_stop_sits_50_below_the_signal_candle_low(self, mocker):
        """FR-C06: measured from the candle the indicator fired on, and
        from its low - not from the entry price."""
        signal_candle = candle(7950, 8010, 7960, 8000)
        candles = [
            signal_candle,
            candle(7900, 8010, 8000, 7890, minute=15),
        ]
        trades = run(mocker, candles, {0: long_entry(signal_candle)})
        assert len(trades) == 1
        # 7950 - 50 = 7900, and both lots exit there.
        assert trades[0].exit_price == 7900.0
        assert trades[0].exit_reason == ExitReason.STOP_LOSS

    def test_both_lots_stop_out_together_before_tp1(self, mocker):
        """FR-C05's "SL is x2": the leg counts twice while both lots are
        open."""
        signal_candle = candle(7950, 8010, 7960, 8000)
        candles = [
            signal_candle,
            candle(7900, 8010, 8000, 7890, minute=15),
        ]
        trades = run(mocker, candles, {0: long_entry(signal_candle)})
        assert trades[0].points == pytest.approx(2 * (7900.0 - 8000.0))

    def test_an_entry_is_declined_when_tp1_is_already_past(self, mocker):
        """FR-C10: opening here would fire TP1 on the next candle, bank a
        loss as a take-profit and arm break-even before the stop could do
        anything."""
        signal_candle = candle(7950, 8010, 7960, 8000)
        candles = [signal_candle, candle(8050, 8100, 8060, 8090, minute=15)]
        trades = run(
            mocker,
            candles,
            {0: long_entry(signal_candle, price=8070.0)},
        )
        assert trades == []


class TestTargets:
    def test_tp1_at_the_mm20_banks_and_arms_break_even(self, mocker):
        """FR-C07/FR-C08: the first lot exits at the mm20 and the
        runner's stop moves to entry - nothing else arms it."""
        signal_candle = candle(7950, 8010, 7960, 8000)
        candles = [
            signal_candle,
            candle(8000, 8070, 8010, 8065, minute=15),
            candle(7990, 8010, 8060, 8000, minute=30),
        ]
        trades = run(mocker, candles, {0: long_entry(signal_candle)})
        assert len(trades) == 1
        # TP1 banked 60, runner closed at break-even.
        assert trades[0].exit_reason == ExitReason.BREAK_EVEN
        assert trades[0].points == pytest.approx(60.0)

    def test_tp2_at_the_opposite_band_closes_the_runner(self, mocker):
        signal_candle = candle(7950, 8010, 7960, 8000)
        candles = [
            signal_candle,
            candle(8000, 8070, 8010, 8065, minute=15),
            candle(8060, 8130, 8070, 8125, minute=30),
        ]
        trades = run(mocker, candles, {0: long_entry(signal_candle)})
        assert trades[0].exit_reason == ExitReason.TAKE_PROFIT
        # (8060 - 8000) + (8120 - 8000)
        assert trades[0].points == pytest.approx(180.0)

    def test_one_candle_reaching_both_targets_fills_both(self, mocker):
        signal_candle = candle(7950, 8010, 7960, 8000)
        candles = [
            signal_candle,
            candle(8000, 8130, 8010, 8125, minute=15),
        ]
        trades = run(mocker, candles, {0: long_entry(signal_candle)})
        assert len(trades) == 1
        assert trades[0].points == pytest.approx(180.0)

    def test_the_stop_wins_over_tp1_on_the_same_candle(self, mocker):
        """FR-C14, the conservative same-candle rule."""
        signal_candle = candle(7950, 8010, 7960, 8000)
        candles = [
            signal_candle,
            candle(7890, 8070, 8000, 7900, minute=15),
        ]
        trades = run(mocker, candles, {0: long_entry(signal_candle)})
        assert trades[0].exit_reason == ExitReason.STOP_LOSS
        assert trades[0].points == pytest.approx(-200.0)

    def test_the_targets_are_re_read_every_candle(self, mocker):
        """A target frozen at entry would exit at 8120 here; the moving
        one exits at the band the *exit* candle reports."""
        signal_candle = candle(7950, 8010, 7960, 8000)
        candles = [
            signal_candle,
            candle(8000, 8200, 8010, 8190, minute=15),
        ]
        moved = BandLevels(mm20=8060.0, upper=8150.0, bottom=7940.0)
        trades = run(mocker, candles, {0: long_entry(signal_candle)}, moved)
        assert trades[0].exit_price == 8150.0

    def test_a_mm20_below_entry_banks_tp1_at_a_loss(self, mocker):
        """Specified behavior, not a defect: FR-C10 only guards the
        entry, so a mm20 that crosses below afterwards fills TP1 for a
        loss and arms break-even on the runner."""
        signal_candle = candle(7950, 8010, 7960, 8000)
        candles = [
            signal_candle,
            candle(7960, 8010, 8000, 7970, minute=15),
        ]
        # Favorable at entry (so FR-C10 lets it open), crossed below by
        # the time the position is being managed.
        FixedSearch.entries = {0: long_entry(signal_candle)}
        mocker.patch(SEARCH, FixedSearch)
        mocker.patch(BANDS, return_value=LEVELS)
        mocker.patch(
            BANDS_STRICT,
            return_value=BandLevels(mm20=7980.0, upper=8120.0, bottom=7900.0),
        )

        trades = strategy()._run(DEFINITION, PARAMS, candles)

        assert len(trades) == 1
        # TP1 filled at 7980, banking -20; the runner then closed at its
        # break-even stop for roughly nothing.
        assert trades[0].points < 0


class TestShortMirror:
    def test_a_short_stops_50_above_the_signal_candle_high(self, mocker):
        signal_candle = candle(7990, 8050, 8040, 8000)
        candles = [
            signal_candle,
            candle(7990, 8110, 8000, 8105, minute=15),
        ]
        entry = Entry(price=8000.0, side=SHORT, signal_candle=signal_candle)
        levels = BandLevels(mm20=7940.0, upper=8120.0, bottom=7880.0)
        trades = run(mocker, candles, {0: entry}, levels)
        assert trades[0].exit_price == 8100.0
        assert trades[0].exit_reason == ExitReason.STOP_LOSS

    def test_a_short_runs_to_the_lower_band(self, mocker):
        signal_candle = candle(7990, 8050, 8040, 8000)
        candles = [
            signal_candle,
            candle(7930, 8010, 8000, 7935, minute=15),
            candle(7870, 7940, 7930, 7875, minute=30),
        ]
        entry = Entry(price=8000.0, side=SHORT, signal_candle=signal_candle)
        levels = BandLevels(mm20=7940.0, upper=8120.0, bottom=7880.0)
        trades = run(mocker, candles, {0: entry}, levels)
        assert trades[0].exit_reason == ExitReason.TAKE_PROFIT
        # (8000 - 7940) + (8000 - 7880)
        assert trades[0].points == pytest.approx(180.0)


class TestHolding:
    def test_a_position_carries_across_a_day_boundary(self, mocker):
        """FR-C11: no end-of-day close. The position opened on the 2nd is
        the same object that exits on the 3rd."""
        signal_candle = candle(7950, 8010, 7960, 8000)
        candles = [
            signal_candle,
            candle(7980, 8010, 8000, 7990, hour=21, minute=45),
            candle(8000, 8130, 8010, 8125, day=3, hour=9),
        ]
        trades = run(mocker, candles, {0: long_entry(signal_candle)})
        assert len(trades) == 1
        assert trades[0].entry_time.day == 2
        assert trades[0].exit_time.day == 3

    def test_a_signal_while_in_a_position_is_ignored(self, mocker):
        """FR-C09: one position at a time, never reversed, never added
        to. The second entry is offered and must not be taken."""
        signal_candle = candle(7950, 8010, 7960, 8000)
        second = candle(7990, 8020, 8000, 8010, minute=15)
        candles = [
            signal_candle,
            second,
            candle(8000, 8130, 8010, 8125, minute=30),
        ]
        trades = run(
            mocker,
            candles,
            {0: long_entry(signal_candle), 1: long_entry(second)},
        )
        assert len(trades) == 1

    def test_a_position_open_at_the_end_closes_as_end_of_run(self, mocker):
        """FR-C12: the range's total is never missing an open trade."""
        signal_candle = candle(7950, 8010, 7960, 8000)
        candles = [
            signal_candle,
            candle(7990, 8020, 8000, 8010, minute=15),
        ]
        trades = run(mocker, candles, {0: long_entry(signal_candle)})
        assert len(trades) == 1
        assert trades[0].exit_reason == ExitReason.END_OF_RUN
        assert trades[0].exit_price == 8010.0

    def test_the_search_resumes_after_a_position_closes(self, mocker):
        signal_candle = candle(7950, 8010, 7960, 8000)
        third = candle(7950, 8010, 7960, 8000, minute=30)
        candles = [
            signal_candle,
            candle(7890, 8010, 8000, 7895, minute=15),
            third,
            candle(7890, 8010, 8000, 7895, minute=45),
        ]
        trades = run(
            mocker,
            candles,
            {0: long_entry(signal_candle), 2: long_entry(third)},
        )
        assert len(trades) == 2


def numbered(count):
    """A series whose candles differ only by index - the window tests
    care about order and length, not prices or times."""
    return [
        Candle(
            lower=0,
            higher=i,
            open=i,
            close=i,
            ut=UnitTime.M15,
            date=datetime.datetime(2026, 6, 2, 10, 0)
            + datetime.timedelta(minutes=15 * i),
        )
        for i in range(count)
    ]


class TestWindow:
    def test_the_window_is_newest_first(self):
        """CLAUDE.md's ordering rule, and what combo and bollinger_bands
        both assume."""
        series = numbered(5)
        window = ComboStrategy._window(series, 4)
        assert window[0] is series[4]
        assert window[-1] is series[0]

    def test_it_is_bounded_so_cost_does_not_grow_with_the_run(self):
        from api.services.backtest.combo_strategy import EVALUATION_WINDOW

        series = numbered(EVALUATION_WINDOW + 50)
        window = ComboStrategy._window(series, len(series) - 1)
        assert len(window) == EVALUATION_WINDOW

    def test_an_early_candle_gets_whatever_history_exists(self):
        series = numbered(5)
        assert len(ComboStrategy._window(series, 2)) == 3


class TestNoBands:
    def test_no_entry_is_opened_before_the_bands_exist(self, mocker):
        """FR-C13: the warm-up candles at the head of a run produce no
        levels, and an entry there would have no targets."""
        signal_candle = candle(7950, 8010, 7960, 8000)
        candles = [signal_candle, candle(7990, 8020, 8000, 8010, minute=15)]
        trades = run(mocker, candles, {0: long_entry(signal_candle)}, None)
        assert trades == []

    def test_the_daily_regime_columns_survive_a_fetch_failure(self, mocker):
        from utils.exception import SaxoException

        engine = strategy()
        engine.candles_service.build_candles.side_effect = SaxoException(
            "no data"
        )
        assert (
            engine._fetch_daily_candles(
                DEFINITION,
                datetime.date(2026, 6, 1),
                datetime.date(2026, 6, 5),
            )
            == []
        )
