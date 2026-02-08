<!--
SYNC IMPACT REPORT
==================
Version Change: 1.2.0 → 1.2.1
Action: Clarified Layered Architecture Discipline - added client encapsulation rule

Principles Modified:
  I. Layered Architecture Discipline - Enforcement section
     ADDED: "Backend: NEVER access client internals from service layer - use client methods,
             never client.dynamodb.Table() or similar"
     ADDED: "Backend: Clients MUST expose methods for all operations - encapsulate implementation details"

Rationale for Change:
  - Violation found in alerting_service.py accessing dynamodb_client.dynamodb.Table() directly
  - Breaks encapsulation and couples service layer to client implementation details
  - Makes testing harder (must mock internal client structure, not just methods)
  - Prevents client refactoring without cascading service layer changes
  - Common anti-pattern that needs explicit prohibition

Previous Version (1.2.0):
  - Expanded Domain Model Integrity with explicit exchange field requirement
  - 5 core principles with full-stack governance

New in 1.2.1:
  - Clarified encapsulation requirement for client-service interaction
  - Explicit prohibition of accessing client internals (e.g., .dynamodb.Table())
  - Requirement that clients expose proper methods for all operations

Templates Requiring Updates:
  ✅ plan-template.md - Constitution Check section will pick up new rule automatically
  ✅ spec-template.md - No changes needed
  ✅ tasks-template.md - No changes needed

Follow-up TODOs:
  - Refactor alerting_service.py to use DynamoDBClient methods instead of direct access
  - Add get_last_run_at() and update_last_run_at() methods to DynamoDBClient

Rationale for PATCH version (1.2.1):
  - Clarification of existing Layered Architecture Discipline principle
  - No new principles added, no existing requirements removed
  - Makes implicit encapsulation rule explicit and enforceable
-->

# saxo-order Constitution

## Core Principles

### I. Layered Architecture Discipline

The codebase MUST maintain strict separation between architectural layers:

**Backend Layers:**
1. **CLI Layer** (`saxo_order/commands/`): Click-based commands only - NO business logic
2. **API Layer** (`api/`): FastAPI routers exposing HTTP endpoints - thin orchestration of Services
3. **Service Layer** (`services/`): Business logic and orchestration - NO direct external API calls
4. **Client Layer** (`client/`): External API integrations (Saxo, Binance, Google Sheets) - NO business logic
5. **Model Layer** (`model/`): Data structures and domain models - NO external dependencies

**Frontend Layers:**
6. **Pages** (`frontend/src/pages/`): Page-level components with routing - NO direct API calls
7. **Components** (`frontend/src/components/`): Reusable UI components - props in, events out
8. **Services** (`frontend/src/services/`): API client with TypeScript interfaces - single source of API interaction
9. **Utils** (`frontend/src/utils/`): Pure utility functions - NO side effects

**Rationale**: This separation ensures testability through mocked dependencies, enables independent evolution of each layer, and prevents tight coupling between external APIs and business logic. The Service layer orchestrates Clients to perform domain operations. The API layer provides HTTP endpoints for frontend consumption. The frontend service layer isolates all API communication.

**Enforcement**:
- Backend: Service classes receive clients as constructor parameters (dependency injection)
- Backend: Client methods return domain models, never raw API responses
- Backend: Models use enums for status/type fields, never hardcoded strings
- Backend: **NEVER access client internals from service layer** - use client methods, never `client.dynamodb.Table()` or similar
- Backend: Clients MUST expose methods for all operations - encapsulate implementation details
- Backend: **NEVER use underscore prefix for public methods** - methods called from outside the class (routers, other services) MUST NOT start with `_`
- Frontend: All API calls MUST go through services in `frontend/src/services/`
- Frontend: Components receive data via props, emit events via callbacks - NO direct API calls
- API: TypeScript interfaces in frontend MUST match Pydantic models in backend (use exact field names)

### II. Clean Code First

Code MUST prioritize clarity and simplicity over premature abstraction:

1. **Self-Documenting**: Code must be readable without inline comments explaining obvious operations
2. **No Over-Engineering**: Only build what's needed - no speculative features or abstractions
3. **Enum-Driven**: Use existing enums instead of hardcoded strings throughout the codebase
4. **No Unnecessary Comments**: Avoid inline comments like "// Use unique account ID" or "// Send enum key directly"

**Rationale**: Clean, self-evident code reduces maintenance burden and cognitive load. Comments that explain "what" indicate unclear code; comments should explain "why" for non-obvious decisions only. Enums provide type safety and IDE autocomplete.

**Enforcement**:
- Code reviews reject unnecessary comments and hardcoded strings
- Black formatter (79 char line length) and isort enforce consistent style
- MyPy type checking required for all new code

### III. Configuration-Driven Design

External integrations and environment-specific behavior MUST use configuration files:

**Backend Configuration:**
1. **YAML Configuration**: `config.yml` for non-sensitive settings, `secrets.yml` (gitignored) for credentials
2. **Environment Overrides**: Environment variables override YAML values for deployment flexibility
3. **No Hardcoding**: API endpoints, timeouts, retry logic, and thresholds live in config files

**Frontend Configuration:**
4. **Vite Environment Variables**: Use `VITE_*` prefixed variables in `.env` files
5. **API URL Configuration**: `VITE_API_URL` for backend endpoint (defaults to `http://localhost:8000`)
6. **Build-Time vs Runtime**: Vite inlines env vars at build time - use `import.meta.env.VITE_*`

**API Configuration:**
7. **CORS Origins**: Allowed origins in `api/main.py` (localhost:3000, localhost:5173 for dev)

**Rationale**: Configuration externalization enables environment-specific behavior without code changes, simplifies testing with test configurations, and prevents credential leakage through version control. Frontend environment variables ensure proper API endpoint targeting across dev/prod.

**Enforcement**:
- Backend: `secrets.yml` included in `.gitignore`
- Backend: Configuration loaded once at application startup
- Backend: Integration tests use test-specific config files
- Frontend: `.env` files gitignored, `.env.example` committed
- Frontend: Never hardcode API URLs - always use `import.meta.env.VITE_API_URL`

### IV. Safe Deployment Practices

Infrastructure changes and Lambda deployments MUST follow controlled procedures:

1. **Infrastructure as Code**: AWS resources managed exclusively through Pulumi (in `pulumi/`)
2. **Docker-Based Lambda**: Lambda functions deployed as Docker images to ECR, ensuring dependency consistency
3. **Deployment Script**: Use `./deploy.sh` for all deployments - NO manual console changes
4. **Conventional Commits**: Follow commit format (`feat:`, `fix:`, `chore:`, etc.) for clear change history

**Rationale**: Infrastructure-as-code prevents configuration drift and enables reproducible deployments. Docker images guarantee consistent runtime environments. Conventional commits enable automated changelog generation and semantic versioning.

**Enforcement**:
- Pull requests must not include AWS console screenshots showing manual changes
- Deployment changes require both code change AND Pulumi update
- Pre-commit hooks validate commit message format

### V. Domain Model Integrity

Domain models and data structures MUST reflect business reality:

1. **Candle Ordering**: Candle lists always have index 0 = newest, last index = oldest
2. **Saxo API Constraints**: Current day (horizon 1440) and current hour (horizon 60) not returned - rebuild from smaller horizons
3. **Model Boundaries**: Outside SaxoService, use Candle objects everywhere - never raw Saxo responses
4. **Assets and Exchanges**: A Saxo asset CAN be without `country_code`. NEVER use `country_code` presence or absence to determine if an asset is from Saxo or Binance. ALWAYS use an explicit `exchange` field to identify the source exchange. When designing data models that store or transmit asset information, include an `exchange` field (e.g., "saxo", "binance") rather than inferring the exchange from other attributes.

**Rationale**: Consistent domain model conventions prevent subtle bugs from incorrect assumptions. Explicit handling of API limitations (missing current periods) ensures accurate data. Clear boundaries between external API responses and internal models enable API provider changes without cascading changes. The `country_code` field is unreliable for exchange identification because Saxo assets may lack it, leading to false assumptions that could cause navigation errors, incorrect API routing, or data corruption.

**Enforcement**:
- Unit tests validate Candle ordering conventions
- Integration tests verify horizon reconstruction logic
- Code reviews check for raw API response usage outside Client layer
- Code reviews reject exchange inference from `country_code` - require explicit `exchange` field
- Data models (Alert, Order, Asset representations) MUST include explicit `exchange` field

## Development Standards

### Planning Requirement

- **ALWAYS** suggest a plan before implementing features
- **NEVER** implement a plan without human validation
- Use `EnterPlanMode` for non-trivial implementations requiring architectural decisions

### Testing Standards

**Backend Testing:**
- **Structure**: Mirror source structure in `tests/` directory
- **Fixtures**: Use pytest fixtures for common test data
- **Mocking**: Mock external API calls using `unittest.mock`
- **Test Data**: Store test data files in `tests/services/files/`
- **No Mock Testing**: DO NOT write tests that merely verify mocks were called - test actual behavior

**Frontend Testing:**
- Testing standards TBD - currently no testing framework configured
- When added, follow component testing best practices

### Code Quality Standards

**Backend Quality:**
- **Formatting**: Run `poetry run black .` and `poetry run isort .` before commits
- **Type Checking**: Run `poetry run mypy .` - all new code must pass type checking
- **Linting**: Run `poetry run flake8` - address all violations
- **Coverage**: Maintain test coverage with `poetry run pytest --cov`

**Frontend Quality:**
- **Formatting**: Run `npm run lint` in `frontend/` directory
- **Type Checking**: Run `npm run build` - TypeScript must compile without errors
- **Build**: Vite build must succeed without warnings

### Frontend Development Standards

**Technology Stack:**
- **Framework**: React 19+ with TypeScript 5+
- **Build Tool**: Vite 7+ with hot module replacement
- **Routing**: React Router DOM v7+
- **HTTP Client**: Axios for API communication

**Component Standards:**
- **Functional Components**: Use function components with hooks, NO class components
- **TypeScript**: All components and functions MUST have proper type annotations
- **Props Interface**: Define interface for component props - NO implicit `any` types
- **Service Layer**: All API calls through `frontend/src/services/api.ts` - NEVER inline axios calls

**API Contract Standards:**
- **TypeScript Interfaces**: Mirror backend Pydantic models exactly (same field names, types)
- **Response Types**: Define interfaces for all API responses
- **Request Types**: Define interfaces for all API request payloads
- **Service Functions**: Export named service objects (e.g., `fundService`, `reportService`) with typed methods

**File Organization:**
- **Pages**: Route-level components in `frontend/src/pages/` (e.g., `Report.tsx`, `Watchlist.tsx`)
- **Components**: Reusable components in `frontend/src/components/` (e.g., `HomepageCard.tsx`)
- **Services**: API client logic in `frontend/src/services/` (single `api.ts` file for all endpoints)
- **Utils**: Pure functions in `frontend/src/utils/` (e.g., `marketHours.ts`, `tradingview.ts`)
- **Styles**: Component-specific CSS alongside components (e.g., `Report.css` next to `Report.tsx`)

**Development Workflow:**
- **Backend**: Run `poetry run python run_api.py` for API server on port 8000
- **Frontend**: Run `npm run dev` in `frontend/` for Vite dev server on port 5173
- **Hot Reload**: Both backend (uvicorn) and frontend (Vite) support hot reloading

## Quality Gates

### Pre-Commit Gates

**Backend:**
1. Commit message follows conventional commit format
2. Code formatted with Black and imports sorted with isort
3. No type checking errors from MyPy
4. No linting errors from flake8

**Frontend:**
5. TypeScript compiles without errors (`npm run build`)
6. ESLint passes without errors (`npm run lint`)
7. No hardcoded API URLs (must use `import.meta.env.VITE_API_URL`)

### Pre-Merge Gates

**Backend:**
1. All tests pass: `poetry run pytest`
2. Test coverage maintained or improved
3. Architecture layers respected (no cross-layer violations)
4. No hardcoded strings where enums exist
5. Configuration changes documented in config files, not code

**Frontend:**
6. Vite build completes successfully
7. All pages render without console errors
8. API service layer used for all HTTP calls (no inline axios in components)
9. TypeScript interfaces match backend Pydantic models

**Full-Stack:**
10. API endpoints tested with actual frontend calls (manual smoke test)
11. CORS configuration allows frontend origin

### Pre-Deployment Gates

**Backend:**
1. Docker image builds successfully
2. Pulumi preview shows expected infrastructure changes
3. No manual AWS console changes required
4. Deployment script (`./deploy.sh`) executes without errors

**Frontend:**
5. Production build completes: `npm run build` in `frontend/`
6. Frontend dist files generated in `frontend/dist/`
7. Environment variables configured for production (`VITE_API_URL`)

## Governance

### Amendment Procedure

1. **Proposal**: Document proposed amendment with rationale in pull request
2. **Impact Analysis**: Identify affected templates, code, and practices
3. **Version Bump**: Increment constitution version per semantic versioning:
   - **MAJOR**: Backward incompatible governance changes or principle removal
   - **MINOR**: New principle added or material expansion of guidance
   - **PATCH**: Clarifications, wording fixes, non-semantic refinements
4. **Approval**: Requires repository maintainer approval
5. **Propagation**: Update dependent templates (plan, spec, tasks) before merge

### Compliance Review

- Pull request reviews MUST verify constitution compliance
- Architecture violations require explicit justification in "Complexity Tracking" section of plan.md
- Unjustified complexity or over-engineering grounds for rejection

### Runtime Guidance

- This constitution defines **non-negotiable rules**
- **CLAUDE.md** provides runtime development guidance and implementation patterns
- When conflict arises, constitution takes precedence; update CLAUDE.md to align

**Version**: 1.2.1 | **Ratified**: 2026-01-09 | **Last Amended**: 2026-01-17
