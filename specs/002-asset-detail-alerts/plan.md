# Implementation Plan: Asset Detail Alerts Display

**Branch**: `002-asset-detail-alerts` | **Date**: 2026-01-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-asset-detail-alerts/spec.md`

## Summary

Add an alerts section to the asset detail page that displays all active alerts for the currently viewed asset. This provides contextual alert information alongside existing indicators and workflows, allowing traders to see relevant market signals without navigating to the separate alerts page. The feature filters alerts by asset code and country_code, showing only alerts for the asset being viewed.

## Technical Context

**Frontend:**
- **Language/Version**: TypeScript 5+, React 19+
- **Primary Dependencies**: React Router DOM v7+, Axios, Vite 7+
- **Existing Page**: `frontend/src/pages/AssetDetail.tsx` (existing file to be modified)
- **API Integration**: Use existing `alertService.getAll()` from `frontend/src/services/api.ts`
- **Testing**: None currently configured
- **Target Platform**: Web browser (served via Vite dev server on port 5173)

**Backend:**
- **No backend changes required**: Feature uses existing `/api/alerts` endpoint with query parameters
- **Existing API**: `GET /api/alerts?asset_code={code}&country_code={country_code}` already supports filtering
- **Alert Data**: Already available via `alertService.getAll()` with proper filtering

**Project Type**: Frontend-only enhancement (React component addition)
**Performance Goals**:
- Alerts section load time <1 second (parallel with other sections)
- No impact on existing page load time (alerts load asynchronously)
- Support up to 50 alerts per asset without performance degradation

**Constraints**:
- Must not modify existing AssetDetail page structure (indicators, workflows sections)
- Must follow existing CSS patterns in `AssetDetail.css`
- Must handle both assets with and without country_code
- Must parse asset symbol from URL parameter (/:symbol route)
- Alerts load must not block other section loads (indicators, workflows)

**Scale/Scope**:
- Expected 0-10 alerts per asset (typical case)
- Maximum 50 alerts per asset (edge case)
- Single user access pattern
- 7-day alert retention handled by backend TTL

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Layered Architecture Discipline ✅

**Frontend:**
- ✅ Pages: Modify existing `frontend/src/pages/AssetDetail.tsx` - add alerts section
- ✅ Components: Create new `frontend/src/components/AlertCard.tsx` for individual alert display
- ✅ Services: Use existing `frontend/src/services/api.ts` - `alertService.getAll()` already exists
- ✅ No direct API calls in components: All API interaction through service layer
- ✅ Props-based data flow: AlertCard receives alert data via props, emits events via callbacks

**Backend:**
- ✅ No changes required: Uses existing API endpoint `/api/alerts` with filtering support

**Verdict**: ✅ PASS - Frontend-only change respects layered architecture

### II. Clean Code First ✅

- ✅ Self-documenting: Use existing alert type enums, follow AssetDetail.tsx patterns
- ✅ No hardcoded strings: Alert types from backend enum values
- ✅ No over-engineering: Simple section addition, no new complex state management
- ✅ No unnecessary comments: Existing codebase patterns are clear

**Verdict**: ✅ PASS - Follows existing clean code patterns

### III. Configuration-Driven Design ✅

**Frontend:**
- ✅ API URL from `import.meta.env.VITE_API_URL` (existing pattern)
- ✅ No hardcoded backend endpoints
- ✅ No new configuration required

**Verdict**: ✅ PASS - Uses existing configuration patterns

### IV. Safe Deployment Practices ✅

- ✅ No infrastructure changes required
- ✅ No backend changes required
- ✅ Frontend builds via `npm run build` in frontend directory
- ✅ Conventional commits for all changes

**Verdict**: ✅ PASS - Standard frontend deployment process

### V. Domain Model Integrity ✅

- ✅ Alert data structure unchanged: Uses existing `AlertItem` interface from `frontend/src/services/api.ts`
- ✅ Asset identifier parsing: Correctly handles "CODE:COUNTRY" and "SYMBOL" formats
- ✅ No assumptions about country_code: Properly filters with null/empty string values
- ✅ Exchange field: Alert model already includes exchange field (per constitution v1.2.0)

**Verdict**: ✅ PASS - Respects existing domain model and constitution guidance

---

**Overall Constitution Compliance**: ✅ **PASS** - All 5 principles satisfied with no violations

## Project Structure

### Documentation (this feature)

```text
specs/002-asset-detail-alerts/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file (implementation plan)
├── data-model.md        # Data model documentation (Phase 1)
├── quickstart.md        # User guide (Phase 1)
├── checklists/
│   └── requirements.md  # Spec quality checklist (completed)
└── tasks.md             # Task list (Phase 2 - to be generated)
```

### Source Code (repository root)

```text
# Frontend (ONLY changes needed)
frontend/src/
├── pages/
│   └── AssetDetail.tsx           # MODIFIED: Add alerts section
├── components/
│   └── AlertCard.tsx             # NEW: Individual alert display component
└── pages/
    └── AssetDetail.css           # MODIFIED: Add alerts section styles

# No backend changes required - existing API sufficient
# No test changes required - no testing framework configured
```

**Structure Decision**: Frontend-only enhancement. Modify existing AssetDetail page to add a new alerts section that fetches and displays alerts for the current asset. Create reusable AlertCard component for consistent alert rendering. All data fetching uses existing alertService.

## Complexity Tracking

**No violations** - Constitution Check passed completely. No complexity justifications needed.

**Simplifications Made**:
- Leveraged existing `alertService.getAll()` API client (no new API integration)
- Followed existing AssetDetail.tsx section patterns (indicators, workflows sections provide template)
- Reused existing asset symbol parsing logic from AssetDetail.tsx
- Used existing CSS patterns from AssetDetail.css

## Implementation Phases

### Phase 0: Research ✅ COMPLETED

**Status**: ✅ Skipped - No research needed

**Rationale**: Complete understanding achieved through codebase exploration:
- AssetDetail.tsx structure and patterns reviewed
- alertService.getAll() API client verified
- AlertItem interface structure confirmed
- Existing CSS patterns in AssetDetail.css examined

**Artifacts**:
- ❌ `research.md` - Not created (no unknowns to resolve)
- ✅ Codebase exploration completed

---

### Phase 1: Design & Contracts ✅ COMPLETED

**Status**: ✅ All artifacts generated

**Objectives**:
1. Document alert data model for frontend display ✅
2. Create quickstart guide for using the alerts section ✅
3. No API contracts needed (uses existing endpoint) ✅

**Artifacts Created**:
1. ✅ `data-model.md` - Alert display data model (component props, state, transformations)
2. ✅ `quickstart.md` - User guide for viewing alerts on asset detail page
3. ❌ `/contracts/` - Not applicable (no new API endpoints, uses existing `/api/alerts`)

---

### Phase 2: Implementation Planning

**Status**: ⏸️ Not Started

**Objectives**:
1. Create detailed task list in `tasks.md`
2. Break down component creation and integration steps
3. Define testing approach (manual testing checklist)

**Next Command**: `/speckit.tasks` to generate implementation task list

---

## Architecture Decisions

### AD-001: Component Placement

**Decision**: Add alerts section between indicators and workflows sections

**Rationale**:
- Spec requirement (FR-012): "System MUST position the alerts section between the indicators section and the workflows section"
- Logical flow: Indicators → Alerts → Workflows provides context for correlation
- Existing layout supports insertion without breaking responsive design

**Alternatives Considered**:
- Above indicators: Rejected - would push primary data (indicators) down
- Below workflows: Rejected - too far from indicators for correlation
- Separate tab: Rejected - adds navigation complexity, contradicts spec

### AD-002: Alert Filtering Approach

**Decision**: Filter alerts client-side by passing asset_code and country_code query parameters to alertService.getAll()

**Rationale**:
- API already supports filtering via query parameters
- No additional network requests needed
- Consistent with existing indicator/workflow fetching patterns
- Backend handles null/empty country_code correctly

**Alternatives Considered**:
- Fetch all alerts, filter on frontend: Rejected - unnecessary data transfer
- Create new API endpoint: Rejected - existing endpoint sufficient
- Cache alerts globally: Rejected - premature optimization

### AD-003: Alert Display Limit

**Decision**: Show top 3 alerts by default with "Show All" button to expand

**Rationale**:
- Spec requirement (FR-014): "System MUST limit the alerts section height to show the 3 most recent alerts, with an option to expand"
- Prevents page length issues when many alerts exist
- Most users care about recent alerts
- Expand option preserves access to all alerts

**Alternatives Considered**:
- Show all alerts: Rejected - can make page too long
- Pagination: Rejected - adds complexity, not needed for typical case (0-10 alerts)
- Scrollable container: Rejected - harder to scan, doesn't work well on mobile

### AD-004: Alert Card Design

**Decision**: Create reusable AlertCard component with props-based configuration

**Rationale**:
- Follows existing pattern (IndicatorCard component exists)
- Enables consistent alert rendering across different types
- Testable in isolation (if testing added later)
- Can be reused if alerts shown elsewhere in future

**Alternatives Considered**:
- Inline alert rendering: Rejected - harder to maintain, violates component reusability
- Multiple alert type components: Rejected - over-engineering for 6 alert types
- External alert library: Rejected - no suitable library, custom requirements

### AD-005: Timestamp Display

**Decision**: Show relative time (e.g., "2 hours ago") with absolute timestamp on hover

**Rationale**:
- Spec requirement (FR-007): "System MUST provide absolute timestamp on hover or tap"
- Relative time easier to scan (users think "is this recent?")
- Absolute time provides precision when needed
- Standard UX pattern (Twitter, GitHub, etc.)

**Alternatives Considered**:
- Only absolute time: Rejected - harder cognitive load for recency assessment
- Only relative time: Rejected - loses precision for older alerts
- Side-by-side display: Rejected - takes too much space, visually cluttered

## File Changes Summary

### New Files (2)

1. **`frontend/src/components/AlertCard.tsx`** (~150 lines)
   - Purpose: Reusable alert display component
   - Props: `alert` (AlertItem), `showTimestamp` (boolean)
   - Renders: Alert type badge, timestamp, alert-specific data fields

2. **`specs/002-asset-detail-alerts/data-model.md`** (~100 lines)
   - Purpose: Document alert display data structures
   - Content: Component props, state interfaces, data flow

3. **`specs/002-asset-detail-alerts/quickstart.md`** (~50 lines)
   - Purpose: User guide for viewing alerts
   - Content: How to access, what information is shown, filtering behavior

### Modified Files (2)

1. **`frontend/src/pages/AssetDetail.tsx`** (+~100 lines)
   - Add: Alerts section state (loading, error, alerts list, expanded)
   - Add: `fetchAlerts()` function with asset filtering
   - Add: `useEffect` hook to fetch alerts on symbol change
   - Add: Alerts section JSX between indicators and workflows
   - Add: Expand/collapse functionality

2. **`frontend/src/pages/AssetDetail.css`** (+~50 lines)
   - Add: `.alerts-section` styles
   - Add: `.alert-card` styles
   - Add: `.alert-type-badge` styles with color coding
   - Add: `.expand-alerts-btn` styles
   - Add: Responsive breakpoints for mobile

### Unchanged Files (Backend)

- ✅ `api/routers/alerting.py` - No changes needed
- ✅ `api/services/alerting_service.py` - No changes needed
- ✅ `frontend/src/services/api.ts` - No changes needed (alertService exists)

**Total LOC Impact**: ~350 lines added (300 frontend code, 50 docs)

## Next Steps

1. ✅ Complete Phase 1: Generate `data-model.md` and `quickstart.md`
2. ⏭️ Run `/speckit.tasks` to generate detailed task list in `tasks.md`
3. ⏭️ Run `/speckit.implement` to execute tasks from task list
4. ⏭️ Manual testing against spec success criteria
5. ⏭️ Create commit following conventional commit format

**Ready for**: `/speckit.tasks` command to generate implementation task list
