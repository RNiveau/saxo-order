from contextlib import asynccontextmanager

import aioboto3
from botocore.config import Config
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routers import (
    alerting,
    asset_details,
    fund,
    homepage,
    indexes,
    indicator,
    order,
    report,
    search,
    tradingview,
    watchlist,
    workflow,
)
from client.aws_client import DynamoDBClient, DynamoDBOperationError
from utils.logger import Logger

logger = Logger.get_logger("api_main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle with async DynamoDB resource."""
    logger.info("Starting saxo-order API...")

    session = aioboto3.Session()
    config = Config(
        max_pool_connections=10,
        connect_timeout=10,
        read_timeout=10,
        tcp_keepalive=True,
        retries={"mode": "standard", "total_max_attempts": 3},
    )

    async with session.resource(
        "dynamodb", region_name="eu-west-1", config=config
    ) as dynamodb:
        app.state.dynamodb = dynamodb
        yield

    stats = DynamoDBClient.get_stats()
    logger.info(
        f"DynamoDB stats on shutdown: "
        f"total_requests={stats['total_requests']}, "
        f"avg_latency={stats['avg_latency_ms']}ms"
    )
    logger.info("Shutting down saxo-order API...")


app = FastAPI(
    title="Saxo Order API",
    description="Backend API for Saxo Order management system",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS for local UI access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DynamoDBOperationError)
async def dynamodb_error_handler(
    request: Request, exc: DynamoDBOperationError
):
    """Return HTTP 503 for DynamoDB failures without exposing internals."""
    logger.error(f"DynamoDB error on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Service temporarily unavailable. Please try again later."
        },
    )


# Include routers
app.include_router(alerting.router)
app.include_router(asset_details.router)
app.include_router(fund.router)
app.include_router(homepage.router)
app.include_router(indexes.router)
app.include_router(indicator.router)
app.include_router(order.router)
app.include_router(report.router)
app.include_router(search.router)
app.include_router(tradingview.router)
app.include_router(watchlist.router)
app.include_router(workflow.router)


@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {"message": "Saxo Order API is running", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
