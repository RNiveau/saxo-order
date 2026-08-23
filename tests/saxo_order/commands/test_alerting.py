import datetime
from typing import List
from unittest.mock import AsyncMock, MagicMock

import pytest

from model import (
    AlertType,
    Candle,
    ComboSignal,
    Direction,
    SignalStrength,
    UnitTime,
)
from saxo_order.commands.alerting import (
    _build_weekly_candles,
    run_detection_for_asset,
)
from services.indicator_service import COMBO_SETTINGS
from utils.exception import SaxoException


def _make_candles(closes: List[float]) -> List[Candle]:
    base_date = datetime.datetime(2026, 1, 1)
    return [
        Candle(
            lower=c,
            higher=c,
            open=c,
            close=c,
            ut=UnitTime.D,
            date=base_date - datetime.timedelta(days=i),
        )
        for i, c in enumerate(closes)
    ]


def _mm50_touch_candles() -> List[Candle]:
    # close=100.5 → ~0.5% above ma50_last≈100, slope≈5
    return _make_candles([100.5] + [102.1666666667] * 9 + [99.5] * 50)


@pytest.fixture
def saxo_client():
    return MagicMock()


@pytest.fixture
def dynamodb_client():
    client = MagicMock()
    client.store_alerts = AsyncMock()
    return client


@pytest.fixture
def patched_alerting(mocker):
    mocker.patch(
        "saxo_order.commands.alerting._run_double_top", return_value=None
    )
    mocker.patch(
        "saxo_order.commands.alerting._run_containing_candle",
        return_value=None,
    )
    mocker.patch(
        "saxo_order.commands.alerting._run_double_inside_bar",
        return_value=None,
    )
    mocker.patch(
        "saxo_order.commands.alerting._run_congestion_indicator",
        return_value=None,
    )
    mocker.patch(
        "saxo_order.commands.alerting.indicator_service.combo",
        return_value=None,
    )
    return mocker


class TestRunDetectionForAssetMM50Touch:

    async def test_emits_mm50_touch_when_conditions_met(
        self, saxo_client, dynamodb_client, patched_alerting
    ):
        candles = _mm50_touch_candles()
        patched_alerting.patch(
            "saxo_order.commands.alerting._build_candles",
            return_value=candles,
        )

        alerts = await run_detection_for_asset(
            asset_code="TST",
            country_code="xpar",
            exchange="saxo",
            asset_description="Test Asset",
            saxo_uic=12345,
            saxo_client=saxo_client,
            dynamodb_client=dynamodb_client,
        )

        mm50_alerts = [
            a for a in alerts if a.alert_type == AlertType.MM50_TOUCH
        ]
        assert len(mm50_alerts) == 1
        data = mm50_alerts[0].data
        assert "close" in data
        assert "ma50" in data
        assert "distance_pct" in data
        assert "slope" in data
        assert "ma50_slope" in data
        assert data["slope"] == data["ma50_slope"]
        assert mm50_alerts[0].asset_code == "TST"
        assert mm50_alerts[0].country_code == "xpar"
        assert mm50_alerts[0].exchange == "saxo"
        dynamodb_client.store_alerts.assert_awaited_once()

    async def test_no_mm50_touch_when_conditions_not_met(
        self, saxo_client, dynamodb_client, patched_alerting
    ):
        # Flat MA50 (slope ≈ 0) → no MM50_TOUCH
        candles = _make_candles([100.0] * 60)
        patched_alerting.patch(
            "saxo_order.commands.alerting._build_candles",
            return_value=candles,
        )

        alerts = await run_detection_for_asset(
            asset_code="FLAT",
            country_code="xpar",
            exchange="saxo",
            asset_description="Flat Asset",
            saxo_uic=12345,
            saxo_client=saxo_client,
            dynamodb_client=dynamodb_client,
        )

        assert all(a.alert_type != AlertType.MM50_TOUCH for a in alerts)

    async def test_emits_mm50_touch_for_binance_asset_without_country_code(
        self, saxo_client, dynamodb_client, patched_alerting
    ):
        candles = _mm50_touch_candles()
        patched_alerting.patch(
            "saxo_order.commands.alerting._build_candles",
            return_value=candles,
        )

        alerts = await run_detection_for_asset(
            asset_code="BTCUSDT",
            country_code=None,
            exchange="binance",
            asset_description="Bitcoin",
            saxo_uic=99999,
            saxo_client=saxo_client,
            dynamodb_client=dynamodb_client,
        )

        mm50_alerts = [
            a for a in alerts if a.alert_type == AlertType.MM50_TOUCH
        ]
        assert len(mm50_alerts) == 1
        assert mm50_alerts[0].country_code is None
        assert mm50_alerts[0].exchange == "binance"


class TestRunDetectionForAssetMM7Break:

    async def test_emits_mm7_break_when_conditions_met(
        self, patched_alerting, saxo_client, dynamodb_client
    ):
        # close 95 under a 7-MA near 99.3, after 3 candles closing above it
        candles = _make_candles([95.0] + [100.0] * 9)
        patched_alerting.patch(
            "saxo_order.commands.alerting._build_candles",
            return_value=candles,
        )

        alerts = await run_detection_for_asset(
            asset_code="TST",
            country_code="xpar",
            exchange="saxo",
            asset_description="Test Asset",
            saxo_uic=12345,
            saxo_client=saxo_client,
            dynamodb_client=dynamodb_client,
        )

        mm7_alerts = [a for a in alerts if a.alert_type == AlertType.MM7_BREAK]
        assert len(mm7_alerts) == 1
        data = mm7_alerts[0].data
        assert data["direction"] == Direction.SELL.value
        assert data["close"] == 95.0
        assert data["distance_pct"] < 0
        assert data["streak"] >= 3
        assert "mm7" in data
        assert "ma50_slope" in data
        assert mm7_alerts[0].asset_code == "TST"
        dynamodb_client.store_alerts.assert_awaited_once()

    async def test_no_mm7_break_when_price_hugs_the_average(
        self, saxo_client, dynamodb_client, patched_alerting
    ):
        candles = _make_candles([100.0] * 60)
        patched_alerting.patch(
            "saxo_order.commands.alerting._build_candles",
            return_value=candles,
        )

        alerts = await run_detection_for_asset(
            asset_code="FLAT",
            country_code="xpar",
            exchange="saxo",
            asset_description="Flat Asset",
            saxo_uic=12345,
            saxo_client=saxo_client,
            dynamodb_client=dynamodb_client,
        )

        assert all(a.alert_type != AlertType.MM7_BREAK for a in alerts)


class TestStockDeduplication:
    """Test deduplication logic for combining API and manual stocks."""

    def test_deduplication_removes_duplicates_keeps_first(self):
        """Test that duplicate stocks are removed, keeping first occurrence."""
        french_stocks = [
            {"name": "Sanofi (API)", "code": "SAN:xpar", "saxo_uic": 114879}
        ]

        followup_stocks = [
            {"name": "Sanofi (Manual)", "code": "SAN:xpar", "saxo_uic": 99999}
        ]

        all_stocks = french_stocks + followup_stocks

        # Deduplication logic (same as in run_alerting)
        seen = set()
        unique_stocks = []
        for stock in all_stocks:
            if stock["code"] not in seen:
                unique_stocks.append(stock)
                seen.add(stock["code"])

        assert len(unique_stocks) == 1
        # First occurrence (API) should be kept
        assert unique_stocks[0]["name"] == "Sanofi (API)"
        assert unique_stocks[0]["saxo_uic"] == 114879

    def test_deduplication_preserves_unique_stocks(self):
        """Test that unique stocks from both sources are preserved."""
        french_stocks = [
            {"name": "TotalEnergies", "code": "TTE:xpar", "saxo_uic": 111},
            {"name": "Sanofi", "code": "SAN:xpar", "saxo_uic": 222},
        ]

        followup_stocks = [
            {"name": "Apple", "code": "AAPL:xnas", "saxo_uic": 333},
            {"name": "Microsoft", "code": "MSFT:xnas", "saxo_uic": 444},
        ]

        all_stocks = french_stocks + followup_stocks

        # Deduplication logic
        seen = set()
        unique_stocks = []
        for stock in all_stocks:
            if stock["code"] not in seen:
                unique_stocks.append(stock)
                seen.add(stock["code"])

        assert len(unique_stocks) == 4
        codes = [s["code"] for s in unique_stocks]
        assert "TTE:xpar" in codes
        assert "SAN:xpar" in codes
        assert "AAPL:xnas" in codes
        assert "MSFT:xnas" in codes

    def test_deduplication_handles_multiple_duplicates(self):
        """Test deduplication with multiple duplicate entries."""
        french_stocks = [
            {"name": "Stock A v1", "code": "A:xpar", "saxo_uic": 1},
            {"name": "Stock B v1", "code": "B:xpar", "saxo_uic": 2},
        ]

        followup_stocks = [
            {"name": "Stock A v2", "code": "A:xpar", "saxo_uic": 99},
            {"name": "Stock B v2", "code": "B:xpar", "saxo_uic": 98},
            {"name": "Stock C", "code": "C:xpar", "saxo_uic": 3},
        ]

        all_stocks = french_stocks + followup_stocks

        # Deduplication logic
        seen = set()
        unique_stocks = []
        for stock in all_stocks:
            if stock["code"] not in seen:
                unique_stocks.append(stock)
                seen.add(stock["code"])

        assert len(unique_stocks) == 3
        # First occurrences should be kept
        assert unique_stocks[0]["name"] == "Stock A v1"
        assert unique_stocks[1]["name"] == "Stock B v1"
        assert unique_stocks[2]["name"] == "Stock C"


class TestStockTransformation:
    """Test data transformation from Saxo API format to internal format."""

    def test_transform_complete_instrument(self):
        """Test transformation of instrument with all fields."""
        instrument = {
            "Symbol": "TTE:xpar",
            "Description": "TotalEnergies SE",
            "Identifier": 23255427,
        }

        # Transformation logic (same as in fetch_french_stocks)
        stock = {
            "name": instrument.get("Description", ""),
            "code": instrument.get("Symbol", ""),
            "saxo_uic": instrument.get("Identifier"),
        }

        assert stock["name"] == "TotalEnergies SE"
        assert stock["code"] == "TTE:xpar"
        assert stock["saxo_uic"] == 23255427

    def test_transform_missing_description(self):
        """Test transformation with missing Description field."""
        instrument = {"Symbol": "SAN:xpar", "Identifier": 114879}

        stock = {
            "name": instrument.get("Description", ""),
            "code": instrument.get("Symbol", ""),
            "saxo_uic": instrument.get("Identifier"),
        }

        assert stock["name"] == ""
        assert stock["code"] == "SAN:xpar"
        assert stock["saxo_uic"] == 114879

    def test_transform_missing_symbol(self):
        """Test transformation with missing Symbol field."""
        instrument = {"Description": "Test Company", "Identifier": 999}

        stock = {
            "name": instrument.get("Description", ""),
            "code": instrument.get("Symbol", ""),
            "saxo_uic": instrument.get("Identifier"),
        }

        assert stock["name"] == "Test Company"
        assert stock["code"] == ""
        assert stock["saxo_uic"] == 999

    def test_transform_missing_identifier(self):
        """Test transformation with missing Identifier field."""
        instrument = {"Symbol": "MC:xpar", "Description": "LVMH"}

        stock = {
            "name": instrument.get("Description", ""),
            "code": instrument.get("Symbol", ""),
            "saxo_uic": instrument.get("Identifier"),
        }

        assert stock["name"] == "LVMH"
        assert stock["code"] == "MC:xpar"
        assert stock["saxo_uic"] is None


class TestAssetExclusionFiltering:
    """Test exclusion filtering logic in batch alerting."""

    def test_exclusion_filters_out_excluded_assets(self):
        """Test that excluded assets are filtered out from processing."""
        # Input assets
        all_assets = [
            {"name": "Santander", "code": "SAN:xpar", "saxo_uic": 111},
            {"name": "Interparfums", "code": "ITP:xpar", "saxo_uic": 222},
            {"name": "BNP Paribas", "code": "BNP:xpar", "saxo_uic": 333},
        ]

        # Excluded asset IDs (from DynamoDB)
        excluded_asset_ids = ["SAN:xpar", "BNP:xpar"]

        # Exclusion filtering logic (same as in run_alerting)
        original_count = len(all_assets)
        filtered_assets = [
            s for s in all_assets if s["code"] not in excluded_asset_ids
        ]
        filtered_count = original_count - len(filtered_assets)

        # Assertions
        assert len(filtered_assets) == 1
        assert filtered_count == 2
        assert filtered_assets[0]["code"] == "ITP:xpar"
        assert filtered_assets[0]["name"] == "Interparfums"

    def test_exclusion_no_filtering_when_no_exclusions(self):
        """Test that all assets remain when no exclusions are set."""
        # Input assets
        all_assets = [
            {"name": "Santander", "code": "SAN:xpar", "saxo_uic": 111},
            {"name": "Interparfums", "code": "ITP:xpar", "saxo_uic": 222},
            {"name": "BNP Paribas", "code": "BNP:xpar", "saxo_uic": 333},
        ]

        # No excluded assets
        excluded_asset_ids = []

        # Exclusion filtering logic
        original_count = len(all_assets)
        filtered_assets = [
            s for s in all_assets if s["code"] not in excluded_asset_ids
        ]
        filtered_count = original_count - len(filtered_assets)

        # Assertions
        assert len(filtered_assets) == 3
        assert filtered_count == 0
        assert filtered_assets == all_assets

    def test_exclusion_all_assets_excluded(self):
        """Test handling when all assets are excluded."""
        # Input assets
        all_assets = [
            {"name": "Santander", "code": "SAN:xpar", "saxo_uic": 111},
            {"name": "Interparfums", "code": "ITP:xpar", "saxo_uic": 222},
        ]

        # All assets excluded
        excluded_asset_ids = ["SAN:xpar", "ITP:xpar"]

        # Exclusion filtering logic
        original_count = len(all_assets)
        filtered_assets = [
            s for s in all_assets if s["code"] not in excluded_asset_ids
        ]
        filtered_count = original_count - len(filtered_assets)

        # Assertions
        assert len(filtered_assets) == 0
        assert filtered_count == 2
        # In actual implementation, this would trigger early return
        # with Slack notification

    def test_exclusion_preserves_non_excluded_assets(self):
        """Test that non-excluded assets are preserved correctly."""
        # Input assets
        all_assets = [
            {"name": "Stock A", "code": "A:xpar", "saxo_uic": 1},
            {"name": "Stock B", "code": "B:xpar", "saxo_uic": 2},
            {"name": "Stock C", "code": "C:xpar", "saxo_uic": 3},
            {"name": "Stock D", "code": "D:xpar", "saxo_uic": 4},
        ]

        # Exclude middle two assets
        excluded_asset_ids = ["B:xpar", "C:xpar"]

        # Exclusion filtering logic
        filtered_assets = [
            s for s in all_assets if s["code"] not in excluded_asset_ids
        ]

        # Assertions
        assert len(filtered_assets) == 2
        assert filtered_assets[0]["code"] == "A:xpar"
        assert filtered_assets[1]["code"] == "D:xpar"
        # Verify data integrity
        assert filtered_assets[0]["saxo_uic"] == 1
        assert filtered_assets[1]["saxo_uic"] == 4

    def test_exclusion_handles_assets_without_country_code(self):
        """Test exclusion filtering for assets without country code."""
        # Input assets (mix of Saxo with country code and assets without)
        all_assets = [
            {"name": "Santander", "code": "SAN:xpar", "saxo_uic": 111},
            {"name": "Bitcoin", "code": "BTCUSDT", "saxo_uic": None},
            {"name": "Ethereum", "code": "ETHUSDT", "saxo_uic": None},
        ]

        # Exclude Binance assets (no country code)
        excluded_asset_ids = ["BTCUSDT", "ETHUSDT"]

        # Exclusion filtering logic
        filtered_assets = [
            s for s in all_assets if s["code"] not in excluded_asset_ids
        ]

        # Assertions
        assert len(filtered_assets) == 1
        assert filtered_assets[0]["code"] == "SAN:xpar"
        assert filtered_assets[0]["name"] == "Santander"


class TestRunDetectionForAssetIsolatesDetectors:
    """
    Every detector has its own history requirement, and they used to share
    one try/except that also wrapped the DynamoDB write. So the most
    demanding detector decided how much history an asset needed before *any*
    of its alerts were kept, and an unlisted error type escaped the handler
    entirely and aborted the whole scan.
    """

    @staticmethod
    def _saxo_client() -> MagicMock:
        """A bare MagicMock makes `"TickSizeScheme" not in detail` true, which
        sends _run_double_top down a branch that never reads candles[0] - so
        the mock has to carry a tick size scheme for the no-candle case to
        exercise the code path it is about."""
        saxo_client = MagicMock()
        saxo_client.get_asset_detail.return_value = {
            "TickSizeScheme": {
                "DefaultTickSize": 0.01,
                "Elements": [{"HighPrice": 100000, "TickSize": 0.01}],
            }
        }
        return saxo_client

    async def _run(self, mocker, candles: List[Candle]) -> tuple:
        mocker.patch(
            "saxo_order.commands.alerting._build_candles",
            return_value=candles,
        )
        saxo_client = self._saxo_client()
        dynamodb_client = MagicMock()
        dynamodb_client.store_alerts = AsyncMock()
        alerts = await run_detection_for_asset(
            asset_code="TST",
            country_code="xpar",
            exchange="saxo",
            asset_description="Test Asset",
            saxo_uic=12345,
            saxo_client=saxo_client,
            dynamodb_client=dynamodb_client,
        )
        return alerts, dynamodb_client

    async def test_no_candle_is_skipped_without_raising(
        self, mocker, dynamodb_client
    ):
        """A delisted or brand new instrument returns no candle at all. That
        used to reach _run_double_top and raise IndexError, which the
        SaxoException handler did not catch, killing the whole run."""
        alerts, dynamodb_client = await self._run(mocker, [])
        assert alerts == []
        dynamodb_client.store_alerts.assert_not_called()

    @pytest.mark.parametrize("count", [1, 2, 3, 59, 60, 234])
    async def test_short_history_never_raises(self, mocker, count: int):
        alerts, _ = await self._run(mocker, _make_candles([100.0] * count))
        assert isinstance(alerts, list)

    async def test_a_failing_detector_does_not_discard_the_others(
        self, dynamodb_client, mocker
    ):
        """combo raising must not cost the asset its mm50_touch alert, nor
        the DynamoDB write that persists it."""
        mocker.patch(
            "saxo_order.commands.alerting.indicator_service.combo",
            side_effect=SaxoException("Missing candles"),
        )
        mocker.patch(
            "saxo_order.commands.alerting._run_double_top", return_value=None
        )
        mocker.patch(
            "saxo_order.commands.alerting._run_double_bottom",
            return_value=None,
        )
        mocker.patch(
            "saxo_order.commands.alerting._run_containing_candle",
            return_value=None,
        )
        mocker.patch(
            "saxo_order.commands.alerting._run_double_inside_bar",
            return_value=None,
        )
        mocker.patch(
            "saxo_order.commands.alerting._run_congestion_indicator",
            return_value=None,
        )
        alerts, dynamodb_client = await self._run(
            mocker, _mm50_touch_candles()
        )

        assert [a.alert_type for a in alerts] == [AlertType.MM50_TOUCH]
        dynamodb_client.store_alerts.assert_awaited_once()
        assert dynamodb_client.store_alerts.await_args.args[2] == alerts

    async def test_a_failing_store_does_not_raise(self, mocker):
        mocker.patch(
            "saxo_order.commands.alerting._run_congestion_indicator",
            return_value=None,
        )
        mocker.patch(
            "saxo_order.commands.alerting._build_candles",
            return_value=_mm50_touch_candles(),
        )
        dynamodb_client = MagicMock()
        dynamodb_client.store_alerts = AsyncMock(
            side_effect=RuntimeError("dynamo is down")
        )
        alerts = await run_detection_for_asset(
            asset_code="TST",
            country_code="xpar",
            exchange="saxo",
            asset_description="Test Asset",
            saxo_uic=12345,
            saxo_client=self._saxo_client(),
            dynamodb_client=dynamodb_client,
        )
        assert len(alerts) > 0


def _weekly_candles(count: int, base: datetime.datetime) -> List[Candle]:
    return [
        Candle(
            lower=100.0,
            higher=100.0,
            open=100.0,
            close=100.0,
            ut=UnitTime.W,
            date=base - datetime.timedelta(weeks=i),
        )
        for i in range(count)
    ]


class TestBuildWeeklyCandles:
    """
    The provider never returns the week currently trading. The daily candles
    the scan already fetched are that week's elapsed days, so the forming bar
    comes from those rather than from a second purchase.
    """

    def _saxo_client_returning(self, mocker, candles: List[Candle]):
        client = MagicMock()
        client.get_historical_data.return_value = [{"raw": True}]
        mocker.patch(
            "saxo_order.commands.alerting.client_helper.map_data_to_candles",
            return_value=candles,
        )
        return client

    def test_it_prepends_the_forming_week(self, mocker):
        today = datetime.datetime.now(datetime.UTC)
        last_week = today - datetime.timedelta(weeks=1)
        client = self._saxo_client_returning(
            mocker, _weekly_candles(60, last_week)
        )
        forming = Candle(
            lower=1.0,
            higher=2.0,
            open=1.5,
            close=1.8,
            ut=UnitTime.W,
            date=today,
        )
        mocker.patch(
            "saxo_order.commands.alerting."
            "build_current_weekly_candle_from_daily",
            return_value=forming,
        )

        candles = _build_weekly_candles(client, {"saxo_uic": 1}, [])

        assert candles[0] is forming
        assert len(candles) == 61

    def test_it_does_not_prepend_when_the_provider_already_returned_it(
        self, mocker
    ):
        today = datetime.datetime.now(datetime.UTC)
        client = self._saxo_client_returning(
            mocker, _weekly_candles(60, today)
        )
        build = mocker.patch(
            "saxo_order.commands.alerting."
            "build_current_weekly_candle_from_daily",
        )

        candles = _build_weekly_candles(client, {"saxo_uic": 1}, [])

        assert len(candles) == 60
        build.assert_not_called()

    def test_it_ends_at_the_last_completed_week_before_monday_opens(
        self, mocker
    ):
        """No daily candle falls in the current ISO week, so there is nothing
        to assemble a forming bar from."""
        last_week = datetime.datetime.now(datetime.UTC) - datetime.timedelta(
            weeks=1
        )
        client = self._saxo_client_returning(
            mocker, _weekly_candles(60, last_week)
        )
        mocker.patch(
            "saxo_order.commands.alerting."
            "build_current_weekly_candle_from_daily",
            return_value=None,
        )

        candles = _build_weekly_candles(client, {"saxo_uic": 1}, [])

        assert len(candles) == 60

    def test_it_asks_the_provider_for_weekly_bars_once(self, mocker):
        client = self._saxo_client_returning(
            mocker, _weekly_candles(60, datetime.datetime.now(datetime.UTC))
        )

        _build_weekly_candles(client, {"saxo_uic": 42}, [])

        client.get_historical_data.assert_called_once()
        kwargs = client.get_historical_data.call_args[1]
        assert kwargs["horizon"] == 10080
        assert kwargs["count"] == 70


class TestRunDetectionForAssetWeeklyCombo:

    def _weekly_signal(self) -> ComboSignal:
        return ComboSignal(
            price=42.5,
            direction=Direction.BUY,
            has_been_triggered=False,
            strength=SignalStrength.MEDIUM,
            details={"ma50_over_bb": True},
        )

    async def test_it_emits_a_weekly_combo_alert(
        self, saxo_client, dynamodb_client, patched_alerting, mocker
    ):
        candles = _mm50_touch_candles()
        patched_alerting.patch(
            "saxo_order.commands.alerting._build_candles",
            return_value=candles,
        )
        bar_date = datetime.datetime(2026, 8, 17, 0, 0)
        patched_alerting.patch(
            "saxo_order.commands.alerting._build_weekly_candles",
            return_value=[
                Candle(
                    lower=1.0,
                    higher=2.0,
                    open=1.5,
                    close=1.8,
                    ut=UnitTime.W,
                    date=bar_date,
                )
            ],
        )
        signal = self._weekly_signal()
        patched_alerting.patch(
            "saxo_order.commands.alerting.indicator_service.combo",
            side_effect=lambda c, settings=None: (
                signal if settings == COMBO_SETTINGS[UnitTime.W] else None
            ),
        )

        alerts = await run_detection_for_asset(
            asset_code="TST",
            country_code="xpar",
            exchange="saxo",
            asset_description="Test Asset",
            saxo_uic=12345,
            saxo_client=saxo_client,
            dynamodb_client=dynamodb_client,
        )

        weekly = [a for a in alerts if a.alert_type == AlertType.COMBO_WEEKLY]
        assert len(weekly) == 1
        data = weekly[0].data
        assert data["direction"] == "Buy"
        assert data["price"] == 42.5
        assert data["weekly_bar_date"] == "2026-08-17"
        assert data["timeframe"] == UnitTime.W.value
        assert "ma50_slope" in data
        assert not any(a.alert_type == AlertType.COMBO for a in alerts)

    async def test_a_weak_weekly_combo_is_not_emitted(
        self, saxo_client, dynamodb_client, patched_alerting
    ):
        """It met none of its four criteria. Emitting it would spend a whole
        asset entry in the reasoning payload to say nothing."""
        patched_alerting.patch(
            "saxo_order.commands.alerting._build_candles",
            return_value=_mm50_touch_candles(),
        )
        patched_alerting.patch(
            "saxo_order.commands.alerting._build_weekly_candles",
            return_value=[
                Candle(
                    lower=1.0,
                    higher=2.0,
                    open=1.5,
                    close=1.8,
                    ut=UnitTime.W,
                    date=datetime.datetime(2026, 8, 17, 0, 0),
                )
            ],
        )
        weak = ComboSignal(
            price=42.5,
            direction=Direction.BUY,
            has_been_triggered=False,
            strength=SignalStrength.WEAK,
            details={
                "ma50_over_bb": False,
                "price_within_bb": False,
                "strong_ma50": False,
                "both_bb_flat": False,
            },
        )
        patched_alerting.patch(
            "saxo_order.commands.alerting.indicator_service.combo",
            side_effect=lambda c, settings=None: (
                weak if settings == COMBO_SETTINGS[UnitTime.W] else None
            ),
        )

        alerts = await run_detection_for_asset(
            asset_code="TST",
            country_code="xpar",
            exchange="saxo",
            asset_description="Test Asset",
            saxo_uic=12345,
            saxo_client=saxo_client,
            dynamodb_client=dynamodb_client,
        )

        assert all(a.alert_type != AlertType.COMBO_WEEKLY for a in alerts)
        # The asset is still scanned and its other detectors still store.
        assert any(a.alert_type == AlertType.MM50_TOUCH for a in alerts)

    async def test_a_weekly_failure_leaves_the_other_detectors_alone(
        self, saxo_client, dynamodb_client, patched_alerting
    ):
        """One asset's weekly fetch failing is not a reason to lose the
        alerts already found for it, or to stop the scan."""
        candles = _mm50_touch_candles()
        patched_alerting.patch(
            "saxo_order.commands.alerting._build_candles",
            return_value=candles,
        )
        patched_alerting.patch(
            "saxo_order.commands.alerting._build_weekly_candles",
            side_effect=SaxoException("provider said no"),
        )

        alerts = await run_detection_for_asset(
            asset_code="TST",
            country_code="xpar",
            exchange="saxo",
            asset_description="Test Asset",
            saxo_uic=12345,
            saxo_client=saxo_client,
            dynamodb_client=dynamodb_client,
        )

        assert any(a.alert_type == AlertType.MM50_TOUCH for a in alerts)
        assert all(a.alert_type != AlertType.COMBO_WEEKLY for a in alerts)
        dynamodb_client.store_alerts.assert_awaited_once()

    async def test_the_weekly_timeframe_costs_one_extra_request(
        self, saxo_client, dynamodb_client, patched_alerting, mocker
    ):
        """Three would mean the forming week is being fetched separately
        instead of built from the daily candles already in hand."""
        candles = _mm50_touch_candles()
        patched_alerting.patch(
            "saxo_order.commands.alerting._build_candles",
            return_value=candles,
        )
        # Dated last week, so the forming-week branch runs - that branch is
        # where a second fetch would hide.
        mocker.patch(
            "saxo_order.commands.alerting.client_helper.map_data_to_candles",
            return_value=_weekly_candles(
                60,
                datetime.datetime.now(datetime.UTC)
                - datetime.timedelta(weeks=1),
            ),
        )
        saxo_client.get_historical_data.return_value = [{"raw": True}]

        await run_detection_for_asset(
            asset_code="TST",
            country_code="xpar",
            exchange="saxo",
            asset_description="Test Asset",
            saxo_uic=12345,
            saxo_client=saxo_client,
            dynamodb_client=dynamodb_client,
        )

        assert saxo_client.get_historical_data.call_count == 1
