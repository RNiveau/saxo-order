# Feature Specifications

This directory contains feature specifications, implementation plans, and task lists for saxo-order features.

## Directory Structure

```text
specs/
├── README.md                    # This file
├── [###-feature-name]/         # Feature directory (### = issue number)
│   ├── spec.md                 # Feature specification (user stories, requirements)
│   ├── plan.md                 # Implementation plan (architecture, design)
│   ├── tasks.md                # Task list (implementation steps)
│   ├── research.md             # Technical research (optional)
│   ├── data-model.md           # Data models (optional)
│   ├── quickstart.md           # Usage guide (optional)
│   └── contracts/              # API contracts (optional)
```

## Feature Lifecycle

### New Features (Forward Process)

For new features, follow the spec-first workflow:

1. **Create Specification**: Use `/speckit.specify "feature description"`
   - Generates `spec.md` with user stories and requirements

2. **Create Plan**: Use `/speckit.plan`
   - Generates `plan.md` with architecture and design decisions

3. **Generate Tasks**: Use `/speckit.tasks`
   - Generates `tasks.md` with implementation steps

4. **Implement**: Use `/speckit.implement`
   - Executes tasks from `tasks.md`

### Existing Features (Backport Process)

For features already implemented, document retroactively:

#### Option 1: Manual Documentation (Learning)

Create spec and plan manually by reverse-engineering:

```bash
# 1. Create feature directory
mkdir -p .specify/specs/[issue-number]-[feature-name]

# 2. Write spec.md
# - Document what problem it solved
# - Reverse-engineer user stories from implementation
# - List requirements that were met

# 3. Write plan.md
# - Document architecture used
# - List files created/modified
# - Explain design decisions made

# 4. Optional: Write tasks.md
# - List what was actually implemented
# - Document in retrospect
```

#### Option 2: AI-Assisted Documentation

Use spec kit commands with retroactive descriptions:

```bash
/speckit.specify "Describe what the implemented feature does,
its user stories, and requirements based on the implementation"
```

Then manually review and adjust to match actual implementation.

## Backported Features

These features were implemented before spec kit adoption:

- ✅ **511-homepage-feature**: Homepage dashboard with MA50 indicators (retroactively documented)
- ✅ **471-binance-reporting**: Binance order reporting with Google Sheets integration (retroactively documented)
- ✅ **409-order-creation-api**: REST API and web UI for order creation with service layer extraction (retroactively documented)
- ✅ **473-binance-asset-indicators**: Binance crypto asset indicators with strict client encapsulation (retroactively documented)

## Active Features

Features currently in development:

- (none)

## Planned Features

Features with specs but not yet implemented:

- (none)

## Naming Convention

Feature directories use the format: `[issue-number]-[feature-name]`

Examples:
- `511-homepage-feature`
- `515-alert-storage`
- `513-create-order-button`

If no GitHub issue exists, use sequential numbers: `001-feature-name`

## Constitution Compliance

All features must comply with the project constitution (`.specify/memory/constitution.md`):

- ✅ Layered architecture (CLI/API/Service/Client/Model + Frontend)
- ✅ Clean code principles (self-documenting, enum-driven)
- ✅ Configuration-driven design (no hardcoded values)
- ✅ Safe deployment practices (Pulumi, Docker, conventional commits)
- ✅ Domain model integrity (proper data structures)

The `plan.md` for each feature must include a "Constitution Check" section.

## Priority Guide

When backporting, prioritize features in this order:

1. **High Priority**: Core business features (order management, reporting)
2. **Medium Priority**: User-facing features (homepage, watchlist, search)
3. **Low Priority**: Internal tools and utilities

## Next Steps

### Immediate Backporting Candidates

Based on recent commits, consider documenting these next:

1. **515-alert-storage**: Store alerts in DynamoDB with TTL
2. **513-create-order-button**: Add order creation from asset detail page
3. **512-autofill-order-date**: Auto-populate current date in order forms
4. **189-weekly-timeframe**: Weekly candle support for workflows and indicators

### Approach

For each feature:
1. Review git commits and implementation
2. Create spec directory
3. Write `spec.md` with user stories (what problem it solved)
4. Write `plan.md` with architecture (how it was built)
5. Commit with message: `docs: backport spec for [feature-name]`

## Questions?

- See templates in `.specify/templates/` for structure guidance
- See constitution in `.specify/memory/constitution.md` for principles
- Use `/speckit.*` commands for assistance
