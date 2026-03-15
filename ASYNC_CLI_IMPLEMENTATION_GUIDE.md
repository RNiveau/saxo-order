# Async/CLI Implementation Guide for saxo-order

**Practical examples and implementation strategies for the saxo-order project**

---

## Current Architecture Analysis

### Existing Pattern in saxo-order

The project uses a **layered synchronous architecture**:

- **CLI Layer** (`saxo_order/commands/`): Click commands - synchronous
- **Service Layer** (`services/`): Business logic - synchronous
- **Client Layer** (`client/`): API clients (SaxoClient, BinanceClient) - synchronous, uses `requests`
- **API Layer** (`api/routers/`): FastAPI with async handlers - asynchronous

**Key Observation:** There's already a mix - FastAPI is async, but the CLI is sync. The business logic (clients/services) is synchronous.

### Where Async Would Help

1. **I/O-Bound Operations**: Making concurrent API calls to Saxo/Binance
2. **Workflow Engine**: Running multiple workflows concurrently
3. **Data Fetching**: Parallel candle/asset data retrieval
4. **FastAPI Integration**: Sharing async logic between CLI and API

---

## Implementation Strategy for saxo-order

### Phase 1: Non-Breaking Changes (Recommended Start)

Use `asyncio.run()` wrapper pattern to enable async code without refactoring existing code.

#### Step 1.1: Create Async Wrapper Utilities

Create `saxo_order/async_utils.py`:

```python
"""Utilities for running async code in synchronous CLI commands."""

import asyncio
import functools
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

def run_async(func: Callable) -> Callable:
    """Decorator to run async functions in synchronous Click commands.

    Usage:
        @click.command()
        @run_async
        async def my_command():
            await some_async_operation()
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        return asyncio.run(func(*args, **kwargs))
    return wrapper
```

#### Step 1.2: Create Async Versions of Services

Extend `services/` with async variants while keeping sync versions:

```python
# services/candles_service_async.py
"""Async version of candles service for concurrent operations."""

import asyncio
from typing import Dict, List
from client.saxo_client import SaxoClient
from model.candle import Candle

class CandlesServiceAsync:
    """Async candles service for concurrent retrieval."""

    def __init__(self, saxo_client: SaxoClient):
        self.client = saxo_client

    async def get_candles_for_assets_concurrent(
        self, assets: List[Dict[str, str]], horizon: int = 30
    ) -> Dict[str, List[Candle]]:
        """Fetch candles for multiple assets concurrently.

        Args:
            assets: List of asset dicts with 'code' and 'country_code'
            horizon: Time horizon in minutes

        Returns:
            Dict mapping asset code to candle list
        """
        tasks = [
            self._fetch_asset_candles(asset, horizon)
            for asset in assets
        ]
        results = await asyncio.gather(*tasks)

        return {
            asset["code"]: candles
            for asset, candles in zip(assets, results)
        }

    async def _fetch_asset_candles(
        self, asset: Dict[str, str], horizon: int
    ) -> List[Candle]:
        """Fetch candles for a single asset (wrapped for async)."""
        # Wrap blocking operation in executor for true concurrency
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.client.get_candles_for_asset(
                code=asset["code"],
                country_code=asset.get("country_code"),
                horizon=horizon,
            ),
        )
```

#### Step 1.3: Update CLI Commands to Use Async Wrapper

Example: `/Users/kiva/codes/saxo-order/saxo_order/commands/workflow.py`

```python
# Modified version with async support
import asyncio
import click
from click.core import Context
from saxo_order.async_utils import run_async
from engines.workflow_engine import WorkflowEngine

# Keep existing sync implementation
def execute_workflow(
    config: str, force_from_disk: bool = False, select_workflow: bool = False
) -> None:
    """Original synchronous implementation."""
    configuration = Configuration(config)
    saxo_client = SaxoClient(configuration)
    candles_service = CandlesService(saxo_client)
    dynamodb_client = DynamoDBClient()
    workflows = load_workflows(force_from_disk)

    # ... existing code ...

    engine = WorkflowEngine(
        workflows=workflows,
        slack_client=WebClient(token=configuration.slack_token),
        candles_service=candles_service,
        saxo_client=saxo_client,
        dynamodb_client=dynamodb_client,
    )
    engine.run()

# Add async variant
async def execute_workflow_async(
    config: str, force_from_disk: bool = False, select_workflow: bool = False
) -> None:
    """Async version allowing concurrent operations."""
    configuration = Configuration(config)
    saxo_client = SaxoClient(configuration)

    # Use async service for concurrent candle fetching
    candles_service = CandlesServiceAsync(saxo_client)

    dynamodb_client = DynamoDBClient()
    workflows = load_workflows(force_from_disk)

    # Can now do concurrent operations
    # Example: fetch candles for multiple assets concurrently
    # assets = [w.index for w in workflows]
    # candles_dict = await candles_service.get_candles_for_assets_concurrent(assets)

    engine = WorkflowEngine(
        workflows=workflows,
        slack_client=WebClient(token=configuration.slack_token),
        candles_service=candles_service,
        saxo_client=saxo_client,
        dynamodb_client=dynamodb_client,
    )
    engine.run()

# Update Click command to use async version
@click.command()
@click.pass_context
@click.option(
    "--force-from-disk",
    type=click.Choice(["y", "n"]),
    required=True,
    default="n",
)
@click.option(
    "--select-workflow",
    type=click.Choice(["y", "n"]),
    required=True,
    default="n",
)
def run(ctx: Context, force_from_disk: str, select_workflow: str):
    """Run workflows."""
    config = ctx.obj["config"]

    # Use async version with asyncio.run()
    asyncio.run(execute_workflow_async(
        config,
        True if force_from_disk == "y" else False,
        True if select_workflow == "y" else False,
    ))
```

### Phase 2: Incremental Async Adoption

As the codebase evolves, gradually make more services async-aware.

#### Option A: Dual Clients (If API + CLI Both Need Optimization)

```python
# client/saxo_client_base.py - Shared logic
class SaxoClientBase:
    """Shared methods between sync and async clients."""

    def __init__(self, configuration: Configuration):
        self.configuration = configuration
        self.session_headers = {
            "Authorization": f"Bearer {configuration.access_token}",
            "Content-Type": "application/json",
        }

    def _build_url(self, endpoint: str) -> str:
        """Build full API URL."""
        return f"{self.configuration.saxo_base_url}{endpoint}"

# client/saxo_client.py (existing sync version)
class SaxoClient(SaxoClientBase):
    """Synchronous Saxo API client using requests."""

    def __init__(self, configuration: Configuration):
        super().__init__(configuration)
        self.session = requests.Session()
        self.session.headers.update(self.session_headers)

    def get_asset(self, code: str, market: Optional[str] = None) -> Dict:
        """Synchronous asset fetch."""
        # Existing implementation
        pass

# client/saxo_async_client.py (new async version)
class SaxoAsyncClient(SaxoClientBase):
    """Asynchronous Saxo API client using aiohttp."""

    def __init__(self, configuration: Configuration):
        super().__init__(configuration)
        self.session: aiohttp.ClientSession = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.session_headers)
        return self

    async def __aexit__(self, *args):
        await self.session.close()

    async def get_asset(self, code: str, market: Optional[str] = None) -> Dict:
        """Asynchronous asset fetch."""
        url = self._build_url(f"/ref/v1/instruments/{code}")
        async with self.session.get(url) as response:
            response.raise_for_status()
            return await response.json()

    async def get_assets_concurrent(self, codes: List[str]) -> Dict[str, Dict]:
        """Fetch multiple assets concurrently."""
        tasks = [self.get_asset(code) for code in codes]
        results = await asyncio.gather(*tasks)
        return {code: result for code, result in zip(codes, results)}
```

#### Option B: Share Service Logic with Shared Base Class

```python
# services/order_service_base.py
class OrderServiceBase:
    """Shared order service logic."""

    def _validate_order(self, order: Order) -> bool:
        """Validation logic (no I/O)."""
        # Validation code
        return True

    def _calculate_fees(self, quantity: float, price: float) -> float:
        """Calculation logic (no I/O)."""
        # Fee calculation
        return quantity * price * 0.001

# services/order_service.py (sync)
class OrderService(OrderServiceBase):
    def __init__(self, saxo_client: SaxoClient):
        self.client = saxo_client

    def place_order(self, order: Order) -> str:
        self._validate_order(order)
        response = self.client.place_order(order)
        return response["id"]

# services/order_service_async.py (async)
class OrderServiceAsync(OrderServiceBase):
    def __init__(self, saxo_client: SaxoAsyncClient):
        self.client = saxo_client

    async def place_order(self, order: Order) -> str:
        self._validate_order(order)
        response = await self.client.place_order(order)
        return response["id"]

    async def place_orders_concurrent(self, orders: List[Order]) -> List[str]:
        """Place multiple orders concurrently."""
        tasks = [self.place_order(order) for order in orders]
        return await asyncio.gather(*tasks)
```

### Phase 3: Full Async Adoption (Optional Long-Term)

If async becomes pervasive, consider:

1. **AsyncClick Migration**: Replace Click with AsyncClick for cleaner syntax
2. **Unified Async Services**: Make all services async-native
3. **Shared FastAPI/CLI Logic**: Both use the same async backends

```python
# Long-term: Single async service used by both CLI and API
class WorkflowService:
    """Unified async workflow service."""

    async def execute(self, workflow_id: str) -> Dict:
        """Execute workflow asynchronously."""
        # Async logic
        pass

# CLI usage
@click.command()
@run_async
async def workflow_run(workflow_id: str):
    service = WorkflowService()
    result = await service.execute(workflow_id)
    click.echo(result)

# API usage (FastAPI)
@app.post("/workflow/{workflow_id}/execute")
async def api_workflow_run(workflow_id: str):
    service = WorkflowService()
    result = await service.execute(workflow_id)
    return result
```

---

## Migration Checklist

### For Each Command That Would Benefit From Async

- [ ] Identify I/O operations (API calls, DB queries)
- [ ] Create async service variant with same interface
- [ ] Add `asyncio.run()` wrapper to Click command
- [ ] Test async logic independently with pytest-asyncio
- [ ] Benchmark performance (should be equivalent or faster)
- [ ] Update documentation
- [ ] Consider backward compatibility

### Testing Async Code

```python
# tests/services/test_candles_service_async.py
import pytest
import asyncio
from services.candles_service_async import CandlesServiceAsync

@pytest.fixture
def mock_saxo_client(mocker):
    """Mock Saxo client for testing."""
    client = mocker.MagicMock()
    return client

@pytest.mark.asyncio
async def test_get_candles_concurrent(mock_saxo_client):
    """Test concurrent candle fetching."""
    service = CandlesServiceAsync(mock_saxo_client)

    assets = [
        {"code": "AAPL", "country_code": "xnas"},
        {"code": "GOOGL", "country_code": "xnas"},
    ]

    # Mock the sync blocking call
    mock_saxo_client.get_candles_for_asset.side_effect = [
        [Candle(...), Candle(...)],
        [Candle(...), Candle(...)],
    ]

    result = await service.get_candles_for_assets_concurrent(assets)

    assert len(result) == 2
    assert "AAPL" in result
    assert "GOOGL" in result

# Run with: poetry run pytest tests/services/test_candles_service_async.py
```

---

## Common Patterns in saxo-order

### Pattern 1: Concurrent API Calls

**Current (Sync):**
```python
assets = [asset1, asset2, asset3]
for asset in assets:
    candles = saxo_client.get_candles(asset)  # Sequential: 3 x 1s = 3s
    process(candles)
```

**With Async:**
```python
async def get_all_candles():
    tasks = [
        saxo_client_async.get_candles(asset)
        for asset in assets
    ]
    return await asyncio.gather(*tasks)  # Concurrent: 1s

@click.command()
@run_async
async def my_command():
    results = await get_all_candles()
```

### Pattern 2: Workflow Execution

**Current:**
```python
def run_workflows(workflows):
    for workflow in workflows:
        execute_workflow(workflow)  # Sequential
```

**With Async:**
```python
async def run_workflows_concurrent(workflows):
    tasks = [
        execute_workflow_async(w)
        for w in workflows
    ]
    await asyncio.gather(*tasks)  # Parallel

@click.command()
@run_async
async def run():
    workflows = load_workflows()
    await run_workflows_concurrent(workflows)
```

### Pattern 3: Fallback to Sync When Needed

```python
async def hybrid_operation():
    """Can mix async and sync code."""
    # Async operation
    result = await async_fetch_data()

    # Fallback to sync if needed (wrapped in executor)
    loop = asyncio.get_event_loop()
    blocking_result = await loop.run_in_executor(
        None,
        sync_blocking_operation
    )

    return result, blocking_result
```

---

## Dependencies to Consider

### Required Packages

```toml
# pyproject.toml additions

[tool.poetry.dependencies]
# Minimal: no new dependencies needed for asyncio.run() pattern

# Optional: For concurrent HTTP in future
aiohttp = "^3.9.0"  # Only if creating SaxoAsyncClient

# Optional: For async testing
pytest-asyncio = "^0.23.0"  # Already should be there
```

### No Breaking Changes

The `asyncio.run()` wrapper approach requires **zero changes** to existing code. You're adding new async variants alongside existing sync code.

---

## Performance Expectations

### Benchmarking Example

```python
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor

def sync_fetch(url):
    """Simulate blocking network call."""
    time.sleep(1)
    return f"fetched {url}"

async def async_fetch(url):
    """Simulate async network call."""
    await asyncio.sleep(1)
    return f"fetched {url}"

async def fetch_multiple_async(urls):
    """Concurrent async fetching."""
    tasks = [async_fetch(url) for url in urls]
    return await asyncio.gather(*tasks)

# Benchmark
urls = ["url1", "url2", "url3"]

# Sync: ~3 seconds
start = time.time()
for url in urls:
    sync_fetch(url)
print(f"Sync: {time.time() - start:.1f}s")

# Async: ~1 second
start = time.time()
asyncio.run(fetch_multiple_async(urls))
print(f"Async: {time.time() - start:.1f}s")
```

**Expected Results:**
- **Sequential sync**: 3 seconds (1s × 3 calls)
- **Concurrent async**: 1 second (1s for all calls in parallel)
- **Speedup**: 3x for 3 concurrent I/O operations

---

## Troubleshooting

### Issue 1: "asyncio.run() cannot be called from a running event loop"

**Cause:** Trying to call `asyncio.run()` from within existing async code.

**Solution:** Don't nest `asyncio.run()`. If already in async context, just `await` directly.

```python
# ✗ WRONG
@click.command()
def command():
    asyncio.run(wrapper())

async def wrapper():
    asyncio.run(inner())  # ERROR!

# ✓ RIGHT: No nesting
async def wrapper():
    await inner()
```

### Issue 2: "RuntimeWarning: coroutine 'X' was never awaited"

**Cause:** Forgetting to `await` or wrap in `asyncio.run()`.

**Solution:** Always either `await` or use `asyncio.run()`.

```python
# ✗ WRONG
def command():
    coroutine = async_function()  # Created but not awaited

# ✓ RIGHT
def command():
    result = asyncio.run(async_function())  # Properly executed
```

### Issue 3: Event Loop Already Closed

**Cause:** Multiple `asyncio.run()` calls can occasionally have issues.

**Solution:** Use `asyncio.set_event_loop_policy()` if needed (rare).

```python
import asyncio
import sys

# For some environments (like Jupyter)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

---

## Recommendation for saxo-order

**Start with Phase 1: asyncio.run() wrapper pattern**

Rationale:
1. ✓ Zero breaking changes
2. ✓ No new dependencies
3. ✓ Gradual adoption possible
4. ✓ Keep existing code as-is
5. ✓ Measurable performance gains for concurrent operations
6. ✓ Can expand later if needed

**Implementation Priority:**
1. `CandlesServiceAsync` - Biggest performance win (concurrent API calls)
2. `WorkflowEngine` - Run multiple workflows in parallel
3. Gradually expand other services as needed

**Timeline:** Implement as requirements emerge, not preemptively.
