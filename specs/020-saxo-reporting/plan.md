# Implementation Plan: Auto-suggest signal from selected strategy (Saxo Reporting US5)

**Branch**: `RNiveau/auto-select-signal` (against spec `020-saxo-reporting`) | **Date**: 2026-05-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/020-saxo-reporting/spec.md` (User Story 5, FR-017/018/019, SC-008)

## Summary

When the user picks a strategy in the create-journal modal of the Report page, the signal field MUST be pre-filled with the canonical signal for three mapped strategies (Bougie de 9h → Breakout 5m; Intraday → Breakout h1; Congestion → Breakout daily). The auto-fill is a default only: a manual change wins, and selecting a strategy outside the mapping leaves the signal field untouched. This is a pure frontend change inside `frontend/src/pages/Report.tsx` — no backend, API, or persistence changes.

**Technical approach**: extend the existing `onChange` handler of the strategy `<select>` (lines 578 and 676) to also call `setSignal(...)` when the chosen strategy is one of the three mapped enum keys. Mapping defined as a module-level `const STRATEGY_DEFAULT_SIGNAL: Record<string, string>` keyed by `Strategy` enum names (`B9H`, `INTRA`, `CONG`) and valued with `Signal` enum names (`BO5M`, `BOH1`, `BHD`) — the same `value` fields the backend already returns from `GET /report/config` (see `api/routers/report.py:34-35`).

## Technical Context

**Language/Version**: TypeScript 5+ / React 19+
**Primary Dependencies**: React (`useState`), existing `reportConfigService` from `frontend/src/services/api.ts` (already loaded — no new dependency)
**Storage**: N/A — purely in-memory component state (`strategy`, `signal`)
**Testing**: Manual smoke test in `npm run dev` (no frontend test framework configured — see constitution §Testing Standards, "Frontend Testing: TBD")
**Target Platform**: Web (Vite dev server on :5173, production build on Lambda-hosted dist)
**Project Type**: Web application (existing FastAPI backend + React frontend) — only the frontend module changes
**Performance Goals**: N/A — adds a constant-time lookup on a `<select>` change event
**Constraints**: Must not break the existing US2/US3 create/update flow; manual override of the auto-filled signal MUST be preserved (FR-018)
**Scale/Scope**: One file modified (`frontend/src/pages/Report.tsx`), two `<select onChange>` handlers updated, one module-level constant added. ~10 LOC.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies? | Verdict |
|-----------|----------|---------|
| I. Layered Architecture Discipline | Yes (frontend layer) | PASS — change stays inside the Page component; no inline axios calls added; `reportConfigService` (services layer) continues to be the sole API surface. |
| II. Clean Code First | Yes | PASS — one named `Record<string, string>` constant; no comments needed; uses the enum-key values already produced by the backend (no hardcoded strings duplicating the enum). |
| III. Configuration-Driven Design | Partial | PASS — the mapping is product behaviour (three canonical strategy→signal defaults) defined by the spec, not deployment configuration; lives next to the component that consumes it. No new env vars, no `VITE_*` change. |
| IV. Safe Deployment Practices | Yes | PASS — no infra change; ships as part of the frontend build; commit follows conventional commits (`feat:`). |
| V. Domain Model Integrity | Yes | PASS — uses backend-provided `Strategy.name` / `Signal.name` values; does not introduce new domain models; does not bypass the existing enum boundary. |

**Initial Constitution Check: PASS** — no violations, Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/020-saxo-reporting/
├── plan.md              # This file
├── spec.md              # Updated with US5 / FR-017–019 / SC-008
├── research.md          # Phase 0 — see ./research.md (US5 section appended)
├── data-model.md        # Phase 1 — unchanged; no entities added (see note in file)
├── quickstart.md        # Phase 1 — US5 section appended with manual verification steps
├── contracts/           # Unchanged — no API contract change for US5
└── tasks.md             # NOT created by /speckit.plan
```

### Source Code (repository root)

```text
frontend/
└── src/
    └── pages/
        └── Report.tsx          # ONLY file modified
            - add module-level STRATEGY_DEFAULT_SIGNAL constant
            - extend strategy <select> onChange at line 578 (create flow)
            - extend strategy <select> onChange at line 676 (update flow)
```

**Structure Decision**: Single-file frontend change. The existing `OrderModal` component (`Report.tsx:344`) already owns both the `strategy` and `signal` state and renders both `<select>` elements (create form at lines 575–599, update form at lines 673–697). The auto-fill behaviour belongs to the same component because (a) it operates on local component state, (b) both selects already share the same `strategies` / `signals` lists loaded from `reportConfigService`, and (c) factoring out a hook would be premature for ~10 LOC (Constitution §II: no over-engineering).

## Phase 0 — Outline & Research

No NEEDS CLARIFICATION markers in the spec. Two micro-questions worth recording in `research.md`:

1. **Which form(s) should auto-fill apply to** — create only, or also update? Both forms share `strategy`/`signal` state and render the same `<select>`s, so resolving this is a behavioural decision, not an architectural one. **Decision recorded in research.md**: apply to both (the user expects consistency; the update form is also used to add stop/objective/strategy/signal to an existing row, per US3 acceptance scenario #1).
2. **Should auto-fill overwrite a signal the user has already chosen** — or only fill when empty? Spec FR-019 says "the existing signal value (chosen or empty) is preserved" only for non-mapped strategies; for mapped strategies the spec is silent on a previously-set signal. **Decision recorded in research.md**: always overwrite on strategy-change for the three mapped strategies (this matches AC #6 "switching to another strategy that also has an auto-filled signal updates the field" and makes the behaviour predictable). The user remains free to manually change the signal afterwards (FR-018).

## Phase 1 — Design & Contracts

### Data model

No new entities or persisted fields. The mapping is a frontend constant. `data-model.md` does not need US5-specific changes; a one-line note will be added pointing back to this plan.

**Mapping (frontend constant)**:

```ts
const STRATEGY_DEFAULT_SIGNAL: Record<string, string> = {
  B9H: 'BO5M',     // Bougie de 9h → Breakout 5m
  INTRA: 'BOH1',   // Intraday      → Breakout h1
  CONG: 'BHD',     // Congestion    → Breakout daily
};
```

Keys/values use the same `value` field already produced by `GET /report/config` (the Python `Enum.name`), so no transformation is required at the `<select>` boundary.

### API contracts

No change. The mapping is client-side; the backend already exposes `strategies` and `signals` through `GET /report/config` (`api/routers/report.py:30-36`). The `POST` create/update endpoints continue to receive and persist whatever signal value the user finally submits (auto-filled or manually changed), so server contracts and validation stay intact.

### Quickstart additions

Append a "Verify US5 auto-suggest signal" section to `quickstart.md` with the manual steps that match AC #1–6.

### Agent context update

Run `.specify/scripts/bash/update-agent-context.sh claude` to refresh `CLAUDE.md` with the spec 020 update. No new technologies — only the spec entry is renewed.

## Post-Design Constitution Check

Re-evaluated after producing the design above. Still PASS — the design adds zero new dependencies, no new files, no new API surfaces, and stays inside the Page component that already owns the relevant state. No items required for "Complexity Tracking".

## Complexity Tracking

> Constitution Check passed without violations; this section intentionally empty.
