# Implementation Plan for Issue #409: Create APIs to Create Orders

## Status: ✅ COMPLETED

All tasks have been implemented and tested successfully. 22/22 tests passing.

## Analysis Summary

The codebase has:
- **3 CLI order commands**: `set_order`, `set_oco_order`, `set_stop_limit_order` in `saxo_order/commands/`
- **Existing FastAPI infrastructure**: `api/main.py` with routers for search, workflow, indicators, etc.
- **Business logic in services**: `saxo_order/service.py` contains validation (`apply_rules`, `validate_ratio`, `validate_fund`)
- **Interactive CLI helpers**: `input_helper.py` has user prompts (`select_account`, `update_order`, `confirm_order`)
- **Core client**: `SaxoClient.set_order()` does actual order placement

## Implementation Strategy

### 1. **Extract Business Logic Layer**
Create `saxo_order/services/order_service.py` to extract non-interactive logic from CLI commands:
- Order creation logic (from `set_order.py`, `set_oco_order.py`, `set_stop_limit_order.py`)
- Validation orchestration (using existing `apply_rules`, `validate_ratio`, etc.)
- Remove dependency on `click` prompts and `input_helper` functions

### 2. **Create API Request/Response Models**
Create `api/models/order.py` with Pydantic models:
- `OrderRequest` (matches CLI params: code, price, quantity, order_type, direction, conditional, etc.)
- `OcoOrderRequest` (limit_price, limit_direction, stop_price, stop_direction, etc.)
- `StopLimitOrderRequest` (limit_price, stop_price, etc.)
- `OrderResponse` (success status, order details, validation messages)
- Validation with Pydantic ensures same validation as Click type checking

### 3. **Create Order Router**
Create `api/routers/order.py` with endpoints:
- `POST /api/orders` - place regular order
- `POST /api/orders/oco` - place OCO order
- `POST /api/orders/stop-limit` - place stop-limit order
- Use dependency injection for `SaxoClient` (like existing routers)
- Error handling: catch `SaxoException` → HTTP 400 with human-readable JSON error
- Use `OrderService` for business logic

### 4. **Refactor CLI Commands**
Update `saxo_order/commands/set_order.py`, `set_oco_order.py`, `set_stop_limit_order.py`:
- Keep Click decorators and interactive prompts
- Delegate to new `OrderService` for business logic
- CLI provides user interaction, service provides logic (separation of concerns)

### 5. **Update Main API**
Modify `api/main.py`:
- Import and include new `order.router`

### 6. **Unit Tests**
Create comprehensive test coverage:
- `tests/saxo_order/services/test_order_service.py` - test business logic
- `tests/api/routers/test_order.py` - test API endpoints with FastAPI TestClient
- Mock `SaxoClient` to avoid real API calls
- Test validation errors return HTTP 400 with clear messages
- Test successful order placement flows

## Key Design Decisions

- **Shared validation**: Both CLI and API use same `OrderService` → consistent validation
- **Pydantic validation**: API request models validate types/constraints (mirrors Click validation)
- **Error mapping**: `SaxoException` → HTTP 400 (as required), unexpected errors → HTTP 500
- **Account selection**: API will accept `account_key` parameter (CLI prompts interactively)
- **No auto-confirmation in API**: API skips CLI's `confirm_order` step (API caller confirms before sending request)

## Files Created/Modified

**New files:** ✅
- `saxo_order/services/__init__.py` - Service layer package
- `saxo_order/services/order_service.py` - Business logic for order management (315 lines)
- `api/models/order.py` - Pydantic models for request/response validation (106 lines)
- `api/routers/order.py` - FastAPI endpoints for order operations (172 lines)
- `tests/saxo_order/services/__init__.py` - Test package
- `tests/saxo_order/services/test_order_service.py` - OrderService unit tests (268 lines, 11 tests)
- `tests/api/routers/test_order.py` - API endpoint integration tests (323 lines, 11 tests)

**Modified files:** ✅
- `saxo_order/commands/set_order.py` - Refactored to use OrderService (122 lines)
- `saxo_order/commands/set_oco_order.py` - Refactored to use OrderService (115 lines)
- `saxo_order/commands/set_stop_limit_order.py` - Refactored to use OrderService (81 lines)
- `api/main.py` - Added order router import and registration

## Implementation Results

### API Endpoints Created
1. **POST /api/orders** - Create regular orders (limit, stop, open_stop, market)
2. **POST /api/orders/oco** - Create OCO (One-Cancels-Other) orders
3. **POST /api/orders/stop-limit** - Create stop-limit orders

### Test Coverage
- **Service Layer**: 11 tests covering order creation, validation, account management
- **API Layer**: 11 tests covering endpoints, validation, error handling
- **Total**: 22 tests, all passing ✅

### Key Features Delivered
✅ API uses same code as CLI (shared `OrderService`)
✅ API accepts same inputs as CLI (validated by Pydantic)
✅ API uses same validation rules as CLI (`apply_rules`, `validate_ratio`, etc.)
✅ Validation errors return HTTP 400 with clear human-readable JSON messages
✅ CLI refactored to use `OrderService` (maintaining backward compatibility)
✅ Complete separation of concerns (CLI handles interaction, service handles logic)
✅ Comprehensive test coverage with mocked dependencies

### Example API Usage

```bash
# Create a limit order
curl -X POST http://localhost:8000/api/orders \
  -H "Content-Type: application/json" \
  -d '{
    "code": "AAPL",
    "price": 150.0,
    "quantity": 10,
    "order_type": "limit",
    "direction": "buy",
    "stop": 145.0,
    "objective": 165.0,
    "country_code": "xnas"
  }'

# Create an OCO order
curl -X POST http://localhost:8000/api/orders/oco \
  -H "Content-Type: application/json" \
  -d '{
    "code": "AAPL",
    "quantity": 10,
    "limit_price": 155.0,
    "limit_direction": "sell",
    "stop_price": 145.0,
    "stop_direction": "sell"
  }'

# Create a stop-limit order
curl -X POST http://localhost:8000/api/orders/stop-limit \
  -H "Content-Type: application/json" \
  -d '{
    "code": "AAPL",
    "quantity": 10,
    "limit_price": 150.0,
    "stop_price": 148.0,
    "stop": 145.0,
    "objective": 160.0
  }'
```

### Error Response Example

```json
{
  "detail": "Not enough money for this order"
}
```

HTTP Status: 400 Bad Request
