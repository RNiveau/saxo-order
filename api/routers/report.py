from typing import Union

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import (
    get_binance_client,
    get_configuration,
    get_saxo_client,
)
from api.models.report import (
    CreateGSheetOrderRequest,
    ReportListResponse,
    ReportOrderResponse,
    ReportSummaryResponse,
    UpdateGSheetOrderRequest,
)
from api.services.binance_report_service import BinanceReportService
from api.services.report_service import ReportService
from client.binance_client import BinanceClient
from client.saxo_client import SaxoClient
from model import Signal, Strategy
from utils.configuration import Configuration
from utils.exception import SaxoException
from utils.logger import Logger

router = APIRouter(prefix="/api/report", tags=["report"])
logger = Logger.get_logger("report_router")


@router.get("/config")
async def get_report_config():
    """Get report configuration including strategies and signals."""
    return {
        "strategies": [{"value": s.name, "label": s.value} for s in Strategy],
        "signals": [{"value": s.name, "label": s.value} for s in Signal],
    }


@router.get("/orders", response_model=ReportListResponse)
async def get_report_orders(
    account_id: str = Query(..., description="Account ID (Saxo or Binance)"),
    from_date: str = Query(..., description="Start date (YYYY-MM-DD format)"),
    saxo_client: SaxoClient = Depends(get_saxo_client),
    binance_client: BinanceClient = Depends(get_binance_client),
    config: Configuration = Depends(get_configuration),
):
    """
    Get trading report orders for a specific account from a given date.

    Supports both Saxo and Binance accounts. Binance accounts use the
    "binance_" prefix in account_id.

    Returns a list of executed orders with currency conversion and
    summary data.
    """
    try:
        # Route to appropriate service based on account_id prefix
        report_service: Union[BinanceReportService, ReportService]
        if account_id.startswith("binance_"):
            report_service = BinanceReportService(binance_client, config)
        else:
            report_service = ReportService(saxo_client, config)

        orders = report_service.get_orders_report(account_id, from_date)

        # Convert orders to response format
        order_responses = []
        for order in orders:
            price_eur, total_eur, _, _ = report_service.convert_order_to_eur(
                order
            )
            order_responses.append(
                ReportOrderResponse.from_report_order(
                    order, price_eur=price_eur, total_eur=total_eur
                )
            )

        return ReportListResponse(
            orders=order_responses,
            total_count=len(order_responses),
            from_date=from_date,
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
    account_id: str = Query(..., description="Account ID (Saxo or Binance)"),
    from_date: str = Query(..., description="Start date (YYYY-MM-DD format)"),
    saxo_client: SaxoClient = Depends(get_saxo_client),
    binance_client: BinanceClient = Depends(get_binance_client),
    config: Configuration = Depends(get_configuration),
):
    """
    Get summary statistics for trading report.

    Supports both Saxo and Binance accounts.

    Returns aggregated data like total orders, volume, fees, etc.
    """
    try:
        # Route to appropriate service based on account_id prefix
        report_service: Union[BinanceReportService, ReportService]
        if account_id.startswith("binance_"):
            report_service = BinanceReportService(binance_client, config)
        else:
            report_service = ReportService(saxo_client, config)

        orders = report_service.get_orders_report(account_id, from_date)

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
    saxo_client: SaxoClient = Depends(get_saxo_client),
    binance_client: BinanceClient = Depends(get_binance_client),
    config: Configuration = Depends(get_configuration),
):
    """
    Create a new order entry in Google Sheets.

    Supports both Saxo and Binance accounts.

    This opens a new position with stop loss, target, and strategy tracking.
    """
    try:
        # Route to appropriate service based on account_id prefix
        report_service: Union[BinanceReportService, ReportService]
        if request.account_id.startswith("binance_"):
            report_service = BinanceReportService(binance_client, config)
        else:
            report_service = ReportService(saxo_client, config)

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
    saxo_client: SaxoClient = Depends(get_saxo_client),
    binance_client: BinanceClient = Depends(get_binance_client),
    config: Configuration = Depends(get_configuration),
):
    """
    Update an existing order entry in Google Sheets.

    Supports both Saxo and Binance accounts.

    This can either update an open position or close it.
    """
    try:
        # Route to appropriate service based on account_id prefix
        report_service: Union[BinanceReportService, ReportService]
        if request.account_id.startswith("binance_"):
            report_service = BinanceReportService(binance_client, config)
        else:
            report_service = ReportService(saxo_client, config)

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
            close=request.close,
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
