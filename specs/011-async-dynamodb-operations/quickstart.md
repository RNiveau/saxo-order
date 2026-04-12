# Quickstart Guide: Async DynamoDB Operations

**Feature**: 011-async-dynamodb-operations
**Phase**: 1 (Testing & Verification)
**Date**: 2026-02-22

## Prerequisites

- Poetry installed with project dependencies
- AWS credentials configured (or DynamoDB Local for testing)
- Python 3.11+
- FastAPI backend running

## Local Development Setup

### 1. Install Dependencies

```bash
# Ensure aioboto3 is installed
cd /Users/kiva/codes/saxo-order
poetry install

# Verify aioboto3 installation
poetry run python -c "import aioboto3; print(f'aioboto3 {aioboto3.__version__} installed')"
```

### 2. Configure DynamoDB Local (Optional for Testing)

```bash
# Download and run DynamoDB Local
docker run -p 8000:8000 amazon/dynamodb-local

# Verify DynamoDB Local is running
curl http://localhost:8000
```

### 3. Run Async API Server

```bash
# Start FastAPI server with async DynamoDB support
poetry run python run_api.py

# Expected output:
# INFO:     Started server process
# INFO:     Waiting for application startup.
# INFO:     Starting saxo-order API...
# INFO:     DynamoDB tables initialized successfully
# INFO:     Application startup complete.
# INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 4. Verify API Health

```bash
# Test root endpoint
curl http://localhost:8000/

# Test DynamoDB-backed endpoint
curl http://localhost:8000/api/workflows
```

---

## Testing Async Operations

### Running Async Tests

```bash
# Run all tests with async support
poetry run pytest -v

# Run only async DynamoDB tests
poetry run pytest tests/client/test_aws_client.py -v

# Run with coverage
poetry run pytest --cov=client --cov=services --cov=api tests/
```

### Expected Test Output

```bash
tests/client/test_aws_client.py::test_async_get_workflow_by_id PASSED
tests/client/test_aws_client.py::test_async_get_workflow_orders PASSED
tests/services/test_workflow_service.py::test_async_list_workflows PASSED
tests/api/routers/test_workflow.py::test_get_workflows_endpoint PASSED

================= 45 passed in 2.34s =================
```

---

## Manual Verification

### Test 1: Verify Concurrent Request Handling

**Objective**: Confirm that multiple concurrent API requests complete in parallel (not sequentially).

#### Create Test Script (`test_concurrent_requests.py`)

```python
import asyncio
import time
import httpx

async def make_request(client: httpx.AsyncClient, request_id: int):
    """Make a single API request and measure latency."""
    start = time.time()
    response = await client.get("/api/workflows")
    latency = (time.time() - start) * 1000  # Convert to ms
    return {
        "request_id": request_id,
        "status": response.status_code,
        "latency_ms": round(latency, 2)
    }

async def test_concurrent_performance(num_requests: int = 10):
    """Test concurrent API request performance."""
    print(f"Testing {num_requests} concurrent requests...")

    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        start_time = time.time()

        # Make all requests concurrently
        tasks = [make_request(client, i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks)

        total_time = (time.time() - start_time) * 1000  # Convert to ms

    # Print results
    print(f"\n✅ Total time for {num_requests} requests: {total_time:.2f}ms")
    print(f"   Average per request: {total_time / num_requests:.2f}ms")
    print(f"   Speedup vs sequential: {sum(r['latency_ms'] for r in results) / total_time:.2f}x\n")

    for result in results:
        status_emoji = "✅" if result['status'] == 200 else "❌"
        print(f"{status_emoji} Request {result['request_id']}: {result['status']} ({result['latency_ms']}ms)")

    # Expected: Total time ≈ 2 seconds (not 10+ seconds)
    if total_time < 3000:  # 3 seconds threshold
        print("\n🎉 SUCCESS: Concurrent requests are executing in parallel!")
    else:
        print("\n⚠️  WARNING: Requests may be executing sequentially. Check async implementation.")

if __name__ == "__main__":
    asyncio.run(test_concurrent_performance(10))
```

#### Run Test

```bash
poetry run python test_concurrent_requests.py

# Expected output:
# Testing 10 concurrent requests...
#
# ✅ Total time for 10 requests: 1823.45ms
#    Average per request: 182.35ms
#    Speedup vs sequential: 5.48x
#
# ✅ Request 0: 200 (178.23ms)
# ✅ Request 1: 200 (185.67ms)
# ... (all 10 requests complete in ~2 seconds total)
#
# 🎉 SUCCESS: Concurrent requests are executing in parallel!
```

**Pass Criteria**:
- Total time for 10 requests < 3 seconds
- All requests return status 200
- Speedup ratio > 3x

---

### Test 2: Verify Connection Pool Behavior

**Objective**: Confirm connection pooling is working and connections are reused.

#### Create Test Script (`test_connection_pool.py`)

```python
import asyncio
import httpx
import time

async def stress_test_connection_pool(
    num_requests: int = 50,
    concurrency: int = 10
):
    """Stress test connection pool with high concurrency."""
    print(f"Stress testing with {num_requests} requests ({concurrency} concurrent)...")

    async with httpx.AsyncClient(
        base_url="http://localhost:8000",
        limits=httpx.Limits(max_connections=concurrency)
    ) as client:

        start_time = time.time()
        latencies = []

        # Execute in batches of concurrency
        for i in range(0, num_requests, concurrency):
            batch = min(concurrency, num_requests - i)
            tasks = [
                client.get("/api/workflows")
                for _ in range(batch)
            ]

            batch_start = time.time()
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            batch_time = (time.time() - batch_start) * 1000

            latencies.append(batch_time)

            # Check for errors
            errors = [r for r in responses if isinstance(r, Exception)]
            if errors:
                print(f"❌ Batch {i//concurrency + 1}: {len(errors)} errors")
                for err in errors:
                    print(f"   Error: {err}")
            else:
                print(f"✅ Batch {i//concurrency + 1}: {batch} requests in {batch_time:.2f}ms")

        total_time = (time.time() - start_time) * 1000

    # Statistics
    print(f"\n📊 Statistics:")
    print(f"   Total requests: {num_requests}")
    print(f"   Total time: {total_time:.2f}ms")
    print(f"   Average per batch: {sum(latencies) / len(latencies):.2f}ms")
    print(f"   Throughput: {(num_requests / total_time) * 1000:.2f} req/s")

    # Pass criteria
    if total_time < num_requests * 100:  # < 100ms per request average
        print("\n🎉 SUCCESS: Connection pool is handling load efficiently!")
    else:
        print("\n⚠️  WARNING: High latency detected. Check connection pool configuration.")

if __name__ == "__main__":
    asyncio.run(stress_test_connection_pool(50, 10))
```

#### Run Test

```bash
poetry run python test_connection_pool.py

# Expected output:
# Stress testing with 50 requests (10 concurrent)...
# ✅ Batch 1: 10 requests in 234.56ms
# ✅ Batch 2: 10 requests in 189.23ms
# ✅ Batch 3: 10 requests in 201.45ms
# ✅ Batch 4: 10 requests in 195.67ms
# ✅ Batch 5: 10 requests in 203.89ms
#
# 📊 Statistics:
#    Total requests: 50
#    Total time: 1024.80ms
#    Average per batch: 204.96ms
#    Throughput: 48.79 req/s
#
# 🎉 SUCCESS: Connection pool is handling load efficiently!
```

**Pass Criteria**:
- No connection pool exhaustion errors
- Throughput > 20 req/s
- No degradation across batches

---

### Test 3: Verify Error Handling Under Load

**Objective**: Confirm graceful degradation when DynamoDB is unavailable.

#### Simulate DynamoDB Unavailability

```bash
# Option 1: Stop DynamoDB Local (if using it)
docker stop $(docker ps -q --filter ancestor=amazon/dynamodb-local)

# Option 2: Temporarily block AWS endpoints
# (requires network manipulation, advanced)
```

#### Test API Response

```bash
# Expected: HTTP 503 Service Unavailable
curl -v http://localhost:8000/api/workflows

# Expected response (within 5 seconds):
# HTTP/1.1 503 Service Unavailable
# {"detail":"DynamoDB service temporarily unavailable"}
```

**Pass Criteria**:
- API returns HTTP 503 (not 500)
- Response time < 5 seconds (not hanging indefinitely)
- Error message is descriptive
- API doesn't crash (remains responsive)

---

### Test 4: Verify CLI Async Compatibility

**Objective**: Confirm CLI commands work with async DynamoDB client using asyncio.run() wrapper.

#### Test CLI Command

```bash
# Test workflow list command (uses async DynamoDB)
poetry run k-order workflow list

# Expected output:
# Fetching workflows...
# ┌──────────────────────────────────────┬────────────────┬───────────┬────────┐
# │ ID                                   │ Name           │ Index     │ Enabled│
# ├──────────────────────────────────────┼────────────────┼───────────┼────────┤
# │ 12345678-1234-1234-1234-123456789012 │ Workflow 1     │ DAX.I     │ True   │
# └──────────────────────────────────────┴────────────────┴───────────┴────────┘
```

**Pass Criteria**:
- Command executes without errors
- Output displays workflow data correctly
- Execution time reasonable (< 3 seconds for small datasets)
- No event loop warnings or errors

---

## Performance Benchmarking

### Before/After Comparison

Run this benchmark script to compare synchronous vs asynchronous performance:

```python
import asyncio
import time
from typing import List, Dict

async def benchmark_async(num_requests: int) -> Dict:
    """Benchmark async DynamoDB operations."""
    import httpx

    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        start = time.time()
        tasks = [client.get("/api/workflows") for _ in range(num_requests)]
        responses = await asyncio.gather(*tasks)
        duration = time.time() - start

    return {
        "mode": "async",
        "requests": num_requests,
        "duration_sec": duration,
        "throughput_rps": num_requests / duration,
        "avg_latency_ms": (duration / num_requests) * 1000
    }

def benchmark_sync(num_requests: int) -> Dict:
    """Benchmark synchronous DynamoDB operations (simulated)."""
    import requests

    start = time.time()
    for _ in range(num_requests):
        requests.get("http://localhost:8000/api/workflows")
    duration = time.time() - start

    return {
        "mode": "sync",
        "requests": num_requests,
        "duration_sec": duration,
        "throughput_rps": num_requests / duration,
        "avg_latency_ms": (duration / num_requests) * 1000
    }

async def run_benchmark():
    """Run async vs sync benchmark."""
    num_requests = 10

    print("🔬 Performance Benchmark: Async vs Sync\n")

    # Async benchmark
    print("Testing async mode...")
    async_result = await benchmark_async(num_requests)

    # Sync benchmark (for comparison)
    print("Testing sync mode (sequential)...")
    sync_result = benchmark_sync(num_requests)

    # Compare results
    print("\n📊 Results:")
    print(f"\nAsync Mode:")
    print(f"  Duration: {async_result['duration_sec']:.2f}s")
    print(f"  Throughput: {async_result['throughput_rps']:.2f} req/s")
    print(f"  Avg Latency: {async_result['avg_latency_ms']:.2f}ms")

    print(f"\nSync Mode:")
    print(f"  Duration: {sync_result['duration_sec']:.2f}s")
    print(f"  Throughput: {sync_result['throughput_rps']:.2f} req/s")
    print(f"  Avg Latency: {sync_result['avg_latency_ms']:.2f}ms")

    speedup = sync_result['duration_sec'] / async_result['duration_sec']
    print(f"\n🚀 Speedup: {speedup:.2f}x")
    print(f"   Time saved: {sync_result['duration_sec'] - async_result['duration_sec']:.2f}s")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
```

**Expected Results**:
- Async mode: 10 requests in ~2 seconds
- Sync mode: 10 requests in ~10 seconds
- Speedup: ~5x

---

## Troubleshooting

### Issue 1: "Event loop is closed" Error

**Symptom**:
```
RuntimeError: Event loop is closed
```

**Cause**: aioboto3 caches DEFAULT_SESSION with event loop reference.

**Solution**: Reset aioboto3 session in pytest fixture:
```python
@pytest.fixture(autouse=True)
def reset_aioboto_session():
    yield
    aioboto3.DEFAULT_SESSION = None
```

### Issue 2: "TypeError: object AsyncMock can't be used in 'await' expression"

**Symptom**:
```
TypeError: object AsyncMock can't be used in 'await' expression
```

**Cause**: Missing `__aenter__` and `__aexit__` for async context managers.

**Solution**: Configure async context manager properly:
```python
mock = AsyncMock()
mock.__aenter__ = AsyncMock(return_value=mock)
mock.__aexit__ = AsyncMock(return_value=False)
```

### Issue 3: Connection Pool Exhaustion

**Symptom**:
```
urllib3.exceptions.PoolError: Connection pool is full
```

**Cause**: `max_pool_connections` too low for concurrent load.

**Solution**: Increase connection pool size in config:
```python
config = Config(max_pool_connections=20)  # Increase from 10
```

### Issue 4: Slow API Response Times

**Symptom**: API responses take > 1 second for simple operations.

**Checks**:
1. Verify async/await chain is complete (no blocking sync calls)
2. Check DynamoDB latency (should be < 50ms)
3. Verify connection reuse (tcp_keepalive=True)
4. Check if requests are truly concurrent (use test scripts above)

---

## Success Criteria

✅ **All criteria must pass before considering migration complete**:

- [ ] All unit tests pass (`pytest tests/`)
- [ ] Integration tests pass with async client
- [ ] Concurrent requests complete in < 3 seconds (10 requests)
- [ ] Throughput > 20 req/s under load
- [ ] No connection pool exhaustion under stress test
- [ ] CLI commands execute without errors
- [ ] Error handling works (HTTP 503 when DynamoDB unavailable)
- [ ] Performance improvement verified (5x+ speedup)
- [ ] No "event loop closed" errors in tests
- [ ] No resource leaks after 1000 requests

---

## Next Steps

After verifying all success criteria:

1. **Load Test in Staging**: Deploy to staging environment and run production-like load tests
2. **Monitor Metrics**: Set up CloudWatch metrics for async operation latency
3. **Deploy to Production**: Roll out async implementation with gradual traffic ramp
4. **Performance Validation**: Confirm 5x+ throughput improvement in production

---

## Additional Resources

- [Phase 0 Research](./research.md) - Complete technical research
- [Migration Guide](./MIGRATION_GUIDE.md) - Step-by-step migration instructions
- [Code Templates](./CODE_TEMPLATES.md) - Production-ready code examples
- [Implementation Plan](./plan.md) - Overall project plan

**Questions?** Review the research documentation or check troubleshooting section above.
