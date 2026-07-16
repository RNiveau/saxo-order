import datetime
from unittest.mock import MagicMock

from api.services.backtest_service import BacktestService
from model import BacktestDefinition, Candle, UnitTime
from model.enum import DayStatus, ExitReason
from services.candles_service import CandlesService
from utils.exception import SaxoException

DEFINITION = BacktestDefinition(
    code="B9H",
    name="Bougie de 9h",
    display_name="CAC40 Bougie de 9h",
    instrument="FRA40.I",
)
TRADING_DATE = datetime.date(2026, 6, 2)

H1_HIGH = 8050.0
H1_LOW = 8000.0


def h1_candle(higher=H1_HIGH, lower=H1_LOW):
    return Candle(
        lower=lower,
        higher=higher,
        open=8020.0,
        close=8030.0,
        ut=UnitTime.H1,
        date=datetime.datetime(2026, 6, 2, 7, 0),
    )


def m5_candle(minute_offset, open, higher, lower, close):
    return Candle(
        lower=lower,
        higher=higher,
        open=open,
        close=close,
        ut=UnitTime.M5,
        date=datetime.datetime(2026, 6, 2, 8, 0)
        + datetime.timedelta(minutes=5 * minute_offset),
    )


def make_service(h1_candles, m5_candles, raise_on_h1=False, raise_on_m5=False):
    candles_service = MagicMock(spec=CandlesService)

    def side_effect(code, ut, horizon, start, end):
        if ut == UnitTime.H1:
            if raise_on_h1:
                raise SaxoException("boom")
            return h1_candles
        if raise_on_m5:
            raise SaxoException("boom")
        return m5_candles

    candles_service.get_candles_in_window.side_effect = side_effect
    return BacktestService(candles_service)


class TestEvaluateDayNoData:
    def test_missing_h1_candle_returns_no_data(self):
        service = make_service(h1_candles=[], m5_candles=[])
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.NO_DATA
        assert result.trades == []
        assert result.h1_high is None
        assert result.h1_low is None

    def test_h1_fetch_raising_returns_no_data(self):
        service = make_service(h1_candles=[], m5_candles=[], raise_on_h1=True)
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.NO_DATA


class TestEvaluateDayNoTrade:
    def test_no_breakout_below_h1_low(self):
        candles = [
            m5_candle(0, 8010, 8020, 8005, 8015),
            m5_candle(1, 8015, 8025, 8010, 8020),
        ]
        service = make_service([h1_candle()], candles)
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.NO_TRADE
        assert result.trades == []
        assert result.h1_high == H1_HIGH
        assert result.h1_low == H1_LOW

    def test_breakdown_without_confirmed_reversal(self):
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),  # breach, no close-back
            m5_candle(1, 7995, 8000, 7985, 7990),  # still below h1_low
        ]
        service = make_service([h1_candle()], candles)
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.NO_TRADE
        assert result.trades == []


class TestEvaluateDayExits:
    def test_stop_loss_exit(self):
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),  # breach
            m5_candle(1, 8000, 8015, 7995, 8010),  # confirm -> entry @8010
            m5_candle(2, 8005, 8010, 7950, 7955),  # SL: low<=7960, no gap
        ]
        service = make_service([h1_candle()], candles)
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.TRADED
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.entry_price == 8010
        assert trade.exit_reason == ExitReason.STOP_LOSS
        assert trade.exit_price == 7960
        assert trade.points == -50

    def test_stop_loss_exit_with_gap(self):
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),
            m5_candle(1, 8000, 8015, 7995, 8010),  # entry @8010
            m5_candle(2, 7900, 7910, 7850, 7880),  # gap below 7960
        ]
        service = make_service([h1_candle()], candles)
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.STOP_LOSS
        assert trade.exit_price == 7900
        assert trade.points == -110

    def test_take_profit_exit(self):
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),
            m5_candle(1, 8000, 8015, 7995, 8010),  # entry @8010
            m5_candle(2, 8020, 8045, 8015, 8035),  # TP: high>=8040, no gap
        ]
        service = make_service([h1_candle()], candles)
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.TAKE_PROFIT
        assert trade.exit_price == 8040
        assert trade.points == 30

    def test_end_of_day_exit(self):
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),
            m5_candle(1, 8000, 8015, 7995, 8010),  # entry @8010
            m5_candle(2, 8012, 8020, 8005, 8015),  # last candle of the day
        ]
        service = make_service([h1_candle()], candles)
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.END_OF_DAY
        assert trade.exit_price == 8015
        assert trade.points == 5

    def test_break_even_exit(self):
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),
            m5_candle(1, 8000, 8015, 7995, 8010),  # entry @8010
            m5_candle(2, 8015, 8035, 8005, 8020),  # arms BE (>=8030)
            m5_candle(3, 8020, 8025, 8005, 8000),  # BE exit: low<=8010
        ]
        service = make_service([h1_candle()], candles)
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.BREAK_EVEN
        assert trade.exit_price == 8010
        assert trade.points == 0

    def test_multi_trade_day_reentry(self):
        candles = [
            # Trade 1: breach -> entry @8010 -> stop-loss
            m5_candle(0, 8005, 8010, 7990, 7995),
            m5_candle(1, 8000, 8015, 7995, 8010),
            m5_candle(2, 8005, 8010, 7950, 7955),
            # Trade 2: fresh breach -> entry -> end of day
            m5_candle(3, 7950, 7960, 7930, 7935),
            m5_candle(4, 7940, 8005, 7935, 8005),
            m5_candle(5, 8010, 8020, 8000, 8015),
        ]
        service = make_service([h1_candle()], candles)
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        assert result.status == DayStatus.TRADED
        assert len(result.trades) == 2
        assert result.trades[0].exit_reason == ExitReason.STOP_LOSS
        assert result.trades[1].entry_price == 8005
        assert result.trades[1].exit_reason == ExitReason.END_OF_DAY
        assert result.trades[1].exit_price == 8015


class TestEvaluateDaySameCandleEdgeCases:
    def test_stop_loss_priority_over_same_candle_be_arm(self):
        """A candle that would both breach the original stop-loss and
        reach the +20pt break-even-arm threshold resolves as a
        stop-loss using the pre-candle level, not a break-even arm."""
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),
            m5_candle(1, 8000, 8015, 7995, 8010),  # entry @8010
            # low breaches original stop (7960) AND high reaches +20 (8030)
            m5_candle(2, 8005, 8035, 7950, 8000),
        ]
        service = make_service([h1_candle()], candles)
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.STOP_LOSS
        assert trade.exit_price == 7960

    def test_arm_and_breach_round_trip_does_not_exit_same_candle(self):
        """A candle whose high reaches the +20pt arm threshold and whose
        low would also breach the not-yet-armed break-even level (but
        not the original stop) must not itself produce a break-even
        exit -- arming only takes effect on the next candle."""
        candles = [
            m5_candle(0, 8005, 8010, 7990, 7995),
            m5_candle(1, 8000, 8015, 7995, 8010),  # entry @8010
            # high reaches +20 (8030->8035) AND low dips to 8005 (<=entry
            # 8010, but > original stop 7960 -- no exit this candle)
            m5_candle(2, 8015, 8035, 8005, 8020),
            # now armed: low breaches the new stop (8010)
            m5_candle(3, 8020, 8025, 8005, 8000),
        ]
        service = make_service([h1_candle()], candles)
        result = service.evaluate_day(DEFINITION, TRADING_DATE)
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.exit_reason == ExitReason.BREAK_EVEN
        assert trade.exit_price == 8010
        assert trade.exit_time == candles[3].date
