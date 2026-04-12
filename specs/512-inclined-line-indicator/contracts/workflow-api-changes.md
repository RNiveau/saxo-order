# API Contract Changes: Inclined Line Indicator

**Date**: 2026-04-12
**Feature**: 512-inclined-line-indicator

## Modified Endpoints

### POST /api/workflow/workflows — Create Workflow

**Change**: `WorkflowIndicatorInput` gains optional `x1` and `x2` fields.

#### Request Body (inclined indicator example)

```json
{
  "name": "ACA ROB support",
  "index": "aca:xpar",
  "cfd": "aca:xpar",
  "enable": true,
  "dry_run": true,
  "is_us": false,
  "conditions": [
    {
      "indicator": {
        "name": "inclined",
        "ut": "h1",
        "x1": {
          "date": "2024-09-19",
          "price": 27.94
        },
        "x2": {
          "date": "2024-09-27",
          "price": 27.46
        }
      },
      "close": {
        "direction": "below",
        "ut": "h1",
        "spread": 0.5
      }
    }
  ],
  "trigger": {
    "ut": "h1",
    "location": "lower",
    "order_direction": "buy",
    "quantity": 100
  }
}
```

**Validation**:
- When `indicator.name` is `"inclined"`, `x1` and `x2` are required
- `x1.date` and `x2.date` must be valid ISO date strings (YYYY-MM-DD)
- `x1.date` must differ from `x2.date`
- `x1.price` and `x2.price` must be positive floats
- `value` and `zone_value` are ignored for inclined indicators

### PUT /api/workflow/workflows/{workflow_id} — Update Workflow

Same changes as POST. The `x1` and `x2` fields follow the same validation rules.

### GET /api/workflow/workflows/{workflow_id} — Get Workflow Detail

**Change**: `IndicatorDetail` response gains optional reference point fields.

#### Response Body (inclined indicator condition)

```json
{
  "indicator": {
    "name": "inclined",
    "ut": "h1",
    "value": null,
    "zone_value": null,
    "x1_date": "2024-09-19",
    "x1_price": 27.94,
    "x2_date": "2024-09-27",
    "x2_price": 27.46
  }
}
```

### GET /api/workflow/indicator-types — List Indicator Types

**Change**: Response includes the new inclined type.

#### Response Body (addition)

```json
{
  "value": "inclined",
  "label": "Inclined (ROB/SOH)"
}
```

## New Pydantic Models

### PointInput

```python
class PointInput(BaseModel):
    date: str  # ISO date YYYY-MM-DD
    price: float = Field(..., gt=0)
```

## Modified Pydantic Models

### WorkflowIndicatorInput

```python
class WorkflowIndicatorInput(BaseModel):
    name: str
    ut: str
    value: Optional[float] = None
    zone_value: Optional[float] = None
    x1: Optional[PointInput] = None  # NEW
    x2: Optional[PointInput] = None  # NEW
```

### IndicatorDetail

```python
class IndicatorDetail(BaseModel):
    name: str
    ut: str
    value: Optional[float] = None
    zone_value: Optional[float] = None
    x1_date: Optional[str] = None    # NEW
    x1_price: Optional[float] = None  # NEW
    x2_date: Optional[str] = None    # NEW
    x2_price: Optional[float] = None  # NEW
```

## Backward Compatibility

- All new fields are optional — existing workflows without inclined indicators are unaffected
- No existing endpoint signatures change
- No breaking changes to request/response formats for non-inclined indicators
