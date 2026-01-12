# Feature Specification: Binance Asset Indicators

**Feature Branch**: `473-binance-asset-indicators` (merged)
**Created**: 2026-01-09 (retroactive documentation)
**Status**: Implemented
**Input**: Reverse-engineered from commits ef5d36f, cb4689d, 7210054, 6434728 and plan file

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Unified Asset Detail View (Priority: P1)

As a trader using both Saxo and Binance, I want to view technical indicators (MA7, MA20, MA50, MA200) for Binance crypto assets in the same asset detail interface as Saxo stocks so I can analyze all my assets consistently.

**Why this priority**: Unified interface reduces cognitive overhead and enables consistent technical analysis across asset classes.

**Independent Test**: Navigate to Binance asset detail page, verify moving averages display correctly.

**Acceptance Scenarios**:

1. **Given** Binance asset symbol (e.g., BTCUSDT), **When** I view asset details, **Then** I see MA7, MA20, MA50, MA200 calculated from historical data
2. **Given** Binance asset, **When** indicators load, **Then** current price and 24-hour variation percentage display
3. **Given** both Saxo and Binance assets, **When** I view details for each, **Then** indicator layout and calculations are consistent

---

### User Story 2 - Real-Time Price Display (Priority: P2)

As a crypto trader, I want to see the current Binance asset price updated from the latest 1-minute candle so I have accurate real-time pricing for decision-making.

**Why this priority**: Crypto markets operate 24/7, real-time pricing is essential for timely trades.

**Independent Test**: Load Binance asset detail, verify current price matches latest Binance 1m candle close.

**Acceptance Scenarios**:

1. **Given** Binance asset, **When** I load asset details, **Then** current price reflects latest 1-minute candle close
2. **Given** price changes, **When** I reload page, **Then** updated price displays
3. **Given** variation calculation, **When** current price vs previous close, **Then** percentage change is accurate

---

### User Story 3 - Historical Candle Data Access (Priority: P3)

As a developer, I want BinanceClient to provide candle data in the same format as SaxoClient so indicator calculations work uniformly across exchanges without code duplication.

**Why this priority**: Code reuse and maintainability - indicator functions should be exchange-agnostic.

**Independent Test**: Call `binance_client.get_candles()`, verify returns list of Candle objects sorted newest first.

**Acceptance Scenarios**:

1. **Given** symbol and unit_time, **When** I call `get_candles()`, **Then** I receive List[Candle] sorted newest first
2. **Given** different unit times (D, W, M, H1, H4, M15), **When** I fetch candles, **Then** each returns appropriate Binance interval data
3. **Given** candle objects, **When** I pass to indicator functions, **Then** calculations work identically to Saxo candles

---

### Edge Cases

- What happens when Binance API is unavailable? (Log error, return appropriate HTTP status)
- What happens when invalid symbol requested? (Return 400 with "Asset not found" message)
- What happens when insufficient candles for MA200? (Calculate with available data, mark as incomplete)
- What happens with Binance rate limits? (Handle gracefully with exponential backoff)
- What happens when country_code provided for Binance asset? (Ignore parameter, use symbol only)
- What happens with Saxo asset without country_code? (Allow None, use identifier-based lookup)
- What happens when exchange parameter missing? (Default to SAXO for backwards compatibility)

## Requirements *(mandatory)*

### Functional Requirements

**BinanceClient Extension (Phase 1):**
- **FR-001**: System MUST provide `get_candles(symbol, unit_time, limit)` returning List[Candle]
- **FR-002**: System MUST provide `get_latest_candle(symbol)` returning most recent 1m Candle
- **FR-003**: System MUST map UnitTime enum to Binance intervals (D→"1d", W→"1w", M→"1M", H1→"1h", H4→"4h", M15→"15m")
- **FR-004**: System MUST convert Binance kline arrays to Candle objects with 4-decimal price rounding
- **FR-005**: System MUST return candles sorted newest first (index 0 = latest)
- **FR-006**: System MUST encapsulate all Binance API calls within BinanceClient (no external API access)
- **FR-007**: System MUST never expose raw Binance objects outside BinanceClient (only Candle objects)

**Indicator Service Extension (Phase 2):**
- **FR-008**: System MUST accept exchange parameter in `get_asset_indicators()` (SAXO or BINANCE)
- **FR-009**: System MUST route to BinanceClient when exchange=BINANCE
- **FR-010**: System MUST route to SaxoClient when exchange=SAXO
- **FR-011**: System MUST fetch 210 daily candles for Binance assets (safety margin for MA200)
- **FR-012**: System MUST calculate MA7, MA20, MA50, MA200 using exchange-agnostic functions
- **FR-013**: System MUST calculate variation from current price vs previous period close
- **FR-014**: System MUST return USD currency for Binance assets (most pairs USDT-quoted)

**API Router Extension (Phase 3):**
- **FR-015**: System MUST accept exchange query parameter in `/api/indicator/asset/{code}`
- **FR-016**: System MUST default exchange parameter to "saxo" (backwards compatibility)
- **FR-017**: System MUST make country_code optional for all assets
- **FR-018**: System MUST validate exchange parameter (only "saxo" or "binance" allowed)
- **FR-019**: System MUST inject BinanceClient dependency to IndicatorService
- **FR-020**: System MUST handle 24/7 trading for Binance (no market hours logic)

### Key Entities

- **BinanceClient Extension** (`client/binance_client.py`):
  - `get_candles(symbol, unit_time, limit)`: Fetch historical candles
  - `get_latest_candle(symbol)`: Get current 1m candle for price
  - `_unit_time_to_binance_interval(unit_time)`: Map enum to Binance interval string
  - `_get_klines(symbol, interval, limit)`: Fetch raw kline data from Binance API
  - `_map_kline_to_candle(kline, unit_time)`: Convert Binance kline array to Candle object

- **IndicatorService Exchange Routing** (`api/services/indicator_service.py`):
  - `get_asset_indicators(code, country_code, unit_time, exchange)`: Main entry point with routing
  - `_get_binance_asset_indicators(symbol, unit_time)`: Binance-specific indicator logic
  - `_get_saxo_asset_indicators(code, country_code, unit_time)`: Saxo-specific indicator logic (refactored)

- **Candle Model** (existing, no changes):
  - `open`, `close`, `higher`, `lower`: float (4-decimal precision)
  - `date`: datetime (from Binance timestamp milliseconds)
  - `ut`: UnitTime enum

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: BinanceClient never makes API calls outside its class (100% encapsulation)
- **SC-002**: BinanceClient never returns raw Binance objects (100% Candle conversion)
- **SC-003**: Indicator calculations work identically for Saxo and Binance (shared functions)
- **SC-004**: Candles always sorted newest first (index 0 = latest)
- **SC-005**: Test coverage 100% for BinanceClient candle methods (12 tests pass)
- **SC-006**: Test coverage 100% for indicator router with Binance (4 new tests pass)
- **SC-007**: All 27 tests pass (12 BinanceClient + 11 existing + 4 new)
- **SC-008**: API response time <2 seconds for indicator endpoint
- **SC-009**: Backwards compatibility maintained (existing Saxo calls work unchanged)
- **SC-010**: Price accuracy matches Binance API (4-decimal rounding)

## Technical Constraints

- **TC-001**: No Binance API calls outside BinanceClient (strict encapsulation)
- **TC-002**: Always return Candle or List[Candle] (never raw Binance data structures)
- **TC-003**: Methods must support indicator needs (MA7, MA20, MA50, MA200)
- **TC-004**: Candles newest first (index 0 = latest) for consistency
- **TC-005**: Max 1000 candles per Binance request (API limit)
- **TC-006**: Fetch 210 candles minimum for MA200 calculation (safety margin)
- **TC-007**: Exchange parameter explicit (cannot rely on symbol format detection)
- **TC-008**: Backwards compatible API (defaults to SAXO, country_code optional)

## Non-Functional Requirements

- **NFR-001**: Binance API response time <1.5 seconds for candle fetching
- **NFR-002**: Indicator calculations complete <500ms (after candle fetch)
- **NFR-003**: Error messages user-friendly (not technical Binance API errors)
- **NFR-004**: Logging at INFO level for API calls, ERROR for failures
- **NFR-005**: Handle Binance rate limits gracefully (no cascading failures)
- **NFR-006**: 24/7 availability (Binance crypto markets never close)

## Symbol Format Differences

| Aspect | Saxo | Binance |
|--------|------|---------|
| Symbol format | "CODE:MARKET" or "CODE" | "BASEQUOTE" (e.g., "BTCUSDT") |
| Identifier | UIC integer required | None |
| Interval format | Horizon in minutes (1440) | String intervals ("1d", "1h") |
| Max candles | 1200 per request | 1000 per request |
| Market hours | Varies by exchange (9:30-16:00 EST for US) | 24/7 for crypto |
| Authentication | OAuth with token refresh | API key/secret (not needed for public klines) |
| Country code | Required for most assets | Not applicable |
| Currency | Varies (EUR, USD, etc.) | Mostly USDT (USD equivalent) |
