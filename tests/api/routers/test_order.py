from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


class TestOrderEndpoint:
    def test_create_order_missing_api_key(self):
        """Test that requests without valid credentials fail."""
        response = client.post(
            "/api/orders",
            json={
                "code": "TEST",
                "price": 100.0,
                "quantity": 5,
                "order_type": "limit",
                "direction": "Buy",
            },
        )
        # Should fail due to missing/invalid Saxo credentials
        assert response.status_code in [400, 500]

    def test_create_order_invalid_price(self):
        """Test order creation with negative price."""
        response = client.post(
            "/api/orders",
            json={
                "code": "TEST",
                "price": -100.0,
                "quantity": 10,
                "order_type": "limit",
                "direction": "Buy",
            },
        )
        assert response.status_code == 422
        assert "price" in response.text.lower()

    def test_create_order_missing_quantity(self):
        """Test order creation with missing quantity field."""
        response = client.post(
            "/api/orders",
            json={
                "code": "TEST",
                "price": 100.0,
                "order_type": "limit",
                "direction": "Buy",
            },
        )
        assert response.status_code == 422
        assert "quantity" in response.text.lower()

    def test_create_order_invalid_order_type(self):
        """Test order creation with invalid order type."""
        response = client.post(
            "/api/orders",
            json={
                "code": "TEST",
                "price": 100.0,
                "quantity": 10,
                "order_type": "invalid_type",
                "direction": "Buy",
            },
        )
        assert response.status_code == 422
        assert "order_type" in response.text.lower()

    def test_create_order_invalid_direction(self):
        """Test order creation with invalid direction."""
        response = client.post(
            "/api/orders",
            json={
                "code": "TEST",
                "price": 100.0,
                "quantity": 10,
                "order_type": "limit",
                "direction": "sideways",
            },
        )
        assert response.status_code == 422
        assert "direction" in response.text.lower()

    def test_create_order_zero_quantity(self):
        """Test order creation with zero quantity."""
        response = client.post(
            "/api/orders",
            json={
                "code": "TEST",
                "price": 100.0,
                "quantity": 0,
                "order_type": "limit",
                "direction": "Buy",
            },
        )
        assert response.status_code == 422
        assert "quantity" in response.text.lower()


class TestOcoOrderEndpoint:
    def test_create_oco_order_missing_credentials(self):
        """Test that OCO requests without valid credentials fail."""
        response = client.post(
            "/api/orders/oco",
            json={
                "code": "TEST",
                "quantity": 10,
                "limit_price": 105.0,
                "limit_direction": "Sell",
                "stop_price": 95.0,
                "stop_direction": "Sell",
            },
        )
        assert response.status_code in [400, 500]

    def test_create_oco_order_missing_fields(self):
        """Test OCO order creation with missing required fields."""
        response = client.post(
            "/api/orders/oco",
            json={
                "code": "TEST",
                "quantity": 10,
                "limit_price": 105.0,
            },
        )
        assert response.status_code == 422


class TestStopLimitOrderEndpoint:
    def test_create_stop_limit_order_missing_credentials(self):
        """Test that stop-limit requests without valid credentials fail."""
        response = client.post(
            "/api/orders/stop-limit",
            json={
                "code": "TEST",
                "quantity": 5,
                "limit_price": 100.0,
                "stop_price": 95.0,
            },
        )
        assert response.status_code in [400, 500]

    def test_create_stop_limit_order_missing_fields(self):
        """Test stop-limit order creation with missing stop_price."""
        response = client.post(
            "/api/orders/stop-limit",
            json={
                "code": "TEST",
                "quantity": 10,
                "limit_price": 100.0,
            },
        )
        assert response.status_code == 422
        assert "stop_price" in response.text.lower()
