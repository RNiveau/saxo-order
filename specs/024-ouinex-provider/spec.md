# Feature Specification: Ouinex crypto provider

**Feature Branch**: `024-ouinex-provider`  
**Created**: 2026-07-21  
**Status**: Draft  
**Input**: User description: "Introduce this new provider ouinex. Here is the api doc https://api.ouinex.com/ It's a crypto provider and I want the same behavior that for binance. In the gsheet, ouinex has to be map as binance"

## Overview

Ouinex is a new cryptocurrency provider to be introduced alongside the existing Binance provider. It must offer the same capabilities the platform already offers for Binance — searching crypto instruments, adding them to the watchlist, retrieving market data for indicators and alerts, and reporting trading activity into the trading journal. When any Ouinex activity is written to the Google Sheet trading journal, it must be recorded under the existing "binance" provider so that all crypto activity stays consolidated under a single journal identity.

## Clarifications

### Session 2026-07-21

- Q: What is the capability scope for Ouinex — full read-only parity with Binance, or also placing/executing orders? → A: Read-only parity — instrument search, candle/market data for indicators & alerts, and trade-history reporting only. Order placement/execution is out of scope (Binance has none today).
- Q: Does Ouinex coexist with Binance, or replace it as the crypto provider? → A: Coexist — both providers remain available and independent; Binance is unchanged.
- Q: Do Ouinex market-data endpoints (instrument search + candles) require API credentials, or are they public like Binance? → A: Require API key — all Ouinex operations, including search and candle retrieval, require authenticated Ouinex credentials (this differs from Binance's public market-data endpoints).
- Q: In the Google Sheet journal, how exactly should Ouinex trades be recorded as "binance"? → A: Same "binance" identity — Ouinex journal entries are indistinguishable from native Binance rows.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recognize Ouinex as a selectable crypto provider (Priority: P1)

As a trader, I can choose Ouinex as a provider wherever I currently choose Binance, so that I can work with crypto instruments sourced from Ouinex the same way I do with Binance.

**Why this priority**: Nothing else in the feature can be exercised until the system recognizes Ouinex as a valid provider. This is the foundational slice that unlocks every other capability.

**Independent Test**: Select Ouinex as the provider in any place that currently accepts Binance, and confirm the system accepts it as valid and routes subsequent actions to Ouinex without error.

**Acceptance Scenarios**:

1. **Given** the provider options that today include Binance, **When** I view the available crypto providers, **Then** Ouinex is offered as a selectable option.
2. **Given** I select Ouinex as the provider, **When** I perform an action that requires provider credentials, **Then** the system uses the Ouinex credentials and does not fall back to Binance credentials.

---

### User Story 2 - Search and add Ouinex crypto instruments to the watchlist (Priority: P1)

As a trader, I can search for crypto instruments available on Ouinex and add them to my watchlist, so that I can track them just like Binance instruments.

**Why this priority**: Searching and watch-listing is the primary entry point for tracking any instrument. Delivered on its own, this already provides value by letting the trader curate Ouinex instruments.

**Independent Test**: Search for a known Ouinex crypto pair, add it to the watchlist, and confirm it appears with the crypto classification, exactly as a Binance instrument would.

**Acceptance Scenarios**:

1. **Given** I have selected Ouinex, **When** I search by keyword for a crypto pair, **Then** I see matching Ouinex instruments in the results.
2. **Given** a matching Ouinex instrument, **When** I add it to my watchlist, **Then** it is stored as a crypto instrument tagged the same way a Binance crypto instrument is tagged.
3. **Given** an Ouinex instrument in my watchlist, **When** I view the watchlist, **Then** it is presented consistently with how Binance crypto instruments are presented.

---

### User Story 3 - Retrieve Ouinex market data for indicators and alerts (Priority: P2)

As a trader, I can view indicators and receive alerts for Ouinex instruments based on their market data (candles), so that I get the same analytical signals I get for Binance instruments.

**Why this priority**: Indicators and alerts are the core analytical value of the platform, but they depend on the provider and watch-listing slices being in place first.

**Independent Test**: Request indicators for an Ouinex instrument across supported timeframes and confirm candle-based indicators are computed and alerts can fire, matching Binance behavior.

**Acceptance Scenarios**:

1. **Given** an Ouinex instrument, **When** I request its indicators for a supported timeframe, **Then** the system retrieves Ouinex market data and computes the same indicators it computes for Binance.
2. **Given** an Ouinex instrument being monitored, **When** market conditions meet an alert rule, **Then** the alert is raised the same way it would be for a Binance instrument.
3. **Given** a request for a timeframe the provider does not return directly (such as the in-progress current day or hour), **When** indicators are computed, **Then** the current period is reconstructed from a smaller timeframe, exactly as done for Binance.

---

### User Story 4 - Report Ouinex trading activity into the journal as Binance (Priority: P2)

As a trader, I can pull my Ouinex trading activity and record it in the Google Sheet trading journal, and those entries are recorded under the "binance" provider so that all my crypto trades stay consolidated in one place.

**Why this priority**: Journal reporting is important for record-keeping and is the concrete embodiment of the "map as binance" requirement, but it depends on the provider being recognized first.

**Independent Test**: Generate a report of Ouinex trades for a date range, write selected trades to the journal, and confirm the journal records them under the "binance" provider identity — indistinguishable in provider label from native Binance entries.

**Acceptance Scenarios**:

1. **Given** trading activity on Ouinex over a date range, **When** I generate a report, **Then** I see the Ouinex trades with the same fields shown for Binance reports.
2. **Given** an Ouinex trade from the report, **When** I write it to the trading journal, **Then** the journal entry is recorded under the "binance" provider, not "ouinex".
3. **Given** both native Binance trades and Ouinex trades written to the journal, **When** I inspect the journal, **Then** the provider identity is "binance" for both and crypto activity is consolidated.

---

### Edge Cases

- What happens when Ouinex credentials are missing or invalid? Because every Ouinex operation requires credentials, all Ouinex actions (search, candles, alerts, reporting) fail with a clear provider-specific error, without affecting Binance functionality.
- What happens when a search keyword matches no Ouinex instrument? An empty result set is returned, consistent with Binance search behavior.
- What happens when Ouinex is temporarily unavailable or returns an error while fetching market data or trades? The failure should be isolated to Ouinex actions and should not degrade Binance or other providers.
- What happens if the same crypto instrument (e.g., a BTC pair) exists on both Ouinex and Binance? The user can track and report each independently, but journal entries from either roll up under the "binance" provider identity.
- What happens when Ouinex returns a currency or amount format that differs from Binance? Reported values must be normalized to the same journal conventions used for Binance entries.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST recognize Ouinex as a valid crypto provider everywhere Binance is currently accepted as a provider (search, watchlist, indicators, alerts, and reporting).
- **FR-002**: System MUST authenticate to Ouinex using Ouinex-specific credentials, kept separate from Binance credentials, and MUST NOT reuse Binance credentials for Ouinex actions. All Ouinex operations — including instrument search and candle retrieval — require valid Ouinex credentials (unlike Binance, whose market-data endpoints are public).
- **FR-003**: Users MUST be able to search Ouinex for crypto instruments by keyword and see matching instruments in the results.
- **FR-004**: Users MUST be able to add an Ouinex instrument to the watchlist, and the system MUST store and classify it as a crypto instrument using the same classification and tagging applied to Binance crypto instruments.
- **FR-005**: System MUST retrieve Ouinex market data (candles) for all timeframes currently supported for Binance and compute the same indicators from it.
- **FR-006**: System MUST reconstruct the in-progress current day and current hour candles for Ouinex from a smaller timeframe when the provider does not return them directly, consistent with the existing Binance behavior.
- **FR-007**: System MUST raise the same alerts for Ouinex instruments, under the same rules, as it does for Binance instruments.
- **FR-008**: Users MUST be able to generate a report of Ouinex trading activity for a given date range, presenting the same fields as a Binance report.
- **FR-009**: System MUST allow selected Ouinex trades to be written to the Google Sheet trading journal.
- **FR-010**: System MUST record every Ouinex journal entry under the "binance" provider identity, so that Ouinex activity is indistinguishable from native Binance activity in the journal's provider/account field.
- **FR-011**: System MUST normalize Ouinex-reported amounts and currencies to the same conventions used for Binance journal entries.
- **FR-012**: System MUST isolate Ouinex failures (missing credentials, provider errors, unavailability) so they do not affect Binance or other providers.
- **FR-013**: Introducing Ouinex MUST NOT change or remove any existing Binance capability; Binance continues to operate independently and unchanged.
- **FR-014**: Order placement/execution on Ouinex is OUT OF SCOPE. Parity with Binance covers read-only capabilities only (search, market data, indicators, alerts, and trade-history reporting); the system MUST NOT place or execute orders on Ouinex.

### Key Entities *(include if feature involves data)*

- **Provider (Exchange)**: The source of a crypto instrument and its market/trade data. Today includes Saxo and Binance; this feature adds Ouinex as a new crypto provider. For journal-writing purposes, Ouinex maps to the existing Binance provider identity.
- **Crypto Instrument**: A tradable crypto pair sourced from a provider, tracked in the watchlist and analyzed via indicators/alerts. An Ouinex instrument behaves identically to a Binance instrument.
- **Market Data (Candle)**: Time-series price data retrieved from the provider, used to compute indicators and evaluate alerts.
- **Trade / Report Order**: A record of trading activity retrieved from the provider and written to the journal. Ouinex trades are written under the "binance" provider identity.
- **Trading Journal Entry**: A row in the Google Sheet recording a trade under a provider/account. Ouinex entries carry the "binance" provider identity.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A trader can search, add to watchlist, view indicators/alerts for, and report trades from an Ouinex instrument using the same steps as Binance, with no Ouinex-specific detour.
- **SC-002**: 100% of Ouinex trades written to the trading journal are recorded under the "binance" provider identity (0% appear under a separate "ouinex" identity).
- **SC-003**: Every capability available for Binance instruments (search, watchlist, indicators, alerts, reporting) is available for Ouinex instruments — feature parity is complete with no capability gaps.
- **SC-004**: All existing Binance workflows continue to function unchanged after Ouinex is introduced (no regressions).
- **SC-005**: An Ouinex failure (bad credentials, provider outage) never prevents a Binance or Saxo action from succeeding.

## Assumptions

- **"Map as binance" scope**: The mapping to Binance applies to the provider/account identity written to the Google Sheet trading journal — Ouinex entries use the exact same "binance" identity (see Clarifications). Market data, search, and analytics operate against the real Ouinex source; only the journal provider label is "binance".
- **Credential model**: Ouinex authenticates with a provider-issued API key/secret pair, supplied via the same secure configuration mechanism used for Binance credentials (separate keys). Per Clarifications, these credentials are required for every Ouinex call, including search and candles.
- **Capability parity baseline**: "Same behavior as Binance" means matching the current Binance feature set — instrument search, watchlist add/classification, candle retrieval for indicators, alert evaluation, and trade reporting into the journal.
- **Timeframe parity**: Ouinex supports (or can be made to support via reconstruction) the same set of timeframes currently used for Binance, including reconstruction of the in-progress current day/hour candle.
- **API capabilities**: The Ouinex API (https://api.ouinex.com/) exposes equivalent endpoints for instrument search, historical market data (candles), and trade/order history sufficient to achieve Binance parity. Exact endpoint details are an implementation concern to be validated during planning.

## Dependencies

- **Ouinex API** (https://api.ouinex.com/): external provider API for instrument search, market data, and trade history.
- **Ouinex account and credentials**: an active Ouinex account with API key/secret provisioned.
- **Existing Google Sheet trading journal**: the destination for reported trades, where Ouinex entries are recorded under the "binance" provider identity.
