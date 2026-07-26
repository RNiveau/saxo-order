"""Position sizing: how a closed position's points are computed and which
bucket the run summary files it under."""

from api.services.backtest.lots import SINGLE_LOT, Outcome, TwoLot
from api.services.backtest.rules import build_lot_model
from model import BacktestDefinition
from model.enum import ExitReason
from tests.api.services.backtest.helpers import closed_trade

TWO_LOT = TwoLot(first_target_fraction=0.5)


class TestSingleLotPoints:
    def test_points_are_the_exit_leg(self):
        assert SINGLE_LOT.total_points(35, 0, False) == 35
        assert SINGLE_LOT.total_points(-50, 0, False) == -50

    def test_banked_points_are_ignored(self):
        """A single lot never banks a partial fill, so a stray banked
        value must not leak into its result."""
        assert SINGLE_LOT.total_points(10, 999, True) == 10

    def test_has_no_first_target(self):
        assert SINGLE_LOT.first_target_level(8050, 8000) is None


class TestTwoLotPoints:
    def test_both_lots_exit_together_before_the_first_target(self):
        """The "SL is x2" loss: both lots are still open, so the leg
        counts twice."""
        assert TWO_LOT.total_points(-165, 0, False) == -330

    def test_runner_leg_is_added_to_the_banked_first_lot(self):
        assert TWO_LOT.total_points(15, 25, True) == 40

    def test_runner_stopped_at_break_even_keeps_the_banked_gain(self):
        assert TWO_LOT.total_points(0, 25, True) == 25

    def test_first_target_is_the_fraction_across_the_range(self):
        assert TWO_LOT.first_target_level(8050, 8000) == 8025
        assert TwoLot(0.25).first_target_level(8050, 8000) == 8012.5


class TestSingleLotClassification:
    def test_break_even_exit_is_a_break_even_whatever_the_points(self):
        trade = closed_trade(10, ExitReason.BREAK_EVEN)
        assert SINGLE_LOT.classify(trade) == Outcome.BREAK_EVEN

    def test_positive_points_win(self):
        trade = closed_trade(5, ExitReason.TAKE_PROFIT)
        assert SINGLE_LOT.classify(trade) == Outcome.WIN

    def test_flat_end_of_day_is_a_loss(self):
        """Preserved from the original bucketing: outside a break-even
        exit, only strictly positive points count as a win."""
        trade = closed_trade(0, ExitReason.END_OF_DAY)
        assert SINGLE_LOT.classify(trade) == Outcome.LOSS


class TestTwoLotClassification:
    """FR-G08: classified by the sign of net points, because a
    TP1-then-break-even runner closes BREAK_EVEN while banking a gain."""

    def test_break_even_exit_with_a_net_gain_is_a_win(self):
        trade = closed_trade(10, ExitReason.BREAK_EVEN)
        assert TWO_LOT.classify(trade) == Outcome.WIN

    def test_negative_points_lose(self):
        trade = closed_trade(-330, ExitReason.STOP_LOSS)
        assert TWO_LOT.classify(trade) == Outcome.LOSS

    def test_only_a_genuinely_flat_position_is_a_break_even(self):
        trade = closed_trade(0, ExitReason.BREAK_EVEN)
        assert TWO_LOT.classify(trade) == Outcome.BREAK_EVEN


class TestBuildLotModel:
    def _definition(self, **kwargs):
        return BacktestDefinition(
            code="X",
            name="x",
            display_name="x",
            instrument="FRA40.I",
            **kwargs,
        )

    def test_plain_definition_is_single_lot(self):
        assert build_lot_model(self._definition()) is SINGLE_LOT

    def test_double_take_profit_with_a_fraction_is_two_lot(self):
        definition = self._definition(
            double_take_profit=True, first_target_fraction=0.5
        )
        assert build_lot_model(definition) == TwoLot(0.5)

    def test_double_take_profit_without_a_fraction_degrades_to_one_lot(self):
        """BacktestDefinition rejects this combination outright, so it is
        only reachable by mutating a definition after construction - but
        build_lot_model still refuses to build a two-lot position whose
        TP1 could never fill."""
        definition = self._definition(
            double_take_profit=True, first_target_fraction=0.5
        )
        definition.first_target_fraction = None
        assert build_lot_model(definition) is SINGLE_LOT

    def test_ger40_ships_as_two_lot(self):
        from api.services.backtest import get_definition

        assert build_lot_model(get_definition("G9H")) == TwoLot(0.5)
