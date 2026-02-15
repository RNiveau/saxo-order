# Feature Specification: Workflow Management UI & Database Migration

**Feature Branch**: `009-workflow-db-ui`
**Created**: 2026-02-08
**Status**: Draft
**Input**: User description: "create a workflow management UI page that displays all workflows in a table with their status, indicators, and conditions. Migrate workflow storage from workflows.yml file to a DynamoDB table. Users should be able to view all workflows (not just by asset), see their enabled/disabled status, dry run mode, and full configuration details. The database should store all workflow properties: name, index, cfd, enable flag, dry_run flag, is_us flag, end_date, conditions (indicator type, unit time, values, close direction, spread), and trigger (signal, location, order direction, quantity). The Lambda function should load workflows from DynamoDB instead of S3/YAML. The API should have endpoints to list all workflows and get workflow details by ID. Workflow creation/editing UI is out of scope for now."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View All Active Workflows (Priority: P1)

A trader opens the workflow management page to see all configured trading strategies across all assets. They see a comprehensive table showing workflow names, target indices, enabled/disabled status, dry run mode, and indicator types at a glance.

**Why this priority**: Core functionality - provides essential visibility into the automation system. Without this view, traders have no way to understand what strategies are currently active.

**Independent Test**: Can be fully tested by navigating to the workflows page and verifying all workflows are displayed with correct status indicators and delivers immediate visibility into trading automation.

**Acceptance Scenarios**:

1. **Given** 50 workflows exist in the database, **When** the trader opens the workflows page, **Then** all 50 workflows are displayed in a paginated table
2. **Given** workflows have different enabled states, **When** viewing the table, **Then** enabled workflows show a green ✓ icon and disabled workflows show a red ✗ icon
3. **Given** workflows have dry run mode enabled, **When** viewing the table, **Then** those workflows display a "DRY RUN" badge
4. **Given** workflows target different indices (DAX, CAC40, S&P500), **When** viewing the table, **Then** the index column shows the correct asset symbol
5. **Given** workflows use different indicators (MA50, BBB, Combo), **When** viewing the table, **Then** the indicator type is clearly displayed

---

### User Story 2 - Filter and Sort Workflows (Priority: P1)

A trader wants to quickly find specific workflows. They can filter by enabled status, index, indicator type, or dry run mode, and sort by name, index, or last modified date to locate the workflows they need.

**Why this priority**: Essential for usability - with dozens of workflows, filtering/sorting is necessary for efficient management.

**Independent Test**: Can be tested by applying filters and verifying the table updates to show only matching workflows.

**Acceptance Scenarios**:

1. **Given** 30 workflows with 10 enabled and 20 disabled, **When** the trader filters by "Enabled only", **Then** only 10 workflows are displayed
2. **Given** workflows for DAX, CAC40, and S&P500, **When** the trader filters by index="DAX.I", **Then** only DAX workflows are shown
3. **Given** workflows with various indicators, **When** the trader filters by indicator="ma50", **Then** only MA50 workflows are displayed
4. **Given** unsorted workflows, **When** the trader clicks the "Name" column header, **Then** workflows are sorted alphabetically by name
5. **Given** workflows have different end dates, **When** the trader sorts by end date, **Then** workflows are ordered with nearest end dates first

---

### User Story 3 - View Workflow Details (Priority: P1)

A trader clicks on a workflow row to see complete configuration details including all conditions (indicator values, spreads, close directions), trigger parameters (signal type, location, quantity), and market settings (US vs EU).

**Why this priority**: Critical for understanding - traders need to verify exact strategy parameters before making trading decisions.

**Independent Test**: Can be tested by clicking a workflow and verifying a detail panel shows all configuration fields matching the database values.

**Acceptance Scenarios**:

1. **Given** a workflow with specific indicator configuration, **When** the trader clicks the workflow row, **Then** a detail panel opens showing indicator name, unit time, value, and zone value
2. **Given** a workflow with condition spread of 40 points, **When** viewing workflow details, **Then** the spread value "40" is displayed in the close configuration
3. **Given** a workflow with trigger quantity of 0.1, **When** viewing workflow details, **Then** the trigger section shows quantity "0.1" and order direction
4. **Given** a workflow with end date 2026-12-31, **When** viewing workflow details, **Then** the end date is formatted and displayed
5. **Given** a US market workflow (is_us=true), **When** viewing workflow details, **Then** a "US Market" indicator is shown

---

### User Story 4 - Migrate Workflows from YAML to Database (Priority: P1)

The system administrator runs a one-time migration script that reads all workflows from workflows.yml and inserts them into the database table with unique IDs. After migration, the Lambda function loads workflows from the database instead of S3/YAML.

**Why this priority**: Foundation requirement - all other features depend on workflows being in the database.

**Independent Test**: Can be tested by running the migration script with a sample workflows.yml file and verifying all workflows are created in the database with correct field mappings.

**Acceptance Scenarios**:

1. **Given** a workflows.yml file with 50 workflows, **When** the migration script runs, **Then** 50 workflow records are created in the database
2. **Given** a workflow with nested condition structure, **When** migrated, **Then** the condition is stored as structured data preserving indicator, close, and element fields
3. **Given** a workflow with missing trigger configuration, **When** migrated, **Then** the default trigger values are applied (H1, breakout, direction-based location/order)
4. **Given** workflows with end dates in YYYY/MM/DD format, **When** migrated, **Then** end dates are converted to ISO 8601 format
5. **Given** migration completes successfully, **When** Lambda loads workflows, **Then** workflows are loaded from database instead of S3

---

### User Story 5 - List Workflows via API (Priority: P2)

The frontend or external tools call an API endpoint to retrieve all workflows with optional filtering parameters. The API returns paginated results with complete workflow information in a structured format.

**Why this priority**: Enables frontend integration - without this API, the UI cannot display workflow data.

**Independent Test**: Can be tested by calling the API endpoint and verifying it returns all workflows in the expected JSON structure with pagination metadata.

**Acceptance Scenarios**:

1. **Given** 100 workflows exist, **When** API is called with no filters, **Then** first 20 workflows are returned with pagination metadata (total, page, per_page)
2. **Given** API request includes filter enabled=true, **When** processing the request, **Then** only enabled workflows are returned
3. **Given** API request includes page=3 and per_page=10, **When** processing the request, **Then** workflows 21-30 are returned
4. **Given** API request includes sort_by=name and sort_order=asc, **When** processing the request, **Then** workflows are returned in alphabetical order
5. **Given** a workflow with complex condition data, **When** API returns the workflow, **Then** conditions are serialized as JSON objects with all nested fields

---

### User Story 6 - Get Workflow Details via API (Priority: P2)

The frontend calls an API endpoint with a workflow ID to retrieve complete details for a single workflow. The API returns all configuration fields including conditions array, trigger object, and metadata.

**Why this priority**: Supports detail view - frontend needs to fetch full workflow configuration when user clicks a row.

**Independent Test**: Can be tested by calling the API with a valid workflow ID and verifying all fields are returned accurately.

**Acceptance Scenarios**:

1. **Given** a valid workflow ID, **When** API is called, **Then** the complete workflow object is returned with all fields
2. **Given** a workflow with 3 conditions, **When** API returns details, **Then** the conditions array contains 3 condition objects with full details
3. **Given** a workflow with zone indicator (value and zone_value), **When** API returns details, **Then** both value and zone_value are included
4. **Given** an invalid workflow ID, **When** API is called, **Then** HTTP 404 is returned with error message "Workflow not found"
5. **Given** a workflow with null end_date, **When** API returns details, **Then** end_date field is null (not omitted)

---

### Edge Cases

- What happens when the database table doesn't exist during Lambda execution? (Lambda logs error and falls back to YAML loading if available, or fails gracefully with notification)
- How are workflows with duplicate names handled? (Database enforces unique names, migration script fails if duplicates exist in YAML with error listing conflicts)
- What happens if a workflow has no conditions array? (Validation error - workflows must have at least one condition)
- How are workflows with invalid indicator types handled? (Validation error during migration - only supported types allowed: ma50, combo, bbb, bbh, polarite, zone)
- What if the UI tries to display 1000+ workflows? (Pagination ensures only requested page is loaded; frontend displays page controls)
- How are concurrent Lambda executions prevented from causing race conditions? (Database reads are consistent; no writes during Lambda execution, only reads)
- What happens if a workflow's index asset no longer exists in Saxo API? (Workflow still displays; execution failures are logged separately in workflow engine)

## Requirements *(mandatory)*

### Functional Requirements

#### User Interface

- **FR-001**: System MUST provide a workflows management page accessible from the main navigation menu
- **FR-002**: Workflow table MUST display columns: Name, Index, CFD, Status (enabled/disabled), Dry Run indicator, Indicator Type, Unit Time, End Date
- **FR-003**: Workflow table MUST show enabled status with visual indicator (green checkmark for enabled, red X for disabled)
- **FR-004**: Workflow table MUST show dry run mode with badge (e.g., "DRY RUN" label) when workflow.dry_run is true
- **FR-005**: Workflow table MUST support pagination with configurable items per page (default 20, options: 10, 20, 50, 100)
- **FR-006**: Workflow table MUST support filtering by: enabled status, index, indicator type, dry run mode
- **FR-007**: Workflow table MUST support sorting by: name, index, end date (ascending and descending)
- **FR-008**: Workflow table MUST display loading state while fetching data from API
- **FR-009**: Workflow table MUST display error state with retry button when API call fails
- **FR-010**: Workflow table MUST display empty state with message when no workflows match filters
- **FR-011**: Clicking a workflow row MUST open a detail panel or modal showing complete workflow configuration
- **FR-012**: Workflow detail view MUST display all fields: name, index, cfd, enabled, dry_run, is_us, end_date, conditions, trigger
- **FR-013**: Workflow detail view MUST display conditions as formatted list showing: indicator (name, unit time, value, zone_value), close (direction, unit time, spread), element (if present)
- **FR-014**: Workflow detail view MUST display trigger as formatted section showing: unit time, signal, location, order direction, quantity
- **FR-015**: Workflow detail view MUST show US Market indicator when is_us is true
- **FR-016**: Workflow page MUST auto-refresh data every 60 seconds when browser tab is visible
- **FR-017**: Workflow page MUST NOT auto-refresh when browser tab is hidden

#### Database Schema

- **FR-018**: Database MUST have a workflows table with primary key "id" (unique identifier)
- **FR-019**: Workflow record MUST store: id, name, index, cfd, enable, dry_run, is_us, end_date, conditions, trigger, created_at, updated_at
- **FR-020**: Workflow name field MUST be unique across all workflows
- **FR-021**: Workflow enable field MUST be boolean (true/false)
- **FR-022**: Workflow dry_run field MUST be boolean (true/false)
- **FR-023**: Workflow is_us field MUST be boolean (true/false)
- **FR-024**: Workflow end_date field MUST be ISO 8601 date string or null
- **FR-025**: Workflow conditions field MUST store array of condition objects
- **FR-026**: Each condition object MUST contain: indicator (object), close (object), element (string or null)
- **FR-027**: Indicator object MUST contain: name (string), ut (string), value (number or null), zone_value (number or null)
- **FR-028**: Close object MUST contain: direction (string), ut (string), spread (number)
- **FR-029**: Workflow trigger field MUST store trigger object
- **FR-030**: Trigger object MUST contain: ut (string), signal (string), location (string), order_direction (string), quantity (number)
- **FR-031**: Database MUST support querying workflows by index with case-insensitive matching
- **FR-032**: Database MUST support querying workflows by enabled status
- **FR-033**: Database MUST support querying workflows by indicator type (nested in conditions array)

#### Migration System

- **FR-034**: System MUST provide a migration script that reads workflows.yml and creates database records
- **FR-035**: Migration script MUST parse YAML workflows and validate all required fields before insertion
- **FR-036**: Migration script MUST generate unique IDs for each workflow (e.g., UUID or auto-increment)
- **FR-037**: Migration script MUST convert end_date from YYYY/MM/DD format to ISO 8601 format
- **FR-038**: Migration script MUST apply default trigger values when trigger section is missing in YAML
- **FR-039**: Migration script MUST preserve all indicator values (value, zone_value) during migration
- **FR-040**: Migration script MUST preserve condition element when specified in YAML
- **FR-041**: Migration script MUST fail with clear error message if duplicate workflow names are detected
- **FR-042**: Migration script MUST fail with clear error message if unsupported indicator types are found
- **FR-043**: Migration script MUST log progress (number of workflows processed, created, failed)
- **FR-044**: Migration script MUST be idempotent (can be run multiple times without creating duplicates)
- **FR-045**: Migration script MUST provide rollback capability (delete all workflows created in current run)

#### Lambda Integration

- **FR-046**: Lambda workflow loader MUST check if database table exists before attempting to load workflows
- **FR-047**: Lambda workflow loader MUST query all workflows with enable=true from database
- **FR-048**: Lambda workflow loader MUST filter workflows by end_date (only workflows with null end_date or future end_date)
- **FR-049**: Lambda workflow loader MUST transform database records into domain Workflow objects
- **FR-050**: Lambda workflow loader MUST deserialize conditions array into Condition objects with nested Indicator and Close objects
- **FR-051**: Lambda workflow loader MUST deserialize trigger object into Trigger domain object
- **FR-052**: Lambda workflow loader MUST fall back to S3/YAML loading if database table is missing or query fails
- **FR-053**: Lambda workflow loader MUST log workflow source (database vs YAML) for debugging
- **FR-054**: Lambda workflow loader MUST handle empty workflows table (no enabled workflows) without error

#### API Endpoints

- **FR-055**: System MUST provide GET endpoint `/api/workflows` for listing all workflows
- **FR-056**: `/api/workflows` endpoint MUST accept query parameters: page (integer, default 1), per_page (integer, default 20), enabled (boolean, optional), index (string, optional), indicator_type (string, optional), dry_run (boolean, optional), sort_by (string, optional), sort_order (asc or desc, optional)
- **FR-057**: `/api/workflows` endpoint MUST return response with: workflows (array of workflow objects), total (total count), page (current page), per_page (items per page), total_pages (calculated total pages)
- **FR-058**: `/api/workflows` endpoint MUST filter workflows by enabled status when enabled parameter is provided
- **FR-059**: `/api/workflows` endpoint MUST filter workflows by index when index parameter is provided (case-insensitive partial match)
- **FR-060**: `/api/workflows` endpoint MUST filter workflows by indicator type when indicator_type parameter is provided (searches conditions array)
- **FR-061**: `/api/workflows` endpoint MUST filter workflows by dry_run status when dry_run parameter is provided
- **FR-062**: `/api/workflows` endpoint MUST sort workflows by specified field when sort_by parameter is provided
- **FR-063**: `/api/workflows` endpoint MUST return workflows in requested sort order (ascending or descending)
- **FR-064**: System MUST provide GET endpoint `/api/workflows/{id}` for retrieving single workflow details
- **FR-065**: `/api/workflows/{id}` endpoint MUST return complete workflow object with all fields
- **FR-066**: `/api/workflows/{id}` endpoint MUST return HTTP 404 when workflow ID does not exist
- **FR-067**: Both endpoints MUST return HTTP 500 with error message when database query fails
- **FR-068**: Both endpoints MUST serialize workflow objects to JSON matching frontend TypeScript interfaces

### Key Entities

- **Workflow**: Complete trading strategy configuration with unique identifier, name, target index/CFD pair, enabled status, dry run flag, US market indicator, optional end date, conditions array, trigger configuration, and timestamps
- **Condition**: Evaluation rule containing indicator to monitor, close evaluation parameters, and optional element specification (close/high/low)
- **Indicator**: Technical analysis indicator with type name, unit time, optional fixed value, and optional zone range value
- **Close**: Close candle evaluation parameters with direction (above/below), unit time, and spread tolerance
- **Trigger**: Order generation parameters with unit time, signal type, location (higher/lower), order direction (buy/sell), and quantity
- **WorkflowListItem**: Summarized workflow representation for table display containing id, name, index, cfd, status, dry run indicator, primary indicator type, unit time, and end date
- **PaginationMetadata**: Pagination information containing total count, current page, items per page, and total pages

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Traders can view all workflows within 2 seconds of page load
- **SC-002**: Workflow table displays up to 100 workflows without performance degradation
- **SC-003**: Filtering workflows by any criterion updates results within 500 milliseconds
- **SC-004**: Migration script successfully migrates 100% of valid workflows from YAML to database
- **SC-005**: Lambda execution loads workflows from database within 5 seconds
- **SC-006**: Workflow detail view displays complete configuration within 1 second of row click
- **SC-007**: Zero data loss during YAML to database migration (all fields preserved)
- **SC-008**: API pagination handles up to 1000 workflows efficiently (under 2 second response time)
- **SC-009**: Traders can locate specific workflow using filters within 10 seconds
- **SC-010**: System maintains 99.9% uptime for workflow viewing functionality

### System Quality

- **SC-011**: Database migration is reversible - can restore from YAML if issues occur
- **SC-012**: Lambda workflow loading gracefully falls back to YAML if database is unavailable
- **SC-013**: Workflow table UI remains responsive with 500+ workflows through pagination
- **SC-014**: API responses follow consistent structure across all endpoints
- **SC-015**: Workflow data displayed in UI matches database values with 100% accuracy

## Assumptions

1. **Database Structure**: Workflows table uses single-table design with structured data (JSON) for conditions and trigger rather than normalized relational design
2. **Migration Timing**: Migration is performed during a maintenance window when Lambda is not actively executing workflows
3. **Read-Heavy Workload**: Workflows are read frequently (Lambda every hour, UI page views) but written rarely (manual YAML edits followed by migration)
4. **No Concurrent Writes**: Only migration script writes to workflows table; no concurrent workflow updates during Lambda execution
5. **YAML Source of Truth**: After migration, YAML file is retained for backup purposes but database becomes primary data source
6. **Unique Workflow Names**: Existing workflows.yml has unique names per workflow; no naming conflicts exist
7. **Browser Compatibility**: Frontend targets modern browsers with ES6+ JavaScript support
8. **Single User Context**: Workflow management UI is used by single trader or small team; no multi-tenant considerations
9. **No Real-Time Collaboration**: Multiple users can view workflows simultaneously but UI does not sync live updates

## Scope

### In Scope

- Workflow management UI page with table view
- Filtering and sorting workflows
- Workflow detail view (read-only)
- Database table creation for workflows storage
- Migration script from YAML to database
- Lambda integration to load workflows from database
- API endpoints for listing and retrieving workflows
- Pagination for large workflow lists
- Error handling and loading states in UI
- Fallback mechanism to YAML if database unavailable

### Out of Scope

- **Workflow Creation UI**: Creating new workflows through web interface (must still use YAML + migration)
- **Workflow Editing UI**: Modifying existing workflows through web interface
- **Workflow Deletion**: Removing workflows through UI or API
- **Workflow Duplication**: Cloning workflows to create variants
- **Workflow Execution Triggers**: Manually triggering workflow execution from UI
- **Execution History**: Viewing past workflow executions, orders generated, or performance metrics
- **Live Workflow Status**: Real-time indicator values or condition evaluation status
- **Workflow Templates**: Pre-built workflow configurations for common strategies
- **Bulk Operations**: Enabling/disabling multiple workflows at once
- **Workflow Import/Export**: Downloading workflows as YAML or JSON files
- **User Permissions**: Role-based access control for viewing or managing workflows
- **Audit Logging**: Tracking who viewed or modified workflows

## Dependencies

- **Database Service**: Database instance must be provisioned and accessible to Lambda and API server
- **Existing Workflow Engine**: Migration and API must preserve exact data structure expected by workflow engine (engines/workflow_engine.py)
- **Frontend Framework**: React 19+ with TypeScript for UI implementation
- **API Infrastructure**: FastAPI server with database client integration
- **Lambda Environment**: Database client libraries must be available in Lambda runtime
- **YAML Parsing Library**: Migration script requires YAML parser matching existing format

## Risks & Constraints

### Technical Risks

1. **Schema Evolution**: Future workflow features may require schema changes; database design must support migrations
2. **Large Payload Size**: Workflows with many conditions could approach database item size limits
3. **Query Performance**: Filtering by indicator type requires scanning conditions array; may slow down with many workflows
4. **Migration Failures**: Partial migration could leave system in inconsistent state with some workflows in database, others in YAML

### Operational Constraints

1. **No Edit Capability**: Workflow editing still requires YAML file modification and re-running migration
2. **Two-Step Update Process**: Workflow changes require YAML edit + migration run, not immediate
3. **No Version History**: Database stores current workflow state only; no tracking of changes over time
4. **Manual Migration**: Administrator must trigger migration script; not automated

### Business Constraints

1. **Read-Only UI**: Traders can view but not modify workflows, limiting self-service capability
2. **YAML Dependency**: YAML file remains source of truth for defining new workflows
3. **Downtime for Migration**: Initial migration may require brief Lambda suspension to avoid conflicts

## Future Enhancements (Out of Scope)

- Workflow creation form with visual condition builder
- Inline workflow editing from UI
- Workflow activation/deactivation toggle buttons
- Workflow execution history and performance charts
- Workflow testing mode (simulate execution without real orders)
- Workflow version history and rollback capability
- Workflow templates library for common strategies
- Bulk workflow operations (enable all, disable all, export selection)
- Workflow health monitoring (last execution time, error count)
- User authentication and permission management
- Workflow sharing between traders
- API for programmatic workflow creation

---

**Note**: This specification focuses on providing read visibility into workflows and migrating storage infrastructure. Workflow creation and editing remain YAML-based processes until future enhancements add UI editing capabilities.
