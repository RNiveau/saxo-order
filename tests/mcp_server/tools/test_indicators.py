import asyncio
import datetime
from typing import List

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from mcp_server import errors
from mcp_server.tools import indicators
from mcp_server.tools.indicators import build_snapshot
from model import AssetType, Candle, IndicatorName, Provenance, UnitTime
from model.enum import Exchange


def _series(count: int) -> List[Candle]:
    newest = datetime.datetime(2026, 8, 30)
    return [
        Candle(
            lower=99.0,
            higher=101.0,
            open=100.0,
            close=100.0 + i * 0.1,
            ut=UnitTime.D,
            date=newest - datetime.timedelta(days=i),
        )
        for i in range(count)
    ]


@pytest.fixture
def live_client(mocker):
    client = mocker.MagicMock()
    token = errors._market_client.set((client, Provenance.LIVE))
    yield client
    errors._market_client.reset(token)


def _snapshot(**kwargs):
    params = dict(
        instrument_id=42,
        asset_type=AssetType.STOCK,
        unit_time=UnitTime.D,
        include=None,
        exchange=Exchange.SAXO,
        market=None,
    )
    params.update(kwargs)
    return asyncio.run(build_snapshot(**params))


class TestSnapshotProvenanceAndIdentity:
    def test_it_states_where_the_data_came_from_and_what_it_describes(
        self, mocker, live_client
    ):
        mocker.patch.object(
            indicators.candle_source,
            "build_daily_series",
            return_value=_series(300),
        )

        snapshot = _snapshot()

        assert snapshot.meta.provenance is Provenance.LIVE
        assert snapshot.meta.exchange is Exchange.SAXO
        assert snapshot.meta.unit_time is UnitTime.D
        assert snapshot.meta.last_bar_date == datetime.datetime(2026, 8, 30)
        assert snapshot.instrument_id == 42
        assert snapshot.asset_type is AssetType.STOCK

    def test_the_price_and_variation_come_from_the_newest_bars(
        self, mocker, live_client
    ):
        mocker.patch.object(
            indicators.candle_source,
            "build_daily_series",
            return_value=_series(300),
        )

        snapshot = _snapshot()

        assert snapshot.current_price == 100.0
        assert snapshot.variation_pct is not None


class TestSnapshotFetchesOnce:
    def test_one_daily_request_serves_the_whole_bundle(
        self, mocker, live_client
    ):
        """SC-002: the shared cost is the fetch, not the arithmetic."""
        fetch = mocker.patch.object(
            indicators.candle_source,
            "build_daily_series",
            return_value=_series(300),
        )

        _snapshot()

        assert fetch.call_count == 1

    def test_a_shallow_request_does_not_buy_the_deepest_history(
        self, mocker, live_client
    ):
        fetch = mocker.patch.object(
            indicators.candle_source,
            "build_daily_series",
            return_value=_series(300),
        )

        _snapshot(include=[IndicatorName.MM7])

        requested_count = fetch.call_args.args[4]
        assert requested_count < 235

    def test_the_weekly_timeframe_costs_one_extra_series(
        self, mocker, live_client
    ):
        daily = mocker.patch.object(
            indicators.candle_source,
            "build_daily_series",
            return_value=_series(300),
        )
        weekly = mocker.patch.object(
            indicators.candle_source,
            "build_weekly_series",
            return_value=_series(300),
        )

        snapshot = _snapshot(unit_time=UnitTime.W)

        assert daily.call_count == 1
        assert weekly.call_count == 1
        assert snapshot.meta.unit_time is UnitTime.W


class TestSnapshotRejections:
    def test_an_unsupported_timeframe_lists_the_supported_ones(
        self, live_client
    ):
        with pytest.raises(ToolError, match="daily"):
            _snapshot(unit_time=UnitTime.H1)

    def test_an_empty_include_is_a_caller_mistake(self, live_client):
        with pytest.raises(ToolError, match="include"):
            _snapshot(include=[])
