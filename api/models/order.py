from typing import Optional

from pydantic import BaseModel, Field

from model import Direction, OrderType


class OrderRequest(BaseModel):
    """Request model for creating a single order."""

    code: str = Field(..., description="Stock/asset code", min_length=1)
    price: float = Field(..., description="Order price", gt=0)
    quantity: float = Field(..., description="Number of units", gt=0)
    order_type: OrderType = Field(..., description="Order type")
    direction: Direction = Field(..., description="Order direction")
    country_code: str = Field(
        "xpar", description="Market code (default: xpar)"
    )
    stop: Optional[float] = Field(
        None, description="Stop price for risk management", gt=0
    )
    objective: Optional[float] = Field(
        None, description="Objective/target price", gt=0
    )
    strategy: Optional[str] = Field(None, description="Trading strategy")
    signal: Optional[str] = Field(None, description="Trading signal")
    comment: Optional[str] = Field(None, description="Order comment")
    account_key: Optional[str] = Field(
        None, description="Specific account key to use"
    )


class OcoOrderRequest(BaseModel):
    """Request model for creating an OCO (One-Cancels-Other) order."""

    code: str = Field(..., description="Stock/asset code", min_length=1)
    quantity: float = Field(..., description="Number of units", gt=0)
    limit_price: float = Field(..., description="Limit order price", gt=0)
    limit_direction: Direction = Field(
        ..., description="Limit order direction"
    )
    stop_price: float = Field(..., description="Stop order price", gt=0)
    stop_direction: Direction = Field(..., description="Stop order direction")
    country_code: str = Field(
        "xpar", description="Market code (default: xpar)"
    )
    stop: Optional[float] = Field(
        None, description="Stop price for risk management", gt=0
    )
    objective: Optional[float] = Field(
        None, description="Objective/target price", gt=0
    )
    strategy: Optional[str] = Field(None, description="Trading strategy")
    signal: Optional[str] = Field(None, description="Trading signal")
    comment: Optional[str] = Field(None, description="Order comment")
    account_key: Optional[str] = Field(
        None, description="Specific account key to use"
    )


class StopLimitOrderRequest(BaseModel):
    """Request model for creating a stop-limit order."""

    code: str = Field(..., description="Stock/asset code", min_length=1)
    quantity: float = Field(..., description="Number of units", gt=0)
    limit_price: float = Field(..., description="Limit price", gt=0)
    stop_price: float = Field(..., description="Stop trigger price", gt=0)
    country_code: str = Field(
        "xpar", description="Market code (default: xpar)"
    )
    stop: Optional[float] = Field(
        None, description="Stop price for risk management", gt=0
    )
    objective: Optional[float] = Field(
        None, description="Objective/target price", gt=0
    )
    strategy: Optional[str] = Field(None, description="Trading strategy")
    signal: Optional[str] = Field(None, description="Trading signal")
    comment: Optional[str] = Field(None, description="Order comment")
    account_key: Optional[str] = Field(
        None, description="Specific account key to use"
    )


class OrderResponse(BaseModel):
    """Response model for order operations."""

    success: bool = Field(..., description="Whether order was successful")
    message: str = Field(..., description="Human-readable status message")
    order_id: Optional[str] = Field(
        None, description="Order ID if successfully placed"
    )
    details: Optional[dict] = Field(
        None, description="Additional order details"
    )
