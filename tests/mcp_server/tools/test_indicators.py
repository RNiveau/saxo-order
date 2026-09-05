import asyncio
import datetime
from typing import List

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from mcp_server import errors
from mcp_server.tools import indicators
from mcp_server.tools.indicators import build_snapshot
from model import (
    AssetType,
    Candle,
    IndicatorName,
    MarketName,
    Provenance,
    UnitTime,
)
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

        snapshot = _snapshot(market=MarketName.EU)

        assert snapshot.meta.provenance is Provenance.LIVE
        assert snapshot.meta.exchange is Exchange.SAXO
        assert snapshot.meta.unit_time is UnitTime.D
        assert snapshot.meta.last_bar_date == datetime.datetime(2026, 8, 30)
        assert snapshot.instrument_id == 42
        assert snapshot.asset_type is AssetType.STOCK
        assert snapshot.meta.forming_period_included is True

    def test_it_admits_when_the_forming_period_is_missing(
        self, mocker, live_client
    ):
        """With no market the newest bar is the last completed day, so the
        price is yesterday's - the caller has to be able to see that."""
        mocker.patch.object(
            indicators.candle_source,
            "build_daily_series",
            return_value=_series(300),
        )

        snapshot = _snapshot(market=None)

        assert snapshot.meta.forming_period_included is False

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

        snapshot = _snapshot(unit_time=UnitTime.W, market=MarketName.EU)

        assert daily.call_count == 1
        assert weekly.call_count == 1
        assert snapshot.meta.unit_time is UnitTime.W

    def test_the_weekly_depth_goes_to_the_weekly_series(
        self, mocker, live_client
    ):
        """The daily leg only supplies the week now forming.

        Sizing it to the indicators' depth would buy 250 days that nothing
        reads, and leaving the weekly series at its default would cap it at
        70 bars - so MM200 could never be computed on W however much
        history the instrument has.
        """
        daily = mocker.patch.object(
            indicators.candle_source,
            "build_daily_series",
            return_value=_series(20),
        )
        weekly = mocker.patch.object(
            indicators.candle_source,
            "build_weekly_series",
            return_value=_series(300),
        )

        _snapshot(
            unit_time=UnitTime.W,
            market=MarketName.EU,
            include=[IndicatorName.MM200],
        )

        assert daily.call_args.args[4] == indicators.DAYS_FOR_FORMING_WEEK
        assert weekly.call_args.args[4] == 200


class TestSnapshotRejections:
    def test_the_weekly_timeframe_refuses_without_a_market(self, live_client):
        """Without session hours the forming week is short by whole days.

        Nothing downstream could tell: the close, high and low would simply
        be understated, so refusing beats answering.
        """
        with pytest.raises(ToolError, match="needs a market"):
            _snapshot(unit_time=UnitTime.W, market=None)

    def test_another_venue_is_refused_rather_than_mislabelled(
        self, live_client
    ):
        """Only saxo data is available, so only saxo may be claimed."""
        with pytest.raises(ToolError, match="not supported"):
            _snapshot(exchange=Exchange.BINANCE)

    def test_the_simulated_client_says_it_has_no_candles(self, mocker):
        """The opt-in the refusal advertises cannot actually work here.

        MockSaxoClient.get_historical_data returns [] unconditionally, so
        without this the caller gets 'needs 7 bars, got 0' and cannot tell
        a simulated client from an instrument with no history.
        """
        client = mocker.MagicMock()
        token = errors._market_client.set((client, Provenance.SIMULATED))
        mocker.patch.object(
            indicators.candle_source, "build_daily_series", return_value=[]
        )
        try:
            with pytest.raises(ToolError, match="simulated client"):
                _snapshot()
        finally:
            errors._market_client.reset(token)

    def test_an_unsupported_timeframe_lists_the_supported_ones(
        self, live_client
    ):
        with pytest.raises(ToolError, match="daily"):
            _snapshot(unit_time=UnitTime.H1)

    def test_an_empty_include_is_a_caller_mistake(self, live_client):
        with pytest.raises(ToolError, match="include"):
            _snapshot(include=[])
