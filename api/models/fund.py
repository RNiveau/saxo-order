from typing import List, Optional

from pydantic import BaseModel, Field


class AccountInfo(BaseModel):
    account_id: str = Field(description="Saxo account ID")
    account_key: str = Field(
        description="Saxo account key (use for order creation)"
    )
    account_name: str = Field(description="Display name of the account")
    total_fund: float = Field(description="Total cash balance")
    available_fund: float = Field(description="Available cash for trading")


class AvailableFundResponse(BaseModel):
    account_id: str = Field(description="Saxo account ID")
    account_name: str = Field(description="Display name of the account")
    total_fund: float = Field(description="Total cash balance")
    available_fund: float = Field(
        description="Available cash for trading from Saxo"
    )
    open_orders_commitment: float = Field(
        description="Total amount committed to open buy orders"
    )
    actual_available_fund: float = Field(
        description="Actual available fund after subtracting open orders"
    )


class AccountsListResponse(BaseModel):
    accounts: List[AccountInfo] = Field(
        description="List of available accounts"
    )


class ErrorResponse(BaseModel):
    error: str = Field(description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")
