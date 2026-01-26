from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers.asset_details import get_asset_details_service

client = TestClient(app)


@pytest.fixture
def mock_asset_details_service():
    """Mock AssetDetailsService."""
    mock_service = MagicMock()

    def override_get_asset_details_service():
        return mock_service

    app.dependency_overrides[get_asset_details_service] = (
        override_get_asset_details_service
    )
    yield mock_service
    app.dependency_overrides.clear()


class TestGetAssetDetails:
    def test_get_asset_details_success(self, mock_asset_details_service):
        """Test GET /api/asset-details/{asset_id} returns asset details."""
        from api.models.asset_details import AssetDetailResponse

        mock_service = mock_asset_details_service
        mock_service.get_asset_details.return_value = AssetDetailResponse(
            asset_id="SAN",
            tradingview_url="https://tradingview.com/SAN",
            updated_at="2026-01-26T10:00:00Z",
            is_excluded=False,
        )

        response = client.get("/api/asset-details/SAN")

        assert response.status_code == 200
        data = response.json()
        assert data["asset_id"] == "SAN"
        assert data["is_excluded"] is False
        mock_service.get_asset_details.assert_called_once_with("SAN")

    def test_get_asset_details_with_exclusion(
        self, mock_asset_details_service
    ):
        """Test GET returns is_excluded=true when asset is excluded."""
        from api.models.asset_details import AssetDetailResponse

        mock_service = mock_asset_details_service
        mock_service.get_asset_details.return_value = AssetDetailResponse(
            asset_id="BNP",
            tradingview_url=None,
            updated_at="2026-01-26T10:00:00Z",
            is_excluded=True,
        )

        response = client.get("/api/asset-details/BNP")

        assert response.status_code == 200
        data = response.json()
        assert data["asset_id"] == "BNP"
        assert data["is_excluded"] is True


class TestUpdateAssetExclusion:
    def test_update_exclusion_to_true(self, mock_asset_details_service):
        """Test PUT exclusion endpoint updates to excluded."""
        from api.models.asset_details import AssetDetailResponse

        mock_service = mock_asset_details_service
        mock_service.update_exclusion.return_value = AssetDetailResponse(
            asset_id="SAN",
            tradingview_url="https://tradingview.com/SAN",
            updated_at="2026-01-26T10:30:00Z",
            is_excluded=True,
        )

        response = client.put(
            "/api/asset-details/SAN/exclusion",
            json={"is_excluded": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["asset_id"] == "SAN"
        assert data["is_excluded"] is True
        mock_service.update_exclusion.assert_called_once_with("SAN", True)

    def test_update_exclusion_to_false(self, mock_asset_details_service):
        """Test PUT can un-exclude an asset."""
        from api.models.asset_details import AssetDetailResponse

        mock_service = mock_asset_details_service
        mock_service.update_exclusion.return_value = AssetDetailResponse(
            asset_id="SAN",
            tradingview_url="https://tradingview.com/SAN",
            updated_at="2026-01-26T10:30:00Z",
            is_excluded=False,
        )

        response = client.put(
            "/api/asset-details/SAN/exclusion",
            json={"is_excluded": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_excluded"] is False
        mock_service.update_exclusion.assert_called_once_with("SAN", False)

    def test_update_exclusion_invalid_request(
        self, mock_asset_details_service
    ):
        """Test PUT with invalid request body returns 422."""
        response = client.put(
            "/api/asset-details/SAN/exclusion",
            json={"invalid_field": "value"},
        )

        assert response.status_code == 422

    def test_update_exclusion_service_error(self, mock_asset_details_service):
        """Test PUT returns 500 when service raises exception."""
        mock_service = mock_asset_details_service
        mock_service.update_exclusion.side_effect = Exception("DynamoDB error")

        response = client.put(
            "/api/asset-details/SAN/exclusion",
            json={"is_excluded": True},
        )

        assert response.status_code == 500


class TestGetAllAssets:
    def test_get_all_assets_success(self, mock_asset_details_service):
        """Test GET /api/asset-details returns all assets with counts."""
        from api.models.asset_details import (
            AssetDetailResponse,
            AssetListResponse,
        )

        mock_service = mock_asset_details_service
        mock_service.get_all_assets_with_details.return_value = (
            AssetListResponse(
                assets=[
                    AssetDetailResponse(
                        asset_id="SAN",
                        tradingview_url="https://tradingview.com/SAN",
                        updated_at="2026-01-26T10:00:00Z",
                        is_excluded=True,
                    ),
                    AssetDetailResponse(
                        asset_id="ITP",
                        tradingview_url=None,
                        updated_at="2026-01-25T15:00:00Z",
                        is_excluded=False,
                    ),
                ],
                count=2,
                excluded_count=1,
                active_count=1,
            )
        )

        response = client.get("/api/asset-details")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert data["excluded_count"] == 1
        assert data["active_count"] == 1
        assert len(data["assets"]) == 2

    def test_get_all_assets_empty(self, mock_asset_details_service):
        """Test GET /api/asset-details with no assets."""
        from api.models.asset_details import AssetListResponse

        mock_service = mock_asset_details_service
        mock_service.get_all_assets_with_details.return_value = (
            AssetListResponse(
                assets=[],
                count=0,
                excluded_count=0,
                active_count=0,
            )
        )

        response = client.get("/api/asset-details")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["assets"] == []


class TestGetExcludedAssets:
    def test_get_excluded_assets_success(self, mock_asset_details_service):
        """Test GET /api/asset-details/excluded/list returns only excluded."""
        from api.models.asset_details import AssetDetailResponse

        mock_service = mock_asset_details_service
        mock_service.get_all_excluded_assets.return_value = [
            AssetDetailResponse(
                asset_id="SAN",
                tradingview_url="https://tradingview.com/SAN",
                updated_at="2026-01-26T10:00:00Z",
                is_excluded=True,
            ),
            AssetDetailResponse(
                asset_id="BNP",
                tradingview_url=None,
                updated_at="2026-01-25T14:00:00Z",
                is_excluded=True,
            ),
        ]

        response = client.get("/api/asset-details/excluded/list")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert data["excluded_count"] == 2
        assert data["active_count"] == 0
        assert all(asset["is_excluded"] for asset in data["assets"])

    def test_get_excluded_assets_empty(self, mock_asset_details_service):
        """Test GET /api/asset-details/excluded/list with no exclusions."""
        mock_service = mock_asset_details_service
        mock_service.get_all_excluded_assets.return_value = []

        response = client.get("/api/asset-details/excluded/list")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["excluded_count"] == 0
        assert data["assets"] == []
