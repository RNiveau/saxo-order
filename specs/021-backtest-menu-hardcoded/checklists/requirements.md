# Specification Quality Checklist: Backtest Menu with Hardcoded "CAC40 Bougie de 9h" Backtest

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-07-14
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

- All open questions (entry fill price, gap/slippage handling on exits) were resolved with the user before the spec was written and are captured directly in FR-010 rather than as open markers.
- Re-entry: the user corrected the initial "one trade per day" assumption — the strategy allows multiple sequential trades per day as long as the previous position has closed first. This is captured in FR-006 and FR-011, Acceptance Scenario 7, and the "Repeat breakdown after a closed trade" edge case.
- Range output: the user specified the exact range-run summary fields (number of days, number of trades, number of winning/losing positions, average win, average loss, final result). Captured in FR-012/FR-013, User Story 2, and SC-003. Win/loss classification, average-loss sign convention, and the "number of days" definition were filled in as documented assumptions rather than re-clarified with the user, since they are conventional choices with limited scope impact.
- Break-even stop: the user added a rule where the stop-loss moves to break-even once price is 20 points in profit, with its own "number of BE" figure in the summary. Captured in FR-008a, FR-009/FR-010/FR-011 (extended), FR-013, User Story 1 (Scenarios 8-9) and User Story 2 (Scenario 4), the Key Entities, and three new edge cases covering same-candle arm/breach ordering. The same-candle ordering rule (arming only takes effect from the next candle) is a documented assumption, since only candle OHLC data is available, not tick-level price paths.
- Post-implementation review (PR #626): a reviewer caught a genuine internal contradiction — FR-008a's "a points result of 0" for break-even exits vs. FR-010's gap-fill rule, which (as literally written) also applies to break-even and can produce a small non-zero result on a gap. The user resolved this in favor of FR-010 (gap-fill applies uniformly to all three exit types, including break-even) rather than special-casing break-even to always clamp to exactly 0. FR-008a, FR-010, FR-013, and the Assumptions section were updated to state this explicitly: "break-even" is a classification of *which mechanism* closed the trade, not a guarantee that the outcome was exactly flat. `data-model.md`'s validation rule was corrected to match, and `data-model.md`'s `Trade.exit_time` field type was corrected from `Optional[datetime]` to `datetime` (a separate, pre-existing doc/code drift noticed while making this edit — the implementation never constructs an open `Trade`).
- Ready for `/speckit.clarify` (optional, given clarifications were already resolved) or `/speckit.plan`.
