import asyncio

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from client.saxo_client import SaxoClient
from mcp_server.tools import assets
from mcp_server.tools.assets import search_asset
from model import AssetType, Provenance
from model.asset import Asset
from model.enum import Exchange
from utils.exception import SaxoException


def _asset(symbol="AI", identifier=1234, asset_type=AssetType.STOCK):
    return Asset(
        symbol=symbol,
        description=f"{symbol} description",
        asset_type=asset_type,
        exchange=Exchange.SAXO,
        identifier=identifier,
    )


def _client_returning(mocker, result):
    client = mocker.MagicMock(spec=SaxoClient)
    if isinstance(result, Exception):
        client.search.side_effect = result
    else:
        client.search.return_value = result
    mocker.patch.object(
        assets,
        "resolve_market_client",
        return_value=(client, Provenance.LIVE),
    )
    return client


class TestSearchAsset:
    def test_candidates_carry_what_the_other_tools_need(self, mocker):
        _client_returning(mocker, [_asset("AI"), _asset("SAN", 5678)])

        found = asyncio.run(search_asset("air liquide"))

        assert [a.code for a in found] == ["AI", "SAN"]
        assert [a.instrument_id for a in found] == [1234, 5678]
        assert all(a.exchange is Exchange.SAXO for a in found)
        assert all(a.asset_type is AssetType.STOCK for a in found)

    def test_no_match_is_an_empty_list_not_a_failure(self, mocker):
        """The client raises on zero results instead of returning [].

        Without catching it, every empty search would reach the caller as a
        venue failure, indistinguishable from the venue being down.
        """
        _client_returning(mocker, SaxoException("Nothing found for zzzz"))

        assert asyncio.run(search_asset("zzzz")) == []

    def test_a_venue_failure_is_still_a_failure(self, mocker):
        _client_returning(mocker, SaxoException("The access_token is expired"))

        with pytest.raises(SaxoException, match="expired"):
            asyncio.run(search_asset("air liquide"))

    def test_an_unanalysable_instrument_is_returned_with_its_reason(
        self, mocker
    ):
        """Dropping it would read as 'this asset does not exist'."""
        _client_returning(mocker, [_asset("XYZ", identifier=None)])

        found = asyncio.run(search_asset("xyz"))

        assert len(found) == 1
        assert found[0].instrument_id is None
        assert found[0].unavailable_reason

    def test_an_unsupported_venue_says_so(self, mocker):
        with pytest.raises(ToolError, match="not supported"):
            asyncio.run(search_asset("btc", exchange=Exchange.BINANCE))


class TestSearchAssetNeedsALiveVenue:
    def test_it_refuses_rather_than_inventing_instruments(self, mocker):
        """MockSaxoClient has no catalogue and no search method.

        Falling through would AttributeError and reach the caller as an
        opaque crash; inventing results would be worse still, since a
        fabricated instrument_id leads every later call astray.
        """
        mocker.patch.object(
            assets,
            "resolve_market_client",
            return_value=(mocker.MagicMock(), Provenance.SIMULATED),
        )

        with pytest.raises(ToolError, match="live venue"):
            asyncio.run(search_asset("air liquide"))
