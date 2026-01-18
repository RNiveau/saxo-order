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

## Recent Changes
- 004-watchlist-menu: Added Python 3.11 (backend), TypeScript 5+ / React 19+ (frontend) + FastAPI (backend), Vite + React Router DOM v7+ (frontend)
