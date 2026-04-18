# Quickstart: Inclined Line Indicator (ROB/SOH)

**Date**: 2026-04-12
**Feature**: 512-inclined-line-indicator

## Prerequisites

- Python 3.11+ with Poetry
- Node.js 18+ with npm (for frontend)
- Saxo API credentials in `secrets.yml`

## Setup

```bash
# Install backend dependencies
poetry install

# Install frontend dependencies
cd frontend && npm install && cd ..
```

## Development

### Backend

```bash
# Run API server
poetry run python run_api.py

# Run tests
poetry run pytest tests/engines/test_workflows.py -v
poetry run pytest tests/services/test_indicator_service.py -v

# Run all tests with coverage
poetry run pytest --cov

# Code quality
poetry run black .
poetry run isort .
poetry run mypy .
poetry run flake8
```

### Frontend

```bash
cd frontend
npm run dev    # Dev server on port 5173
npm run build  # Type check + production build
npm run lint   # ESLint
```

## Testing the Feature

### Via YAML workflow definition

Add to `workflows.yml`:

```yaml
- name: ACA ROB support
  index: aca:xpar
  cfd: aca:xpar
  enable: true
  conditions:
    - indicator:
          name: inclined
          ut: h1
          x1:
            x: "2024-09-19"
            y: 27.94
          x2:
            x: "2024-09-27"
            y: 27.46
      close:
         direction: below
         ut: h1
         spread: 0.5
  trigger:
    ut: h1
    signal: breakout
    location: lower
    order_direction: buy
    quantity: 100
```

### Via API

```bash
curl -X POST http://localhost:8000/api/workflow/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ACA ROB support",
    "index": "aca:xpar",
    "cfd": "aca:xpar",
    "enable": true,
    "dry_run": true,
    "conditions": [{
      "indicator": {
        "name": "inclined",
        "ut": "h1",
        "x1": {"date": "2024-09-19", "price": 27.94},
        "x2": {"date": "2024-09-27", "price": 27.46}
      },
      "close": {"direction": "below", "ut": "h1", "spread": 0.5}
    }],
    "trigger": {"ut": "h1", "location": "lower", "order_direction": "buy", "quantity": 100}
  }'
```

## Key Files

| File | Purpose |
|------|---------|
| `model/workflow.py` | Point, IndicatorInclined, IndicatorType.INCLINED |
| `engines/workflows.py` | InclinedWorkflow class |
| `engines/workflow_engine.py` | INCLINED case dispatch |
| `engines/workflow_loader.py` | YAML parsing for x1/x2 |
| `services/indicator_service.py` | Linear math + business day calculation |
| `model/workflow_api.py` | Pydantic models (PointInput, extended WorkflowIndicatorInput) |
| `api/routers/workflow.py` | INCLINED label in indicator types |
| `services/workflow_service.py` | Inclined-specific validation |
| `frontend/src/components/WorkflowCreateModal.tsx` | UI reference point inputs |
