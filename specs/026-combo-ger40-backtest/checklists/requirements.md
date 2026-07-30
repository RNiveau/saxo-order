# Specification Quality Checklist: "GER40 Combo" Backtest (5m / 15m / H1)

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-07-30
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

- All six open strategy questions were resolved with the user before the spec was written
  (Clarifications, Session 2026-07-30), so no `[NEEDS CLARIFICATION]` markers were needed.
- Three assumptions are explicitly flagged for validation rather than left implicit, because
  each one changes a single requirement if wrong:
  1. **TP2 band deviation** — the spec assumes the inner (2.0) band; the outer (2.5) band would
     change FR-C07 only.
  2. **Pending-level validity of one candle** (FR-C04) — a longer window would change FR-C04 only.
  3. **CFD session (9:00–22:00) candle construction** — the cash session would shrink the signal
     universe on all three timeframes.
- The largest engineering risk is called out in Assumptions rather than hidden in the
  requirements: **FR-C11 (positions carry overnight) breaks the day-independent run engine**
  every existing backtest is built on. `/speckit.plan` must address that first.
- The 15-minute timeframe is not used by any existing backtest and may need to be assembled
  from smaller candles; also a plan-phase concern.
