import asyncio

import pytest

from mcp_server.server import ServerContext, lifespan


class TestLifespan:
    """The lifespan must never become the story when something else fails."""

    def test_a_server_error_reaches_the_caller_unchanged(self, monkeypatch):
        """Regression: the yield used to sit inside the except.

        An exception raised while the context was active was thrown back in
        at the yield, caught, and followed by a second yield - which
        asynccontextmanager turns into "generator didn't stop after
        athrow()", replacing the real cause and blaming storage for it.
        """
        monkeypatch.delenv("AWS_PROFILE", raising=False)
        monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)

        async def run():
            async with lifespan(None):
                raise ValueError("server blew up")

        with pytest.raises(ValueError, match="server blew up"):
            asyncio.run(run())

    def test_without_aws_credentials_the_server_still_starts(
        self, monkeypatch
    ):
        """Market data must not depend on the alert store being reachable."""
        monkeypatch.delenv("AWS_PROFILE", raising=False)
        monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)

        async def run():
            async with lifespan(None) as ctx:
                return ctx

        context = asyncio.run(run())

        assert isinstance(context, ServerContext)
        assert context.dynamodb is None

    def test_a_failure_opening_the_store_is_not_fatal(self, monkeypatch):
        monkeypatch.setenv("AWS_PROFILE", "whatever")
        monkeypatch.setattr(
            "mcp_server.server.dynamodb_client",
            lambda: (_ for _ in ()).throw(OSError("no route to host")),
        )

        async def run():
            async with lifespan(None) as ctx:
                return ctx

        assert asyncio.run(run()).dynamodb is None
