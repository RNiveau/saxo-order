from typing import Optional

from pydantic import BaseModel, Field


class ReportOrderResponse(BaseModel):
    """Response model for a single report order."""

    code: str
    name: str
    date: str
    direction: str  # BUY or SELL
    quantity: float
    price: float
    price_eur: Optional[float] = None
    total: float
    total_eur: Optional[float] = None
    currency: str
    asset_type: str
    underlying_price: Optional[float] = None


class ReportListResponse(BaseModel):
    """Response model for list of report orders."""

    orders: list[ReportOrderResponse]
    total_count: int = Field(..., description="Total number of orders")
    from_date: str
    to_date: Optional[str] = None


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
    stopped: bool = False
    be_stopped: bool = False
    stop: Optional[float] = None
    objective: Optional[float] = None
    strategy: Optional[str] = None
    signal: Optional[str] = None
    comment: Optional[str] = None
