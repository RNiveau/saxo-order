# Quickstart: Create Workflow

**Feature**: 016-workflow-create
**Date**: 2026-03-22

---

## Prerequisites

- Backend running: `poetry run python run_api.py` (port 8000)
- Frontend running: `npm run dev` in `frontend/` (port 5173)
- DynamoDB accessible (local or AWS with credentials)

---

## Scenario 1: Create a workflow from the Workflows page

**Test**: Basic creation with MA50 indicator (no extra value fields)

1. Navigate to `http://localhost:5173/workflows`
2. Click the "New Workflow" button (top-right of the page)
3. Verify the creation modal opens with defaults: Dry Run = ON, Enabled = ON
4. Fill in:
   - Index: `DAX.I`
   - CFD: `GER40.I`
   - Indicator Type: `MA50`
   - Verify: no "value" or "zone value" fields appear
   - Indicator Timeframe: `H1`
   - Condition Direction: `Above`
   - Condition Timeframe: `H1`
   - Spread: `40`
   - Trigger Timeframe: `H1`
   - Order Location: `Higher`
   - Order Direction: `Buy`
   - Quantity: `0.1`
5. Verify the Name field auto-suggests `"Buy MA50 H1 DAX"` (or similar)
6. Click "Save"
7. Verify the modal closes
8. Verify the new workflow appears immediately in the Workflows list

**curl equivalent**:
```bash
curl -X POST http://localhost:8000/api/workflow/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Buy MA50 H1 DAX",
    "index": "DAX.I",
    "cfd": "GER40.I",
    "enable": true,
    "dry_run": true,
    "is_us": false,
    "end_date": null,
    "conditions": [{
      "indicator": {"name": "ma50", "ut": "h1", "value": null, "zone_value": null},
      "close": {"direction": "above", "ut": "h1", "spread": 40.0},
      "element": null
    }],
    "trigger": {
      "ut": "h1",
      "location": "higher",
      "order_direction": "buy",
      "quantity": 0.1
    }
  }'
```

Expected response: `201 Created` with full `WorkflowDetail` JSON including generated `id`, `created_at`, `updated_at`.

---

## Scenario 2: Create a POL workflow (requires value field)

1. Open the creation modal from the Workflows page
2. Set Indicator Type: `POL (Polarité)`
3. Verify a "Value" field appears
4. Fill in Value: `7500`
5. Verify "Zone Value" field does NOT appear
6. Complete remaining fields and save

---

## Scenario 3: Create a ZONE workflow (requires two value fields)

1. Open the creation modal
2. Set Indicator Type: `ZONE`
3. Verify both "Value" (lower bound) and "Zone Value" (upper bound) fields appear
4. Fill in Value: `18000`, Zone Value: `18500`
5. Complete and save

---

## Scenario 4: Create from Asset Detail page (pre-fill)

1. Navigate to an asset detail page, e.g., `http://localhost:5173/asset/GER40.I:xpar`
2. Click "Create Workflow"
3. Verify the modal opens with:
   - CFD pre-filled: `GER40.I`
   - Index pre-filled: `GER40.I`
4. Adjust index to `DAX.I` (the underlying index)
5. Complete remaining fields and save

---

## Scenario 5: Validation — missing required field

1. Open the creation modal
2. Leave the "Index" field empty
3. Click "Save"
4. Verify the form does NOT submit and highlights the Index field with an inline error
5. Fill in Index and click "Save" — form should submit successfully

---

## Scenario 6: Validation — past end date

1. Open the creation modal
2. Set End Date to yesterday's date
3. Click "Save"
4. Verify inline error: "End date must be a future date"

---

## Scenario 7: Name auto-suggestion updates dynamically

1. Open the creation modal
2. Set Indicator Type: `BBB`, Trigger Direction: `Buy`, Indicator Timeframe: `H4`
3. Verify Name field shows `"Buy BBB H4"` (or similar with asset if pre-filled)
4. Change Indicator Type to `MA50`
5. Verify Name updates to `"Buy MA50 H4"`
6. Manually type a custom name
7. Verify custom name persists even after changing other fields

---

## Scenario 8: Cancel discards input

1. Open the creation modal
2. Fill in several fields
3. Click "Cancel" (or click the backdrop)
4. Verify modal closes
5. Verify the Workflows list is unchanged (no partial workflow created)

---

## Scenario 9: Save failure — error banner

1. Stop the backend server
2. Open the creation modal and fill all fields
3. Click "Save"
4. Verify an error banner appears inside the modal (e.g., "Failed to create workflow. Please try again.")
5. Verify all form input is preserved
6. Restart the backend, click "Save" again — workflow should be created successfully
