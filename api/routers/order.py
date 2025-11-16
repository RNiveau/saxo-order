from fastapi import APIRouter, Depends, HTTPException
from slack_sdk import WebClient

from api.dependencies import (
    get_configuration,
    get_gsheet_client,
    get_saxo_client,
)
from api.models.order import (
    OcoOrderRequest,
    OrderRequest,
    OrderResponse,
    StopLimitOrderRequest,
)
from client.gsheet_client import GSheetClient
from client.saxo_client import SaxoClient
from model import Direction
from saxo_order.service import calculate_currency
from saxo_order.services.order_service import OrderService
from utils.configuration import Configuration
from utils.exception import SaxoException
from utils.logger import Logger

router = APIRouter(prefix="/api/orders", tags=["orders"])
logger = Logger.get_logger("order_router")


def _log_order_to_gsheet(
    gsheet_client: GSheetClient,
    configuration: Configuration,
    order,
    account,
):
    """Log order to Google Sheets and Slack (mirrors CLI behavior)."""
    try:
        new_order = calculate_currency(order, configuration.currencies_rate)
        result = gsheet_client.create_order(account, new_order, order)
        updated_range = result["updates"]["updatedRange"]
        logger.info(f"Order logged to Google Sheets: {updated_range}")

        slack_client = WebClient(token=configuration.slack_token)
        slack_client.chat_postMessage(
            channel="#execution-logs",
            text=f"New order created: {new_order.name} "
            f"({new_order.code}) - {new_order.direction} "
            f"{new_order.quantity} at {new_order.price:.4f}$",
        )
    except Exception as e:
        logger.error(f"Failed to log order to Google Sheets/Slack: {e}")


@router.post("", response_model=OrderResponse)
async def create_order(
    request: OrderRequest,
    client: SaxoClient = Depends(get_saxo_client),
    configuration: Configuration = Depends(get_configuration),
    gsheet_client: GSheetClient = Depends(get_gsheet_client),
):
    """
    Create and place a single order.

    This endpoint accepts the same parameters as the CLI command
    and uses the same validation logic.
    """
    try:
        order_service = OrderService(client, configuration)
        result = order_service.create_order(
            code=request.code,
            price=request.price,
            quantity=request.quantity,
            order_type=request.order_type,
            direction=request.direction,
            country_code=request.country_code,
            stop=request.stop,
            objective=request.objective,
            strategy=request.strategy,
            signal=request.signal,
            comment=request.comment,
            account_key=request.account_key,
        )

        # Log BUY orders to Google Sheets (same as CLI behavior)
        if request.direction == Direction.BUY and "order" in result:
            account_key = (
                request.account_key
                or client.get_accounts()["Data"][0]["AccountKey"]
            )
            account = client.get_account(account_key)
            _log_order_to_gsheet(
                gsheet_client, configuration, result["order"], account
            )

        return OrderResponse(
            success=True,
            message=f"Order for {request.code} placed successfully",
            order_id=str(result.get("result", {}).get("OrderId")),
            details={
                "code": request.code,
                "price": request.price,
                "quantity": request.quantity,
                "direction": request.direction,
                "order_type": request.order_type,
            },
        )

    except SaxoException as e:
        logger.error(f"Saxo error during order creation: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during order creation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/oco", response_model=OrderResponse)
async def create_oco_order(
    request: OcoOrderRequest,
    client: SaxoClient = Depends(get_saxo_client),
    configuration: Configuration = Depends(get_configuration),
    gsheet_client: GSheetClient = Depends(get_gsheet_client),
):
    """
    Create and place an OCO (One-Cancels-Other) order.

    This endpoint accepts the same parameters as the CLI command
    and uses the same validation logic.
    """
    try:
        order_service = OrderService(client, configuration)
        result = order_service.create_oco_order(
            code=request.code,
            quantity=request.quantity,
            limit_price=request.limit_price,
            limit_direction=request.limit_direction,
            stop_price=request.stop_price,
            stop_direction=request.stop_direction,
            country_code=request.country_code,
            stop=request.stop,
            objective=request.objective,
            strategy=request.strategy,
            signal=request.signal,
            comment=request.comment,
            account_key=request.account_key,
        )

        # Log stop_order to Google Sheets if it's a BUY (same as CLI behavior)
        if request.stop_direction == Direction.BUY and "stop_order" in result:
            account_key = (
                request.account_key
                or client.get_accounts()["Data"][0]["AccountKey"]
            )
            account = client.get_account(account_key)
            _log_order_to_gsheet(
                gsheet_client, configuration, result["stop_order"], account
            )

        return OrderResponse(
            success=True,
            message=f"OCO order for {request.code} placed successfully",
            order_id=str(result.get("result", {}).get("OrderId")),
            details={
                "code": request.code,
                "limit_price": request.limit_price,
                "limit_direction": request.limit_direction,
                "stop_price": request.stop_price,
                "stop_direction": request.stop_direction,
                "quantity": request.quantity,
            },
        )

    except SaxoException as e:
        logger.error(f"Saxo error during OCO order creation: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during OCO order creation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/stop-limit", response_model=OrderResponse)
async def create_stop_limit_order(
    request: StopLimitOrderRequest,
    client: SaxoClient = Depends(get_saxo_client),
    configuration: Configuration = Depends(get_configuration),
    gsheet_client: GSheetClient = Depends(get_gsheet_client),
):
    """
    Create and place a stop-limit order.

    This endpoint accepts the same parameters as the CLI command
    and uses the same validation logic.
    """
    try:
        order_service = OrderService(client, configuration)
        result = order_service.create_stop_limit_order(
            code=request.code,
            quantity=request.quantity,
            limit_price=request.limit_price,
            stop_price=request.stop_price,
            country_code=request.country_code,
            stop=request.stop,
            objective=request.objective,
            strategy=request.strategy,
            signal=request.signal,
            comment=request.comment,
            account_key=request.account_key,
        )

        # Log order to Google Sheets (stop-limit orders are always BUY)
        if "order" in result:
            account_key = (
                request.account_key
                or client.get_accounts()["Data"][0]["AccountKey"]
            )
            account = client.get_account(account_key)
            _log_order_to_gsheet(
                gsheet_client, configuration, result["order"], account
            )

        return OrderResponse(
            success=True,
            message=f"Stop-limit order for {request.code} placed successfully",
            order_id=str(result.get("result", {}).get("OrderId")),
            details={
                "code": request.code,
                "limit_price": request.limit_price,
                "stop_price": request.stop_price,
                "quantity": request.quantity,
            },
        )

    except SaxoException as e:
        logger.error(f"Saxo error during stop-limit order creation: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during stop-limit order creation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
