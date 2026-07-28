"""The two-lot impulsive variant (spec 025 addendum 3, FR-G24-FR-G31).

Same H1 range as the single-lot impulsive tests (8000-8100) and the same
8015 long entry, so the two are directly comparable. Here TP1 is 8090 -
the level G9HIC exits at outright - and the runner targets 8190, a hundred
points beyond it and outside the H1 range. Break-even arms at 8065, and on
the TP1 fill regardless.
"""

import datetime

from model.enum import DayStatus, Direction, ExitReason
from tests.api.services.backtest.helpers import (
    ger_entry_candles,
    m5_candle,
    run_impulsive,
    run_impulsive_double,
)

TP1 = 8090.0
TP2 = 8190.0
ENTRY = 8015.0


def tp1_fill_candle(offset=3):
    """Reaches TP1 (8090) without reaching TP2, so the first lot banks and
    the runner arms break-even."""
    return m5_candle(offset, 8020, 8095, 8015, 8090)


class TestBothTargets:
    async def test_tp1_then_tp2_sums_both_legs(self):
        candles = ger_entry_candles() + [
            tp1_fill_candle(),
            m5_candle(4, 8090, 8195, 8085, 8190),
        ]

        result = await run_impulsive_double(candles)

        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.TAKE_PROFIT
        assert trade.exit_price == TP2
        # (8090 - 8015) + (8190 - 8015)
        assert trade.points == 250.0

    async def test_the_runner_target_sits_outside_the_h1_range(self):
        """The point of the variant: 8190 is 90 points above the 8100 H1
        high, a level the range-bound variants can never reach."""
        candles = ger_entry_candles() + [
            tp1_fill_candle(),
            m5_candle(4, 8090, 8195, 8085, 8190),
        ]

        result = await run_impulsive_double(candles)

        assert result.trades[0].exit_price > result.h1_high


class TestRunnerProtection:
    async def test_tp1_then_break_even_keeps_the_banked_lot(self):
        candles = ger_entry_candles() + [
            tp1_fill_candle(),
            m5_candle(4, 8090, 8092, 8010, 8020),  # back through entry
        ]

        result = await run_impulsive_double(candles)

        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.BREAK_EVEN
        assert trade.exit_price == ENTRY
        assert trade.points == 75.0

    async def test_an_impulse_after_tp1_loses_to_the_break_even_stop(self):
        """FR-G27: TP1 arms break-even, and an armed stop leads the chain -
        so the impulse rule can only ever protect the pre-TP1 position."""
        candles = ger_entry_candles() + [
            tp1_fill_candle(),
            # Impulsive and below the H1 low, but break-even is armed.
            m5_candle(4, 8090, 8092, 7985, 7990),
        ]

        result = await run_impulsive_double(candles)

        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.BREAK_EVEN
        assert trade.exit_price == ENTRY
        assert trade.points == 75.0


class TestImpulseBeforeTp1:
    async def test_an_impulse_closes_both_lots_at_twice_the_leg(self):
        candles = ger_entry_candles() + [
            m5_candle(3, 8010, 8012, 7935, 7940),  # impulsive, below 8000
        ]

        result = await run_impulsive_double(candles)

        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.STOP_LOSS
        assert trade.exit_price == 7940.0
        # -75 on each of the two open lots
        assert trade.points == -150.0

    async def test_the_fifty_point_trigger_still_arms_before_tp1(self):
        candles = ger_entry_candles() + [
            m5_candle(3, 8015, 8070, 8010, 8060),  # high 8070 >= 8065
            m5_candle(4, 8060, 8062, 7985, 7990),  # impulsive, but armed
        ]

        result = await run_impulsive_double(candles)

        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.BREAK_EVEN
        assert trade.exit_price == ENTRY
        # Both lots still open at a flat exit: 2 x 0.
        assert trade.points == 0.0


class TestEndOfDay:
    async def test_both_lots_close_at_the_last_candle(self):
        candles = ger_entry_candles() + [
            m5_candle(3, 8015, 8020, 8010, 8018),
            m5_candle(143, 8018, 8026, 8016, 8024),
        ]

        result = await run_impulsive_double(candles)

        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.END_OF_DAY
        assert trade.exit_time == datetime.datetime(2026, 6, 2, 19, 55)
        # 2 x (8024 - 8015)
        assert trade.points == 18.0

    async def test_the_runner_alone_closes_at_the_last_candle(self):
        candles = ger_entry_candles() + [
            tp1_fill_candle(),
            m5_candle(143, 8090, 8095, 8085, 8092),
        ]

        result = await run_impulsive_double(candles)

        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.END_OF_DAY
        # banked 75, plus the runner's 8092 - 8015
        assert trade.points == 152.0


class TestShortMirror:
    def _entry_candles(self):
        return [
            m5_candle(0, 8095, 8110, 8090, 8105),  # breach above 8100
            m5_candle(1, 8105, 8108, 8085, 8095),  # candidate, lower=8085
            m5_candle(2, 8090, 8095, 8080, 8085),  # breakout -> entry @8085
        ]

    async def test_tp1_at_8010_and_tp2_a_hundred_below(self):
        candles = self._entry_candles() + [
            m5_candle(3, 8080, 8082, 8005, 8008),  # reaches TP1 (8010)
            m5_candle(4, 8005, 8010, 7905, 7910),  # reaches TP2 (7910)
        ]

        result = await run_impulsive_double(candles)

        trade = result.trades[0]
        assert trade.direction == Direction.SELL
        assert trade.entry_price == 8085.0
        assert trade.exit_reason == ExitReason.TAKE_PROFIT
        assert trade.exit_price == 7910.0
        # (8085 - 8010) + (8085 - 7910)
        assert trade.points == 250.0


class TestEntryParityWithTheSingleLotVariant:
    """SC-G15: given the same state, both variants accept the same
    breakouts - the two-lot entry filter adds no constraint here, because
    TP1 is the ordinary take-profit G9HIC already checks against.

    This is parity *per breakout*, not over a day: the runner holds the
    one-position-at-a-time slot until TP2, break-even or the close, so on
    a day with several setups G9HIC can take entries G9HICD is still
    holding through. These candles are arranged so both are flat before
    the second setup, which is what isolates the property under test.
    """

    CANDLES = [
        *ger_entry_candles(),
        m5_candle(3, 8015, 8095, 8010, 8090),
        m5_candle(4, 8090, 8092, 8010, 8020),
        m5_candle(10, 8005, 8010, 7990, 7995),
        m5_candle(11, 8000, 8015, 7995, 8010),
        m5_candle(12, 8010, 8020, 8005, 8015),
        m5_candle(13, 8010, 8012, 7935, 7940),
    ]

    async def test_the_same_positions_open_at_the_same_prices(self):
        single = await run_impulsive(self.CANDLES)
        double = await run_impulsive_double(self.CANDLES)

        assert single.status == DayStatus.TRADED
        assert [
            (trade.entry_time, trade.entry_price, trade.direction)
            for trade in single.trades
        ] == [
            (trade.entry_time, trade.entry_price, trade.direction)
            for trade in double.trades
        ]

    async def test_but_the_exits_and_points_differ(self):
        single = await run_impulsive(self.CANDLES)
        double = await run_impulsive_double(self.CANDLES)

        # The single lot takes 8090 as its whole take-profit and is done;
        # the two-lot banks it as TP1 and gives the runner back at
        # break-even. The losing trade costs twice as much at two lots.
        assert [trade.points for trade in single.trades] == [75.0, -75.0]
        assert [trade.points for trade in double.trades] == [75.0, -150.0]


class TestTrailToFirstTarget:
    """FR-G32: once the runner is 50 points past TP1 (8140), its stop
    moves up from break-even (8015) to TP1 (8090)."""

    TRAIL_TRIGGER = 8140.0

    async def test_the_runner_falls_back_to_tp1_not_to_break_even(self):
        candles = ger_entry_candles() + [
            tp1_fill_candle(),
            m5_candle(4, 8090, 8145, 8085, 8140),  # reaches TP1 + 50
            m5_candle(5, 8140, 8142, 8080, 8085),  # back through TP1
        ]

        result = await run_impulsive_double(candles)

        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.TRAILING_STOP
        assert trade.exit_price == TP1
        # Banked TP1 plus the runner matching it: 2 x (8090 - 8015).
        assert trade.points == 150.0

    async def test_without_the_trigger_it_still_falls_back_to_break_even(self):
        candles = ger_entry_candles() + [
            tp1_fill_candle(),
            m5_candle(4, 8090, 8135, 8085, 8130),  # 8135 < 8140, no trail
            m5_candle(5, 8130, 8132, 8010, 8020),
        ]

        result = await run_impulsive_double(candles)

        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.BREAK_EVEN
        assert trade.exit_price == ENTRY
        assert trade.points == 75.0

    async def test_the_trail_does_not_prevent_tp2_on_a_later_candle(self):
        candles = ger_entry_candles() + [
            tp1_fill_candle(),
            m5_candle(4, 8090, 8145, 8085, 8140),  # arms the trail
            m5_candle(5, 8140, 8195, 8135, 8190),  # reaches TP2, no retrace
        ]

        result = await run_impulsive_double(candles)

        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.TAKE_PROFIT
        assert trade.points == 250.0

    async def test_the_trailed_stop_wins_when_one_candle_hits_both(self):
        """FR-009 applied to the trail: a candle that retraces to TP1 and
        also reaches TP2 resolves conservatively as the stop, because Stop
        leads the chain. So the trail can cost the runner a take-profit -
        250 points become 150 - which is a real cost of the rule and is
        recorded here rather than left to be rediscovered."""
        candles = ger_entry_candles() + [
            tp1_fill_candle(),
            m5_candle(4, 8090, 8145, 8085, 8140),  # arms the trail
            m5_candle(5, 8140, 8195, 8080, 8190),  # dips to 8080 AND TP2
        ]

        result = await run_impulsive_double(candles)

        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.TRAILING_STOP
        assert trade.exit_price == TP1
        assert trade.points == 150.0

    async def test_arming_and_falling_back_on_one_candle_does_not_close(self):
        """Like break-even arming, the trail applies from the *next*
        candle - so a spike to 8145 closing back at 8085 arms it and
        leaves the position open."""
        candles = ger_entry_candles() + [
            tp1_fill_candle(),
            m5_candle(4, 8090, 8145, 8080, 8085),  # spike and back
            # Stays clear of the now-trailed 8090 stop, so the position
            # survives to the close - which is the point: the arming
            # candle itself dipped to 8080 and did not close it.
            m5_candle(5, 8095, 8100, 8092, 8098),
        ]

        result = await run_impulsive_double(candles)

        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.END_OF_DAY
        assert trade.exit_price == 8098.0
        # banked 75, plus the runner's 8098 - 8015
        assert trade.points == 158.0

    async def test_no_trail_before_the_first_lot_fills(self):
        """8140 is past TP1, but TP1 has not been reached on the way -
        impossible for a long, so this asserts the guard directly: a
        position whose first lot has not filled never trails."""
        candles = ger_entry_candles() + [
            m5_candle(3, 8015, 8020, 8010, 8018),
            m5_candle(4, 8018, 8022, 8010, 8020),
        ]

        result = await run_impulsive_double(candles)

        assert result.trades[0].exit_reason == ExitReason.END_OF_DAY
        # Both lots still open: 2 x (8020 - 8015).
        assert result.trades[0].points == 10.0


class TestTrailShortMirror:
    async def test_the_short_runner_trails_down_to_tp1(self):
        candles = [
            m5_candle(0, 8095, 8110, 8090, 8105),
            m5_candle(1, 8105, 8108, 8085, 8095),
            m5_candle(2, 8090, 8095, 8080, 8085),  # entry @8085 short
            m5_candle(3, 8080, 8082, 8005, 8008),  # TP1 (8010) fills
            m5_candle(4, 8008, 8012, 7955, 7960),  # reaches TP1 - 50 (7960)
            m5_candle(5, 7960, 8015, 7958, 8012),  # back through TP1
        ]

        result = await run_impulsive_double(candles)

        trade = result.trades[0]
        assert trade.direction == Direction.SELL
        assert trade.exit_reason == ExitReason.TRAILING_STOP
        assert trade.exit_price == 8010.0
        # 2 x (8085 - 8010)
        assert trade.points == 150.0
