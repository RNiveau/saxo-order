# Performance Validation: Asset Exclusion Feature

**Feature**: User Story 4 - Asset Exclusion
**Date**: 2026-01-26
**Status**: Ready for Validation

## Overview

The asset exclusion feature is designed to improve batch alerting performance by skipping excluded assets during detection. This document outlines the expected performance improvements and provides a validation methodology.

## Performance Goals

### Primary Goal: Proportional Time Reduction
**Success Criterion**: Batch alerting runtime should decrease proportionally to the percentage of excluded assets.

**Formula**:
```
Expected Reduction % = (Excluded Assets / Total Assets) × 100
Target Runtime = Baseline Runtime × (1 - Expected Reduction %)
```

**Example**:
- Baseline: 100 assets, 60 minutes runtime
- Scenario: Exclude 30 assets (30%)
- Expected: ~42 minutes (30% reduction)

### Secondary Goals
1. **Filtering Overhead**: < 100ms for exclusion list retrieval and filtering
2. **API Response Time**: < 500ms for exclusion toggle operations
3. **UI Responsiveness**: < 2 seconds for page load

## Validation Methodology

### 1. Batch Alerting Performance Test

#### Test Setup
```bash
# Prerequisites
- Ensure DynamoDB is accessible
- Ensure Saxo API credentials are valid
- Have at least 50+ assets in the system
```

#### Baseline Measurement (0% Excluded)
```bash
# 1. Clear all exclusions
curl -X GET "http://localhost:8000/api/asset-details" | \
  jq -r '.assets[] | select(.is_excluded == true) | .asset_id' | \
  while read asset_id; do
    curl -X PUT "http://localhost:8000/api/asset-details/$asset_id/exclusion" \
      -H "Content-Type: application/json" \
      -d '{"is_excluded": false}'
  done

# 2. Run batch alerting and measure time
time poetry run k-order alerting --country-code xpar

# 3. Record baseline metrics
# - Total runtime
# - Number of assets processed
# - Average time per asset
```

#### Performance Test Scenarios

**Scenario 1: 25% Exclusion**
```bash
# Exclude 25% of assets (e.g., if 100 assets, exclude 25)
# Example: Exclude assets with low priority
ASSETS_TO_EXCLUDE=("SAN" "BNP" "AIR" ... )  # 25 assets
for asset in "${ASSETS_TO_EXCLUDE[@]}"; do
  curl -X PUT "http://localhost:8000/api/asset-details/$asset/exclusion" \
    -H "Content-Type: application/json" \
    -d '{"is_excluded": true}'
done

# Run batch alerting
time poetry run k-order alerting --country-code xpar

# Record metrics
# - Total runtime
# - Number of assets processed
# - Number of assets filtered
# - Runtime reduction %
```

**Scenario 2: 50% Exclusion**
```bash
# Exclude 50% of assets
# Follow same process as Scenario 1 but with 50 assets
```

**Scenario 3: 75% Exclusion**
```bash
# Exclude 75% of assets
# Follow same process as Scenario 1 but with 75 assets
```

#### Expected Results

| Scenario | Excluded % | Expected Runtime | Acceptable Range |
|----------|-----------|------------------|------------------|
| Baseline | 0% | T₀ (baseline) | N/A |
| Scenario 1 | 25% | 0.75 × T₀ | 0.70-0.80 × T₀ |
| Scenario 2 | 50% | 0.50 × T₀ | 0.45-0.55 × T₀ |
| Scenario 3 | 75% | 0.25 × T₀ | 0.20-0.30 × T₀ |

**Note**: Acceptable range accounts for:
- API rate limiting
- Network latency variance
- DynamoDB access time
- Slack notification overhead

### 2. Filtering Overhead Test

#### Test: Exclusion List Retrieval
```bash
# Measure time to retrieve excluded assets from DynamoDB
time poetry run python -c "
from client.aws_client import DynamoDBClient
client = DynamoDBClient()
excluded = client.get_excluded_assets()
print(f'Excluded assets: {len(excluded)}')
"
```

**Expected**: < 100ms for any reasonable number of excluded assets (< 1000)

#### Test: Asset Filtering Operation
```python
# Performance test script: test_exclusion_filtering_perf.py
import time
from typing import List, Dict

def test_filtering_performance():
    # Simulate asset list
    assets: List[Dict] = [
        {"code": f"ASSET{i}", "name": f"Asset {i}", "saxo_uic": i}
        for i in range(1000)
    ]

    # Simulate excluded list (50%)
    excluded_ids = [f"ASSET{i}" for i in range(0, 1000, 2)]

    # Measure filtering time
    start = time.perf_counter()
    filtered_assets = [s for s in assets if s["code"] not in excluded_ids]
    end = time.perf_counter()

    duration_ms = (end - start) * 1000
    print(f"Filtered {len(assets)} assets in {duration_ms:.2f}ms")
    print(f"Result: {len(filtered_assets)} assets remaining")

    assert duration_ms < 50, "Filtering should take < 50ms for 1000 assets"
    assert len(filtered_assets) == 500

if __name__ == "__main__":
    test_filtering_performance()
```

**Expected**: < 50ms for 1000 assets (< 10ms for typical ~100 assets)

### 3. API Performance Test

#### Test: Exclusion Toggle Endpoint
```bash
# Test 1: Exclude an asset
time curl -X PUT "http://localhost:8000/api/asset-details/SAN/exclusion" \
  -H "Content-Type: application/json" \
  -d '{"is_excluded": true}' -w "\nTime: %{time_total}s\n"

# Test 2: Un-exclude an asset
time curl -X PUT "http://localhost:8000/api/asset-details/SAN/exclusion" \
  -H "Content-Type: application/json" \
  -d '{"is_excluded": false}' -w "\nTime: %{time_total}s\n"

# Test 3: Get all assets (with exclusion status)
time curl -X GET "http://localhost:8000/api/asset-details" \
  -w "\nTime: %{time_total}s\n" | jq '.count'

# Test 4: Get excluded assets only
time curl -X GET "http://localhost:8000/api/asset-details/excluded/list" \
  -w "\nTime: %{time_total}s\n" | jq '.excluded_count'
```

**Expected Results**:
- Exclusion toggle: < 500ms
- Get all assets: < 2000ms (< 2s)
- Get excluded only: < 1000ms

### 4. Frontend Performance Test

#### Test: Asset Exclusions Page Load
```javascript
// Use browser DevTools Performance tab
// 1. Open http://localhost:5173/exclusions
// 2. Start Performance recording
// 3. Reload page
// 4. Stop recording

// Metrics to measure:
// - First Contentful Paint (FCP): < 1s
// - Largest Contentful Paint (LCP): < 2.5s
// - Time to Interactive (TTI): < 3s
// - API call duration: < 2s
```

#### Test: Exclusion Toggle UI Responsiveness
```javascript
// Manual test with browser DevTools Network tab
// 1. Click "Exclude" button on an asset
// 2. Measure time from click to UI update
// Expected: < 500ms (including API call)

// 3. Click "Un-exclude" button
// 4. Measure time from click to UI update
// Expected: < 500ms (including API call)
```

#### Test: Search Performance
```javascript
// Manual test
// 1. Load page with 100+ assets
// 2. Type quickly in search bar (e.g., "ASSET")
// 3. Observe lag or freezing
// Expected: No lag, smooth updates
```

### 5. Scalability Test

#### Test: Large Dataset Performance
```python
# Simulate large dataset filtering
def test_large_dataset():
    import time

    # Simulate 10,000 assets
    assets = [{"code": f"A{i}", "name": f"Asset {i}"} for i in range(10000)]
    excluded_ids = [f"A{i}" for i in range(0, 10000, 2)]  # 50% excluded

    start = time.perf_counter()
    excluded_set = set(excluded_ids)  # Convert to set for O(1) lookup
    filtered = [a for a in assets if a["code"] not in excluded_set]
    end = time.perf_counter()

    duration_ms = (end - start) * 1000
    print(f"Filtered {len(assets)} assets in {duration_ms:.2f}ms")

    assert duration_ms < 500, "Should handle 10k assets in < 500ms"
```

**Expected**: Should handle up to 10,000 assets without performance degradation

## Logging and Monitoring

### Key Metrics to Log

The batch alerting command logs the following metrics:

```python
# From saxo_order/commands/alerting.py (lines 435-444)
logger.info(f"Excluded assets: {excluded_asset_ids}")
logger.info(f"Assets after exclusion filtering: {len(assets)}")
logger.info(f"Filtered out {filtered_count} excluded assets")
```

### Sample Log Output
```
INFO - Excluded assets: ['SAN', 'BNP', 'AIR']
INFO - Assets after exclusion filtering: 97
INFO - Filtered out 3 excluded assets
INFO - Processing 97 total stocks (97 French + 0 followup)
```

### CloudWatch Metrics (Production)

Create CloudWatch metrics for:
1. **Exclusion Filtering Duration**: Time to retrieve and filter excluded assets
2. **Excluded Asset Count**: Number of assets currently excluded
3. **Batch Alerting Duration**: Total runtime with/without exclusions
4. **Assets Processed Count**: Number of assets actually processed

## Performance Validation Results

### Batch Alerting Performance
| Test Run | Date | Total Assets | Excluded | Excluded % | Runtime | Reduction | Status |
|----------|------|--------------|----------|------------|---------|-----------|--------|
| Baseline | TBD | TBD | 0 | 0% | TBD | N/A | ⏳ Pending |
| Test 1 | TBD | TBD | TBD | 25% | TBD | TBD | ⏳ Pending |
| Test 2 | TBD | TBD | TBD | 50% | TBD | TBD | ⏳ Pending |
| Test 3 | TBD | TBD | TBD | 75% | TBD | TBD | ⏳ Pending |

### API Performance Results
| Endpoint | Expected | Actual | Status |
|----------|----------|--------|--------|
| PUT /exclusion | < 500ms | TBD | ⏳ Pending |
| GET /asset-details | < 2s | TBD | ⏳ Pending |
| GET /excluded/list | < 1s | TBD | ⏳ Pending |

### Frontend Performance Results
| Metric | Expected | Actual | Status |
|--------|----------|--------|--------|
| Page Load (FCP) | < 1s | TBD | ⏳ Pending |
| Page Load (LCP) | < 2.5s | TBD | ⏳ Pending |
| Toggle Responsiveness | < 500ms | TBD | ⏳ Pending |
| Search Performance | Smooth | TBD | ⏳ Pending |

### Filtering Overhead Results
| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| DynamoDB Retrieval | < 100ms | TBD | ⏳ Pending |
| Filtering 100 assets | < 10ms | TBD | ⏳ Pending |
| Filtering 1000 assets | < 50ms | TBD | ⏳ Pending |

## Performance Optimization Notes

### Current Implementation Optimizations

1. **Set-based Lookup** (Implemented in alerting.py line 440):
   ```python
   assets = [s for s in assets if s["code"] not in excluded_asset_ids]
   ```
   - Python's `in` operator on lists is O(n), but for small excluded lists this is acceptable
   - For optimization with large excluded lists (100+), convert to set:
   ```python
   excluded_set = set(excluded_asset_ids)
   assets = [s for s in assets if s["code"] not in excluded_set]
   ```

2. **Single DynamoDB Call**: Exclusions retrieved once at start, not per-asset

3. **Early Exit**: If all assets excluded, skip detection entirely (line 446-452)

4. **Client-side Filtering**: Alert filtering happens in-memory (fast)

### Potential Future Optimizations

1. **DynamoDB Caching**: Cache excluded asset list for 5-10 minutes
2. **Pagination**: For UI with 1000+ assets, implement pagination
3. **Lazy Loading**: Load assets on-demand as user scrolls
4. **Debounced Search**: Already minimal overhead, but could add debouncing for very large lists

## Sign-off

### Performance Goals Met
- [ ] Batch alerting shows proportional time reduction
- [ ] Filtering overhead < 100ms
- [ ] API response times within targets
- [ ] UI responsiveness within targets
- [ ] Scalability validated for expected dataset sizes

### Performance Testing Complete
- [ ] Baseline measurements recorded
- [ ] Multiple exclusion scenarios tested
- [ ] API performance validated
- [ ] Frontend performance validated
- [ ] Scalability limits identified

**Validated by**: ________________
**Date**: ________________
**Notes**: ________________

## Troubleshooting Performance Issues

### Issue: Batch Alerting Not Showing Expected Reduction
**Possible Causes**:
- API rate limiting (Saxo Bank)
- Network latency dominating runtime
- Excluded assets were low-cost assets (fast to process anyway)

**Solution**:
- Test with high-cost assets (complex patterns)
- Check Saxo API rate limit headers
- Monitor per-asset processing time in logs

### Issue: High DynamoDB Latency
**Possible Causes**:
- Cold start (first query slow)
- Large number of excluded assets (1000+)
- Network latency to AWS

**Solution**:
- Implement caching for excluded list
- Use DynamoDB DAX for caching
- Pre-warm connection during Lambda initialization

### Issue: UI Lag with Large Asset Lists
**Possible Causes**:
- Rendering 1000+ DOM elements
- No virtualization
- Inefficient React re-renders

**Solution**:
- Implement virtual scrolling (react-window)
- Add pagination (50-100 assets per page)
- Memoize components with React.memo()
