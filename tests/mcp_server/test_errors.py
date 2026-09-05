import asyncio
import inspect

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from mcp_server import errors
from mcp_server.errors import (
    current_market_client,
    market_tool,
    tool_boundary,
)
from model import Provenance
from utils.exception import SaxoException


class TestToolBoundary:
    def test_a_domain_failure_keeps_its_message(self):
        @tool_boundary
        async def failing():
            raise SaxoException("Missing candles to calcule the ma")

        with pytest.raises(ToolError) as caught:
            asyncio.run(failing())

        assert "Missing candles to calcule the ma" in str(caught.value)

    def test_a_wiring_bug_stays_a_crash(self):
        """RuntimeError is how this project reports its own mistakes.

        Translating it would hand the model a tidy explanation for a bug and
        lose the traceback the SDK would otherwise log.
        """

        @tool_boundary
        async def broken():
            raise RuntimeError("client was never wired up")

        with pytest.raises(RuntimeError):
            asyncio.run(broken())

    def test_an_existing_tool_error_passes_through_unwrapped(self):
        original = ToolError("already explained")

        @tool_boundary
        async def already():
            raise original

        with pytest.raises(ToolError) as caught:
            asyncio.run(already())

        assert caught.value is original


class TestMarketTool:
    def _simulated(self, mocker):
        mocker.patch.object(
            errors,
            "resolve_market_client",
            return_value=(object(), Provenance.SIMULATED),
        )

    def _live(self, mocker):
        mocker.patch.object(
            errors,
            "resolve_market_client",
            return_value=(object(), Provenance.LIVE),
        )

    def test_simulated_data_is_refused_by_default(self, mocker):
        self._simulated(mocker)

        @market_tool
        async def analyse(allow_simulated: bool = False):
            return "answered"

        with pytest.raises(ToolError) as caught:
            asyncio.run(analyse())

        assert "simulated" in str(caught.value)

    def test_the_opt_in_is_honoured_for_that_call_only(self, mocker):
        self._simulated(mocker)

        @market_tool
        async def analyse(allow_simulated: bool = False):
            return current_market_client()[1]

        assert asyncio.run(analyse(allow_simulated=True)) is (
            Provenance.SIMULATED
        )

        with pytest.raises(ToolError):
            asyncio.run(analyse())

    def test_live_data_needs_no_opt_in(self, mocker):
        self._live(mocker)

        @market_tool
        async def analyse(allow_simulated: bool = False):
            return current_market_client()[1]

        assert asyncio.run(analyse()) is Provenance.LIVE

    def test_a_tool_without_the_opt_in_parameter_is_rejected(self):
        """The refusal advertises an escape hatch, so it has to exist.

        allow_simulated only reaches the caller if it is in the signature,
        which is what becomes the tool's JSON schema.
        """
        with pytest.raises(TypeError) as caught:

            @market_tool
            async def analyse(code: str):
                return code

        assert "allow_simulated" in str(caught.value)

    def test_the_signature_survives_decoration(self, mocker):
        """The signature is the schema the model is shown."""
        self._live(mocker)

        @market_tool
        async def analyse(code: str, allow_simulated: bool = False) -> str:
            return code

        assert list(inspect.signature(analyse).parameters) == [
            "code",
            "allow_simulated",
        ]

    def test_the_client_does_not_leak_between_calls(self, mocker):
        self._live(mocker)

        @market_tool
        async def analyse(allow_simulated: bool = False):
            return current_market_client()

        asyncio.run(analyse())

        with pytest.raises(RuntimeError):
            current_market_client()
