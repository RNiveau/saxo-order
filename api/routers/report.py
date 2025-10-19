from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_configuration, get_saxo_client
from api.models.report import (
    CreateGSheetOrderRequest,
    ReportListResponse,
    ReportOrderResponse,
    ReportSummaryResponse,
    UpdateGSheetOrderRequest,
)
from api.services.report_service import ReportService
from client.saxo_client import SaxoClient
from utils.configuration import Configuration
from utils.exception import SaxoException
from utils.logger import Logger

router = APIRouter(prefix="/api/report", tags=["report"])
logger = Logger.get_logger("report_router")


@router.get("/orders", response_model=ReportListResponse)
async def get_report_orders(
    account_id: str = Query(..., description="Saxo account ID"),
    from_date: str = Query(..., description="Start date (YYYY-MM-DD format)"),
    to_date: Optional[str] = Query(None, description="End date (optional)"),
    client: SaxoClient = Depends(get_saxo_client),
    config: Configuration = Depends(get_configuration),
):
    """
    Get trading report orders for a specific account and date range.

    Returns a list of executed orders with currency conversion and
    summary data.
    """
    try:
        report_service = ReportService(client, config)
        orders = report_service.get_orders_report(
            account_id, from_date, to_date
        )

        # Convert orders to response format
        order_responses = []
        for order in orders:
            price_eur, total_eur, _, _ = report_service.convert_order_to_eur(
                order
            )

            order_responses.append(
                ReportOrderResponse(
                    code=order.code,
                    name=order.name,
                    date=order.date.isoformat(),
                    direction=(
                        order.direction.value if order.direction else "UNKNOWN"
                    ),
                    quantity=order.quantity,
                    price=order.price,
                    price_eur=(
                        price_eur if order.currency.value != "EURO" else None
                    ),
                    total=order.price * order.quantity,
                    total_eur=total_eur,
                    currency=order.currency.value,
                    asset_type=(
                        order.asset_type.value
                        if hasattr(order.asset_type, "value")
                        else str(order.asset_type)
                    ),
                    underlying_price=(
                        order.underlying.price if order.underlying else None
                    ),
                )
            )

        return ReportListResponse(
            orders=order_responses,
            total_count=len(order_responses),
            from_date=from_date,
            to_date=to_date,
        )

    except ValueError as e:
        logger.error(f"Invalid request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except SaxoException as e:
        logger.error(f"Saxo error getting report: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback

        logger.error(f"Unexpected error getting report: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/summary", response_model=ReportSummaryResponse)
async def get_report_summary(
    account_id: str = Query(..., description="Saxo account ID"),
    from_date: str = Query(..., description="Start date (YYYY-MM-DD format)"),
    to_date: Optional[str] = Query(None, description="End date (optional)"),
    client: SaxoClient = Depends(get_saxo_client),
    config: Configuration = Depends(get_configuration),
):
    """
    Get summary statistics for trading report.

    Returns aggregated data like total orders, volume, fees, etc.
    """
    try:
        report_service = ReportService(client, config)
        orders = report_service.get_orders_report(
            account_id, from_date, to_date
        )

        summary = report_service.calculate_summary(orders)
        return ReportSummaryResponse(**summary)

    except ValueError as e:
        logger.error(f"Invalid request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except SaxoException as e:
        logger.error(f"Saxo error getting summary: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting summary: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/gsheet/create")
async def create_gsheet_order(
    request: CreateGSheetOrderRequest,
    client: SaxoClient = Depends(get_saxo_client),
    config: Configuration = Depends(get_configuration),
):
    """
    Create a new order entry in Google Sheets.

    This opens a new position with stop loss, target, and strategy tracking.
    """
    try:
        report_service = ReportService(client, config)

        # Get orders using the same from_date as the frontend used
        orders = report_service.get_orders_report(
            request.account_id, from_date=request.from_date
        )

        if request.order_index >= len(orders):
            raise HTTPException(status_code=400, detail="Invalid order index")

        order = orders[request.order_index]

        # Create in Google Sheets
        report_service.create_gsheet_order(
            account_id=request.account_id,
            order=order,
            stop=request.stop,
            objective=request.objective,
            strategy=request.strategy,
            signal=request.signal,
            comment=request.comment,
        )

        return {
            "status": "success",
            "message": "Order created in Google Sheets",
        }

    except ValueError as e:
        logger.error(f"Invalid request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating order in Google Sheets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gsheet/update")
async def update_gsheet_order(
    request: UpdateGSheetOrderRequest,
    client: SaxoClient = Depends(get_saxo_client),
    config: Configuration = Depends(get_configuration),
):
    """
    Update an existing order entry in Google Sheets.

    This can either update an open position or close it.
    """
    try:
        report_service = ReportService(client, config)

        # Get orders using the same from_date as the frontend used
        orders = report_service.get_orders_report(
            request.account_id, from_date=request.from_date
        )

        if request.order_index >= len(orders):
            raise HTTPException(status_code=400, detail="Invalid order index")

        order = orders[request.order_index]

        # Update in Google Sheets
        report_service.update_gsheet_order(
            account_id=request.account_id,
            order=order,
            line_number=request.line_number,
            stopped=request.stopped,
            be_stopped=request.be_stopped,
            stop=request.stop,
            objective=request.objective,
            strategy=request.strategy,
            signal=request.signal,
            comment=request.comment,
        )

        return {
            "status": "success",
            "message": "Order updated in Google Sheets",
        }

    except ValueError as e:
        logger.error(f"Invalid request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating order in Google Sheets: {e}")
        raise HTTPException(status_code=500, detail=str(e))
