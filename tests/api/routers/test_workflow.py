from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_saxo_client
from api.main import app

client = TestClient(app)


@pytest.fixture
def mock_dynamodb_client():
    """Mock DynamoDBClient with async methods."""
    with patch("api.dependencies.DynamoDBClient") as mock_class:
        mock_instance = AsyncMock()
        mock_class.return_value = mock_instance
        yield mock_instance


def create_workflow_data(
    workflow_id: str,
    name: str,
    index: str,
    cfd: str,
    enabled: bool = True,
    dry_run: bool = False,
    indicator_name: str = "bbb",
    indicator_ut: str = "h1",
    close_direction: str = "above",
    close_spread: int = 20,
    order_direction: str = "buy",
):
    """Helper to create workflow data dict for testing."""
    return {
        "id": workflow_id,
        "name": name,
        "index": index,
        "cfd": cfd,
        "enable": enabled,
        "dry_run": dry_run,
        "is_us": False,
        "end_date": None,
        "conditions": [
            {
                "indicator": {
                    "name": indicator_name,
                    "ut": indicator_ut,
                    "value": None,
                    "zone_value": None,
                },
                "close": {
                    "direction": close_direction,
                    "ut": indicator_ut,
                    "spread": close_spread,
                },
                "element": None,
            }
        ],
        "trigger": {
            "ut": indicator_ut,
            "signal": "breakout",
            "location": "higher" if order_direction == "buy" else "lower",
            "order_direction": order_direction,
            "quantity": 0.1,
        },
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
    }


class TestWorkflowEndpoint:
    def test_get_asset_workflows_success(self, mock_dynamodb_client):
        """Test successful retrieval of workflows for an asset."""
        mock_dynamodb_client.get_all_workflows.return_value = [
            create_workflow_data("1", "buy bbb h1 dax", "DAX.I", "GER40.I"),
            create_workflow_data(
                "2",
                "sell bbh h1 dax",
                "DAX.I",
                "GER40.I",
                indicator_name="bbh",
                close_direction="below",
                order_direction="sell",
            ),
        ]

        response = client.get(
            "/api/workflow/asset?code=DAX.I&country_code=xpar"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["asset_symbol"] == "DAX.I:xpar"
        assert data["total"] == 2
        assert len(data["workflows"]) == 2
        assert data["workflows"][0]["name"] == "buy bbb h1 dax"
        assert data["workflows"][0]["index"] == "DAX.I"
        assert data["workflows"][0]["enabled"] is True
        assert data["workflows"][0]["dry_run"] is False

    def test_get_asset_workflows_with_default_country_code(
        self, mock_dynamodb_client
    ):
        """Test workflow retrieval with default country_code."""
        mock_dynamodb_client.get_all_workflows.return_value = [
            create_workflow_data(
                "1",
                "test workflow",
                "ITP:xpar",
                "ITP.PAR",
                dry_run=True,
                indicator_name="ma50",
                indicator_ut="h4",
            )
        ]

        response = client.get("/api/workflow/asset?code=ITP")

        assert response.status_code == 200
        data = response.json()
        assert data["asset_symbol"] == "ITP:xpar"
        assert data["total"] == 1

    def test_get_asset_workflows_no_results(self, mock_dynamodb_client):
        """Test when no workflows match the asset."""
        mock_dynamodb_client.get_all_workflows.return_value = [
            create_workflow_data("1", "other workflow", "OTHER.I", "OTHER.I")
        ]

        response = client.get("/api/workflow/asset?code=NONEXISTENT")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["workflows"]) == 0

    def test_get_asset_workflows_missing_code(self):
        """Test request without required code parameter."""
        response = client.get("/api/workflow/asset")

        assert response.status_code == 422  # Validation error

    def test_get_asset_workflows_force_from_disk(self, mock_dynamodb_client):
        """Test that force_from_disk parameter is no longer supported."""
        mock_dynamodb_client.get_all_workflows.return_value = []

        # force_from_disk parameter is ignored now
        response = client.get(
            "/api/workflow/asset?code=TEST&force_from_disk=true"
        )

        assert response.status_code == 200

    def test_get_asset_workflows_saxo_exception(self, mock_dynamodb_client):
        """Test handling of exceptions (no longer SaxoException)."""
        mock_dynamodb_client.get_all_workflows.side_effect = Exception(
            "Database error"
        )

        response = client.get("/api/workflow/asset?code=TEST")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"

    def test_get_asset_workflows_unexpected_exception(
        self, mock_dynamodb_client
    ):
        """Test handling of unexpected exception."""
        mock_dynamodb_client.get_all_workflows.side_effect = Exception(
            "Unexpected error"
        )

        response = client.get("/api/workflow/asset?code=TEST")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"

    def test_get_asset_workflows_case_insensitive(self, mock_dynamodb_client):
        """Test that asset matching is case-insensitive."""
        mock_dynamodb_client.get_all_workflows.return_value = [
            create_workflow_data("1", "test workflow", "DAX.I", "GER40.I")
        ]

        response = client.get("/api/workflow/asset?code=dax.i")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1


class TestInclinedWorkflowCurrentValue:
    """Tests for inclined indicator current_value computation."""

    def _inclined_workflow_data(
        self,
        x1_date: str,
        x1_price: float,
        x2_date: str,
        x2_price: float,
    ) -> dict:
        return {
            "id": "1",
            "name": "inclined wf",
            "index": "DAX.I",
            "cfd": "GER40.I",
            "enable": True,
            "dry_run": False,
            "is_us": False,
            "end_date": None,
            "conditions": [
                {
                    "indicator": {
                        "name": "inclined",
                        "ut": "h1",
                        "value": None,
                        "zone_value": None,
                        "x1": {"x": x1_date, "y": x1_price},
                        "x2": {"x": x2_date, "y": x2_price},
                    },
                    "close": {
                        "direction": "below",
                        "ut": "h1",
                        "spread": 20,
                    },
                    "element": None,
                }
            ],
            "trigger": {
                "ut": "h1",
                "signal": "breakout",
                "location": "lower",
                "order_direction": "sell",
                "quantity": 0.1,
            },
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }

    @pytest.fixture
    def mock_saxo(self):
        mock = MagicMock()
        mock.get_asset.return_value = {
            "Identifier": 123,
            "AssetType": "Stock",
        }
        mock.is_day_open.return_value = True
        app.dependency_overrides[get_saxo_client] = lambda: mock
        yield mock
        app.dependency_overrides.pop(get_saxo_client, None)

    def test_inclined_current_value_computed(
        self, mock_dynamodb_client, mock_saxo
    ):
        """A linear line from (Mon, 100) to (Fri, 108) is +2/day.
        On the following Monday (3 business days later) the value is 110."""
        mock_dynamodb_client.get_all_workflows.return_value = [
            self._inclined_workflow_data(
                "2024-01-01", 100.0, "2024-01-05", 108.0
            )
        ]

        with patch(
            "api.routers.workflow.get_date_utc0",
            return_value=__import__("datetime").datetime(2024, 1, 8),
        ):
            response = client.get("/api/workflow/asset?code=DAX.I")

        assert response.status_code == 200
        data = response.json()
        indicator = data["workflows"][0]["conditions"][0]["indicator"]
        assert indicator["name"] == "inclined"
        assert indicator["x1_date"] == "2024-01-01"
        assert indicator["x2_date"] == "2024-01-05"
        assert indicator["current_value"] == pytest.approx(110.0)

    def test_inclined_current_value_handles_saxo_error(
        self, mock_dynamodb_client, mock_saxo
    ):
        """If the Saxo lookup fails, current_value is None but the request
        still succeeds."""
        mock_saxo.get_asset.side_effect = RuntimeError("boom")
        mock_dynamodb_client.get_all_workflows.return_value = [
            self._inclined_workflow_data(
                "2024-01-01", 100.0, "2024-01-05", 108.0
            )
        ]

        response = client.get("/api/workflow/asset?code=DAX.I")

        assert response.status_code == 200
        data = response.json()
        indicator = data["workflows"][0]["conditions"][0]["indicator"]
        assert indicator["current_value"] is None
        assert indicator["x1_date"] == "2024-01-01"

    def test_non_inclined_indicator_has_no_current_value(
        self, mock_dynamodb_client, mock_saxo
    ):
        mock_dynamodb_client.get_all_workflows.return_value = [
            create_workflow_data("1", "bbb wf", "DAX.I", "GER40.I")
        ]

        response = client.get("/api/workflow/asset?code=DAX.I")

        assert response.status_code == 200
        indicator = response.json()["workflows"][0]["conditions"][0][
            "indicator"
        ]
        assert indicator["current_value"] is None
        assert indicator["x1_date"] is None
        # Saxo client should not have been touched for non-inclined indicators
        mock_saxo.get_asset.assert_not_called()
