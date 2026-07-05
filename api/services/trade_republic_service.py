import csv
import io
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple, Type, Union

from client.gsheet_client import GSheetClient
from model import AssetType, Currency, ParseError, TradeRepublicTransaction
from utils.logger import Logger

logger = Logger.get_logger("trade_republic_service")

REQUIRED_FIELDS = [
    "datetime",
    "date",
    "account_type",
    "category",
    "type",
    "amount",
    "currency",
    "transaction_id",
]

ASSET_CLASS_MAP = {
    "FUND": AssetType.ETF,
    "STOCK": AssetType.STOCK,
}


class TradeRepublicService:
    """Service for parsing Trade Republic CSV exports and exporting
    selected transactions to Google Sheets."""

    def __init__(self, gsheet_client: GSheetClient):
        self.gsheet_client = gsheet_client

    def export_transactions(
        self, transactions: List[TradeRepublicTransaction]
    ) -> int:
        self.gsheet_client.append_etf_dca_rows(transactions)
        return len(transactions)

    def parse_csv(
        self, file_content: str
    ) -> Tuple[List[TradeRepublicTransaction], List[ParseError]]:
        dialect = self._sniff_dialect(file_content)
        reader = csv.DictReader(io.StringIO(file_content), dialect=dialect)

        transactions: List[TradeRepublicTransaction] = []
        errors: List[ParseError] = []

        for row_number, row in enumerate(reader, start=1):
            try:
                transactions.append(self._parse_row(row))
            except ValueError as e:
                errors.append(
                    ParseError(
                        row_number=row_number,
                        raw_line=",".join(v or "" for v in row.values()),
                        reason=str(e),
                    )
                )

        return transactions, errors

    def _sniff_dialect(self, file_content: str) -> Type[csv.Dialect]:
        sample = file_content.splitlines()[0] if file_content else ""
        try:
            return csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            return csv.excel

    def _parse_row(self, row: Dict[str, str]) -> TradeRepublicTransaction:
        missing = [f for f in REQUIRED_FIELDS if not row.get(f)]
        if missing:
            raise ValueError(
                f"missing required field(s): {', '.join(missing)}"
            )

        asset_class_raw = row.get("asset_class") or None
        asset_class = (
            ASSET_CLASS_MAP.get(asset_class_raw) if asset_class_raw else None
        )

        original_currency_raw = row.get("original_currency") or None

        return TradeRepublicTransaction(
            datetime=datetime.fromisoformat(
                row["datetime"].replace("Z", "+00:00")
            ),
            date=date.fromisoformat(row["date"]),
            account_type=row["account_type"],
            category=row["category"],
            type=row["type"],
            amount=float(row["amount"]),
            currency=self._parse_currency(row["currency"]),
            transaction_id=row["transaction_id"],
            asset_class=asset_class,
            name=row.get("name") or None,
            symbol=row.get("symbol") or None,
            shares=self._parse_float(row.get("shares")),
            price=self._parse_float(row.get("price")),
            fee=self._parse_float(row.get("fee")),
            tax=self._parse_float(row.get("tax")),
            original_amount=self._parse_float(row.get("original_amount")),
            original_currency=(
                self._parse_currency(original_currency_raw)
                if original_currency_raw
                else None
            ),
            fx_rate=self._parse_float(row.get("fx_rate")),
            description=row.get("description") or None,
            counterparty_name=row.get("counterparty_name") or None,
            counterparty_iban=row.get("counterparty_iban") or None,
            payment_reference=row.get("payment_reference") or None,
            mcc_code=row.get("mcc_code") or None,
        )

    @staticmethod
    def _parse_float(value: Optional[str]) -> Optional[float]:
        if not value:
            return None
        return float(value)

    @staticmethod
    def _parse_currency(value: str) -> Union[Currency, str]:
        try:
            return Currency.get_value(value)
        except ValueError:
            return value
