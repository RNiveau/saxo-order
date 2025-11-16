from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_saxo_client
from api.models.fund import (
    AccountInfo,
    AccountsListResponse,
    AvailableFundResponse,
)
from api.services.fund_service import FundService
from client.saxo_client import SaxoClient
from utils.exception import SaxoException
from utils.logger import Logger

router = APIRouter(prefix="/api/fund", tags=["fund"])
logger = Logger.get_logger("fund_router")


@router.get("/accounts", response_model=AccountsListResponse)
async def get_accounts(client: SaxoClient = Depends(get_saxo_client)):
    """Get list of all available accounts."""
    try:
        fund_service = FundService(client)
        accounts = fund_service.get_accounts()

        account_list = []
        for acc in accounts:
            account_key = acc["AccountKey"]
            try:
                # Get DisplayName from the account list
                account_name = acc.get("DisplayName", "NoName")

                # Use get_account to fetch balance details
                account = client.get_account(account_key)
                account_list.append(
                    AccountInfo(
                        account_id=acc["AccountId"],
                        account_key=account_key,
                        account_name=account_name,
                        total_fund=account.fund,
                        available_fund=account.available_fund,
                    )
                )
            except Exception as e:
                logger.error(
                    f"Error getting account details for {account_key}: {e}"
                )
                continue

        return AccountsListResponse(accounts=account_list)
    except SaxoException as e:
        logger.error(f"Saxo error getting accounts: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting accounts: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/available", response_model=AvailableFundResponse)
async def get_available_fund(
    account_id: Optional[str] = Query(
        None,
        description="Saxo account ID. If not provided, uses default",
    ),
    client: SaxoClient = Depends(get_saxo_client),
):
    """
    Get available funds for trading.

    This endpoint calculates the actual available funds by subtracting
    open buy order commitments from the available fund reported by Saxo.

    If no account_id is provided, uses the default (first) account.
    """
    try:
        fund_service = FundService(client)

        # If no account_id provided, get the default account
        if not account_id:
            accounts = fund_service.get_accounts()
            if not accounts:
                raise HTTPException(
                    status_code=404, detail="No accounts found"
                )
            account_id = accounts[0]["AccountId"]

        result = fund_service.calculate_available_fund(account_id)

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        return AvailableFundResponse(**result)

    except HTTPException:
        raise
    except SaxoException as e:
        logger.error(f"Saxo error calculating available fund: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error calculating available fund: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
