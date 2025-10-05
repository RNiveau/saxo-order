from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from model.workflow import (
    Close,
    Condition,
    Indicator,
    IndicatorType,
    Trigger,
    UnitTime,
    Workflow,
    WorkflowDirection,
    WorkflowLocation,
    WorkflowSignal,
)
from utils.exception import SaxoException

client = TestClient(app)


@pytest.fixture
def mock_load_workflows():
    """Mock load_workflows function."""
    with patch("api.services.workflow_service.load_workflows") as mock:
        yield mock


class TestWorkflowEndpoint:
    def test_get_asset_workflows_success(self, mock_load_workflows):
        """Test successful retrieval of workflows for an asset."""
        # Create mock workflows
        workflow1 = Workflow(
            name="buy bbb h1 dax",
            index="DAX.I",
            cfd="GER40.I",
            enable=True,
            dry_run=False,
            conditions=[
                Condition(
                    indicator=Indicator(IndicatorType.BBB, UnitTime.H1),
                    close=Close(WorkflowDirection.ABOVE, UnitTime.H1, 20),
                )
            ],
            trigger=Trigger(
                ut=UnitTime.H1,
                signal=WorkflowSignal.BREAKOUT,
                location=WorkflowLocation.HIGHER,
                order_direction="buy",
                quantity=0.1,
            ),
        )

        workflow2 = Workflow(
            name="sell bbh h1 dax",
            index="DAX.I",
            cfd="GER40.I",
            enable=True,
            dry_run=False,
            conditions=[
                Condition(
                    indicator=Indicator(IndicatorType.BBH, UnitTime.H1),
                    close=Close(WorkflowDirection.BELOW, UnitTime.H1, 20),
                )
            ],
            trigger=Trigger(
                ut=UnitTime.H1,
                signal=WorkflowSignal.BREAKOUT,
                location=WorkflowLocation.LOWER,
                order_direction="sell",
                quantity=0.1,
            ),
        )

        mock_load_workflows.return_value = [workflow1, workflow2]

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
        self, mock_load_workflows
    ):
        """Test workflow retrieval with default country_code."""
        workflow = Workflow(
            name="test workflow",
            index="ITP:xpar",
            cfd="ITP.PAR",
            enable=True,
            dry_run=True,
            conditions=[
                Condition(
                    indicator=Indicator(IndicatorType.MA50, UnitTime.H4),
                    close=Close(WorkflowDirection.ABOVE, UnitTime.H4, 10),
                )
            ],
            trigger=Trigger(
                ut=UnitTime.H4,
                signal=WorkflowSignal.BREAKOUT,
                location=WorkflowLocation.HIGHER,
                order_direction="buy",
                quantity=1.0,
            ),
        )

        mock_load_workflows.return_value = [workflow]

        response = client.get("/api/workflow/asset?code=ITP")

        assert response.status_code == 200
        data = response.json()
        assert data["asset_symbol"] == "ITP:xpar"
        assert data["total"] == 1

    def test_get_asset_workflows_no_results(self, mock_load_workflows):
        """Test when no workflows match the asset."""
        workflow = Workflow(
            name="other workflow",
            index="OTHER.I",
            cfd="OTHER.I",
            enable=True,
            dry_run=False,
            conditions=[
                Condition(
                    indicator=Indicator(IndicatorType.MA50, UnitTime.D),
                    close=Close(WorkflowDirection.ABOVE, UnitTime.D, 0),
                )
            ],
            trigger=Trigger(
                ut=UnitTime.D,
                signal=WorkflowSignal.BREAKOUT,
                location=WorkflowLocation.HIGHER,
                order_direction="buy",
                quantity=1.0,
            ),
        )

        mock_load_workflows.return_value = [workflow]

        response = client.get("/api/workflow/asset?code=NONEXISTENT")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["workflows"]) == 0

    def test_get_asset_workflows_missing_code(self):
        """Test request without required code parameter."""
        response = client.get("/api/workflow/asset")

        assert response.status_code == 422  # Validation error

    def test_get_asset_workflows_force_from_disk(self, mock_load_workflows):
        """Test force_from_disk parameter."""
        mock_load_workflows.return_value = []

        response = client.get(
            "/api/workflow/asset?code=TEST&force_from_disk=true"
        )

        assert response.status_code == 200
        mock_load_workflows.assert_called_once_with(True)

    def test_get_asset_workflows_saxo_exception(self, mock_load_workflows):
        """Test handling of SaxoException."""
        mock_load_workflows.side_effect = SaxoException("No yaml to load")

        response = client.get("/api/workflow/asset?code=TEST")

        assert response.status_code == 400
        assert "No yaml to load" in response.json()["detail"]

    def test_get_asset_workflows_unexpected_exception(
        self, mock_load_workflows
    ):
        """Test handling of unexpected exception."""
        mock_load_workflows.side_effect = Exception("Unexpected error")

        response = client.get("/api/workflow/asset?code=TEST")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"

    def test_get_asset_workflows_case_insensitive(self, mock_load_workflows):
        """Test that asset matching is case-insensitive."""
        workflow = Workflow(
            name="test workflow",
            index="DAX.I",
            cfd="GER40.I",
            enable=True,
            dry_run=False,
            conditions=[
                Condition(
                    indicator=Indicator(IndicatorType.MA50, UnitTime.H1),
                    close=Close(WorkflowDirection.ABOVE, UnitTime.H1, 0),
                )
            ],
            trigger=Trigger(
                ut=UnitTime.H1,
                signal=WorkflowSignal.BREAKOUT,
                location=WorkflowLocation.HIGHER,
                order_direction="buy",
                quantity=1.0,
            ),
        )

        mock_load_workflows.return_value = [workflow]

        response = client.get("/api/workflow/asset?code=dax.i")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
