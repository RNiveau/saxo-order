from unittest.mock import MagicMock

from api.main import app, lifespan
from client.saxo_client import SaxoClient


async def test_each_lifespan_owns_its_saxo_client_and_report_service(
    mocker,
):
    clients = [MagicMock(spec=SaxoClient), MagicMock(spec=SaxoClient)]
    mocker.patch("api.main.build_saxo_client", side_effect=clients)
    mocker.patch("api.main.get_configuration")
    mocker.patch("api.main.aioboto3.Session")

    async with lifespan(app):
        assert app.state.saxo_client is clients[0]
        app.state.report_service = MagicMock()

    clients[0].aclose.assert_awaited_once()
    assert app.state.saxo_client is None
    assert app.state.report_service is None

    async with lifespan(app):
        assert app.state.saxo_client is clients[1]
        assert app.state.report_service is None

    clients[1].aclose.assert_awaited_once()
