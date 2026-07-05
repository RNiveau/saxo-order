from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers.trade_republic import get_trade_republic_service
from api.services.trade_republic_service import TradeRepublicService

client = TestClient(app)

FIXTURE_PATH = (
    Path(__file__).parent.parent.parent
    / "services"
    / "files"
    / "trade_republic_sample.csv"
)


@pytest.fixture(autouse=True)
def _clear_overrides():
    """Clear dependency overrides after each test."""
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def real_trade_republic_service() -> TradeRepublicService:
    """Real service (parsing has no external dependency) with a mocked
    GSheetClient, since export isn't exercised by these upload tests."""
    service = TradeRepublicService(MagicMock())
    app.dependency_overrides[get_trade_republic_service] = lambda: service
    return service


class TestUploadEndpoint:
    def test_upload_happy_path(self, real_trade_republic_service):
        with open(FIXTURE_PATH, "rb") as f:
            response = client.post(
                "/api/trade-republic/upload",
                files={
                    "file": (
                        "trade_republic_sample.csv",
                        f,
                        "text/csv",
                    )
                },
            )

        assert response.status_code == 200
        body = response.json()
        assert len(body["transactions"]) == 3
        assert len(body["errors"]) == 1
        assert body["total_rows"] == 4
        assert body["transactions"][0]["transaction_id"] == (
            "019ca92b-2e1d-7a63-831a-88c8927ba850"
        )


class TestExportEndpoint:
    def _get_uploaded_transactions(self):
        with open(FIXTURE_PATH, "rb") as f:
            response = client.post(
                "/api/trade-republic/upload",
                files={"file": ("trade_republic_sample.csv", f, "text/csv")},
            )
        return response.json()["transactions"]

    def test_export_success(self, real_trade_republic_service):
        transactions = self._get_uploaded_transactions()

        response = client.post(
            "/api/trade-republic/gsheet/export",
            json={"transactions": transactions[:2]},
        )

        assert response.status_code == 200
        assert response.json()["exported_count"] == 2
        gsheet_client = real_trade_republic_service.gsheet_client
        gsheet_client.append_etf_dca_rows.assert_called_once()

    def test_export_empty_selection_returns_400(
        self, real_trade_republic_service
    ):
        response = client.post(
            "/api/trade-republic/gsheet/export",
            json={"transactions": []},
        )

        assert response.status_code == 400

    def test_export_gsheet_failure_returns_500(
        self, real_trade_republic_service
    ):
        transactions = self._get_uploaded_transactions()
        gsheet_client = real_trade_republic_service.gsheet_client
        gsheet_client.append_etf_dca_rows.side_effect = RuntimeError("boom")

        response = client.post(
            "/api/trade-republic/gsheet/export",
            json={"transactions": transactions[:1]},
        )

        assert response.status_code == 500
