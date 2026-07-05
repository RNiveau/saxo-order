from pathlib import Path
from unittest.mock import MagicMock

import pytest

from api.services.trade_republic_service import TradeRepublicService
from client.gsheet_client import GSheetClient
from model import AssetType, Currency

FIXTURE_PATH = (
    Path(__file__).parent.parent.parent
    / "services"
    / "files"
    / "trade_republic_sample.csv"
)


@pytest.fixture
def service() -> TradeRepublicService:
    return TradeRepublicService(MagicMock(spec=GSheetClient))


@pytest.fixture
def sample_csv() -> str:
    return FIXTURE_PATH.read_text()


class TestParseCsv:
    def test_parses_well_formed_rows_and_flags_the_malformed_one(
        self, service, sample_csv
    ):
        transactions, errors = service.parse_csv(sample_csv)

        assert len(transactions) == 3
        assert len(errors) == 1
        assert errors[0].row_number == 4
        assert "amount" in errors[0].reason

    def test_cash_interest_row_has_blank_optional_fields(
        self, service, sample_csv
    ):
        transactions, _ = service.parse_csv(sample_csv)
        interest_row = transactions[0]

        assert interest_row.category == "CASH"
        assert interest_row.type == "INTEREST_PAYMENT"
        assert interest_row.amount == -2.97
        assert interest_row.currency == Currency.EURO
        assert interest_row.asset_class is None
        assert interest_row.name is None
        assert interest_row.symbol is None
        assert interest_row.shares is None
        assert interest_row.price is None
        assert (
            interest_row.transaction_id
            == "019ca92b-2e1d-7a63-831a-88c8927ba850"
        )

    def test_stock_trade_row_has_populated_trade_fields(
        self, service, sample_csv
    ):
        transactions, _ = service.parse_csv(sample_csv)
        stock_row = transactions[1]

        assert stock_row.asset_class == AssetType.STOCK
        assert stock_row.name == "Apple Inc."
        assert stock_row.symbol == "US0378331005"
        assert stock_row.shares == 2
        assert stock_row.price == 150.25

    def test_foreign_currency_row_keeps_original_amount_and_rate(
        self, service, sample_csv
    ):
        transactions, _ = service.parse_csv(sample_csv)
        etf_row = transactions[2]

        assert etf_row.asset_class == AssetType.ETF
        assert etf_row.currency == Currency.EURO
        assert etf_row.original_amount == -480.00
        assert etf_row.original_currency == "USD"
        assert etf_row.fx_rate == 1.0862

    def test_asset_class_mapping(self, service, sample_csv):
        transactions, _ = service.parse_csv(sample_csv)

        assert transactions[1].asset_class == AssetType.STOCK  # STOCK
        assert transactions[2].asset_class == AssetType.ETF  # FUND
        assert transactions[0].asset_class is None  # empty

    def test_detects_semicolon_delimiter(self, service):
        header = (
            "datetime;date;account_type;category;type;asset_class;name;"
            "symbol;shares;price;amount;fee;tax;currency;original_amount;"
            "original_currency;fx_rate;description;transaction_id;"
            "counterparty_name;counterparty_iban;payment_reference;mcc_code"
        )
        row = (
            "2026-03-01T11:31:45.309887Z;2026-03-01;DEFAULT;CASH;"
            "INTEREST_PAYMENT;;;;;;-2.97;;;EUR;;;;Interest payment;"
            "019ca92b-2e1d-7a63-831a-88c8927ba850;;;;"
        )
        content = f"{header}\n{row}\n"

        transactions, errors = service.parse_csv(content)

        assert errors == []
        assert len(transactions) == 1
        assert transactions[0].amount == -2.97
        assert transactions[0].transaction_id == (
            "019ca92b-2e1d-7a63-831a-88c8927ba850"
        )

    def test_detects_comma_delimiter(self, service):
        header = (
            "datetime,date,account_type,category,type,asset_class,name,"
            "symbol,shares,price,amount,fee,tax,currency,original_amount,"
            "original_currency,fx_rate,description,transaction_id,"
            "counterparty_name,counterparty_iban,payment_reference,mcc_code"
        )
        row = (
            "2026-03-01T11:31:45.309887Z,2026-03-01,DEFAULT,CASH,"
            "INTEREST_PAYMENT,,,,,,-2.97,,,EUR,,,,Interest payment,"
            "019ca92b-2e1d-7a63-831a-88c8927ba850,,,,"
        )
        content = f"{header}\n{row}\n"

        transactions, errors = service.parse_csv(content)

        assert errors == []
        assert len(transactions) == 1
        assert transactions[0].amount == -2.97
