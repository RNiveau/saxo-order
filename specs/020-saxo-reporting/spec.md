# Feature Specification: Saxo Order Reporting

**Feature Branch**: `020-saxo-reporting`
**Created**: 2026-05-31 (retroactive documentation)
**Status**: Implemented
**Input**: User description: "we need a retro spec about the saxo reporting feature, (backend + UI)"

## Overview

The Saxo reporting feature lets a trader review the orders that were executed on a Saxo Bank account over a chosen period and selectively persist the resulting positions to a Google Sheets trading journal with risk-management metadata (stop loss, objective, strategy, signal). It is exposed both as an interactive CLI (`k-order get-report`) and as a web UI backed by an HTTP API, and is the original implementation later generalized to support Binance (see `specs/471-binance-reporting/spec.md`).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Review executed Saxo orders for a period (Priority: P1)

As a trader, I want to list every order that was filled on one of my Saxo accounts since a chosen start date so I can audit my recent trading activity in a single view, with prices expressed in both the original currency and EUR.

**Why this priority**: Without this list, the trader has no consolidated view of what was filled on Saxo and cannot reconcile the broker's activity with the trading journal. Every downstream action (journaling, P&L analysis, position management) depends on it.

**Independent Test**: Pick a Saxo account, enter a start date, and verify that all orders filled since that date are listed with date, asset, direction, quantity, price, and EUR conversion. Aggregated counters (total orders, buy/sell volume, fees) match the row-level data.

**Acceptance Scenarios**:

1. **Given** a Saxo account with executed orders since 2025-01-01, **When** the trader requests the report from 2025-01-01, **Then** every executed order is listed in chronological order with date, name, direction, quantity, and execution price.
2. **Given** an order executed in a non-EUR currency (e.g. USD, JPY), **When** the report is displayed, **Then** the price and total are shown both in original currency and converted to EUR using the configured exchange rate.
3. **Given** a warrant/turbo order with an underlying asset, **When** the report is displayed, **Then** the underlying asset's price at execution is also shown.
4. **Given** an account with no executed orders in the period, **When** the trader requests the report, **Then** an explicit "no orders" message is shown instead of an empty table.
5. **Given** multiple Saxo accounts on the user's profile, **When** the trader opens the report, **Then** they can choose which account to report on before fetching the orders.

---

### User Story 2 - Journal a new position to Google Sheets (Priority: P1)

As a trader, after reviewing an opening order in the report, I want to save it as a new position in my Google Sheets trading journal with my stop loss, objective, strategy, and signal so my journal stays in sync with what I actually traded and my risk management is captured at the moment of entry.

**Why this priority**: Capturing entries with stop and objective is the core of the trader's journaling discipline. Without it the report is read-only and the journal must be updated by hand, which is error-prone and skipped under pressure.

**Independent Test**: From a populated report, pick an opening order, enter stop / objective / strategy / signal (and optional comment), confirm; verify a new row appears in the configured Google Sheets with the order data and the risk-management fields populated, prices shown in both original currency and EUR, and computed risk/reward.

**Acceptance Scenarios**:

1. **Given** an opening order in the report, **When** the trader opens the "create" flow and enters stop, objective, strategy, and signal, **Then** a new row is appended to the Google Sheets journal with the order's date, asset, direction, quantity, prices (original + EUR), strategy, signal, stop, objective, and the computed risk/reward.
2. **Given** the create flow, **When** the trader omits strategy or signal, **Then** the journal entry is rejected with a validation error and no row is written.
3. **Given** an order in a currency other than EUR, **When** the journal entry is created, **Then** both the original currency price and the EUR-converted price are persisted on the row.
4. **Given** the order belongs to a stock (not a derivative/crypto), **When** the journal entry is created, **Then** the row includes the regulatory taxes computed from the order's total amount.

---

### User Story 3 - Update an existing journaled position (Priority: P2)

As a trader, I want to update a position that is already in my Google Sheets journal — either to adjust the stop/objective while the position is still open, or to mark it as closed (and indicate whether it was stopped or break-even-stopped) — so the journal reflects the lifecycle of each trade without manual sheet editing.

**Why this priority**: Tracking lifecycle events is essential for accurate P&L and post-trade analysis, but it is less critical than the initial journaling: a missed update degrades historical analytics, while a missed entry loses the trade entirely.

**Independent Test**: From the report, select an order corresponding to an already-journaled position, point at the row in the sheet, choose "adjust" or "close"; verify the targeted row is updated with the new stop/objective or with the closure flags and computed taxes, and that no other row is affected.

**Acceptance Scenarios**:

1. **Given** an open position already in the journal, **When** the trader adjusts the stop and/or objective for a given row, **Then** only that row's stop, objective, and dependent computed fields (e.g. risk/reward) are updated.
2. **Given** a closing order in the report, **When** the trader marks the corresponding journal row as closed, **Then** the row is updated with the closing price, closing date, the "stopped" / "BE-stopped" flags, and the computed taxes.
3. **Given** a closing update on a stock, **When** it is persisted, **Then** the regulatory taxes for the closing leg are computed and written to the journal.
4. **Given** the trader targets a wrong row number, **When** the update is submitted, **Then** the system updates only the targeted row (no implicit row search) — selecting the correct row remains the trader's responsibility.

---

### User Story 4 - Aggregated summary of the period (Priority: P3)

As a trader, while reviewing the report I want to see aggregated statistics for the period (total number of orders, buy vs sell breakdown, total volume in EUR, total fees) so I can get a quick sense of activity without scanning every row.

**Why this priority**: The summary is decision-support: useful but not blocking. The detailed list already covers the audit need.

**Independent Test**: Load a report with a known mix of buys and sells in mixed currencies; verify the summary shows the correct counts, the buy/sell volume split, and a total EUR amount consistent with the per-row EUR conversions.

**Acceptance Scenarios**:

1. **Given** a non-empty report, **When** it is displayed in the UI, **Then** summary cards show total orders, total volume in EUR, total fees, and a buy/sell breakdown.
2. **Given** orders in multiple currencies, **When** the summary is computed, **Then** all monetary aggregates are expressed in EUR using the configured conversion rates.

---

### User Story 5 - CLI parity for power users (Priority: P3)

As a power user / script author, I want the same reporting and journaling capabilities available from a CLI command so I can run the workflow from a terminal and keep my pre-existing scripts working.

**Why this priority**: The CLI predates the UI and remains the source of truth for the underlying behavior; preserving it keeps existing workflows intact, but day-to-day use is shifting to the UI.

**Independent Test**: Run the CLI command with a start date, select an account interactively, view the printed orders, optionally answer the interactive prompts to create or update Google Sheets rows; verify the resulting sheet matches what the UI would produce.

**Acceptance Scenarios**:

1. **Given** the CLI command is invoked with a start date, **When** the user selects a Saxo account, **Then** the executed orders since that date are printed with the same fields and EUR conversion as the UI.
2. **Given** the CLI is run with the gsheet-update flag, **When** the user picks an order row and chooses "create", **Then** a new journal row is appended exactly as it would be from the UI flow.
3. **Given** the CLI is run with the gsheet-update flag, **When** the user picks an order row and chooses "update", **Then** they can either adjust the stop/objective or mark the position closed (with stopped / BE-stopped flags), with the same outcome as the UI.

---

### Edge Cases

- **Empty period**: No order matches the date range → the system shows an explicit empty-state message instead of an empty table or an error.
- **Missing currency rate**: An order is in a currency for which no conversion rate is configured → the report still displays the order, falling back to a default rate or omitting the EUR column for that row rather than failing the whole report.
- **Underlying-less derivative**: A derivative order has no underlying price returned → the row is still shown; the underlying line is omitted.
- **Single-account user**: A user with a single Saxo account is not forced through an extra selection step.
- **Google Sheets write failure**: A network or permission error during create/update surfaces a clear error to the user; no partial row is left in the sheet, and the in-memory report is not corrupted.
- **Wrong row update**: The user targets a non-existent or wrong row → the update is rejected with a clear message; existing rows are not silently overwritten.
- **Non-stock asset taxation**: Regulatory taxes are only computed for stocks; derivatives and crypto journal entries do not include a tax line.
- **Stale conversion rates**: Conversion rates come from configuration and are not real-time → the report reflects journaling-time accuracy, not mark-to-market, and this is acceptable for journal use.
- **Date format mismatch**: The user enters a start date in an unexpected format → the system rejects it with an explicit error rather than silently returning no orders.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow the user to fetch the list of executed orders on a chosen Saxo account from a chosen start date up to today.
- **FR-002**: System MUST let the user select the target Saxo account when several accounts exist on their profile.
- **FR-003**: System MUST display, for each order, at minimum: execution date, asset name/code, direction (buy/sell), quantity, execution price, and total amount.
- **FR-004**: System MUST display prices and totals in EUR using configured conversion rates whenever the order's currency is not EUR, in addition to the original-currency values.
- **FR-005**: System MUST display the underlying asset's price for derivative orders (e.g. warrants/turbos) when the broker provides one.
- **FR-006**: System MUST provide an aggregated summary of the period including total order count, buy/sell breakdown, total EUR volume, and total fees.
- **FR-007**: System MUST allow the user to create a new journal entry in Google Sheets from any executed order in the report, capturing at least: order data, stop loss, objective, strategy, signal, and an optional free-text comment.
- **FR-008**: System MUST reject creation of a journal entry that does not specify both a strategy and a signal.
- **FR-009**: System MUST allow the user to update an existing journal row in Google Sheets, either by adjusting the stop/objective (position still open) or by marking the position as closed.
- **FR-010**: System MUST capture closure flags "stopped" and "break-even-stopped" on a closing update so post-trade analysis can distinguish those outcomes.
- **FR-011**: System MUST compute regulatory taxes for stock orders when persisting to Google Sheets, and MUST NOT add a tax line for non-stock assets (derivatives, crypto).
- **FR-012**: System MUST expose the reporting and journaling capabilities via two surfaces with equivalent behavior: an interactive CLI command and a web UI backed by an HTTP API.
- **FR-013**: System MUST provide the list of valid strategies and signals to the UI so the user picks them from controlled vocabularies rather than typing free text.
- **FR-014**: System MUST route reporting requests to the Saxo backend for Saxo account identifiers and to the Binance backend for Binance account identifiers (shared report surface, see `specs/471-binance-reporting/spec.md`).
- **FR-015**: System MUST clearly surface failures from the broker API or Google Sheets to the user without corrupting the journal or the in-memory report.
- **FR-016**: System MUST require the user to confirm the journal row number to update; it MUST NOT try to auto-detect which journal row corresponds to which order.

### Key Entities

- **ReportOrder**: An order that was actually executed on a broker account. Carries asset identity (code, name), direction, quantity, execution price, currency, execution date, asset type (stock / derivative / crypto), and, for derivatives, an optional underlying price. Extended with journaling metadata when persisted: stop, objective, strategy, signal, comment, and lifecycle flags (`open_position`, `stopped`, `be_stopped`).
- **Account**: A trading account on a broker. Identified by an account id whose prefix determines which backend serves the report (Saxo vs Binance).
- **Strategy / Signal**: Controlled vocabularies (enums) describing the trader's reason for entering the trade. Required at journal creation time.
- **Taxes**: Per-order fee/tax structure (broker cost + regulatory tax) computed for stocks only and persisted to the journal alongside the order.
- **Journal Row (Google Sheets)**: The persisted representation of a position in the trader's external journal. Holds order data (in original currency and EUR), risk-management fields (stop, objective, strategy, signal, comment), computed taxes, and lifecycle status (open / closed / stopped / BE-stopped).
- **Period Summary**: Aggregate over the reported orders — total count, buy/sell breakdown, EUR volume, total fees — recomputed from the displayed orders.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A trader can list all executed orders for a chosen Saxo account and date in under 3 seconds for a typical month of activity.
- **SC-002**: Currency conversions match the configured rates within ±0.01 EUR for every displayed row.
- **SC-003**: Creating a journal entry from the report writes exactly one new row to the Google Sheet, with all mandatory fields (order data, stop, objective, strategy, signal) populated, in 100% of successful runs.
- **SC-004**: Updating a journal entry modifies only the targeted row; no other rows are altered, in 100% of runs.
- **SC-005**: The aggregated summary (counts, EUR volumes, fees) is consistent with the per-row data within ±0.01 EUR.
- **SC-006**: The CLI and the UI produce equivalent results for the same input (same account, same start date) — same orders, same EUR conversions, same journal rows.
- **SC-007**: An empty result set and a broker/Sheets failure are each surfaced with a clear, distinct user-facing message (no silent failures).

## Assumptions

- The trader's Google Sheets journal already exists and has the expected column layout; the feature writes into it, it does not create it.
- Currency conversion rates are maintained in configuration and refreshed out-of-band; the feature does not fetch live FX rates.
- The CLI is run by a single user on a trusted workstation with valid Saxo and Google credentials; multi-tenant authentication is out of scope for the CLI.
- Account selection in the UI uses the same authenticated user profile as the rest of the app; no separate login flow is part of this feature.
- The trader is responsible for selecting the correct journal row when updating; the feature does not auto-match orders to existing journal rows.
- Regulatory taxes only apply to stocks under the current French-resident assumption baked into the tax formula; other tax regimes are out of scope.

## Out of Scope

- Real-time / streaming order updates — the report is a pull on demand for a chosen period.
- Live FX rates — conversions use configured rates.
- Automated reconciliation between Saxo orders and existing journal rows.
- P&L computation, performance analytics, or charting based on journaled positions (the journal is the data source for those, but they are separate features).
- Multi-user / role-based access to the journal — single-trader use is assumed.
- Mobile-specific UI — the web UI is the only graphical surface.

## Dependencies

- **Saxo Bank API**: source of executed order activity for a Saxo account over a period.
- **Google Sheets API**: target of journal create/update operations.
- **Application configuration**: currency conversion rates, Google Sheets spreadsheet id and credentials, list of valid strategies and signals.
- **Binance reporting feature** (`specs/471-binance-reporting`): shares the same report UI/API surface; this Saxo feature is the original implementation that the Binance one generalized.
