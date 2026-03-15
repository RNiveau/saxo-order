# Async/CLI Code Templates - Ready to Use

**Copy-paste ready code templates for implementing async patterns in saxo-order**

---

## Template 1: Basic asyncio.run() Wrapper

### File: `saxo_order/async_utils.py`

```python
"""Utilities for running async code in synchronous Click commands.

This module provides decorators and helpers to bridge between Click's
synchronous design and async/await patterns.
"""

import asyncio
import functools
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def run_async(func: F) -> F:
    """Decorator to run async functions in synchronous Click commands.

    This decorator wraps an async function with asyncio.run(), allowing
    Click commands to call async code without explicit event loop management.

    Usage:
        @click.command()
        @run_async
        async def my_command(arg: str):
            result = await some_async_operation(arg)
            click.echo(result)

    Args:
        func: An async function to be wrapped

    Returns:
        A synchronous wrapper function that calls asyncio.run()
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return asyncio.run(func(*args, **kwargs))
    return wrapper  # type: ignore


def run_async_with_context(func: F) -> F:
    """Variant of run_async that preserves Click context.

    Use this when you need access to Click context in your async function.

    Usage:
        @click.command()
        @click.pass_context
        @run_async_with_context
        async def my_command(ctx: Context, arg: str):
            result = await some_async_operation(arg)
            click.echo(result)
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return asyncio.run(func(*args, **kwargs))
    return wrapper  # type: ignore
```

---

## Template 2: Async Service Implementation

### File: `services/candles_service_async.py`

```python
"""Asynchronous version of CandlesService for concurrent operations.

This module provides async implementations of candle fetching operations
to enable concurrent API calls.
"""

import asyncio
import logging
from typing import Dict, List, Optional

from client.saxo_client import SaxoClient
from model.candle import Candle
from utils.logger import Logger

logger = Logger.get_logger("candles_service_async", logging.DEBUG)


class CandlesServiceAsync:
    """Async candles service for concurrent historical data retrieval."""

    def __init__(self, saxo_client: SaxoClient):
        """Initialize async candles service.

        Args:
            saxo_client: SaxoClient instance for API calls
        """
        self.client = saxo_client

    async def get_candles_for_assets_concurrent(
        self,
        assets: List[Dict[str, Optional[str]]],
        horizon: int = 30,
    ) -> Dict[str, List[Candle]]:
        """Fetch candles for multiple assets concurrently.

        This method fetches historical candle data for multiple assets
        in parallel, significantly reducing total fetch time.

        Args:
            assets: List of asset dicts with 'code' and optional 'country_code'
            horizon: Time horizon in minutes (30, 60, 1440, 10080)

        Returns:
            Dict mapping asset code to list of Candle objects

        Example:
            >>> assets = [
            ...     {"code": "AAPL", "country_code": "xnas"},
            ...     {"code": "GOOGL", "country_code": "xnas"},
            ... ]
            >>> candles = await service.get_candles_for_assets_concurrent(
            ...     assets, horizon=30
            ... )
            >>> print(candles["AAPL"])
            [Candle(...), Candle(...), ...]
        """
        logger.debug(f"Fetching candles for {len(assets)} assets concurrently")

        # Create tasks for all assets
        tasks = [
            self._fetch_asset_candles(asset, horizon)
            for asset in assets
        ]

        # Run all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Build result dictionary, handling any errors
        candles_dict = {}
        for asset, result in zip(assets, results):
            code = asset["code"]
            if isinstance(result, Exception):
                logger.error(f"Error fetching candles for {code}: {result}")
                candles_dict[code] = []
            else:
                candles_dict[code] = result

        return candles_dict

    async def _fetch_asset_candles(
        self,
        asset: Dict[str, Optional[str]],
        horizon: int,
    ) -> List[Candle]:
        """Fetch candles for a single asset (wrapped for async).

        Since SaxoClient uses blocking requests, we wrap the call in
        an executor to avoid blocking the event loop.

        Args:
            asset: Asset dict with 'code' and optional 'country_code'
            horizon: Time horizon in minutes

        Returns:
            List of Candle objects
        """
        code = asset["code"]
        country_code = asset.get("country_code")

        logger.debug(f"Fetching candles for {code}:{country_code} (horizon={horizon})")

        loop = asyncio.get_event_loop()

        try:
            # Run blocking call in thread pool executor
            candles = await loop.run_in_executor(
                None,
                lambda: self.client.get_candles_for_asset(
                    code=code,
                    country_code=country_code,
                    horizon=horizon,
                ),
            )
            logger.debug(f"Fetched {len(candles)} candles for {code}")
            return candles

        except Exception as e:
            logger.error(f"Failed to fetch candles for {code}: {e}")
            raise

    async def get_candles_for_indexes_concurrent(
        self,
        indexes: List[str],
        horizon: int = 30,
    ) -> Dict[str, List[Candle]]:
        """Fetch candles for multiple indexes concurrently.

        Wrapper for common use case with index codes.

        Args:
            indexes: List of index codes (e.g., ["DAX.I", "CAC.I"])
            horizon: Time horizon in minutes

        Returns:
            Dict mapping index code to list of Candle objects
        """
        assets = [{"code": idx, "country_code": None} for idx in indexes]
        return await self.get_candles_for_assets_concurrent(assets, horizon)
```

---

## Template 3: Updated Click Command with Async

### File: `saxo_order/commands/workflow.py` (Modified)

```python
"""Workflow command handlers with async support."""

import asyncio
import logging

import click
from click.core import Context
from slack_sdk import WebClient

from client.aws_client import DynamoDBClient
from client.saxo_client import SaxoClient
from engines.workflow_engine import WorkflowEngine
from engines.workflow_loader import load_workflows
from saxo_order.async_utils import run_async
from saxo_order.commands import catch_exception
from services.candles_service import CandlesService
from services.candles_service_async import CandlesServiceAsync
from utils.configuration import Configuration
from utils.exception import SaxoException
from utils.logger import Logger

logger = Logger.get_logger("workflow", logging.DEBUG)


@click.command()
@click.pass_context
@catch_exception(handle=SaxoException)
@click.option(
    "--force-from-disk",
    type=click.Choice(["y", "n"]),
    required=True,
    default="n",
    help="Load the workflows file from disk",
)
@click.option(
    "--select-workflow",
    type=click.Choice(["y", "n"]),
    required=True,
    default="n",
    help="Select the workflow to run",
)
@run_async
async def run(ctx: Context, force_from_disk: str, select_workflow: str):
    """Run workflows with async support for concurrent operations."""
    config = ctx.obj["config"]
    await execute_workflow_async(
        config,
        True if force_from_disk == "y" else False,
        True if select_workflow == "y" else False,
    )


@click.command()
@click.pass_context
@click.option(
    "--code",
    type=str,
    required=True,
    help="The asset code (e.g., itp, DAX.I)",
)
@click.option(
    "--country-code",
    type=str,
    required=False,
    default="xpar",
    help="The country code of the asset (e.g., xpar)",
)
@click.option(
    "--force-from-disk",
    type=click.Choice(["y", "n"]),
    required=True,
    default="n",
    help="Load the workflows file from disk",
)
@catch_exception(handle=SaxoException)
def asset(ctx: Context, code: str, country_code: str, force_from_disk: str):
    """List all workflows for a specific asset."""
    symbol = f"{code}:{country_code}" if country_code else code
    workflows = load_workflows(True if force_from_disk == "y" else False)

    matching_workflows = [
        w
        for w in workflows
        if w.index.lower() == code.lower() or w.index.lower() == symbol.lower()
    ]

    if not matching_workflows:
        print(f"No workflows found for asset: {symbol}")
        return

    print(f"\nWorkflows for {symbol}:")
    print("=" * 80)
    for workflow in matching_workflows:
        status = "✓ ENABLED" if workflow.enable else "✗ DISABLED"
        dry_run = " [DRY RUN]" if workflow.dry_run else ""
        print(f"\n{workflow.name} - {status}{dry_run}")
        print(f"  Index: {workflow.index}")
        print(f"  CFD: {workflow.cfd}")
        if workflow.end_date:
            print(f"  End Date: {workflow.end_date}")
        print("  Conditions:")
        for cond in workflow.conditions:
            element_str = f" ({cond.element.value})" if cond.element else ""
            print(
                f"    - {cond.indicator.name.value} {cond.indicator.ut.value}"
                f" {cond.close.direction.value} close"
                f" {cond.close.ut.value}{element_str}"
            )
        print("  Trigger:")
        print(
            f"    - {workflow.trigger.signal.value} "
            f"{workflow.trigger.location.value}"
            f" -> {workflow.trigger.order_direction.value}"
            f" (qty: {workflow.trigger.quantity})"
        )
    print("\n" + "=" * 80)
    print(f"Total: {len(matching_workflows)} workflow(s)")


async def execute_workflow_async(
    config: str, force_from_disk: bool = False, select_workflow: bool = False
) -> None:
    """Async version of workflow execution.

    This version uses CandlesServiceAsync for concurrent candle fetching
    when dealing with multiple workflows.

    Args:
        config: Path to configuration file
        force_from_disk: Whether to reload workflows from disk
        select_workflow: Whether to prompt user to select a workflow
    """
    configuration = Configuration(config)
    saxo_client = SaxoClient(configuration)

    # Use async service for better concurrency
    candles_service = CandlesServiceAsync(saxo_client)

    dynamodb_client = DynamoDBClient()
    workflows = load_workflows(force_from_disk)

    if select_workflow is True:
        workflows_select = list(filter(lambda x: x.enable, workflows))
        if len(workflows_select) > 1:
            prompt = "Select the workflow to run:\n"
            for index, workflow in enumerate(workflows_select):
                prompt += f"[{index + 1}] {workflow.name}\n"
            id = input(prompt)
        else:
            id = "1"
        if int(id) < 1 or int(id) > len(workflows_select):
            raise SaxoException("Wrong workflow selection")
        workflows = [workflows_select[int(id) - 1]]

    engine = WorkflowEngine(
        workflows=workflows,
        slack_client=WebClient(token=configuration.slack_token),
        candles_service=candles_service,
        saxo_client=saxo_client,
        dynamodb_client=dynamodb_client,
    )
    engine.run()
```

---

## Template 4: Async Testing

### File: `tests/services/test_candles_service_async.py`

```python
"""Tests for asynchronous candles service."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from model.candle import Candle
from services.candles_service_async import CandlesServiceAsync


@pytest.fixture
def mock_saxo_client():
    """Mock SaxoClient for testing."""
    client = MagicMock()
    return client


@pytest.fixture
def candles_service_async(mock_saxo_client):
    """Create async candles service with mocked client."""
    return CandlesServiceAsync(mock_saxo_client)


@pytest.fixture
def sample_candles():
    """Generate sample candle objects."""
    return [
        Candle(
            timestamp=1000000,
            open=100.0,
            high=102.0,
            low=99.0,
            close=101.0,
            bid=100.5,
            ask=101.5,
        ),
        Candle(
            timestamp=1000060,
            open=101.0,
            high=103.0,
            low=100.0,
            close=102.0,
            bid=101.5,
            ask=102.5,
        ),
    ]


@pytest.mark.asyncio
async def test_get_candles_for_assets_concurrent_success(
    candles_service_async,
    mock_saxo_client,
    sample_candles,
):
    """Test successful concurrent candle fetching for multiple assets."""
    assets = [
        {"code": "AAPL", "country_code": "xnas"},
        {"code": "GOOGL", "country_code": "xnas"},
    ]

    # Mock the sync blocking call
    mock_saxo_client.get_candles_for_asset.side_effect = [
        sample_candles,
        sample_candles,
    ]

    result = await candles_service_async.get_candles_for_assets_concurrent(
        assets, horizon=30
    )

    assert len(result) == 2
    assert "AAPL" in result
    assert "GOOGL" in result
    assert len(result["AAPL"]) == 2
    assert len(result["GOOGL"]) == 2

    # Verify both calls were made
    assert mock_saxo_client.get_candles_for_asset.call_count == 2


@pytest.mark.asyncio
async def test_get_candles_for_assets_concurrent_partial_failure(
    candles_service_async,
    mock_saxo_client,
    sample_candles,
):
    """Test concurrent fetch with partial failure."""
    assets = [
        {"code": "AAPL", "country_code": "xnas"},
        {"code": "INVALID", "country_code": "xnas"},
        {"code": "GOOGL", "country_code": "xnas"},
    ]

    # Mock with one failure
    mock_saxo_client.get_candles_for_asset.side_effect = [
        sample_candles,
        Exception("Asset not found"),
        sample_candles,
    ]

    result = await candles_service_async.get_candles_for_assets_concurrent(
        assets, horizon=30
    )

    assert "AAPL" in result
    assert "INVALID" in result
    assert "GOOGL" in result
    assert len(result["AAPL"]) == 2
    assert len(result["INVALID"]) == 0  # Empty list on error
    assert len(result["GOOGL"]) == 2


@pytest.mark.asyncio
async def test_get_candles_for_indexes_concurrent(
    candles_service_async,
    mock_saxo_client,
    sample_candles,
):
    """Test convenience method for fetching index candles."""
    indexes = ["DAX.I", "CAC.I"]

    mock_saxo_client.get_candles_for_asset.side_effect = [
        sample_candles,
        sample_candles,
    ]

    result = await candles_service_async.get_candles_for_indexes_concurrent(
        indexes, horizon=60
    )

    assert "DAX.I" in result
    assert "CAC.I" in result


@pytest.mark.asyncio
async def test_concurrent_fetch_timing():
    """Test that concurrent fetching is faster than sequential."""
    import time

    async def slow_operation(delay: float) -> str:
        """Simulate slow async operation."""
        await asyncio.sleep(delay)
        return f"done_{delay}"

    # Sequential timing
    start = time.time()
    for _ in range(3):
        await slow_operation(0.1)
    sequential_time = time.time() - start

    # Concurrent timing
    start = time.time()
    tasks = [slow_operation(0.1) for _ in range(3)]
    await asyncio.gather(*tasks)
    concurrent_time = time.time() - start

    # Concurrent should be ~3x faster
    assert concurrent_time < sequential_time * 0.7
    assert concurrent_time < 0.5  # Should complete in ~0.1 + overhead
```

---

## Template 5: Integration with Click Context

### File: `saxo_order/commands/example_async_command.py`

```python
"""Example async command with Click context integration."""

import asyncio

import click
from click.core import Context

from saxo_order.async_utils import run_async


@click.command()
@click.option("--asset-code", required=True, help="Asset code to process")
@click.option("--quantity", type=int, default=1, help="Quantity to process")
@click.pass_context
@run_async
async def process_async(ctx: Context, asset_code: str, quantity: int):
    """Process assets asynchronously.

    This command demonstrates how to use async functions while maintaining
    access to Click context and parameters.
    """
    click.echo(f"Processing {quantity} of {asset_code}...")

    # Access config from Click context
    config = ctx.obj.get("config")

    # Simulate async work
    result = await async_process_asset(asset_code, quantity)

    click.echo(f"Result: {result}")


async def async_process_asset(code: str, quantity: int) -> dict:
    """Simulate async asset processing.

    Args:
        code: Asset code
        quantity: Quantity to process

    Returns:
        Processing result
    """
    # Simulate async I/O
    await asyncio.sleep(0.5)

    return {
        "code": code,
        "quantity": quantity,
        "status": "completed",
    }
```

---

## Template 6: Error Handling with Async

### File: Code pattern for error handling

```python
"""Error handling patterns for async Click commands."""

import asyncio

import click

from saxo_order.async_utils import run_async
from utils.exception import SaxoException


@click.command()
@click.option("--risky", type=bool, default=False)
@run_async
async def handle_errors(risky: bool):
    """Demonstrate error handling in async commands."""
    try:
        if risky:
            raise SaxoException("Simulated error")

        result = await safe_async_operation()
        click.echo(f"Success: {result}")

    except SaxoException as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        raise SystemExit(2)


async def safe_async_operation() -> str:
    """Safe async operation with timeout."""
    try:
        # Set timeout for operation
        result = await asyncio.wait_for(
            long_running_operation(),
            timeout=5.0,
        )
        return result
    except asyncio.TimeoutError:
        raise SaxoException("Operation timed out after 5 seconds")


async def long_running_operation() -> str:
    """Simulate long-running async operation."""
    await asyncio.sleep(1)
    return "operation completed"
```

---

## Template 7: Configuration Setup

### File: `pyproject.toml` additions

```toml
[tool.poetry.dependencies]
# ... existing dependencies ...

# No new dependencies required for asyncio.run() pattern!
# These are optional for enhanced async support:
# pytest-asyncio = "^0.23.0"  # For async test support
# aiohttp = "^3.9.0"  # Only if creating async HTTP clients


[tool.pytest.ini_options]
asyncio_mode = "auto"
markers = [
    "asyncio: marks tests as async (deselect with '-m \"not asyncio\"')",
]
```

---

## Quick Start Checklist

To implement async support in a Click command:

1. **Copy `async_utils.py`** to `/saxo_order/`
2. **Create async service** (e.g., `CandlesServiceAsync`)
3. **Update command**:
   ```python
   from saxo_order.async_utils import run_async

   @click.command()
   @run_async
   async def my_command(arg: str):
       result = await async_operation()
   ```
4. **Add tests** using `@pytest.mark.asyncio` decorator
5. **Update pyproject.toml** if using pytest-asyncio

That's it! No other changes needed.

---

## Common Modifications

### Adding Logging to Async Operations

```python
import logging

logger = logging.getLogger(__name__)

async def logged_operation():
    logger.debug("Starting async operation")
    try:
        result = await some_operation()
        logger.info(f"Operation completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        raise
```

### Using asyncio.gather() with Error Handling

```python
async def safe_gather(tasks):
    """Gather tasks with error handling."""
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if not isinstance(r, Exception)]
```

### Adding Timeout to Async Operations

```python
async def operation_with_timeout(coro, timeout=30):
    """Run operation with timeout."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        raise SaxoException(f"Operation timed out after {timeout}s")
```
