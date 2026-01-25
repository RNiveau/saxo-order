# Feature Specification: Alert System - French Stocks Expansion

**Feature ID**: 006-alert-system-french-stocks
**Status**: Draft
**Created**: 2026-01-25
**Last Updated**: 2026-01-25

---

## Overview

The **Alert System** is a production-grade technical analysis engine that monitors stocks for six types of technical patterns (COMBO, CONGESTION20, CONGESTION100, DOUBLE_TOP, DOUBLE_INSIDE_BAR, CONTAINING_CANDLE), stores alerts in DynamoDB with 7-day TTL, and delivers notifications via Slack and REST API.

**Current Limitation**: The system monitors only ~154 manually curated stocks from a static JSON file.

**Proposed Enhancement**: Expand monitoring to **all French stocks** listed on Euronext Paris (PAR exchange) by dynamically fetching the instrument list from Saxo API at runtime.

---

## Current State Analysis

### Existing Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                CURRENT ALERT SYSTEM (v1.0)                       │
└─────────────────────────────────────────────────────────────────┘

[EventBridge] (Daily @ 6:15 PM Paris)
    ↓
[Lambda: alerting]
    ↓
Load stocks.json (149) + followup-stocks.json (5)
    ↓
For each asset (154 total):
    ├─ Fetch 250 daily candles
    ├─ Run 6 pattern detectors
    ├─ Calculate MA50 slope
    └─ Store to DynamoDB
    ↓
[Slack #stock] ← Post grouped alerts
```

### Monitored Assets (Current)

- **Source Files**:
  - `stocks.json` (149 stocks)
  - `followup-stocks.json` (5 stocks)
- **Total**: ~154 stocks
- **Scope**: Primarily CAC 40 constituents + select mid-caps + US ADRs
- **Maintenance**: Manual updates required for new listings/delistings

**Example Entry**:
```json
{
  "name": "Sanofi SA",
  "code": "SAN:xpar",
  "saxo_uic": 114879
}
```

### Alert Types

Defined in `model/enum.py`:

| Alert Type | Description | Detection Logic |
|------------|-------------|-----------------|
| `CONGESTION20` | 20-period consolidation | Line detection with ≥2 touch points |
| `CONGESTION100` | 100-period consolidation | Line detection with ≥3 touch points |
| `COMBO` | Multi-indicator signal | MA50 + BB + MACD + ATR scoring |
| `DOUBLE_TOP` | Two peaks at similar price | Local highs within 1 tick |
| `DOUBLE_INSIDE_BAR` | Two consecutive inside bars | Range contraction pattern |
| `CONTAINING_CANDLE` | Engulfing candle | Current candle contains previous |

### Data Storage

**DynamoDB Table**: `alerts`

- **Primary Key**: `asset_code` (partition), `country_code` (sort)
- **TTL**: 7-day automatic expiration
- **Deduplication**: Same `alert_type` + same date (ISO) = duplicate
- **Fields**:
  - `alerts[]` - Array of detected patterns
  - `last_updated` - Timestamp of latest detection
  - `last_run_at` - Cooldown enforcement (on-demand API)
  - `ttl` - Unix timestamp for expiration

### Execution Modes

#### 1. Scheduled (Lambda)
- **Trigger**: EventBridge @ 6:15 PM Paris time (Mon-Fri)
- **Handler**: `lambda_function.py::handler({"command": "alerting"})`
- **Process**: Batch process all stocks → Store → Slack
- **Output**: Grouped messages to #stock channel

#### 2. On-Demand (API)
- **Endpoint**: `POST /api/alerts/run`
- **Cooldown**: 5 minutes per asset (asset_code + country_code)
- **Process**: Single asset → Store → JSON response
- **Use Case**: User-triggered analysis from UI

---

## Problem Statement

### Limitations

1. **Manual Curation**: Stock list requires manual JSON edits
2. **Incomplete Coverage**: Missing ~173 French stocks (327 - 154 = 173)
3. **Stale Data**: No automatic handling of IPOs/delistings
4. **Maintenance Burden**: Market changes (splits, mergers) require manual updates

### Business Impact

- **Missed Opportunities**: New IPOs (e.g., Pluxee 2024) not monitored until manual add
- **Wasted Resources**: Delisted stocks (e.g., Orpea 2023) continue consuming API calls
- **Incomplete Analysis**: Traders miss signals from mid/small-cap French stocks

---

## Proposed Solution

### High-Level Approach

**Replace static JSON with dynamic API fetch** at cron job start:

```
[EventBridge] (Daily @ 6:15 PM Paris)
    ↓
[Lambda: alerting]
    ↓
┌──────────────────────────────────────────────┐
│ NEW: Fetch all French stocks from Saxo API   │
│                                               │
│ GET /ref/v1/instruments                      │
│   ?AssetTypes=Stock                          │
│   &ExchangeId=PAR                            │
│   &$top=1000                                 │
│   &$skip=0,1000,2000,...                    │
│   &IncludeNonTradable=false                 │
│                                               │
│ Returns: ~327 stocks                          │
└──────────────────────────────────────────────┘
    ↓
For each stock (327 total):
    ├─ Fetch 250 daily candles
    ├─ Run 6 pattern detectors
    ├─ Calculate MA50 slope
    └─ Store to DynamoDB
    ↓
[Slack #stock] ← Post grouped alerts
```

### API Details

**Saxo Endpoint**: `GET /ref/v1/instruments`

**Query Parameters**:
- `AssetTypes=Stock` - Filter to stocks only
- `ExchangeId=PAR` - Euronext Paris
- `$top=1000` - Page size (max per request)
- `$skip=0,1000,2000...` - Pagination offset
- `IncludeNonTradable=false` - Exclude non-tradable

**Response Structure**:
```json
{
  "Data": [
    {
      "Symbol": "TTE:xpar",
      "Description": "TotalEnergies SE",
      "Identifier": 23255427,
      "AssetType": "Stock",
      "ExchangeId": "PAR",
      "CurrencyCode": "EUR",
      "IssuerCountry": "FR"
    },
    ...
  ]
}
```

**Pagination Logic**:
```python
all_stocks = []
skip = 0
page_size = 1000

while True:
    response = saxo_client.list_instruments(
        asset_type="Stock",
        exchange_id="PAR",
        top=page_size,
        skip=skip,
        include_non_tradable=False
    )

    data = response.get("Data", [])
    if not data:
        break

    all_stocks.extend(data)

    if len(data) < page_size:
        break  # Last page

    skip += page_size
```

---

## User Stories

### User Story 1 (P1): Dynamic French Stock Discovery

**As a** trader
**I want** the alert system to automatically monitor all French stocks
**So that** I don't miss trading opportunities from newly listed or previously ignored stocks

**Acceptance Criteria**:
1. **Given** I am running the daily alerting cron, **When** the job starts, **Then** it fetches all stocks from Euronext Paris via Saxo API
2. **Given** a new stock is listed on Euronext Paris, **When** the next alerting run executes, **Then** the new stock is automatically included in monitoring
3. **Given** a stock is delisted, **When** the next alerting run executes, **Then** the delisted stock is automatically excluded (API won't return it)
4. **Given** there are ~327 French stocks, **When** the alerting job completes, **Then** all 327 stocks have been analyzed for patterns
5. **Given** the API fetch fails, **When** the error occurs, **Then** the system logs the error and falls back to cached data (if available)

### User Story 2 (P2): Maintain Backward Compatibility

**As a** system administrator
**I want** the JSON-based stock list to remain available as a fallback
**So that** the system continues working during API outages

**Acceptance Criteria**:
1. **Given** the Saxo API is unavailable, **When** the fetch fails, **Then** the system loads stocks from `stocks.json` as fallback
2. **Given** both API and JSON file are available, **When** the job runs, **Then** it prioritizes the API fetch (fresher data)
3. **Given** I want to add a specific non-French stock, **When** I add it to `followup-stocks.json`, **Then** it is included alongside API-fetched stocks

---

## Requirements

### Functional Requirements

**FR-001**: System MUST fetch all stocks from Saxo API `/ref/v1/instruments` with `AssetTypes=Stock&ExchangeId=PAR`

**FR-002**: System MUST use pagination (`$skip`/`$top`) to retrieve all stocks, not limited to first 1000

**FR-003**: System MUST filter out non-tradable instruments (`IncludeNonTradable=false`)

**FR-004**: System MUST extract required fields from API response:
- `Symbol` → asset_code + country_code
- `Description` → asset_description
- `Identifier` → saxo_uic

**FR-005**: System MUST maintain existing JSON files (`stocks.json`, `followup-stocks.json`) as fallback

**FR-006**: System MUST combine API-fetched stocks with `followup-stocks.json` entries (for non-French stocks)

**FR-007**: System MUST log total stock count and fetch duration for monitoring

**FR-008**: System MUST deduplicate stocks if same asset appears in both API response and JSON files (API takes precedence)

### Non-Functional Requirements

**NFR-001**: API fetch MUST complete within 5 seconds (acceptable overhead at job start)

**NFR-002**: System MUST handle API rate limiting gracefully (retry with backoff)

**NFR-003**: System MUST cache fetched stock list in memory for the duration of the job (avoid redundant fetches)

**NFR-004**: System MUST maintain existing alert detection performance (no regression in processing time per stock)

**NFR-005**: System MUST log errors to Slack #errors channel if API fetch fails

---

## Technical Design

### Implementation in SaxoClient

**File**: `client/saxo_client.py`

**New Method** (already implemented):
```python
def list_instruments(
    self,
    asset_type: str = "Stock",
    exchange_id: Optional[str] = None,
    top: int = 100,
    skip: int = 0,
    include_non_tradable: bool = False,
) -> Dict:
    """
    List instruments of a specific asset type without keyword filter.
    Returns: Dict with 'Data' key containing list of instruments
    """
```

### Changes to Alerting Command

**File**: `saxo_order/commands/alerting.py`

**Current** (`run_alerting()`):
```python
def run_alerting(config_path: str):
    # Load from JSON files
    with open("stocks.json") as f:
        stocks = json.load(f)
    with open("followup-stocks.json") as f:
        followup_stocks = json.load(f)

    all_stocks = stocks + followup_stocks

    for stock in all_stocks:
        run_detection_for_asset(...)
```

**Proposed**:
```python
def fetch_french_stocks(saxo_client: SaxoClient) -> List[Dict]:
    """Fetch all French stocks from Saxo API"""
    all_instruments = []
    skip = 0
    page_size = 1000

    logger.info("Fetching French stocks from Saxo API...")

    while True:
        response = saxo_client.list_instruments(
            asset_type="Stock",
            exchange_id="PAR",
            top=page_size,
            skip=skip,
            include_non_tradable=False
        )

        data = response.get("Data", [])
        if not data:
            break

        all_instruments.extend(data)

        if len(data) < page_size:
            break

        skip += page_size

    # Transform to stock format
    stocks = []
    for instrument in all_instruments:
        stocks.append({
            "name": instrument.get("Description", ""),
            "code": instrument.get("Symbol", ""),
            "saxo_uic": instrument.get("Identifier")
        })

    logger.info(f"Fetched {len(stocks)} French stocks from Saxo API")
    return stocks


def run_alerting(config_path: str):
    configuration = Configuration(config_path)
    saxo_client = SaxoClient(configuration)

    # NEW: Fetch from API
    try:
        french_stocks = fetch_french_stocks(saxo_client)
    except Exception as e:
        logger.error(f"Failed to fetch French stocks from API: {e}")
        # Fallback to JSON
        with open("stocks.json") as f:
            french_stocks = json.load(f)
        logger.info(f"Loaded {len(french_stocks)} stocks from stocks.json (fallback)")

    # Load followup stocks (non-French)
    with open("followup-stocks.json") as f:
        followup_stocks = json.load(f)

    # Combine (API stocks + followup stocks)
    all_stocks = french_stocks + followup_stocks

    # Deduplicate by code
    seen = set()
    unique_stocks = []
    for stock in all_stocks:
        if stock["code"] not in seen:
            unique_stocks.append(stock)
            seen.add(stock["code"])

    logger.info(f"Processing {len(unique_stocks)} total stocks")

    for stock in unique_stocks:
        run_detection_for_asset(...)
```

### Data Flow Changes

**Before**:
```
[Load JSON files] → [154 stocks] → [Run detection]
```

**After**:
```
[Fetch Saxo API] → [327 stocks] → [Merge followup-stocks.json] → [Deduplicate] → [~330 stocks] → [Run detection]

[If API fails] → [Load stocks.json fallback] → [154 stocks]
```

---

## Risks & Mitigations

### Risk 1: API Rate Limiting
**Impact**: Fetch fails due to rate limit
**Probability**: Low (separate rate limit for `/ref/v1/instruments`)
**Mitigation**: Implement retry with exponential backoff, fall back to JSON

### Risk 2: Increased Processing Time
**Impact**: 2.2x more stocks (154 → 327) increases job duration
**Probability**: High
**Mitigation**:
- Lambda timeout already set to 15 minutes (sufficient for 327 stocks)
- Optimize by parallelizing candle fetches (future enhancement)

### Risk 3: New Stocks with Insufficient History
**Impact**: Newly listed stocks have <60 candles, MA50 calculation fails
**Probability**: Medium
**Mitigation**: Wrap MA50 calculation in try/catch, skip pattern if insufficient data

### Risk 4: API Response Format Changes
**Impact**: Saxo changes response schema, breaks parsing
**Probability**: Low
**Mitigation**: Validate response structure, log errors, fall back to JSON

---

## Testing Strategy

### Unit Tests

**File**: `tests/saxo_order/commands/test_alerting.py`

1. `test_fetch_french_stocks_success` - Verify pagination logic
2. `test_fetch_french_stocks_empty_response` - Handle empty Data array
3. `test_fetch_french_stocks_single_page` - Handle <1000 stocks
4. `test_fetch_french_stocks_api_failure` - Fallback to JSON
5. `test_deduplicate_stocks` - Remove duplicates from API + JSON

### Integration Tests

1. **Manual Run**: `poetry run k-order alerting` with live API
2. **Verify**: Check `all_instruments.json` contains ~327 stocks
3. **Check Logs**: Confirm "Processing X total stocks" message
4. **DynamoDB**: Verify alerts stored for new stocks (not in old JSON)

### Performance Tests

1. **Baseline**: Measure current job duration with 154 stocks
2. **After**: Measure job duration with 327 stocks
3. **Acceptance**: <15 minutes total (Lambda timeout)

---

## Rollout Plan

### Phase 1: Implementation
- [ ] Update `saxo_client.py` with `list_instruments()` (✅ Done)
- [ ] Modify `alerting.py` to call `fetch_french_stocks()`
- [ ] Add error handling and fallback logic
- [ ] Update logging for monitoring

### Phase 2: Testing
- [ ] Unit tests for new fetch logic
- [ ] Manual test with live API
- [ ] Verify DynamoDB storage for new stocks
- [ ] Performance test on Lambda

### Phase 3: Deployment
- [ ] Deploy to staging Lambda
- [ ] Monitor first scheduled run (6:15 PM next day)
- [ ] Verify Slack alerts for new stocks
- [ ] Deploy to production

### Phase 4: Monitoring
- [ ] Track job duration (CloudWatch)
- [ ] Monitor API call count (rate limits)
- [ ] Check error rates in Slack #errors
- [ ] Validate alert quality for new stocks

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Stock Coverage | 327+ French stocks | Count from API fetch log |
| Job Duration | <15 minutes | CloudWatch Lambda execution time |
| API Fetch Success Rate | >99% | Error rate in logs |
| Alerts Generated | >0 for new stocks | DynamoDB count by asset_code |
| Fallback Activation | 0 (unless API down) | "fallback" keyword in logs |

---

## Future Enhancements

### Enhancement 1: Multi-Exchange Support
- Extend to other exchanges (XNAS, XAMS, etc.)
- Configurable exchange list in config.yml

### Enhancement 2: Parallel Processing
- Fetch candles in parallel (ThreadPoolExecutor)
- Reduce job duration from linear O(n) to O(n/threads)

### Enhancement 3: Smart Filtering
- Only analyze stocks with recent volume (filter low-liquidity)
- Configurable market cap threshold

### Enhancement 4: Alert Priority Scoring
- Rank alerts by MA50 slope + volume + volatility
- Highlight "hot" stocks in Slack messages

---

## Open Questions

1. **Should we exclude specific stock categories?** (e.g., ETFs classified as stocks, penny stocks)
   - **Decision Needed**: Define minimum price/volume threshold

2. **How to handle stocks with <60 candles?** (required for MA50)
   - **Decision Needed**: Skip silently or log warning?

3. **Should `stocks.json` be deprecated?**
   - **Recommendation**: Keep as fallback, but don't maintain manually

4. **Rate limit buffer?**
   - **Current**: No explicit limit check
   - **Recommendation**: Monitor X-RateLimit headers

---

## Appendices

### Appendix A: Current Stock List Analysis

**stocks.json** (149 stocks):
- CAC 40: ~40 stocks
- Mid-caps: ~60 stocks
- US ADRs: ~20 stocks
- Other European: ~29 stocks

**followup-stocks.json** (5 stocks):
- Special tracking (manually added)

**Total Current**: 154 stocks

### Appendix B: Saxo API Response Example

```json
{
  "Data": [
    {
      "AssetType": "Stock",
      "CurrencyCode": "EUR",
      "Description": "TotalEnergies SE",
      "ExchangeId": "PAR",
      "GroupId": 6516,
      "Identifier": 23255427,
      "IssuerCountry": "FR",
      "PrimaryListing": 23255427,
      "SummaryType": "Instrument",
      "Symbol": "TTE:xpar",
      "TradableAs": ["Stock", "SrdOnStock"]
    }
  ]
}
```

### Appendix C: Related Files

**Implementation**:
- `/Users/kiva/codes/saxo-order/saxo_order/commands/alerting.py` - Main alerting logic
- `/Users/kiva/codes/saxo-order/client/saxo_client.py` - Saxo API client
- `/Users/kiva/codes/saxo-order/lambda_function.py` - Lambda entry point
- `/Users/kiva/codes/saxo-order/model/enum.py` - AlertType enum

**Configuration**:
- `/Users/kiva/codes/saxo-order/stocks.json` - Current stock list (fallback)
- `/Users/kiva/codes/saxo-order/followup-stocks.json` - Additional stocks
- `/Users/kiva/codes/saxo-order/config.yml` - System configuration

**Infrastructure**:
- `/Users/kiva/codes/saxo-order/pulumi/scheduler.py` - EventBridge schedule
- `/Users/kiva/codes/saxo-order/pulumi/dynamodb.py` - DynamoDB table definition

---

## Changelog

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-01-25 | 1.0 | Claude | Initial specification created from reverse engineering |

