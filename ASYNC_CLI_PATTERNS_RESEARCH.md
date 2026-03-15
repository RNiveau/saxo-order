# Async Code in Synchronous CLI Commands: Research & Patterns

**Date:** February 22, 2026
**Research Focus:** Integrating async/await patterns with Click CLI framework

---

## Executive Summary

Click is a synchronous framework and doesn't natively support async command handlers. There are three primary approaches to integrate async code with Click:

1. **asyncio.run() Wrapper** (Simple, Recommended for most cases)
2. **AsyncClick Library** (Drop-in replacement, Modern approach)
3. **Dual Client Pattern** (For libraries supporting both sync/async)

This document covers all patterns with code examples, trade-offs, and best practices.

---

## Pattern 1: asyncio.run() Wrapper (Recommended)

### Overview

The simplest and most practical approach is to wrap async code with `asyncio.run()` directly in Click command handlers. This creates a new event loop, executes the coroutine, and closes the loop.

### Basic Implementation

```python
import asyncio
import click

# Define async logic separately
async def async_operation(param: str) -> str:
    """Async business logic."""
    # Simulate async work
    await asyncio.sleep(0.1)
    return f"Processed: {param}"

# Wrap in Click command
@click.command()
@click.option("--name", prompt="Your name")
def hello(name: str):
    """Synchronous Click command calling async code."""
    result = asyncio.run(async_operation(name))
    click.echo(result)

if __name__ == "__main__":
    hello()
```

### With functools.wraps Decorator

For cleaner code reuse across multiple commands, create a reusable decorator:

```python
import asyncio
import functools
from typing import Callable, Any

def async_command(func: Callable) -> Callable:
    """Decorator to run async functions in Click commands."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        return asyncio.run(func(*args, **kwargs))
    return wrapper

# Usage
@click.command()
@click.option("--count", default=1, type=int)
@async_command
async def process(count: int):
    """Click command with async handler."""
    for i in range(count):
        await asyncio.sleep(0.1)
        click.echo(f"Step {i+1}")

if __name__ == "__main__":
    process()
```

### Running Multiple Async Tasks Concurrently

```python
import asyncio
import click

async def task_a():
    await asyncio.sleep(1)
    return "Task A complete"

async def task_b():
    await asyncio.sleep(1)
    return "Task B complete"

async def run_tasks():
    """Run multiple async tasks concurrently."""
    results = await asyncio.gather(
        task_a(),
        task_b(),
    )
    return results

@click.command()
def execute():
    """Run concurrent async operations."""
    results = asyncio.run(run_tasks())
    for result in results:
        click.echo(result)

if __name__ == "__main__":
    execute()
```

### Pros & Cons

**Advantages:**
- ✓ Simple to implement - minimal code changes
- ✓ Works with standard Click library (no custom forks)
- ✓ Clear separation between async logic and CLI layer
- ✓ Easy to test async functions independently
- ✓ No special event loop management needed
- ✓ `asyncio.run()` handles resource cleanup automatically
- ✓ Python 3.7+ native support

**Disadvantages:**
- ✗ Creates a new event loop for each command (minor overhead)
- ✗ Can't leverage existing event loop from parent process
- ✗ Slightly more boilerplate than fully async CLI
- ✗ No nested async context support (can't call from within existing loop)

### When to Use

**Best for:**
- Most CLI applications
- Standalone commands with async dependencies
- Projects integrating with async libraries (httpx, aiohttp, etc.)
- Gradual async adoption in existing codebases

---

## Pattern 2: AsyncClick Library

### Overview

[AsyncClick](https://pypi.org/project/asyncclick/) is a maintained fork of Click that provides first-class async/await support. It allows async command handlers without wrapper decorators.

### Installation

```bash
pip install asyncclick
```

### Basic Implementation

```python
import asyncclick as click
import asyncio

@click.command()
@click.option("--name", prompt="Your name")
async def hello(name: str):
    """AsyncClick command - handler is natively async."""
    await asyncio.sleep(0.1)
    click.echo(f"Hello, {name}!")

if __name__ == "__main__":
    hello()
```

### Advanced Example with Subcommands

```python
import asyncclick as click

@click.group()
async def cli():
    """Main command group."""
    pass

@cli.command()
@click.option("--count", default=3, type=int)
async def greet(count: int):
    """Async subcommand."""
    for i in range(count):
        await asyncio.sleep(0.1)
        click.echo(f"Greeting {i+1}")

@cli.command()
async def process():
    """Another async subcommand."""
    # Can freely mix sync and async
    click.echo("Starting async operation...")
    await asyncio.sleep(0.5)
    click.echo("Complete!")

if __name__ == "__main__":
    cli()
```

### Mixing Sync and Async Commands

AsyncClick is backward compatible - you can freely mix sync and async handlers:

```python
import asyncclick as click

@click.group()
async def cli():
    pass

@cli.command()
async def async_cmd():
    """Async handler."""
    await asyncio.sleep(0.1)
    click.echo("Async complete")

@cli.command()
def sync_cmd():
    """Synchronous handler - also works."""
    click.echo("Sync complete")

if __name__ == "__main__":
    cli()
```

### Pros & Cons

**Advantages:**
- ✓ Native async/await syntax in command handlers
- ✓ No wrapper boilerplate required
- ✓ Backward compatible with Click (mostly drop-in replacement)
- ✓ Cleaner code for async-heavy applications
- ✓ Advanced async methods available (async context managers, etc.)
- ✓ Supports both asyncio and Trio async backends

**Disadvantages:**
- ✗ Requires dependency on external package
- ✗ Less mature than Click (smaller community)
- ✗ Potential future compatibility risks if diverges from Click
- ✗ Documentation less extensive than Click
- ✗ Breaking changes may occur between versions
- ✗ Requires Python 3.11+

### When to Use

**Best for:**
- New async-first CLI applications
- Heavy async workloads throughout codebase
- Projects using Trio or other async libraries
- Teams wanting cleaner async syntax

### Real-World Example

```python
import asyncclick as click
from typing import List
import aiohttp

@click.group()
async def cli():
    """Async API client CLI."""
    pass

@cli.command()
@click.argument("urls", nargs=-1, required=True)
async def fetch_urls(urls: List[str]):
    """Fetch multiple URLs concurrently."""
    async with aiohttp.ClientSession() as session:
        async def fetch(url: str) -> str:
            async with session.get(url) as response:
                return await response.text()

        tasks = [fetch(url) for url in urls]
        results = await asyncio.gather(*tasks)

        for url, content in zip(urls, results):
            click.echo(f"{url}: {len(content)} bytes")

if __name__ == "__main__":
    cli()
```

---

## Pattern 3: Dual Client Pattern

### Overview

For library code or API clients that need to support both sync and async usage, maintain separate implementations or use code generation.

### Approach A: Separate Client Classes

```python
# client/base.py - Shared logic
class APIBase:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def _build_url(self, endpoint: str) -> str:
        return f"{self.base_url}/{endpoint}"

# client/sync_client.py
import requests

class SyncAPIClient(APIBase):
    def __init__(self, base_url: str):
        super().__init__(base_url)
        self.session = requests.Session()

    def get(self, endpoint: str) -> dict:
        """Synchronous GET request."""
        url = self._build_url(endpoint)
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def post(self, endpoint: str, data: dict) -> dict:
        """Synchronous POST request."""
        url = self._build_url(endpoint)
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

# client/async_client.py
import aiohttp

class AsyncAPIClient(APIBase):
    def __init__(self, base_url: str):
        super().__init__(base_url)
        self.session: aiohttp.ClientSession = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *args):
        await self.session.close()

    async def get(self, endpoint: str) -> dict:
        """Asynchronous GET request."""
        url = self._build_url(endpoint)
        async with self.session.get(url) as response:
            response.raise_for_status()
            return await response.json()

    async def post(self, endpoint: str, data: dict) -> dict:
        """Asynchronous POST request."""
        url = self._build_url(endpoint)
        async with self.session.post(url, json=data) as response:
            response.raise_for_status()
            return await response.json()
```

### Usage in CLI vs API

```python
# CLI: Use sync client
from client.sync_client import SyncAPIClient

@click.command()
@click.option("--endpoint", required=True)
def cli_command(endpoint: str):
    """CLI command using sync client."""
    client = SyncAPIClient("https://api.example.com")
    data = client.get(endpoint)
    click.echo(data)

# API: Use async client
from client.async_client import AsyncAPIClient
from fastapi import FastAPI

@app.get("/data/{endpoint}")
async def api_endpoint(endpoint: str):
    """FastAPI endpoint using async client."""
    async with AsyncAPIClient("https://api.example.com") as client:
        data = await client.get(endpoint)
    return data
```

### Approach B: Using Unasync for Code Generation

For larger libraries, use [Unasync](https://github.com/python-trio/unasync) to auto-generate sync versions from async code:

```python
# Install: pip install unasync

# pyproject.toml
[tool.unasync]
rules = [
    { based_on_regex = "lib/async_client.py", unasync_replace = { "client.async_": "client.sync_" } }
]

# lib/async_client.py (source of truth)
import aiohttp

class AsyncClient:
    async def get(self, url: str) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json()

# After running: python -m unasync
# Generated: lib/sync_client.py (automated from async_client.py)
```

### Using HTTPX (Built-in Dual Support)

The [httpx](https://www.python-httpx.org/) library natively supports both sync and async:

```python
# Sync
import httpx

client = httpx.Client()
response = client.get("https://api.example.com/data")

# Async - same API, different usage
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get("https://api.example.com/data")
```

### Pros & Cons

**Advantages:**
- ✓ Maximum flexibility for different use cases
- ✓ Optimized for each context (CLI doesn't pay async overhead)
- ✓ Clean APIs for both sync and async callers
- ✓ Works seamlessly with existing sync CLI code
- ✓ Can leverage specialized libraries (httpx, httpcore)

**Disadvantages:**
- ✗ Code duplication if not using code generation
- ✗ Maintenance burden for separate implementations
- ✗ More complex build/release pipeline with Unasync
- ✗ Overkill for simple projects
- ✗ Requires careful API compatibility management

### When to Use

**Best for:**
- Libraries used in both CLI and async contexts
- High-performance requirements (avoiding event loop overhead)
- Teams with mature DevOps/release processes
- Large codebases with many async dependencies

---

## Event Loop Lifecycle Management

### Understanding asyncio.run()

```python
import asyncio

async def main():
    print("Async work here")
    await asyncio.sleep(1)

# asyncio.run() does this internally:
# 1. Creates a new event loop
# 2. Runs the coroutine
# 3. Closes the loop
# 4. Releases all resources

result = asyncio.run(main())
```

### Explicit Event Loop Management (Advanced)

Rarely needed with `asyncio.run()`, but shown for completeness:

```python
import asyncio

async def main():
    await asyncio.sleep(1)

# Manual loop management (Python 3.10+)
loop = asyncio.new_event_loop()
try:
    result = loop.run_until_complete(main())
finally:
    loop.close()  # Always close to release resources

# Python 3.7-3.9
# loop = asyncio.get_event_loop()
# try:
#     result = loop.run_until_complete(main())
# finally:
#     loop.close()
```

### Handling Nested Event Loops

**Problem:** Can't call `asyncio.run()` from within an existing event loop.

```python
# This will raise RuntimeError: asyncio.run() cannot be called from a running event loop
async def outer():
    asyncio.run(inner())  # ✗ ERROR

async def inner():
    await asyncio.sleep(1)
```

**Solution:** Use `nest_asyncio` library for special cases:

```python
import asyncio
import nest_asyncio

nest_asyncio.apply()

async def outer():
    asyncio.run(inner())  # ✓ Works (rare edge case)

async def inner():
    await asyncio.sleep(1)
```

> **Note:** This is rarely needed in well-designed architectures. Usually indicates architectural issues.

### Resource Cleanup

`asyncio.run()` automatically handles cleanup:

```python
import asyncio

async def with_resources():
    # Resources are properly cleaned up
    async with aiohttp.ClientSession() as session:
        # Use session
        pass
    # Session is closed here, loop is closed after asyncio.run() returns

asyncio.run(with_resources())
```

---

## Comparison Matrix

| Criterion | asyncio.run() | AsyncClick | Dual Client |
|-----------|--------------|-----------|------------|
| **Ease of Implementation** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **Async Syntax Clarity** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | N/A |
| **Code Reusability** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Performance** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Framework Maturity** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Varies |
| **Maintenance Burden** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **Flexibility** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Learning Curve** | Easy | Easy | Moderate |

---

## Real-World Example: saxo-order Integration

The `saxo-order` project currently uses synchronous Click commands. Here's how each pattern could be adapted:

### Option 1: asyncio.run() Wrapper (Recommended for saxo-order)

```python
# saxo_order/commands/workflow.py (Modified)
import asyncio
import click
from click.core import Context
from engines.workflow_engine import WorkflowEngine

async def execute_workflow_async(config: str, force_from_disk: bool = False) -> None:
    """Async version of workflow execution."""
    configuration = Configuration(config)
    saxo_client = SaxoClient(configuration)
    candles_service = CandlesService(saxo_client)

    # Can now use async operations here if needed
    workflows = await load_workflows_async(force_from_disk)

    engine = WorkflowEngine(workflows=workflows, ...)
    engine.run()

@click.command()
@click.pass_context
def run(ctx: Context, force_from_disk: str, select_workflow: str):
    """Run workflows."""
    config = ctx.obj["config"]

    # Wrap async operation with asyncio.run()
    asyncio.run(execute_workflow_async(
        config,
        True if force_from_disk == "y" else False,
    ))
```

### Option 2: AsyncClick (For heavy async refactor)

```python
# Requires: pip install asyncclick
import asyncclick as click

@click.command()
@click.pass_context
async def run(ctx: Context, force_from_disk: str, select_workflow: str):
    """Run workflows - async handler."""
    config = ctx.obj["config"]
    await execute_workflow_async(
        config,
        True if force_from_disk == "y" else False,
    )
```

### Option 3: Dual Clients (For API + CLI split)

```python
# cli.py - Uses sync client
from client.saxo_sync_client import SaxoSyncClient

@click.command()
def cli_workflow(config: str):
    client = SaxoSyncClient(config)
    client.execute_workflow()

# api/routers/workflow.py - Uses async client
from client.saxo_async_client import SaxoAsyncClient

@app.post("/workflow")
async def api_workflow(config: str):
    async with SaxoAsyncClient(config) as client:
        result = await client.execute_workflow_async()
    return result
```

---

## Best Practices

### 1. Keep Async Logic Separate

```python
# ✓ GOOD: Clear separation
async def business_logic(data: dict) -> dict:
    """Pure async business logic."""
    return {"processed": data}

@click.command()
def command():
    """Click handler."""
    result = asyncio.run(business_logic({"key": "value"}))
    click.echo(result)

# ✗ BAD: Mixed concerns
@click.command()
def command():
    """Click handler with embedded async."""
    async def inline_logic():
        pass
    asyncio.run(inline_logic())
```

### 2. Handle Exceptions Properly

```python
import asyncio
import click
from utils.exception import SaxoException

async def risky_operation() -> None:
    raise SaxoException("Operation failed")

@click.command()
def safe_command():
    """Handle exceptions from async operations."""
    try:
        asyncio.run(risky_operation())
    except SaxoException as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
```

### 3. Test Async Functions Independently

```python
# tests/test_async_logic.py
import pytest
import asyncio

async def async_function(x: int) -> int:
    await asyncio.sleep(0.01)
    return x * 2

@pytest.mark.asyncio
async def test_async_function():
    """Test async function directly."""
    result = await async_function(5)
    assert result == 10

# Or use asyncio.run() in non-async tests
def test_async_with_asyncio_run():
    result = asyncio.run(async_function(5))
    assert result == 10
```

### 4. Use Context Managers for Resource Cleanup

```python
import asyncio
import aiohttp

async def fetch_with_cleanup(url: str) -> str:
    """Proper resource cleanup with async context manager."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()
    # Both are automatically closed here

@click.command()
@click.option("--url", required=True)
def fetch(url: str):
    """Fetch with proper cleanup."""
    content = asyncio.run(fetch_with_cleanup(url))
    click.echo(content)
```

### 5. Leverage asyncio.gather() for Concurrency

```python
import asyncio

async def concurrent_operations(items: list) -> list:
    """Run multiple async operations concurrently."""
    tasks = [process_item(item) for item in items]
    results = await asyncio.gather(*tasks)
    return results

async def process_item(item: str) -> str:
    await asyncio.sleep(0.1)
    return f"processed: {item}"
```

---

## Decision Tree

```
Do you have async dependencies?
├─ NO → Use standard Click (no changes needed)
└─ YES → Do you want native async syntax in handlers?
    ├─ NO → Use asyncio.run() wrapper (RECOMMENDED)
    │   └─ Pros: Simple, standard library, minimal changes
    │   └─ Cons: New event loop per command
    ├─ YES (light async) → Use AsyncClick
    │   └─ Pros: Clean syntax, backward compatible
    │   └─ Cons: External dependency, less mature
    └─ YES (library code) → Dual client pattern
        └─ Pros: Flexible, optimized for both sync/async
        └─ Cons: Code duplication, complex maintenance
```

---

## Key Takeaways

1. **asyncio.run() is the recommended approach** for most CLI applications integrating async code. It's simple, uses only the standard library, and handles all resource cleanup automatically.

2. **AsyncClick is ideal for async-first applications** where the entire codebase uses async/await syntax. It provides a cleaner developer experience but introduces an external dependency.

3. **Dual client patterns** are for libraries supporting multiple contexts (CLI and API). Use code generation tools like Unasync to minimize maintenance burden.

4. **Event loop management is automatic with asyncio.run()** - you don't need to worry about creating, closing, or cleaning up the loop. Avoid explicit event loop management unless you have specific requirements.

5. **Separate async logic from Click decorators** for cleaner, more testable code. Click handles the CLI layer, async functions handle the business logic.

6. **For saxo-order specifically**, the asyncio.run() wrapper pattern would require minimal changes and allow gradual async adoption without major refactoring.

---

## References & Resources

- [asyncclick · PyPI](https://pypi.org/project/asyncclick/)
- [Feature] Basic async support · Issue #2033 · pallets/click](https://github.com/pallets/click/issues/2033)
- [Using Click for command-line interfaces — Safir](https://safir.lsst.io/user-guide/click.html)
- [GitHub - ahopkins/asynccli: A CLI framework based on asyncio](https://github.com/ahopkins/asynccli)
- [Python's asyncio: A Hands-On Walkthrough – Real Python](https://realpython.com/async-io-python/)
- [Asyncio integration · Issue #85 · pallets/click](https://github.com/pallets/click/issues/85)
- [Python asyncio: Complete Guide to Async Programming 2026 | DevToolbox Blog](https://devtoolbox.dedyn.io/blog/python-asyncio-complete-guide)
- [Asyncio and Click · GitHub Gist](https://gist.github.com/bryaneaton/b4adb1d023c001a73c6319a3a70757d6)
- [HTTPX Documentation - Async Support](https://www.python-httpx.org/async/)
- [Designing Libraries for Async and Sync I/O — Seth Larson](https://sethmlarson.dev/designing-libraries-for-async-and-sync-io)
- [Combining sync and async Python code: writing a DRY package](https://spwoodcock.dev/blog/2025-02-python-dry-async/)
- [Event loops — asyncio developer notes documentation](https://asyncio-notes.readthedocs.io/en/latest/3_asyncio-eventloops.html)
- [Asyncio Event Loop: Starting, Stopping, and Running Tasks](https://codevisionz.com/lessons/asyncio-event-loop-management/)
- [Python Async Decorator · GitHub Gist](https://gist.github.com/Integralist/fb1b5dbb6271632298f44d62a2221905)
- [Leveraging AsyncIO and Decorators to Boost Python Performance](https://www.linkedin.com/pulse/leveraging-asyncio-decorators-boost-python-bahamonde-mu%C3%B1oz)
- [Asyncio Extras — Asyncio Extras 1.3.0.post2 documentation](https://asyncio-extras.readthedocs.io/en/latest/)
