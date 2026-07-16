import datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers.backtest import get_backtest_service
from api.services.backtest_service import BacktestService
from model import (
    BacktestRunResult,
    BacktestSummary,
    DayResult,
    DayResultSummary,
)
from model.enum import DayStatus

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
    def test_traded_day_returns_200(self, mock_backtest_service):
        mock_backtest_service.get_definition.return_value = MagicMock(
            code="B9H"
        )
        mock_backtest_service.evaluate_day.return_value = DayResult(
            date=datetime.date(2026, 6, 2),
            status=DayStatus.NO_TRADE,
            h1_high=8050.0,
            h1_low=8000.0,
        )

        response = client.get(
            "/api/backtest/day",
            params={"definition": "B9H", "date": "2026-06-02"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "no_trade"
        assert body["h1_high"] == 8050.0
        assert body["h1_low"] == 8000.0
        assert body["trades"] == []

    def test_no_data_day_returns_200(self, mock_backtest_service):
        mock_backtest_service.get_definition.return_value = MagicMock(
            code="B9H"
        )
        mock_backtest_service.evaluate_day.return_value = DayResult(
            date=datetime.date(2026, 6, 2), status=DayStatus.NO_DATA
        )

        response = client.get(
            "/api/backtest/day",
            params={"definition": "B9H", "date": "2026-06-02"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "no_data"

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

    def test_future_date_returns_400(self, mock_backtest_service):
        mock_backtest_service.get_definition.return_value = MagicMock(
            code="B9H"
        )
        future_date = (
            datetime.date.today() + datetime.timedelta(days=30)
        ).isoformat()

        response = client.get(
            "/api/backtest/run",
            params={
                "definition": "B9H",
                "start_date": "2026-06-01",
                "end_date": future_date,
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
