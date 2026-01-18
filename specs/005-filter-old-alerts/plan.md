# Implementation Plan: Filter Old Alerts (5-Day Retention)

**Branch**: `005-filter-old-alerts` | **Date**: 2026-01-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-filter-old-alerts/spec.md`

**Type**: Amendment to existing features 001 and 002
**Amends**:
- [001-alerts-ui-page](../001-alerts-ui-page/spec.md)
- [002-asset-detail-alerts](../002-asset-detail-alerts/spec.md)

## Summary

Modify alert display logic to filter alerts older than 5 days (120 hours) and deduplicate alerts by keeping only the most recent alert for each (asset, alert_type) combination. Implementation is client-side only in the frontend React components, requiring no backend API changes. DynamoDB TTL remains at 7 days for storage cleanup while the UI filters at 5 days for display. This amendment addresses the limitation that DynamoDB TTL is not reliable for application-level filtering within specific time windows.

## Technical Context

**Language/Version**: TypeScript 5+ (frontend), Python 3.11+ (backend - no changes)
**Primary Dependencies**: React 19+, Vite 7+, Axios (frontend)
**Storage**: No changes - uses existing DynamoDB alerts table with TTL
**Testing**: Manual testing (no frontend test framework configured), backend tests unchanged
**Target Platform**: Web browsers (Chrome, Firefox, Safari)
**Project Type**: Web application (backend API + frontend SPA)
**Performance Goals**: Filtering + deduplication <50ms for 500 alerts
**Constraints**: Client-side operations only, no API response time impact
**Scale/Scope**: Affects 2 frontend components (Alerts page, Asset Detail page)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Layered Architecture Discipline
✅ **PASS** - Frontend changes only:
- Pages layer: Alerts.tsx and AssetDetail.tsx modified
- Utils layer: New shared utility functions for filtering/deduplication
- No direct API calls added (uses existing alertService.getAll())
- Changes respect existing layer boundaries

### II. Clean Code First
✅ **PASS** - Implementation approach:
- Create self-documenting utility functions (filterRecentAlerts, deduplicateAlertsByType)
- No hardcoded magic numbers (120 hours stored as const FIVE_DAYS_HOURS = 120)
- Minimal inline comments (logic is clear from function names)
- Black/isort formatting for any backend changes (though none expected)

### III. Configuration-Driven Design
✅ **PASS** - Configurable filter threshold:
- 5-day threshold (120 hours) stored as constant in utils file
- Can be easily adjusted without code changes if needed
- No hardcoded retention values scattered across components

### IV. Safe Deployment Practices
✅ **PASS** - Frontend-only deployment:
- No infrastructure changes required
- No backend API changes required
- Standard Vite build process (`npm run build`)
- Conventional commit format will be followed

### V. Domain Model Integrity
✅ **PASS** - Alert data model unchanged:
- AlertItem interface remains the same
- Uses existing `date` field (ISO timestamp) for age calculation
- Uses existing `alert_type` and `asset_code` for deduplication key
- Respects existing data structure and relationships

**Gate Status**: ✅ **ALL GATES PASSED** - No violations, proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/005-filter-old-alerts/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file (in progress)
├── research.md          # Phase 0 output (to be generated)
├── data-model.md        # Phase 1 output (to be generated)
├── quickstart.md        # Phase 1 output (to be generated)
├── contracts/           # Phase 1 output (to be generated)
└── checklists/
    └── requirements.md  # Specification quality checklist (complete)
```

### Source Code (repository root)

```text
# Frontend (modifications only)
frontend/src/
├── pages/
│   ├── Alerts.tsx                  # MODIFY: Add 5-day filter + deduplication
│   └── AssetDetail.tsx             # MODIFY: Add 5-day filter + deduplication
├── utils/
│   └── alertFilters.ts             # NEW: Shared filtering/deduplication utilities
└── services/
    └── api.ts                      # NO CHANGES: Use existing alertService.getAll()

# Backend (no changes expected)
api/
└── (no changes required)

# Tests (manual frontend testing)
No automated frontend tests (framework not configured)
Manual testing checklist to be provided in quickstart.md
```

**Structure Decision**: Web application structure (backend + frontend). Implementation focuses entirely on frontend client-side filtering. No backend changes required since API already returns all alerts with timestamps and type information needed for filtering/deduplication.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*No complexity violations detected. Implementation fully complies with constitution principles.*

---

## Phase 0: Research

**Status**: ⏳ Pending

### Research Questions

Based on Technical Context and frontend exploration, the following research tasks are needed:

1. **Frontend Alert State Management**: How do Alerts.tsx and AssetDetail.tsx manage alert state after API fetch?
2. **Alert Data Structure**: What is the exact structure of AlertItem interface and what fields are available?
3. **Current Filtering Patterns**: What existing filtering logic exists in Alerts.tsx that we can extend?
4. **Utility Function Patterns**: Where should shared utility functions live in the frontend codebase?

### Research Tasks

#### Task 1: Frontend Alert Component Analysis
**Question**: How do Alerts.tsx and AssetDetail.tsx currently fetch, store, and display alerts?
**Approach**:
- Read `frontend/src/pages/Alerts.tsx` to understand current fetch/filter logic
- Read `frontend/src/pages/AssetDetail.tsx` to understand asset-specific alert display
- Identify state management patterns and data flow

**Findings** (from exploration agent):
- **Alerts.tsx (lines 50-77)**:
  - Fetches all alerts with `alertService.getAll()` on mount
  - Stores in state: `alerts: AlertItem[]` and `availableFilters`
  - Client-side filtering already exists for asset_code and alert_type
  - Uses composite key for React rendering: `${asset_code}_${alert_type}_${date}`

- **AssetDetail.tsx (lines 156-169, 667-674)**:
  - Calls `alertService.getAll({ asset_code, country_code })` with params
  - Stores in `alertsData: AlertItem[]` state
  - Shows first 3 alerts, expandable to all
  - Supports on-demand alert detection with NEW badges

#### Task 2: AlertItem Interface Structure
**Question**: What fields are available in AlertItem for filtering and deduplication?
**Approach**:
- Read `frontend/src/services/api.ts` interface definitions
- Identify timestamp fields and type fields

**Findings** (from exploration agent):
```typescript
export interface AlertItem {
  id: string;
  alert_type: string;           // For deduplication key
  asset_code: string;           // For deduplication key
  asset_description: string;
  exchange: string;
  country_code: string | null;  // For deduplication key
  date: string;                 // ISO timestamp - for 5-day filter
  data: Record<string, any>;
  age_hours: number;            // Pre-calculated, can use for display
}
```

**Decision**: Use `date` field (ISO string) for age calculation. Use `(asset_code, country_code, alert_type)` as deduplication key.

#### Task 3: Utility Function Location
**Question**: Where should shared alert filtering utilities be placed?
**Approach**:
- Check existing `frontend/src/utils/` directory structure
- Follow patterns from existing utility files (marketHours.ts, tradingview.ts)

**Decision**: Create `frontend/src/utils/alertFilters.ts` with:
- `filterRecentAlerts(alerts: AlertItem[], maxAgeHours: number): AlertItem[]`
- `deduplicateAlertsByType(alerts: AlertItem[]): AlertItem[]`
- `processAlerts(alerts: AlertItem[]): AlertItem[]` - combines both operations

#### Task 4: Date Calculation Patterns
**Question**: How to calculate age from ISO timestamp strings in TypeScript?
**Approach**:
- Standard JavaScript Date parsing
- Calculate difference in milliseconds, convert to hours

**Decision**:
```typescript
const calculateAgeHours = (isoDateString: string): number => {
  const alertDate = new Date(isoDateString);
  const now = new Date();
  const diffMs = now.getTime() - alertDate.getTime();
  return diffMs / (1000 * 60 * 60);
};
```

**Output**: research.md with consolidated findings and design decisions

---

## Phase 1: Design & Contracts

**Status**: ⏳ Pending (run after Phase 0 completion)

### Design Artifacts

**Prerequisites**: research.md complete

1. **data-model.md**: Document AlertItem structure, deduplication key definition, filtering criteria
2. **contracts/**: No new API contracts (uses existing GET /api/alerts endpoint)
3. **quickstart.md**: Development setup, testing instructions (manual testing checklist)

### API Contracts

**No new API endpoints required** - uses existing:
```
GET /api/alerts?asset_code=&alert_type=&country_code=
Response: AlertsResponse { alerts: AlertItem[], total_count, available_filters }
```

Frontend applies filtering and deduplication client-side after receiving API response.

### Data Model Changes

**No backend data model changes** - client-side processing only:

**Deduplication Key**:
```
Composite key: "${asset_code}:${country_code || 'null'}:${alert_type}"
```

**Filtering Criteria**:
```
Keep alert IF (now - alert.date) <= 120 hours
```

**Processing Order**:
```
1. Fetch all alerts from API
2. Filter by 5-day age (≤120 hours)
3. Deduplicate by (asset, type), keeping most recent
4. Render filtered & deduplicated list
```

**Output**: data-model.md, quickstart.md, agent context updated

---

## Phase 2: Task Generation

**Status**: ⏳ Pending (manual invocation of `/speckit.tasks` required after Phase 1)

**Note**: Phase 2 is executed by running `/speckit.tasks` command separately. This command generates `tasks.md` with dependency-ordered implementation tasks.

---

## Implementation Notes

### Frontend Changes Required

**1. Create Utility Functions** (`frontend/src/utils/alertFilters.ts`):
```typescript
// Constants
export const FIVE_DAYS_HOURS = 120;

// Filter alerts by age
export const filterRecentAlerts = (
  alerts: AlertItem[],
  maxAgeHours: number = FIVE_DAYS_HOURS
): AlertItem[] => {
  const now = new Date();
  return alerts.filter(alert => {
    const alertDate = new Date(alert.date);
    const ageHours = (now.getTime() - alertDate.getTime()) / (1000 * 60 * 60);
    return ageHours <= maxAgeHours;
  });
};

// Deduplicate by asset + type, keep most recent
export const deduplicateAlertsByType = (alerts: AlertItem[]): AlertItem[] => {
  const keyMap = new Map<string, AlertItem>();

  for (const alert of alerts) {
    const key = `${alert.asset_code}:${alert.country_code || 'null'}:${alert.alert_type}`;
    const existing = keyMap.get(key);

    if (!existing || new Date(alert.date) > new Date(existing.date)) {
      keyMap.set(key, alert);
    }
  }

  return Array.from(keyMap.values());
};

// Combined processing pipeline
export const processAlerts = (alerts: AlertItem[]): AlertItem[] => {
  const recent = filterRecentAlerts(alerts);
  const deduped = deduplicateAlertsByType(recent);
  return deduped.sort((a, b) =>
    new Date(b.date).getTime() - new Date(a.date).getTime()
  );
};
```

**2. Modify Alerts Page** (`frontend/src/pages/Alerts.tsx`):
- Import: `import { processAlerts } from '../utils/alertFilters';`
- Line 50: After fetching alerts, apply processing:
  ```typescript
  const data = await alertService.getAll();
  const processedAlerts = processAlerts(data.alerts);
  setAlerts(processedAlerts);
  ```
- Line 161: Update empty state message from "7 days" to "5 days"

**3. Modify Asset Detail Page** (`frontend/src/pages/AssetDetail.tsx`):
- Import: `import { processAlerts } from '../utils/alertFilters';`
- Line 156-161: After fetching alerts, apply processing:
  ```typescript
  const response = await alertService.getAll({ asset_code, country_code });
  const processedAlerts = processAlerts(response.alerts);
  setAlertsData(processedAlerts);
  ```

### Testing Strategy

**Manual Testing Checklist** (to be added to quickstart.md):
1. Create test alerts with timestamps: 1 day, 3 days, 5 days, 6 days, 8 days ago
2. Verify Alerts page shows only 1, 3, 5 day alerts (not 6 or 8)
3. Create 3 COMBO alerts for same asset at different times
4. Verify only most recent COMBO alert displays
5. Create COMBO + CONGESTION20 for same asset
6. Verify both display (different types)
7. Navigate to Asset Detail page, verify same filtering applies
8. Check empty state message says "5 days" not "7 days"

**No automated frontend tests** - project has no testing framework configured per constitution.

### Deployment Checklist

**Frontend Only**:
1. Create `frontend/src/utils/alertFilters.ts`
2. Modify `frontend/src/pages/Alerts.tsx` to use processAlerts()
3. Modify `frontend/src/pages/AssetDetail.tsx` to use processAlerts()
4. Run `npm run lint` and fix any issues
5. Run `npm run build` to verify TypeScript compiles
6. Manual smoke test: View Alerts page and Asset Detail page
7. Deploy frontend via standard process

**No Backend Changes Required**

---

## Success Criteria Mapping

From spec.md Success Criteria:

- **SC-001**: 100% of alerts older than 5 days (>120 hours) are hidden
  - **Implementation**: filterRecentAlerts() function with 120-hour threshold

- **SC-002**: Alerts exactly at 5 days (120 hours) are displayed correctly
  - **Implementation**: Use `<=` comparison (inclusive), not `<`

- **SC-003**: Filtering logic is consistent across Alerts page and Asset Detail page
  - **Implementation**: Both pages use same processAlerts() utility function

- **SC-009**: When multiple alerts of same type exist for asset, 100% of duplicates removed
  - **Implementation**: deduplicateAlertsByType() groups by composite key, keeps most recent

- **SC-010**: Deduplication is applied per-asset
  - **Implementation**: Deduplication key includes asset_code + country_code

- **SC-011**: Alerts of different types are NOT deduplicated
  - **Implementation**: Deduplication key includes alert_type

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Performance degradation with many alerts | Low | Medium | Process alerts client-side after fetch; modern browsers handle 500+ items easily |
| Inconsistent filtering if functions called separately | Low | High | Export single processAlerts() function that combines both operations |
| Timezone issues in date comparison | Low | Medium | Use JavaScript Date objects which handle ISO strings correctly; server timestamps are UTC |
| Missing or invalid alert.date field | Low | Low | Add null check in filterRecentAlerts(); skip invalid alerts |
| User confusion about 5-day change | Medium | Low | Update empty state messages to clearly say "5 days"; document in release notes |

---

## Next Steps

1. **Complete Phase 0**: Generate `research.md` (already complete via exploration agent)
2. **Complete Phase 1**: Generate `data-model.md`, `contracts/`, and `quickstart.md`
3. **Run `/speckit.tasks`**: Generate dependency-ordered tasks in `tasks.md`
4. **Implement**: Follow tasks.md for step-by-step implementation
5. **Test**: Manual testing checklist from quickstart.md
6. **Deploy**: Frontend build and deployment

**Command to continue**: `/speckit.tasks` (after Phase 0 and Phase 1 complete)
