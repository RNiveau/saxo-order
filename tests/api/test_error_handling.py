from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from client.aws_client import DynamoDBOperationError

client = TestClient(app)


class TestDynamoDBErrorHandler:
    def test_dynamodb_error_returns_503(self):
        """Test that DynamoDBOperationError is caught by global handler."""
        from fastapi import Request

        @app.get("/test-dynamo-error")
        async def test_endpoint():
            raise DynamoDBOperationError(
                "test_op", "ResourceNotFoundException"
            )

        response = client.get("/test-dynamo-error")
        assert response.status_code == 503
        body = response.json()
        assert "temporarily unavailable" in body["detail"].lower()
        assert "ResourceNotFoundException" not in body["detail"]

        # Cleanup: remove test route
        app.routes[:] = [
            r
            for r in app.routes
            if getattr(r, "path", "") != "/test-dynamo-error"
        ]

    def test_error_message_does_not_expose_internals(self):
        """Error responses should not contain table names or schema details."""

        @app.get("/test-dynamo-error-2")
        async def test_endpoint():
            raise DynamoDBOperationError(
                "get_watchlist", "ResourceNotFoundException"
            )

        response = client.get("/test-dynamo-error-2")
        body = response.json()
        assert "watchlist" not in body["detail"].lower()
        assert "dynamodb" not in body["detail"].lower()
        assert "table" not in body["detail"].lower()

        app.routes[:] = [
            r
            for r in app.routes
            if getattr(r, "path", "") != "/test-dynamo-error-2"
        ]

    def test_health_check_unaffected(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
