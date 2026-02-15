# Feature Specification: Workflow Automation System Documentation

**Feature Branch**: `008-workflow-system-doc`
**Created**: 2026-02-08
**Status**: Draft
**Type**: Documentation (Existing System)
**Input**: User description: "document the existing workflow automation system for automated trading. This spec should track: 1) workflow execution engine 2) supported indicator types (ma50, combo, bollinger bands, polarite, zone) 3) condition evaluation 4) trigger mechanisms 5) configuration system (YAML) 6) lambda scheduling 7) API endpoints for viewing workflows. This is NOT a feature request but documentation of the existing system"

## Overview

This specification documents the **existing** workflow automation system used for automated trading operations. The system monitors technical indicators (moving averages, Bollinger Bands, combo signals, support/resistance zones, polarity levels) on market indices and CFDs, evaluates pre-defined conditions, and automatically triggers trading orders when conditions are met. The system runs on AWS Lambda on a scheduled basis, loads workflow configurations from S3 or local YAML files, and sends notifications to Slack channels.

**Purpose**: This is a **documentation specification** for the existing workflow system, not a new feature. It serves as the authoritative reference for understanding how workflows are configured, executed, and monitored.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure Automated Trading Strategy (Priority: P1)

A trader wants to automate a trading strategy based on technical indicators. They define a workflow that buys DAX CFD when the price touches the lower Bollinger Band (BBB) on the 1-hour chart with a 20-point spread.

**Why this priority**: Core functionality - without workflow configuration, the entire system has no purpose.

**Independent Test**: Can be fully tested by creating a workflow YAML file, loading it, and verifying the workflow appears in the system with correct parameters.

**Acceptance Scenarios**:

1. **Given** a YAML workflow file with indicator, condition, and trigger configurations, **When** the system loads workflows from S3 or disk, **Then** the workflow is parsed into domain objects with all parameters correctly mapped
2. **Given** a workflow configured with "bbb h1 above close with 20 spread", **When** the workflow is displayed via API or CLI, **Then** all configuration details are accurately shown
3. **Given** multiple workflows for the same asset, **When** requesting workflows for that asset, **Then** all matching workflows are returned with their enabled/disabled status

---

### User Story 2 - Monitor Real-Time Condition Evaluation (Priority: P1)

A trader needs the system to continuously evaluate whether their configured conditions are met. When the DAX price moves within 20 points of the 1-hour Bollinger Band bottom, the system should detect this and prepare to trigger the order.

**Why this priority**: Critical for automation - condition evaluation is what transforms static configuration into dynamic trading decisions.

**Independent Test**: Can be tested by creating a workflow, simulating market data that meets the condition, and verifying the condition evaluator returns true.

**Acceptance Scenarios**:

1. **Given** a workflow with "below" condition and 50-point spread, **When** the close price is within the indicator value minus spread range, **Then** the condition evaluates to true
2. **Given** a workflow with "above" condition, **When** the close price is outside the indicator value plus spread range, **Then** the condition evaluates to false
3. **Given** a combo indicator workflow, **When** the combo signal direction matches the workflow direction, **Then** the condition evaluates to true regardless of spread
4. **Given** a zone indicator with value range 73-78, **When** the close price is 75, **Then** the zone condition evaluates to true
5. **Given** a polarite indicator at 61.5, **When** the candle high touches 61.5 but close is below, **Then** the polarite condition evaluates to true

---

### User Story 3 - Execute Order When Triggered (Priority: P1)

When conditions are met, the system must generate the appropriate order (buy/sell, limit/stop) with the configured quantity at the calculated price point, and notify traders via Slack.

**Why this priority**: The end goal of the system - without order execution, condition evaluation is meaningless.

**Independent Test**: Can be tested by mocking a condition match and verifying the system generates an Order object with correct parameters and posts to Slack.

**Acceptance Scenarios**:

1. **Given** a "below" condition triggers with "lower breakout" at trigger candle low 21000, **When** the workflow executes, **Then** a SELL stop order is created at 20999 (low minus 1)
2. **Given** an "above" condition triggers with "higher breakout" at trigger candle high 22000, **When** the workflow executes, **Then** a BUY stop order is created at 22001 (high plus 1)
3. **Given** a workflow with dry_run=true triggers, **When** the order is generated, **Then** Slack notification is sent but no actual order is placed
4. **Given** a workflow with dry_run=false triggers for a stock asset, **When** the order is generated, **Then** Slack notification is posted to #workflows-stock channel
5. **Given** multiple workflows trigger simultaneously, **When** processing results, **Then** each workflow generates exactly one order with correct asset metadata

---

### User Story 4 - Schedule and Run via Lambda (Priority: P2)

The trading system must run workflows automatically on a schedule (e.g., hourly during market hours) without manual intervention. Lambda receives an event, loads workflow configuration from S3, executes all enabled workflows, and handles errors gracefully.

**Why this priority**: Enables fully automated trading - traders don't need to manually trigger workflow execution.

**Independent Test**: Can be tested by invoking the Lambda handler with `{"command": "workflows"}` and verifying workflows are loaded, executed, and results are logged.

**Acceptance Scenarios**:

1. **Given** Lambda receives event with `command: "workflows"`, **When** handler processes the event, **Then** workflows are loaded from S3 and executed
2. **Given** a workflow with `end_date` in the past, **When** the engine runs, **Then** that workflow is skipped and logged as "will not run"
3. **Given** a workflow with `enable: false`, **When** the engine runs, **Then** that workflow is skipped
4. **Given** a workflow execution fails with SaxoException, **When** the error occurs, **Then** error is logged and Slack notification is sent to #errors channel
5. **Given** Lambda completes successfully, **When** the handler returns, **Then** result is `{"result": "ok"}`

---

### User Story 5 - Query Workflows via API (Priority: P2)

Traders and the frontend need to query which workflows exist for a specific asset. When viewing the asset detail page for DAX, the system should display all configured workflows (MA50, BBB, combo, etc.) with their status and parameters.

**Why this priority**: Provides visibility into automation - traders need to see what strategies are active on their assets.

**Independent Test**: Can be tested by calling the API endpoint `/api/workflow/asset?code=DAX.I` and verifying it returns all workflows matching that index.

**Acceptance Scenarios**:

1. **Given** workflows exist for DAX.I index, **When** API receives request for code="DAX.I", **Then** all workflows with `index: DAX.I` or `index: GER40.I` are returned
2. **Given** no workflows exist for an asset, **When** API receives request for that asset, **Then** empty list is returned with total=0
3. **Given** workflows with various indicator types (ma50, bbb, combo), **When** API returns workflow list, **Then** each workflow includes indicator name, unit time, value, and zone_value
4. **Given** a workflow with trigger configuration, **When** API returns workflow info, **Then** trigger includes unit_time, signal, location, order_direction, and quantity
5. **Given** force_from_disk=true parameter, **When** API loads workflows, **Then** workflows are loaded from local workflows.yml instead of S3

---

### User Story 6 - List Workflows for Asset via CLI (Priority: P3)

Technical users and traders need to query workflows directly from the command line for debugging, verification, or quick checks without accessing the web interface.

**Why this priority**: Useful for troubleshooting and manual verification, but less critical than API/automation functionality.

**Independent Test**: Can be tested by running `k-order workflow asset --code DAX.I --country-code ""` and verifying terminal output shows all matching workflows with formatted details.

**Acceptance Scenarios**:

1. **Given** workflows exist for an asset, **When** running CLI with asset code, **Then** terminal displays workflow name, status, conditions, and trigger in human-readable format
2. **Given** a workflow with end_date set, **When** displaying via CLI, **Then** end date is shown in YYYY-MM-DD format
3. **Given** no workflows match the asset, **When** running CLI query, **Then** message "No workflows found for asset: [symbol]" is displayed
4. **Given** force-from-disk option is "y", **When** CLI loads workflows, **Then** workflows are loaded from local workflows.yml file

---

### Edge Cases

- What happens when a workflow references an asset that doesn't exist in Saxo API? (System logs SaxoException and skips workflow)
- How does the system handle workflows with missing trigger configuration? (Defaults to H1 breakout with 0.1 quantity based on condition direction)
- What happens when Lambda can't reach S3 to load workflows? (Falls back to local workflows.yml if available, otherwise raises SaxoException)
- How are US market hours handled differently from EU markets? (Workflows with `is_us: true` use USMarket open/close hours; others use EUMarket hours)
- What happens when multiple workflows trigger for the same asset simultaneously? (All orders are generated and notified independently - no deduplication)
- How does the system handle indicator calculations when insufficient candle data is available? (Returns empty candle list, workflow execution is skipped with error log)

## Requirements *(mandatory)*

### Functional Requirements

#### Workflow Engine

- **FR-001**: System MUST load workflow configurations from S3 when running in AWS Lambda context
- **FR-002**: System MUST load workflow configurations from local workflows.yml file when `force_from_disk=true` or when not in AWS context
- **FR-003**: System MUST parse YAML workflow files into domain objects (Workflow, Condition, Indicator, Close, Trigger)
- **FR-004**: System MUST filter workflows by `enable` flag and `end_date` before execution
- **FR-005**: System MUST execute workflows sequentially, processing each enabled workflow with valid end_date
- **FR-006**: System MUST retrieve candles for the configured indicator unit time and type
- **FR-007**: System MUST instantiate the appropriate workflow evaluator (MA50Workflow, BBWorkflow, ComboWorkflow, PolariteWorkflow, ZoneWorkflow) based on indicator type
- **FR-008**: System MUST evaluate condition by comparing close candle against indicator value with spread
- **FR-009**: System MUST generate Order object with correct type (LIMIT or OPEN_STOP), direction (BUY or SELL), price (trigger candle high/low +/- 1), and quantity when condition is met
- **FR-010**: System MUST post order notification to Slack channel (#workflows for indices, #workflows-stock for stocks)

#### Indicator Types

- **FR-011**: System MUST support MA50 (50-period moving average) indicator on hourly, 4-hour, and weekly time frames
- **FR-012**: System MUST support BBB (Bollinger Bands Bottom) and BBH (Bollinger Bands High) indicators with 2.5 standard deviation and 20-period calculation
- **FR-013**: System MUST support Combo indicator (proprietary signal combining multiple technical factors) with strength classification (STRONG, WEAK, MEDIUM)
- **FR-014**: System MUST support Polarite (polarity/resistance level) indicator with single price value
- **FR-015**: System MUST support Zone (support/resistance zone) indicator with value and zone_value defining the range
- **FR-016**: System MUST calculate MA50 as simple moving average of last 50 candle closes
- **FR-017**: System MUST calculate Bollinger Bands with middle (20-period SMA), upper (middle + 2.5*stddev), and lower (middle - 2.5*stddev) bands
- **FR-018**: System MUST retrieve sufficient historical candles for indicator calculation (55 for MA50, 750 for Combo, 21 for Bollinger Bands, 1 for Polarite/Zone)

#### Condition Evaluation

- **FR-019**: System MUST support "below" direction conditions that check if close/high is within indicator value minus spread range
- **FR-020**: System MUST support "above" direction conditions that check if close/low is within indicator value plus spread range
- **FR-021**: System MUST evaluate element-specific conditions (CLOSE, HIGH, LOW) when element is specified in workflow configuration
- **FR-022**: System MUST evaluate combo conditions by matching signal direction (BUY or SELL) regardless of spread
- **FR-023**: System MUST evaluate zone conditions by checking if close/high/low is within the zone value range
- **FR-024**: System MUST evaluate polarite conditions with special logic: above if (candle.low <= value AND candle.close >= value) OR (candle.low >= value AND candle.low <= value+spread); below if (candle.higher >= value AND candle.close <= value) OR (candle.higher <= value AND candle.higher >= value-spread)

#### Trigger Mechanisms

- **FR-025**: System MUST support "breakout" signal type (currently the only supported signal)
- **FR-026**: System MUST support "higher" location (triggers above indicator) and "lower" location (triggers below indicator)
- **FR-027**: System MUST generate OPEN_STOP order type when order direction matches breakout direction (BUY higher or SELL lower)
- **FR-028**: System MUST generate LIMIT order type when order direction opposes breakout direction (BUY lower or SELL higher)
- **FR-029**: System MUST calculate order price as trigger candle lower minus 1 for "lower breakout" triggers
- **FR-030**: System MUST calculate order price as trigger candle higher plus 1 for "higher breakout" triggers
- **FR-031**: System MUST use configured quantity from trigger section (or default 0.1 if trigger section is missing)
- **FR-032**: System MUST use H1 (1-hour) unit time for trigger candle retrieval unless otherwise specified in trigger configuration

#### Configuration System

- **FR-033**: System MUST accept YAML workflow files with top-level list of workflow objects
- **FR-034**: Each workflow MUST include: name, index, cfd, enable (boolean), conditions (list), and optionally: end_date, dry_run, is_us, trigger
- **FR-035**: Each condition MUST include: indicator (with name, ut, optional value, optional zone_value), close (with direction, ut, spread), and optionally: element
- **FR-036**: System MUST default missing trigger configuration to: ut=H1, signal=breakout, location based on close direction, order_direction based on close direction, quantity=0.1
- **FR-037**: System MUST parse end_date in YYYY/MM/DD format and convert to date object
- **FR-038**: System MUST validate indicator name against supported types (ma50, combo, bbb, bbh, polarite, zone)
- **FR-039**: System MUST validate unit time against supported values (daily, h1, h4, 15m, weekly, monthly)
- **FR-040**: System MUST validate direction against supported values (above, below)
- **FR-041**: System MUST validate signal against supported values (breakout)
- **FR-042**: System MUST validate location against supported values (higher, lower)
- **FR-043**: System MUST validate order_direction against supported values (buy, sell)
- **FR-044**: System MUST validate element against supported values (close, high, low)

#### Lambda Scheduling

- **FR-045**: Lambda handler MUST accept event with `command` field specifying operation ("workflows", "alerting", "snapshot", "refresh_token")
- **FR-046**: Lambda handler MUST load configuration from environment variable SAXO_CONFIG when command is "workflows"
- **FR-047**: Lambda handler MUST execute workflow engine with workflows loaded from S3 by default
- **FR-048**: Lambda handler MUST catch all exceptions during workflow execution and post error to Slack #errors channel
- **FR-049**: Lambda handler MUST return `{"result": "ok"}` on success or `{"result": "ko", "message": "error details"}` on failure
- **FR-050**: Lambda handler MUST instantiate WorkflowEngine with workflows list, Slack client, candles service, and Saxo client

#### API Endpoints

- **FR-051**: System MUST provide GET endpoint at `/api/workflow/asset` accepting query parameters: code (required), country_code (optional, default "xpar"), force_from_disk (optional, default false)
- **FR-052**: API MUST return AssetWorkflowsResponse containing: asset_symbol (formatted as "code:country_code"), total (count of matching workflows), workflows (list of WorkflowInfo objects)
- **FR-053**: API MUST filter workflows by matching `workflow.index` against code or formatted symbol (case-insensitive)
- **FR-054**: API MUST transform domain Workflow objects into WorkflowInfo API models with all fields serialized to strings/primitives
- **FR-055**: WorkflowInfo MUST include: name, index, cfd, enabled, dry_run, end_date (formatted as YYYY-MM-DD or null), is_us, conditions (list), trigger
- **FR-056**: WorkflowConditionInfo MUST include: indicator (WorkflowIndicatorInfo), close (WorkflowCloseInfo), element (string or null)
- **FR-057**: WorkflowIndicatorInfo MUST include: name (string), unit_time (string), value (float or null), zone_value (float or null)
- **FR-058**: WorkflowCloseInfo MUST include: direction (string), unit_time (string), spread (float)
- **FR-059**: WorkflowTriggerInfo MUST include: unit_time (string), signal (string), location (string), order_direction (string), quantity (float)
- **FR-060**: API MUST return HTTP 400 with error detail when SaxoException occurs during workflow loading
- **FR-061**: API MUST return HTTP 500 with "Internal server error" message when unexpected exceptions occur

#### CLI Commands

- **FR-062**: CLI MUST provide `workflow asset` command accepting: --code (required), --country-code (optional, default "xpar"), --force-from-disk (required, default "n")
- **FR-063**: CLI MUST display formatted output with workflow name, status (✓ ENABLED or ✗ DISABLED), dry run indicator, index, cfd, end_date (if present), conditions, and trigger
- **FR-064**: CLI MUST format conditions as: "{indicator_name} {indicator_ut} {close_direction} close {close_ut} ({element})" with optional element
- **FR-065**: CLI MUST format trigger as: "{signal} {location} -> {order_direction} (qty: {quantity})"
- **FR-066**: CLI MUST display "No workflows found for asset: {symbol}" when no matches exist
- **FR-067**: CLI MUST display total count of workflows found at the end of output
- **FR-068**: CLI MUST provide `workflow run` command accepting: --force-from-disk, --select-workflow (interactive selection)
- **FR-069**: CLI `workflow run` MUST execute WorkflowEngine with all enabled workflows or selected workflow only

### Key Entities

- **Workflow**: Represents a complete trading strategy with name, target index/CFD, enabled status, optional end date, dry run flag, US market flag, list of conditions, and trigger configuration
- **Condition**: Defines when a workflow should trigger, containing an indicator to monitor, close parameters for evaluation, and optional element specification
- **Indicator**: Technical analysis indicator with type (MA50, Combo, BBB, BBH, Polarite, Zone), unit time (H1, H4, Daily, Weekly), optional fixed value (for Polarite/Zone), and optional zone range value
- **Close**: Evaluation parameters specifying direction (above/below indicator), unit time for close candle retrieval, and spread tolerance in points
- **Trigger**: Order generation parameters including unit time for trigger candle, signal type (breakout), location (higher/lower), order direction (buy/sell), and order quantity
- **Order**: Trading order object containing asset code, price, quantity, direction (BUY/SELL), and type (LIMIT/OPEN_STOP)
- **Candle**: OHLC (Open-High-Low-Close) price data with lower, higher, open, close prices, unit time, and datetime
- **ComboSignal**: Proprietary signal containing price level, trigger status, direction (BUY/SELL), strength (STRONG/WEAK/MEDIUM), and calculation details
- **BollingerBands**: Statistical bands containing bottom, upper, middle values, unit time, and datetime

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: System successfully loads and parses 100% of valid YAML workflow files without errors
- **SC-002**: Workflow execution completes for all enabled workflows within Lambda 15-minute timeout limit
- **SC-003**: Condition evaluation produces deterministic results - same market data always evaluates to same true/false result
- **SC-004**: Order generation produces correct order parameters (type, direction, price, quantity) matching workflow configuration in 100% of trigger events
- **SC-005**: API endpoint responds within 2 seconds for asset workflow queries
- **SC-006**: Slack notifications are sent within 5 seconds of order generation
- **SC-007**: System handles workflow configuration errors gracefully, logging errors without crashing Lambda execution
- **SC-008**: CLI commands display human-readable workflow information matching API data accuracy
- **SC-009**: Historical workflow execution data is traceable through Slack channel messages
- **SC-010**: Zero false positives - workflows only trigger when conditions are genuinely met per configuration

### System Quality

- **SC-011**: Workflow engine isolates failures - one workflow error does not prevent other workflows from executing
- **SC-012**: Configuration changes in workflows.yml are reflected in next execution without system restart
- **SC-013**: Dry run mode workflows generate notifications without executing actual trades
- **SC-014**: Multi-workflow assets (e.g., DAX with MA50, BBB, Combo workflows) execute all independent workflows correctly

## Assumptions

1. **Market Data Availability**: Saxo API consistently provides sufficient historical candle data for indicator calculations
2. **Slack Integration**: Slack workspace and channels (#workflows, #workflows-stock, #errors) are pre-configured and accessible
3. **AWS Environment**: Lambda has appropriate IAM permissions to read from S3, has SAXO_CONFIG environment variable set, and has network access to Saxo API and Slack API
4. **YAML Configuration Management**: workflows.yml file is maintained externally and uploaded to S3; system does not provide workflow editing interface
5. **Single Market Session**: Workflows assume standard market hours; overnight gap handling is not explicitly documented
6. **CFD vs Index**: Workflows use CFD code for order execution but index code for indicator calculation (to support trading during after-hours)
7. **No Position Management**: System generates orders but does not track open positions, profit/loss, or portfolio risk
8. **Manual Order Review**: Generated orders require human approval or separate order placement system (dry run suggests orders are not automatically executed by this system)

## Scope

### In Scope

- Workflow configuration loading from S3 or local YAML
- Parsing YAML into domain objects with validation
- Technical indicator calculation (MA50, Bollinger Bands, Combo, Polarite, Zone)
- Condition evaluation logic for all supported indicator types
- Trigger mechanism and order parameter calculation
- Slack notification of generated orders
- Lambda-based scheduled execution
- API endpoint for querying workflows by asset
- CLI commands for workflow management and inspection
- Error handling and logging

### Out of Scope

- **Order Execution**: System generates order parameters but does not place actual trades (requires separate order management system)
- **Position Tracking**: No tracking of open positions, unrealized P&L, or portfolio composition
- **Risk Management**: No position sizing, stop-loss calculation, or risk exposure limits
- **Backtesting**: No historical simulation or performance analysis of workflow strategies
- **Workflow Editing UI**: No web interface for creating/modifying workflows (must edit YAML directly)
- **Real-Time Monitoring Dashboard**: No live view of workflow execution status or pending conditions
- **Alert System Integration**: Workflows operate independently from the alerting system documented elsewhere
- **Portfolio Optimization**: No multi-asset allocation or correlation-based strategy adjustment

## Dependencies

- **External Services**: Saxo Bank API for market data and asset information, Slack API for notifications, AWS S3 for configuration storage
- **Internal Services**: CandlesService for historical OHLC data retrieval, IndicatorService for technical indicator calculations, SaxoClient for API communication
- **Configuration**: SAXO_CONFIG environment variable or file path, Slack token, AWS credentials with S3 read permissions
- **Data Requirements**: Sufficient historical candles for longest lookback period (750 candles for Combo indicator on H4 = ~3000 hours of market data)
- **Market Hours Definition**: EUMarket and USMarket objects defining open/close hours and days for candle boundary calculation

## Risks & Constraints

### Technical Risks

1. **Market Data Gaps**: Missing or delayed candle data from Saxo API could cause indicator calculation failures
2. **Lambda Timeout**: Complex multi-workflow execution approaching 15-minute limit could cause incomplete processing
3. **S3 Availability**: If S3 is unavailable and local workflows.yml is missing, system cannot load configuration
4. **Slack Rate Limits**: Multiple simultaneous workflow triggers could exceed Slack API rate limits

### Operational Constraints

1. **Manual Configuration**: Workflows must be manually created and tested in YAML; no validation tool prevents syntax errors
2. **No Rollback**: Invalid workflow configurations are only detected at runtime; no pre-deployment validation
3. **Single Execution Model**: Workflows run sequentially; long-running indicator calculations block subsequent workflows
4. **No State Persistence**: Each Lambda invocation loads fresh configuration; no memory of previous executions

### Business Constraints

1. **Broker Dependency**: System is tightly coupled to Saxo Bank API structure and data format
2. **Limited Indicator Library**: Only 5 indicator types supported; adding new indicators requires code changes
3. **No User Management**: Single-user system; all workflows execute with same credentials and risk profile

## Future Enhancements (Out of Scope for This Documentation)

- Workflow execution history and performance analytics
- Web-based workflow builder with visual condition editor
- Real-time condition monitoring dashboard
- Automatic order execution integration with broker API
- Position management and risk limits
- Multi-user workflows with per-user strategies
- Workflow backtesting with historical data
- Additional indicator types (RSI, MACD, Ichimoku, etc.)
- Machine learning-based signal optimization

---

**Note**: This specification documents the **existing** workflow automation system. Implementation details such as specific function names, file paths, and internal architecture are intentionally omitted to maintain focus on business capabilities and user value.
