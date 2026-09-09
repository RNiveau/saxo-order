import asyncio
import datetime
from typing import List

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from client.saxo_client import SaxoClient
from mcp_server import errors, formatters
from mcp_server.tools import assets
from mcp_server.tools.assets import get_candles, search_asset
from model import AssetType, Candle, MarketName, Provenance, UnitTime
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


def _series(count: int, newest: datetime.datetime) -> List[Candle]:
    return [
        Candle(
            lower=99.0 + i,
            higher=101.0 + i,
            open=100.0 + i,
            close=100.5 + i,
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


def _candles(**kwargs):
    params = dict(
        instrument_id=42,
        asset_type=AssetType.STOCK,
        unit_time=UnitTime.D,
        count=100,
        exchange=Exchange.SAXO,
        market=None,
    )
    params.update(kwargs)
    return asyncio.run(get_candles(**params))


def _daily_returns(mocker, candles):
    return mocker.patch.object(
        assets.candle_source, "build_daily_series", return_value=candles
    )


def _weekly_returns(mocker, candles):
    _daily_returns(mocker, _series(5, datetime.datetime(2026, 8, 30)))
    return mocker.patch.object(
        assets.candle_source, "build_weekly_series", return_value=candles
    )


def _clock_at(mocker, moment):
    """Pin the tool's clock, without touching the stdlib for everyone else.

    assets.datetime IS the stdlib module, so patching datetime.datetime on
    it rebinds the class process-wide for the duration of the test. The
    module's own _now indirection is the patch point instead.
    """
    return mocker.patch.object(
        assets, "_now", side_effect=lambda tz=None: moment
    )


class TestCandleSeries:
    def test_the_newest_bar_is_row_zero_all_the_way_to_the_wire(
        self, mocker, live_client
    ):
        """The project's ordering convention is the wire contract too."""
        newest = datetime.datetime(2026, 8, 30)
        _daily_returns(mocker, _series(3, newest))

        series = _candles()

        dates = [row[0] for row in series.rows]
        assert dates == [
            newest.isoformat(),
            (newest - datetime.timedelta(days=1)).isoformat(),
            (newest - datetime.timedelta(days=2)).isoformat(),
        ]
        assert series.meta.last_bar_date == newest

    def test_a_row_carries_the_columns_it_says_it_does(
        self, mocker, live_client
    ):
        _daily_returns(mocker, _series(1, datetime.datetime(2026, 8, 30)))

        series = _candles()

        assert series.columns == ["date", "open", "high", "low", "close"]
        assert series.rows[0][1:] == [100.0, 101.0, 99.0, 100.5]
        assert series.count == 1
        assert series.instrument_id == 42

    def test_no_history_is_an_empty_answer_not_a_failure(
        self, mocker, live_client
    ):
        _daily_returns(mocker, [])

        series = _candles()

        assert series.rows == []
        assert series.count == 0
        assert series.meta.last_bar_date is None
        assert series.current_incomplete is False


class TestTheFormingPeriod:
    def test_the_period_now_trading_is_present_and_flagged(
        self, mocker, live_client
    ):
        """build_daily_series prepends today when it knows the hours."""
        _daily_returns(mocker, _series(3, datetime.datetime.now()))

        series = _candles(market=MarketName.EU)

        assert series.current_incomplete is True
        assert series.meta.forming_period_included is True

    def test_an_undeterminable_market_leaves_the_forming_bar_out(
        self, mocker, live_client
    ):
        """Without session hours the top-up is skipped, so saying the
        series is current would misreport a stale price as live."""
        fetch = _daily_returns(mocker, _series(3, datetime.datetime.now()))

        series = _candles(market=None)

        assert fetch.call_args.kwargs["market"] is None
        assert series.current_incomplete is False
        assert series.meta.forming_period_included is False

    def test_a_closed_newest_bar_is_not_called_in_progress(
        self, mocker, live_client
    ):
        """A weekend, or an instrument that has not traded for days.

        The market is known, yet the newest bar is a closed one - flagging
        it anyway would invent an in-progress bar out of a finished one.
        """
        _daily_returns(mocker, _series(3, datetime.datetime(2026, 8, 30)))

        series = _candles(market=MarketName.EU)

        assert series.current_incomplete is False
        # The session hours were known - that is what this flag reports,
        # and it is the same answer get_indicators gives for this call.
        assert series.meta.forming_period_included is True


class TestTheHardCap:
    def test_asking_beyond_the_cap_says_the_server_overrode_you(
        self, mocker, live_client
    ):
        # What a capped fetch can really hand back: the depth asked for,
        # plus the bar the builder prepends for the day now trading.
        _daily_returns(
            mocker,
            _series(
                formatters.MAX_BAR_COUNT + 1, datetime.datetime(2026, 8, 30)
            ),
        )

        series = _candles(count=900)

        assert series.count == formatters.MAX_BAR_COUNT
        assert series.meta.truncated is True

    def test_the_cap_is_reported_even_when_the_history_is_short(
        self, mocker, live_client
    ):
        """The fetch was capped too, so nothing can tell us what was missed.

        Reporting False here would claim the 900 bars asked for were all
        there was, which this code is in no position to know.
        """
        _daily_returns(mocker, _series(10, datetime.datetime(2026, 8, 30)))

        series = _candles(count=900)

        assert series.count == 10
        assert series.meta.truncated is True

    def test_asking_for_fewer_bars_is_a_request_being_honoured(
        self, mocker, live_client
    ):
        """truncated is about the cap, never about the caller's own count."""
        _daily_returns(mocker, _series(20, datetime.datetime(2026, 8, 30)))

        series = _candles(count=5)

        assert series.count == 5
        assert series.meta.truncated is False

    def test_the_fetch_is_sized_to_what_can_be_returned(
        self, mocker, live_client
    ):
        fetch = _daily_returns(
            mocker, _series(10, datetime.datetime(2026, 8, 30))
        )

        _candles(count=900)

        assert fetch.call_args.kwargs["count"] == formatters.MAX_BAR_COUNT


class TestWeeklyCandles:
    def test_the_weekly_series_costs_one_extra_fetch(
        self, mocker, live_client
    ):
        daily = _daily_returns(
            mocker, _series(5, datetime.datetime(2026, 8, 30))
        )
        weekly = mocker.patch.object(
            assets.candle_source,
            "build_weekly_series",
            return_value=_series(5, datetime.datetime(2026, 8, 30)),
        )

        series = _candles(unit_time=UnitTime.W, market=MarketName.EU)

        assert daily.call_args.kwargs["count"] == assets.DAYS_FOR_FORMING_WEEK
        assert weekly.call_args.kwargs["count"] == 100
        assert series.meta.unit_time is UnitTime.W

    def test_the_forming_week_is_flagged_from_the_weekly_bar(
        self, mocker, live_client
    ):
        wednesday = datetime.datetime(2026, 8, 26, tzinfo=datetime.UTC)
        _clock_at(mocker, wednesday)
        _weekly_returns(mocker, _series(5, wednesday))

        series = _candles(unit_time=UnitTime.W, market=MarketName.EU)

        assert series.current_incomplete is True

    def test_a_week_that_closed_earlier_this_year_is_not_in_progress(
        self, mocker, live_client
    ):
        """The ISO week has to match, not just the ISO year."""
        wednesday = datetime.datetime(2026, 8, 26, tzinfo=datetime.UTC)
        _clock_at(mocker, wednesday)
        _weekly_returns(
            mocker, _series(5, wednesday - datetime.timedelta(weeks=6))
        )

        series = _candles(unit_time=UnitTime.W, market=MarketName.EU)

        assert series.current_incomplete is False

    def test_the_week_that_closed_on_friday_is_not_in_progress(
        self, mocker, live_client
    ):
        """ISO weeks run to Sunday, so on a Saturday the week that just
        closed is still 'this week' by the calendar - and build_weekly_series
        prepends nothing then, so row 0 is a finished bar."""
        saturday = datetime.datetime(2026, 8, 29, tzinfo=datetime.UTC)
        _clock_at(mocker, saturday)
        _weekly_returns(mocker, _series(5, saturday))

        series = _candles(unit_time=UnitTime.W, market=MarketName.EU)

        assert series.current_incomplete is False


class TestCandleRejections:
    def test_the_weekly_timeframe_refuses_without_a_market(self, live_client):
        with pytest.raises(ToolError, match="needs a market"):
            _candles(unit_time=UnitTime.W, market=None)

    def test_an_unsupported_timeframe_lists_the_supported_ones(
        self, live_client
    ):
        with pytest.raises(ToolError, match="daily"):
            _candles(unit_time=UnitTime.H1)

    def test_another_venue_is_refused_rather_than_mislabelled(
        self, live_client
    ):
        with pytest.raises(ToolError, match="not supported"):
            _candles(exchange=Exchange.BINANCE)

    def test_the_simulated_client_says_it_has_no_candles(self, mocker):
        """Its empty series would otherwise read as 'this asset has no
        history', which is a different and wrong answer."""
        token = errors._market_client.set(
            (mocker.MagicMock(), Provenance.SIMULATED)
        )
        _daily_returns(mocker, [])
        try:
            with pytest.raises(ToolError, match="simulated client"):
                _candles()
        finally:
            errors._market_client.reset(token)


class TestTheBarCountBoundIsOnTheWire:
    """The schema is the only thing rejecting a nonsense count.

    get_candles has no max(1, ...) of its own, and to_rows no longer floors
    the limit either, so ge=1 in the tool signature is what stops a caller
    asking for zero or negative bars. Nothing else pins it.
    """

    def _schema(self):
        from mcp_server.server import mcp

        tools = asyncio.run(mcp.list_tools())
        tool = next(t for t in tools if t.name == "get_candles")
        return tool.input_schema["properties"]["count"]

    def test_the_schema_forbids_a_count_below_one(self):
        assert self._schema()["minimum"] == 1

    def test_the_schema_names_the_cap_it_does_not_enforce(self):
        """No `le`: a request above the cap is answered and flagged, not
        rejected, which is what keeps meta.truncated reachable."""
        schema = self._schema()

        assert "maximum" not in schema
        assert str(formatters.MAX_BAR_COUNT) in schema["description"]
