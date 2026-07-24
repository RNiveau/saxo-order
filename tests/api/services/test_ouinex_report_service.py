from datetime import datetime
from unittest.mock import MagicMock, patch

from api.services.ouinex_report_service import OuinexReportService
from model import (
    AssetType,
    Currency,
    Direction,
    ReportOrder,
    Signal,
    Strategy,
    crypto_account,
)


def _make_service() -> OuinexReportService:
    configuration = MagicMock()
    configuration.currencies_rate = {"usdeur": 0.5}
    configuration.gsheet_creds_path = "creds.json"
    configuration.spreadsheet_id = "sheet-id"

    with patch("api.services.ouinex_report_service.GSheetClient"):
        service = OuinexReportService(MagicMock(), configuration)
    service.gsheet_client = MagicMock()
    return service


def _make_order() -> ReportOrder:
    return ReportOrder(
        code="BTC",
        name="BTC",
        price=50000,
        quantity=0.1,
        direction=Direction.BUY,
        asset_type=AssetType.CRYPTO,
        date=datetime(2023, 1, 1),
        currency=Currency.USD,
    )


class TestOuinexReportServiceMapAsBinance:
    def test_create_gsheet_order_uses_binance_identity(self):
        service = _make_service()
        order = _make_order()

        service.create_gsheet_order(
            account_id="ouinex_main",
            order=order,
            strategy=Strategy.YOLO,
            signal=Signal.NONE,
        )

        service.gsheet_client.create_order.assert_called_once()
        account = service.gsheet_client.create_order.call_args.kwargs[
            "account"
        ]
        assert account == crypto_account()
        assert account.name == "Coinbase"
        assert account.key == "binance"
