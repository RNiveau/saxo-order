from typing import Optional

from pydantic import BaseModel, Field

from model import AssetType, Currency, Direction, ReportOrder


class ReportOrderResponse(BaseModel):
    """Response model for a single report order.

    Maps from model.ReportOrder for API serialization.
    """

    code: str
    name: str
    date: str
    direction: Optional[Direction] = None
    quantity: float
    price: float
    currency: Currency
    asset_type: AssetType
    # Additional fields for frontend display
    price_eur: Optional[float] = None
    total: float
    total_eur: float
    underlying_price: Optional[float] = None

    @classmethod
    def from_report_order(
        cls,
        order: ReportOrder,
        price_eur: Optional[float] = None,
        total_eur: float = 0.0,
    ) -> "ReportOrderResponse":
        """Convert a ReportOrder domain model to API response."""
        # Handle asset_type which can be either AssetType enum or string
        asset_type_value = (
            order.asset_type
            if isinstance(order.asset_type, AssetType)
            else AssetType.get_value(order.asset_type)
        )

        return cls(
            code=order.code,
            name=order.name,
            date=order.date.isoformat(),
            direction=order.direction,
            quantity=order.quantity,
            price=order.price,
            currency=order.currency,
            asset_type=asset_type_value,
            price_eur=price_eur if order.currency != Currency.EURO else None,
            total=order.price * order.quantity,
            total_eur=total_eur,
            underlying_price=(
                order.underlying.price if order.underlying else None
            ),
        )


class ReportListResponse(BaseModel):
    """Response model for list of report orders."""

    orders: list[ReportOrderResponse]
    total_count: int = Field(..., description="Total number of orders")
    from_date: str


class ReportSummaryResponse(BaseModel):
    """Response model for report summary statistics."""

    total_orders: int
    total_volume_eur: float
    total_fees_eur: float
    buy_orders: int
    buy_volume_eur: float
    sell_orders: int
    sell_volume_eur: float


class CreateGSheetOrderRequest(BaseModel):
    """Request model for creating order in Google Sheets."""

    account_id: str
    from_date: str  # Date used to fetch orders
    order_index: int  # Index in the orders list
    stop: Optional[float] = None
    objective: Optional[float] = None
    strategy: Optional[str] = None
    signal: Optional[str] = None
    comment: Optional[str] = None


class UpdateGSheetOrderRequest(BaseModel):
    """Request model for updating order in Google Sheets."""

    account_id: str
    from_date: str  # Date used to fetch orders
    order_index: int  # Index in the orders list
    line_number: int  # Sheet row to update
    close: bool = False  # Whether to close the position
    stopped: bool = False
    be_stopped: bool = False
    stop: Optional[float] = None
    objective: Optional[float] = None
    strategy: Optional[str] = None
    signal: Optional[str] = None
    comment: Optional[str] = None
