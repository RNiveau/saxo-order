from typing import List, Optional

from pydantic import BaseModel

from model import AssetType, ParseError, TradeRepublicTransaction


class TradeRepublicTransactionResponse(BaseModel):
    """Response model for a single Trade Republic transaction.

    Maps from model.TradeRepublicTransaction for API serialization.
    """

    source: str
    datetime: str
    date: str
    account_type: str
    category: str
    type: str
    asset_class: Optional[AssetType] = None
    name: Optional[str] = None
    symbol: Optional[str] = None
    shares: Optional[float] = None
    price: Optional[float] = None
    amount: float
    fee: Optional[float] = None
    tax: Optional[float] = None
    currency: str
    original_amount: Optional[float] = None
    original_currency: Optional[str] = None
    fx_rate: Optional[float] = None
    description: Optional[str] = None
    transaction_id: str
    counterparty_name: Optional[str] = None
    counterparty_iban: Optional[str] = None
    payment_reference: Optional[str] = None
    mcc_code: Optional[str] = None

    @classmethod
    def from_transaction(
        cls, transaction: TradeRepublicTransaction
    ) -> "TradeRepublicTransactionResponse":
        """Convert a TradeRepublicTransaction domain model to API response."""
        return cls(
            source=transaction.source,
            datetime=transaction.datetime.isoformat(),
            date=transaction.date.isoformat(),
            account_type=transaction.account_type,
            category=transaction.category,
            type=transaction.type,
            asset_class=transaction.asset_class,
            name=transaction.name,
            symbol=transaction.symbol,
            shares=transaction.shares,
            price=transaction.price,
            amount=transaction.amount,
            fee=transaction.fee,
            tax=transaction.tax,
            currency=transaction.currency,
            original_amount=transaction.original_amount,
            original_currency=transaction.original_currency,
            fx_rate=transaction.fx_rate,
            description=transaction.description,
            transaction_id=transaction.transaction_id,
            counterparty_name=transaction.counterparty_name,
            counterparty_iban=transaction.counterparty_iban,
            payment_reference=transaction.payment_reference,
            mcc_code=transaction.mcc_code,
        )


class ParseErrorResponse(BaseModel):
    """Response model for a single row that failed to parse."""

    row_number: int
    raw_line: str
    reason: str

    @classmethod
    def from_parse_error(cls, error: ParseError) -> "ParseErrorResponse":
        return cls(
            row_number=error.row_number,
            raw_line=error.raw_line,
            reason=error.reason,
        )


class UploadTradeRepublicResponse(BaseModel):
    """Response model for a parsed Trade Republic CSV upload."""

    transactions: List[TradeRepublicTransactionResponse]
    errors: List[ParseErrorResponse]
    total_rows: int


class ExportTradeRepublicRequest(BaseModel):
    """Request model to export selected transactions to Google Sheets."""

    transactions: List[TradeRepublicTransactionResponse]


class ExportTradeRepublicResponse(BaseModel):
    """Response model for a Google Sheets export attempt."""

    status: str
    exported_count: int
