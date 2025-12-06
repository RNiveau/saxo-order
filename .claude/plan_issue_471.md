# Implementation Plan: Binance Order Reporting (Issue #471)

**Created:** 2025-12-06
**Status:** Approved - Ready for implementation

## Overview
Add Binance order reporting to API and frontend by extracting logic from existing CLI command. The CLI remains the source of truth - no code duplication.

### Key Insight
80% of code is reusable! The frontend needs ZERO changes because it's already platform-agnostic.

---

## Phase 1: Backend Service Layer (Extract from CLI)

**Create:** `api/services/binance_report_service.py`

Extract methods from `saxo_order/commands/binance.py`:
- `get_orders_report()` - From CLI lines 46-48 (calls BinanceClient.get_report_all)
- `create_gsheet_order()` - From CLI lines 64-73 (remove interactive prompts)
- `update_gsheet_order()` - From CLI lines 75-106 (remove interactive prompts)
- Reuse `convert_order_to_eur()` and `calculate_summary()` from SaxoReportService
- Add 5-minute caching (TTLCache) like Saxo service

Create Binance pseudo-account helper:
```python
Account(key="binance", name="Binance Account", ...)
```

---

## Phase 2: API Router Updates

**Modify:** `api/routers/report.py`

Update all 5 endpoints to detect Binance accounts:
- `GET /orders` - Route to BinanceReportService if `account_id.startswith("binance_")`
- `GET /summary` - Same routing logic
- `POST /gsheet/create` - Same routing logic
- `POST /gsheet/update` - Same routing logic
- `GET /config` - No changes (already generic)

**Modify:** `api/routers/fund.py`

Update `GET /accounts` endpoint to include Binance pseudo-account:
```python
binance_account = AccountInfo(
    account_id="binance_main",
    account_name="Binance",
    ...
)
all_accounts = [binance_account] + saxo_accounts
```

---

## Phase 3: Dependencies Fix

**Modify:** `api/dependencies.py`

Update `get_binance_client()` to use real API keys from config:
```python
return BinanceClient(
    key=config.binance_keys[0],
    secret=config.binance_keys[1]
)
```

---

## Phase 4: Refactor CLI to Use Service

**Modify:** `saxo_order/commands/binance.py`

Replace inline logic with service calls:
- Import BinanceReportService
- Call service methods instead of duplicating logic
- Keep interactive prompts (CLI-specific behavior)

---

## Phase 5: Testing

Add unit tests:
- `tests/api/services/test_binance_report_service.py` (new)
- Extend `tests/api/routers/test_report.py` for Binance routing

---

## Frontend Changes

**NONE REQUIRED!** ✅

The account selector, order table, and Google Sheets modals already work generically.

---

## Files Summary

**Create (1 file):**
- `api/services/binance_report_service.py` (~150 lines)

**Modify (4 files):**
- `api/routers/report.py` (~30 lines added)
- `api/routers/fund.py` (~15 lines added)
- `api/dependencies.py` (~5 lines changed)
- `saxo_order/commands/binance.py` (~50 lines refactored)

**Test (2 files):**
- `tests/api/services/test_binance_report_service.py` (new)
- `tests/api/routers/test_report.py` (extend)

---

## Critical Design Decision

Use account ID prefix `"binance_main"` to distinguish from Saxo accounts. Backend detects prefix and routes to appropriate service (BinanceReportService vs ReportService).

---

## Estimated Effort
- Backend: ~300 lines of code
- Frontend: 0 lines
- Tests: ~200 lines

---

## Implementation Order

1. ✅ Create BinanceReportService (extract from CLI)
2. ✅ Update API dependencies (fix BinanceClient initialization)
3. ✅ Update fund router (add Binance account to list)
4. ✅ Update report router (add account detection and routing)
5. ✅ Refactor CLI to use new service
6. ✅ Add unit tests
7. ✅ Manual testing with frontend
