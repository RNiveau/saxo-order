# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

saxo-order is a Python CLI tool for managing trading orders across Saxo Bank and Binance, with financial reporting, stock analysis, and automated workflows deployed on AWS Lambda.

## Common Development Commands

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest
poetry run pytest --cov  # with coverage

# Run a single test
poetry run pytest tests/path/to/test_file.py::test_function_name

# Code quality
poetry run black .       # Format code
poetry run isort .       # Sort imports
poetry run mypy .        # Type checking
poetry run flake8        # Linting

# Run the CLI
poetry run k-order --help
```

## High-Level Architecture

The codebase follows a layered architecture:

1. **CLI Layer** (`saxo_order/commands/`): Click-based commands that parse arguments and orchestrate services
2. **Service Layer** (`services/`): Business logic for indicators, candles, and domain operations
3. **Client Layer** (`client/`): API integrations with external services (Saxo, Binance, Google Sheets)
4. **Model Layer** (`model/`): Data structures and domain models
5. **Infrastructure** (`pulumi/`): AWS resources managed as code (Lambda, ECR, DynamoDB, S3)

## Key Patterns

- **Command Pattern**: Each CLI command is a separate module in `saxo_order/commands/`
- **Dependency Injection**: Services receive clients as constructor parameters
- **Configuration**: YAML-based with environment variable overrides
- **Testing**: Mirror source structure in `tests/` with mocked external dependencies
- **Deployment**: Docker-based Lambda functions deployed via Pulumi

## Important Files

- `saxo_order/service.py`: Core service orchestration
- `lambda_function.py`: AWS Lambda entry point for scheduled tasks
- `engines/workflow.py`: Workflow engine for automated processes
- `config.yml` / `secrets.yml`: Configuration files (secrets.yml is gitignored)
- `deploy.sh`: Deployment script that builds Docker image and updates infrastructure

## Important guidelines

- ALWAYS suggest a plan before implementing something
- ALWAYS use the existing enums in place of a hardcoded string
- NEVER implement a plan without a human validation
- The Candle list has always the newest candle with the index 0, and the oldest with the last index
- Outside the SaxoService, the candle object must be used everywhere.
- The saxo api doesn't return the current day (horizon 1440) or current hour (horizon 60). You have to rebuild it with a smaller horizon
- DO NOT add unnecessary inline comments explaining obvious code (e.g., "// Use unique account ID", "// Send enum key directly"). Keep code clean and self-documenting 
- A saxo asset CAN be without country_code, DO NOT assume an asset without country code is a binance one

## Testing Guidelines

When writing tests:
- Place test files in `tests/` mirroring the source structure
- Use pytest fixtures for common test data
- Mock external API calls using `unittest.mock`
- Test data files go in `tests/services/files/`
- DON'T test mock, we don't need that

## Deployment

The project deploys to AWS Lambda:
1. Build Docker image with dependencies
2. Push to AWS ECR
3. Update Lambda function via Pulumi
4. Scheduled execution via EventBridge

Use `./deploy.sh` to deploy changes (requires AWS credentials configured).

## Commit Convention

This project follows conventional commit format:

```
<type>: <description>

[optional body]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test additions or modifications
- `chore`: Build process or auxiliary tool changes

Examples:
- `feat: add portfolio analysis command`
- `fix: correct order calculation in Saxo client`
- `chore: update dependencies`

## Active Technologies
- Python 3.11 (backend), TypeScript 5+ / React 19+ (frontend) + FastAPI (backend), Vite + React Router DOM v7+ (frontend) (004-watchlist-menu)
- AWS DynamoDB (existing "watchlist" table) (004-watchlist-menu)
- TypeScript 5+ (frontend), Python 3.11+ (backend - no changes) + React 19+, Vite 7+, Axios (frontend) (005-filter-old-alerts)
- No changes - uses existing DynamoDB alerts table with TTL (005-filter-old-alerts)
- Python 3.11 (backend), TypeScript 5+ (frontend) + FastAPI (backend API), React 19+ (frontend), Vite 7+ (frontend build), DynamoDB (storage) (007-slwin-tag)
- AWS DynamoDB (watchlist table with labels attribute) (007-slwin-tag)
- AWS DynamoDB (workflow_orders table with TTL enabled) (010-workflow-execution-tracking)
- TypeScript 5+ / React 19+ + React Router DOM v7+, Vite 7+ (012-sidebar-navigation)
- `localStorage` (browser-native, no new dependency) (012-sidebar-navigation)
- Python 3.11 (backend), TypeScript 5+ / React 19+ (frontend) + FastAPI + Pydantic v2 (backend), React Router DOM v7+, Vite 7+, Axios (frontend) (014-workflow-orders-list)
- AWS DynamoDB `workflow_orders` table — existing, unchanged (014-workflow-orders-list)
- Python 3.11 + existing `mobile_average()` in `services/indicator_service.py`; `AbstractWorkflow` in `engines/workflows.py` (017-mm7-indicator)
- N/A — no persistence changes (017-mm7-indicator)
- Python 3.11 + FastAPI 0.121+, aioboto3 13.0+ (replacing boto3 1.40+), uvicorn 0.38+, pytest 9.0+ (011-async-dynamodb-operations)
- AWS DynamoDB (6 tables: indicators, watchlist, asset_details, alerts, workflows, workflow_orders) (011-async-dynamodb-operations)
- Python 3.11 + Saxo API client (existing), pytest, unittest.mock (018-candle-builder)
- N/A (no persistence changes) (018-candle-builder)
- Python 3.11 (backend), TypeScript 5+ / React 19+ (frontend — no changes required) + existing — `services/indicator_service.py` (`mobile_average`, `slope_percentage`), `saxo_order/commands/alerting.py` (`run_detection_for_asset`, `_build_candles`), `model.Alert`, `model.AlertType`, `client/aws_client.py` (`DynamoDBClient.store_alerts`), `slack_sdk.WebClient` (019-mm50-slope-alert)
- AWS DynamoDB `alerts` table (existing, schema unchanged — `data` is a free-form `Dict[str, Any]`, alert_type is appended to the existing alerts list with same-type-same-date dedup) (019-mm50-slope-alert)
- Python 3.11 (backend), TypeScript 5+ / React 19+ (frontend) + FastAPI, Click, `cachetools` (TTLCache), Pydantic v2, Axios, React Router DOM v7+, Vite 7+ (020-saxo-reporting)
- Google Sheets (persisted trading journal); in-memory `TTLCache` for report fetches (5 min TTL); no database for this feature (020-saxo-reporting)
- TypeScript 5+ / React 19+ + React (`useState`), existing `reportConfigService` from `frontend/src/services/api.ts` (already loaded — no new dependency) (020-saxo-reporting)
- N/A — purely in-memory component state (`strategy`, `signal`) (020-saxo-reporting)
- Python 3.11 (backend), TypeScript 5+ / React 19+ (frontend) + FastAPI (existing `api/` app), Python standard library `csv` module, existing `client/gsheet_client.py` (Google Sheets API via `googleapiclient`), Axios + React Router DOM v7+ (frontend, existing `frontend/src/services/api.ts`) (022-trade-republic-report)
- N/A — per spec (FR-010), uploaded transactions are held only for the current browser session (React state); no database table or file store is introduced (022-trade-republic-report)
- Python 3.11 (backend), TypeScript 5+ / React 19+ (frontend) — no change from existing stack. + FastAPI (backend, existing), Pydantic v2 (existing), `zoneinfo` (Python stdlib — new usage in this codebase for DST-aware Paris-local time math, see research.md §1), existing `SaxoClient`/`CandlesService`; React Router DOM v7+, Axios, Vite (frontend, existing). (021-backtest-menu-hardcoded)
- N/A — ephemeral, computed on demand per request, nothing persisted (Clarifications, Session 2026-07-14). (021-backtest-menu-hardcoded)
- Python 3.12 (backend), TypeScript 5+ / React 19+ (frontend) + `anthropic` SDK (NEW, backend), FastAPI + Pydantic v2, Click, `aioboto3` (DynamoDB), `slack_sdk`, `cachetools` (TTLCache); React Router DOM v7+, Vite 7+, Axios (frontend) (023-alert-triage)
- AWS DynamoDB — new `alert_digests` table (hash_key `run_date` String, range_key `created_at` Number, **no TTL**); existing `alerts` table unchanged (023-alert-triage)
- Python 3.11 (backend), TypeScript 5+ / React 19+ (frontend — minimal changes) + FastAPI, Pydantic v2, `cachetools` (TTLCache), `googleapiclient` (Google Sheets); NEW: a GraphQL/HTTP client for Ouinex (`httpx` or `requests` — POST GraphQL + JWT auth flow); frontend Axios + React Router DOM v7+ (024-ouinex-provider)
- AWS DynamoDB `watchlist` table (existing `exchange` attribute, unchanged schema); Google Sheets trading journal (existing "Liste d'ordre" sheet, unchanged schema). No new tables. (024-ouinex-provider)
- Python 3.11 (backend), TypeScript 5+ / React 19+ (frontend) — no change from existing stack. + FastAPI + Pydantic v2 (existing), `zoneinfo` (already used by the backtest service for Paris-local math), Python stdlib `csv` (existing exports), existing `SaxoClient`/`CandlesService`; React Router DOM v7+, Axios, Vite (frontend, existing). **No new dependency.** (025-ger40-bougie-9h)
- N/A — ephemeral, computed on demand per request, nothing persisted (inherits spec 021's decision). (025-ger40-bougie-9h)
- Python 3.11 (backend), TypeScript 5+ / React 19+ (frontend) + FastAPI + Pydantic v2, existing `services/indicator_service.py` (`combo`, `bollinger_bands`), existing `services/candles_service.py` (`get_candles_in_window`), `aioboto3` (DynamoDB), `zoneinfo`; React Router DOM v7+, Axios, Vite. **No new dependency.** (026-combo-ger40-backtest)
- existing DynamoDB backtest raw-candle table, under a **new key namespace** for arbitrary-timeframe series (`{instrument}:{session}:{ut}:v1`). No new table, no migration of existing entries. (026-combo-ger40-backtest)
- Python 3.11 (backend), TypeScript 5+ / React 19+ (frontend) + existing only — `aioboto3` (DynamoDB), `anthropic` SDK, `slack_sdk`, FastAPI + Pydantic v2, `zoneinfo`; Axios, React Router DOM v7+, Vite. **No new dependency.** (028-triage-workflow-trigger)
- existing tables only — reads `workflow_orders` and `workflows`, writes enriched asset entries into the existing `alert_digests` items. No new table, no migration. (028-triage-workflow-trigger)
- Python 3.11 (backend), TypeScript 5+ / React 19+ (frontend) + existing only — `services/indicator_service.py` (`combo`, `mobile_average`, `bollinger_bands`), `utils/helper.py` (`build_current_weekly_candle_from_daily`), `client/saxo_client.py` (`get_historical_data`, horizon 10080), `aioboto3`, `anthropic` SDK, `slack_sdk`; Axios, React Router DOM v7+, Vite. **No new dependency.** (029-combo-weekly-timeframe)
- existing `alerts` table, unchanged schema — the free-form `data` map gains `weekly_bar_date` and `timeframe`; calibration is a one-off sampled fetch outside the scan, not a table read. No new table, no migration. (029-combo-weekly-timeframe)
- Python 3.12 (`pyproject.toml` declares `^3.12`) + NEW — `mcp` (official Python SDK). Existing — `services/indicator_service.py`, `services/candles_service.py`, `client/saxo_client.py`, `client/aws_client.py` (`aioboto3`), `pydantic` v2 (030-mcp-asset-analysis)
- Read-only. Existing DynamoDB tables (`alerts`, `alert_digests`, `watchlist`, `workflow_orders`), unchanged schemas. No new table, no migration, no write path. (030-mcp-asset-analysis)

## Recent Changes
- 004-watchlist-menu: Added Python 3.11 (backend), TypeScript 5+ / React 19+ (frontend) + FastAPI (backend), Vite + React Router DOM v7+ (frontend)
