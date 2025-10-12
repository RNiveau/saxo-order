from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import fund, indicator, search, watchlist, workflow
from utils.logger import Logger

logger = Logger.get_logger("api_main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    logger.info("Starting saxo-order API...")
    yield
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

# Include routers
app.include_router(fund.router)
app.include_router(indicator.router)
app.include_router(search.router)
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
