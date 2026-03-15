# Quickstart: Workflow Orders List Page (014)

## Prerequisites

- Python 3.11+ and `poetry` installed
- Node 20+ installed
- AWS credentials configured (for DynamoDB access) OR a local DynamoDB mock

## Run the stack

```bash
# Terminal 1 — backend API
poetry run python run_api.py     # starts FastAPI on http://localhost:8000

# Terminal 2 — frontend
cd frontend
npm run dev                      # starts Vite on http://localhost:5173
```

## Seed test data (optional)

To see the page with data, trigger a workflow execution that places orders, or manually
insert records into the `workflow_orders` DynamoDB table for testing.

## Manual test checklist

### US1 — View all workflow orders

1. Navigate to `http://localhost:5173/workflow-orders` (or click "Workflow Orders" in the sidebar)
2. Verify the page title shows "Workflow Orders"
3. Verify orders from multiple workflows appear in a single flat list, newest first
4. Verify each row shows: timestamp (human-readable), workflow name, asset code, direction badge (BUY/SELL), price, quantity
5. With no orders in DynamoDB (cleared or fresh), verify an empty state message is shown

### US2 — Filter by workflow or direction

6. Click the workflow name dropdown — verify it is populated with unique workflow names from the loaded orders
7. Select one workflow — verify only that workflow's orders remain visible
8. Clear the workflow filter — verify all orders are restored
9. Select "BUY" from the direction filter — verify only buy orders are shown
10. Select "SELL" — verify only sell orders are shown
11. Select "All" (or clear) — verify all orders are restored
12. Combine both filters (workflow X + BUY) — verify only buy orders from workflow X are shown

### API smoke test

```bash
# Should return all orders across all workflows
curl http://localhost:8000/api/workflow/orders

# With limit
curl "http://localhost:8000/api/workflow/orders?limit=10"
```

### Sidebar and routing

13. From any page, verify "Workflow Orders" link is visible in the sidebar
14. Click it — verify navigation to `/workflow-orders` and the page renders correctly
15. Verify the active link is highlighted when on the page

## Build verification

```bash
# Backend
poetry run mypy .
poetry run flake8
poetry run pytest

# Frontend
cd frontend
npm run build    # TypeScript must compile without errors
npm run lint     # ESLint must pass
```
