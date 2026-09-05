# Specification Quality Checklist: Weekly-Timeframe Combo Detection

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-23
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- All three clarifications were resolved in Session 2026-08-23 and encoded in the spec:
  1. **Evaluation cadence** -> every daily scan, on the forming week (FR-003, FR-006).
  2. **History requirement** -> reduced criteria set, ~60 weekly bars (FR-001, FR-004, SC-004).
  3. **Threshold calibration** -> calibrated against historical weekly data before release (FR-010, SC-005).
- Owner review on PR #711 (2026-08-23) raised five items; all are resolved in the spec:
  1. **Repeat suppression vs. the shared de-dup key** → FR-007 keys on weekly bar + direction and requires the change to be inert for other alert types.
  2. **Suppression layer** → FR-013 pins it to the recording layer; SC-005 now counts asset-days.
  3. **Long-only triage** → US2 scenarios and FR-009 restated; a Sell weekly combo can never reach the top band.
  4. **Provider request cost** → US4 states the weekly series cannot be re-cut from the existing fetch and the request count roughly doubles.
  5. **Calibration and validation data** → new Dependencies section names the backtest raw-candle store and the trader-labelled sample as release prerequisites.
- Requirements renumbered after splitting the old FR-004 and, later, after dropping the feature toggle; cross-references updated.
- Second owner review on PR #711 (plan + spec revision) raised three items; all resolved:
  1. **Calibration data source** → the backtest candle cache holds intraday bars for two index CFDs, not weekly bars for the scanned equities. Dependencies bullet and R8 rewritten around a one-off sampled fetch.
  2. **Fallback over-promotion** → new FR-014 and SC-008: daily + weekly combo count as one point in the degraded ranking, matching the congestion precedent. FR-009 and SC-006 scoped to the reasoned path.
  3. **Enumeration sites** → four, not three; the per-type badge CSS is the real gap, the label map is polish.
- The `weekly_combo_enabled` toggle was removed after implementation review (2026-08-23): it was a speculative feature guarding a hypothetical, with `deploy.sh` already providing the revert path. FR-012 dropped, SC-007 restated as a one-time revert check, requirements renumbered to FR-001..FR-014.
- Checklist passes in full.
