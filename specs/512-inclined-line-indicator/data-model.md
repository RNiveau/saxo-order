# Data Model: Inclined Line Indicator (ROB/SOH)

**Date**: 2026-04-12
**Feature**: 512-inclined-line-indicator

## Entities

### Point (NEW — exists on inclined-indicator branch)

A coordinate representing a date and price used to define the inclined line.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| x | datetime | Yes | Calendar date of the reference point |
| y | float | Yes | Price level at this date |

**Validation**: None beyond type constraints. Dates are parsed from ISO format strings.

### IndicatorInclined (NEW — extends Indicator, exists on inclined-indicator branch)

Extends the base `Indicator` class with two reference points that define the inclined line.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | IndicatorType | Yes | Must be `IndicatorType.INCLINED` |
| ut | UnitTime | Yes | Unit time for candle evaluation |
| value | float | No | Unused (inherited, always None) |
| zone_value | float | No | Unused (inherited, always None) |
| x1 | Point | Yes | First reference point (date + price) |
| x2 | Point | Yes | Second reference point (date + price) |

**Validation**:
- `x1.x != x2.x` — the two dates must differ (prevents division by zero in slope calculation)
- Both `x1` and `x2` must be provided when indicator type is "inclined"

### IndicatorType Enum (MODIFIED — add INCLINED)

| Value | String | Description |
|-------|--------|-------------|
| INCLINED | "inclined" | Inclined line projected from two reference points |

### WorkflowIndicatorInput (MODIFIED — Pydantic API model)

Add optional reference point fields for inclined indicator API support.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | str | Yes | Indicator type name |
| ut | str | Yes | Unit time |
| value | float | No | For polarite/zone |
| zone_value | float | No | For zone |
| x1 | PointInput | No | First reference point (for inclined) |
| x2 | PointInput | No | Second reference point (for inclined) |

### PointInput (NEW — Pydantic API model)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| date | str | Yes | ISO date string (YYYY-MM-DD) |
| price | float | Yes | Price level |

### IndicatorDetail (MODIFIED — Pydantic response model)

Add optional reference point fields for inclined indicator in workflow detail responses.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| x1_date | str | No | First reference point date (for inclined) |
| x1_price | float | No | First reference point price (for inclined) |
| x2_date | str | No | Second reference point date (for inclined) |
| x2_price | float | No | Second reference point price (for inclined) |

## Relationships

```
Workflow 1──* Condition
Condition 1──1 Indicator (or IndicatorInclined)
IndicatorInclined 1──2 Point
```

## State Transitions

No state transitions. The inclined line is stateless — it is computed on every workflow run from the static reference points and the current date.

## Storage

No new DynamoDB tables or attributes. Workflows with inclined indicators are stored in the existing `workflows` DynamoDB table. The `x1` and `x2` fields are serialized as nested objects within the condition's indicator data.
