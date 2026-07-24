import datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers.backtest import get_backtest_service
from api.services.backtest_service import BacktestService
from model import (
    BacktestParameters,
    BacktestRunResult,
    BacktestSummary,
    Candle,
    DayResult,
    DayResultSummary,
    Trade,
    UnitTime,
)
from model.enum import DayStatus, ExitReason

client = TestClient(app)


@pytest.fixture
def mock_backtest_service():
    service = MagicMock(spec=BacktestService)

    def override():
        return service

    app.dependency_overrides[get_backtest_service] = override
    yield service
    app.dependency_overrides.clear()


class TestGetBacktestDay:
    def test_traded_day_with_trades_and_candles_returns_200(
        self, mock_backtest_service
    ):
        mock_backtest_service.get_definition.return_value = MagicMock(
            code="B9H"
        )
        mock_backtest_service.evaluate_day.return_value = DayResult(
            date=datetime.date(2026, 6, 2),
            status=DayStatus.TRADED,
            h1_high=8050.0,
            h1_low=8000.0,
            candles=[
                Candle(
                    lower=8005.0,
                    higher=8013.0,
                    open=8009.5,
                    close=8012.0,
                    ut=UnitTime.M5,
                    date=datetime.datetime(2026, 6, 2, 8, 0),
                )
            ],
            trades=[
                Trade(
                    entry_time=datetime.datetime(2026, 6, 2, 8, 5),
                    entry_price=8010.0,
                    exit_time=datetime.datetime(2026, 6, 2, 9, 0),
                    exit_price=7960.0,
                    exit_reason=ExitReason.STOP_LOSS,
                    points=-50.0,
                )
            ],
        )

        response = client.get(
            "/api/backtest/day",
            params={"definition": "B9H", "date": "2026-06-02"},
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body["candles"]) == 1
        assert body["candles"][0]["higher"] == 8013.0
        assert len(body["trades"]) == 1
        assert body["trades"][0]["exit_reason"] == "stop_loss"
        assert body["trades"][0]["points"] == -50.0

    def test_invalid_date_format_returns_400(self, mock_backtest_service):
        mock_backtest_service.get_definition.return_value = MagicMock(
            code="B9H"
        )

        response = client.get(
            "/api/backtest/day",
            params={"definition": "B9H", "date": "not-a-date"},
        )

        assert response.status_code == 400
        mock_backtest_service.evaluate_day.assert_not_called()

    def test_future_date_returns_400(self, mock_backtest_service):
        mock_backtest_service.get_definition.return_value = MagicMock(
            code="B9H"
        )
        future_date = (
            datetime.date.today() + datetime.timedelta(days=30)
        ).isoformat()

        response = client.get(
            "/api/backtest/day",
            params={"definition": "B9H", "date": future_date},
        )

        assert response.status_code == 400
        mock_backtest_service.evaluate_day.assert_not_called()

    def test_today_not_yet_closed_returns_400(
        self, mock_backtest_service, mocker
    ):
        mock_backtest_service.get_definition.return_value = MagicMock(
            code="B9H"
        )
        mocker.patch(
            "api.routers.backtest.is_today_not_yet_closed", return_value=True
        )
        today = datetime.date.today().isoformat()

        response = client.get(
            "/api/backtest/day",
            params={"definition": "B9H", "date": today},
        )

        assert response.status_code == 400
        mock_backtest_service.evaluate_day.assert_not_called()

    def test_today_after_close_returns_200(
        self, mock_backtest_service, mocker
    ):
        mock_backtest_service.get_definition.return_value = MagicMock(
            code="B9H"
        )
        mocker.patch(
            "api.routers.backtest.is_today_not_yet_closed", return_value=False
        )
        today = datetime.date.today()
        mock_backtest_service.evaluate_day.return_value = DayResult(
            date=today, status=DayStatus.NO_TRADE, h1_high=8050, h1_low=8000
        )

        response = client.get(
            "/api/backtest/day",
            params={"definition": "B9H", "date": today.isoformat()},
        )

        assert response.status_code == 200

    def test_unknown_definition_returns_400(self, mock_backtest_service):
        mock_backtest_service.get_definition.return_value = None

        response = client.get(
            "/api/backtest/day",
            params={"definition": "NOPE", "date": "2026-06-02"},
        )

        assert response.status_code == 400
        mock_backtest_service.evaluate_day.assert_not_called()


class TestGetBacktestRun:
    def test_populated_range_returns_200(self, mock_backtest_service):
        mock_backtest_service.get_definition.return_value = MagicMock(
            code="B9H"
        )
        mock_backtest_service.run_range.return_value = BacktestRunResult(
            summary=BacktestSummary(
                definition_code="B9H",
                start_date=datetime.date(2026, 6, 1),
                end_date=datetime.date(2026, 6, 2),
                number_of_days=2,
                number_of_trades=1,
                number_of_winning_positions=1,
                number_of_losing_positions=0,
                number_of_be=0,
                average_win=30.0,
                average_loss=None,
                final_result=30.0,
            ),
            days=[
                DayResultSummary(
                    date=datetime.date(2026, 6, 2),
                    status=DayStatus.TRADED,
                    trade_count=1,
                    points=30.0,
                )
            ],
        )

        response = client.get(
            "/api/backtest/run",
            params={
                "definition": "B9H",
                "start_date": "2026-06-01",
                "end_date": "2026-06-02",
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["summary"]["number_of_trades"] == 1
        assert body["summary"]["average_loss"] is None
        assert len(body["days"]) == 1
        assert body["days"][0]["points"] == 30.0

    def test_end_before_start_returns_400(self, mock_backtest_service):
        mock_backtest_service.get_definition.return_value = MagicMock(
            code="B9H"
        )

        response = client.get(
            "/api/backtest/run",
            params={
                "definition": "B9H",
                "start_date": "2026-06-10",
                "end_date": "2026-06-01",
            },
        )

        assert response.status_code == 400
        mock_backtest_service.run_range.assert_not_called()

    def test_unknown_definition_returns_400(self, mock_backtest_service):
        mock_backtest_service.get_definition.return_value = None

        response = client.get(
            "/api/backtest/run",
            params={
                "definition": "NOPE",
                "start_date": "2026-06-01",
                "end_date": "2026-06-02",
            },
        )

        assert response.status_code == 400
        mock_backtest_service.run_range.assert_not_called()


class TestGetBacktestDayCsv:
    def test_traded_day_returns_csv(self, mock_backtest_service):
        mock_backtest_service.get_definition.return_value = MagicMock(
            code="B9H"
        )
        mock_backtest_service.evaluate_day.return_value = DayResult(
            date=datetime.date(2026, 6, 2),
            status=DayStatus.TRADED,
            h1_high=8050.0,
            h1_low=8000.0,
            candles=[
                Candle(
                    lower=8005.0,
                    higher=8013.0,
                    open=8009.5,
                    close=8012.0,
                    ut=UnitTime.M5,
                    date=datetime.datetime(2026, 6, 2, 8, 0),
                )
            ],
            trades=[
                Trade(
                    entry_time=datetime.datetime(2026, 6, 2, 8, 5),
                    entry_price=8010.0,
                    exit_time=datetime.datetime(2026, 6, 2, 9, 0),
                    exit_price=7960.0,
                    exit_reason=ExitReason.STOP_LOSS,
                    points=-50.0,
                )
            ],
        )

        response = client.get(
            "/api/backtest/day/csv",
            params={"definition": "B9H", "date": "2026-06-02"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert (
            'attachment; filename="backtest-B9H-2026-06-02.csv"'
            in response.headers["content-disposition"]
        )
        body = response.text
        assert "parameter,value" in body
        assert "stop_loss_points,50" in body
        assert "h1_high,h1_low" in body
        assert "8050.0,8000.0" in body
        assert "2026-06-02T08:00:00" in body
        assert "stop_loss" in body

    def test_invalid_date_format_returns_400(self, mock_backtest_service):
        mock_backtest_service.get_definition.return_value = MagicMock(
            code="B9H"
        )

        response = client.get(
            "/api/backtest/day/csv",
            params={"definition": "B9H", "date": "not-a-date"},
        )

        assert response.status_code == 400
        mock_backtest_service.evaluate_day.assert_not_called()

    def test_no_data_day_returns_blank_h1_and_empty_blocks(
        self, mock_backtest_service
    ):
        """Pins the empty-block contract for a no_data day: h1_high/
        h1_low render as blank cells (not "None"), and the candles/
        trades blocks are present but have no rows."""
        mock_backtest_service.get_definition.return_value = MagicMock(
            code="B9H"
        )
        mock_backtest_service.evaluate_day.return_value = DayResult(
            date=datetime.date(2026, 6, 2), status=DayStatus.NO_DATA
        )

        response = client.get(
            "/api/backtest/day/csv",
            params={"definition": "B9H", "date": "2026-06-02"},
        )

        assert response.status_code == 200
        assert response.text == (
            "parameter,value\r\n"
            "stop_loss_points,50\r\n"
            "take_profit_offset_points,10\r\n"
            "break_even_trigger_points,20\r\n"
            "max_entry_distance_points,20\r\n"
            "\r\n"
            "h1_high,h1_low\r\n"
            ",\r\n"
            "\r\n"
            "date,open,higher,lower,close\r\n"
            "\r\n"
            "entry_time,entry_price,exit_time,exit_price,"
            "exit_reason,direction,points\r\n"
        )


class TestGetBacktestRunCsv:
    def test_populated_range_returns_csv(self, mock_backtest_service):
        mock_backtest_service.get_definition.return_value = MagicMock(
            code="B9H"
        )
        mock_backtest_service.run_range.return_value = BacktestRunResult(
            summary=BacktestSummary(
                definition_code="B9H",
                start_date=datetime.date(2026, 6, 1),
                end_date=datetime.date(2026, 6, 2),
                number_of_days=2,
                number_of_trades=1,
                number_of_winning_positions=1,
                number_of_losing_positions=0,
                number_of_be=0,
                average_win=30.0,
                average_loss=None,
                final_result=30.0,
            ),
            days=[
                DayResultSummary(
                    date=datetime.date(2026, 6, 2),
                    status=DayStatus.TRADED,
                    trade_count=1,
                    points=30.0,
                    h1_high=8050.0,
                    h1_low=8000.0,
                    mm50_slope=1.2345,
                    adx14=27.5,
                )
            ],
        )

        response = client.get(
            "/api/backtest/run/csv",
            params={
                "definition": "B9H",
                "start_date": "2026-06-01",
                "end_date": "2026-06-02",
            },
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert (
            'attachment; filename="backtest-B9H-2026-06-01-2026-06-02.csv"'
            in response.headers["content-disposition"]
        )
        body = response.text
        assert "parameter,value" in body
        assert "stop_loss_points,50" in body
        assert (
            "date,status,trade_count,points,h1_high,h1_low,h1_range,"
            "mm50_slope,adx14" in body
        )
        assert (
            "2026-06-02,traded,1,30.0,8050.0,8000.0,50.0,1.2345,27.5" in body
        )

    def test_end_before_start_returns_400(self, mock_backtest_service):
        mock_backtest_service.get_definition.return_value = MagicMock(
            code="B9H"
        )

        response = client.get(
            "/api/backtest/run/csv",
            params={
                "definition": "B9H",
                "start_date": "2026-06-10",
                "end_date": "2026-06-01",
            },
        )

        assert response.status_code == 400
        mock_backtest_service.run_range.assert_not_called()


class TestBacktestParameters:
    def test_omitted_params_default_to_the_strategy_thresholds(
        self, mock_backtest_service
    ):
        mock_backtest_service.get_definition.return_value = MagicMock(
            code="B9H"
        )
        mock_backtest_service.evaluate_day.return_value = DayResult(
            date=datetime.date(2026, 6, 2), status=DayStatus.NO_TRADE
        )

        response = client.get(
            "/api/backtest/day",
            params={"definition": "B9H", "date": "2026-06-02"},
        )

        assert response.status_code == 200
        params = mock_backtest_service.evaluate_day.call_args.args[2]
        assert params == BacktestParameters()

    def test_custom_params_are_passed_to_the_service(
        self, mock_backtest_service
    ):
        mock_backtest_service.get_definition.return_value = MagicMock(
            code="B9H"
        )
        mock_backtest_service.evaluate_day.return_value = DayResult(
            date=datetime.date(2026, 6, 2), status=DayStatus.NO_TRADE
        )

        response = client.get(
            "/api/backtest/day",
            params={
                "definition": "B9H",
                "date": "2026-06-02",
                "stop_loss_points": 40,
                "take_profit_offset_points": 15,
                "break_even_trigger_points": 25,
                "max_entry_distance_points": 12,
            },
        )

        assert response.status_code == 200
        params = mock_backtest_service.evaluate_day.call_args.args[2]
        assert params == BacktestParameters(
            stop_loss_points=40,
            take_profit_offset_points=15,
            break_even_trigger_points=25,
            max_entry_distance_points=12,
        )

    def test_non_positive_param_returns_422(self, mock_backtest_service):
        mock_backtest_service.get_definition.return_value = MagicMock(
            code="B9H"
        )

        response = client.get(
            "/api/backtest/day",
            params={
                "definition": "B9H",
                "date": "2026-06-02",
                "stop_loss_points": 0,
            },
        )

        assert response.status_code == 422
        mock_backtest_service.evaluate_day.assert_not_called()


class TestGetBacktestDefinitions:
    def test_returns_definitions_list(self, mock_backtest_service):
        mock_backtest_service.list_definitions.return_value = [
            MagicMock(
                code="B9H",
                display_name="CAC40 Bougie de 9h",
                instrument="FRA40.I",
            )
        ]

        response = client.get("/api/backtest/definitions")

        assert response.status_code == 200
        body = response.json()
        assert body == [
            {
                "code": "B9H",
                "display_name": "CAC40 Bougie de 9h",
                "instrument": "FRA40.I",
            }
        ]
