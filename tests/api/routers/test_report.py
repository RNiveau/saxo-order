from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.dependencies import (
    get_binance_report_service,
    get_ouinex_report_service,
    get_report_service,
)
from api.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_report_services():
    """Override the three report services with mocks returning no orders."""
    saxo = MagicMock()
    saxo.get_orders_report.return_value = []
    binance = MagicMock()
    binance.get_orders_report.return_value = []
    ouinex = MagicMock()
    ouinex.get_orders_report.return_value = []

    app.dependency_overrides[get_report_service] = lambda: saxo
    app.dependency_overrides[get_binance_report_service] = lambda: binance
    app.dependency_overrides[get_ouinex_report_service] = lambda: ouinex
    yield saxo, binance, ouinex
    app.dependency_overrides.clear()


class TestReportRouting:
    def test_ouinex_account_selects_ouinex_service(self, mock_report_services):
        saxo, binance, ouinex = mock_report_services

        response = client.get(
            "/api/report/orders",
            params={"account_id": "ouinex_main", "from_date": "2024-01-01"},
        )

        assert response.status_code == 200
        ouinex.get_orders_report.assert_called_once_with(
            "ouinex_main", "2024-01-01"
        )
        binance.get_orders_report.assert_not_called()
        saxo.get_orders_report.assert_not_called()

    def test_binance_account_selects_binance_service(
        self, mock_report_services
    ):
        saxo, binance, ouinex = mock_report_services

        response = client.get(
            "/api/report/orders",
            params={"account_id": "binance_main", "from_date": "2024-01-01"},
        )

        assert response.status_code == 200
        binance.get_orders_report.assert_called_once_with(
            "binance_main", "2024-01-01"
        )
        ouinex.get_orders_report.assert_not_called()
        saxo.get_orders_report.assert_not_called()

    def test_saxo_account_selects_saxo_service(self, mock_report_services):
        saxo, binance, ouinex = mock_report_services

        response = client.get(
            "/api/report/orders",
            params={"account_id": "12345", "from_date": "2024-01-01"},
        )

        assert response.status_code == 200
        saxo.get_orders_report.assert_called_once_with("12345", "2024-01-01")
        binance.get_orders_report.assert_not_called()
        ouinex.get_orders_report.assert_not_called()
