# Implementation Plan: Homepage Dashboard

**Branch**: `511-homepage-feature` (merged)
**Date**: 2026-01-09 (retroactive documentation)
**Spec**: [spec.md](./spec.md)
**Input**: Reverse-engineered from implementation

## Summary

Implement homepage dashboard displaying up to 6 watchlist assets tagged as "homepage", showing real-time prices, variation %, MA50 indicator, and TradingView chart links. Backend fetches from DynamoDB watchlist table with "homepage" label filter. Frontend displays in responsive grid with navigation to asset detail pages.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.8 (frontend)
**Primary Dependencies**: FastAPI, React 19, DynamoDB (boto3), Axios
**Storage**: DynamoDB watchlist table (existing)
**Testing**: pytest (backend), manual testing (frontend)
**Target Platform**: Web application (FastAPI + React/Vite)
**Project Type**: Full-stack web application
**Performance Goals**: <2s page load, real-time price updates
**Constraints**: Maximum 6 assets, DynamoDB query limit
**Scale/Scope**: Single page feature, ~500 LOC total

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

✅ **Layered Architecture Discipline**:
- Backend: API router → Indicator service → Saxo/Binance clients ✓
- Frontend: Homepage page → HomepageCard component → API service ✓
- No business logic in API router ✓
- No direct API calls in frontend components ✓

✅ **Clean Code First**:
- Self-documenting code, minimal comments ✓
- Enum-driven (WatchlistTag.HOMEPAGE, Exchange enum) ✓
- No over-engineering ✓

✅ **Configuration-Driven Design**:
- DynamoDB table name from config ✓
- API URL from VITE_API_URL ✓
- No hardcoded endpoints ✓

✅ **Safe Deployment Practices**:
- Conventional commits used ✓
- Backend deployed via Lambda ✓
- Frontend build via Vite ✓

✅ **Domain Model Integrity**:
- Candle objects for price/MA calculation ✓
- Models consistent across backend/frontend ✓

## Project Structure

### Documentation (this feature)

```text
specs/511-homepage-feature/
├── spec.md              # This retroactive specification
├── plan.md              # This retroactive plan
└── (tasks.md omitted - feature already implemented)
```

### Source Code (implemented)

```text
# Backend
api/routers/homepage.py          # FastAPI router with /api/homepage endpoint
api/models/homepage.py           # Pydantic models (HomepageItemResponse, HomepageResponse)
api/services/indicator_service.py # MA50 calculation logic (existing, reused)

# Frontend
frontend/src/components/Home.tsx         # Homepage page component
frontend/src/components/HomepageCard.tsx # Individual asset card component
frontend/src/services/api.ts             # API client (homepageService)
frontend/src/components/Home.css         # Homepage styles
frontend/src/components/HomepageCard.css # Card styles

# Database
# Reused existing DynamoDB watchlist table with labels field
```

**Structure Decision**: Full-stack feature following existing architecture patterns. Backend adds new FastAPI router using existing indicator service. Frontend adds new page component with card subcomponent. No database schema changes required (reuses existing labels field).

## Complexity Tracking

> **No violations - constitution fully compliant**

## Implementation Summary (Retroactive)

### Phase 1: Backend Implementation

**Commits**: 08a4191, 1471640, 790cbcc, b269568

1. Created `api/models/homepage.py` with Pydantic models
2. Created `api/routers/homepage.py` with GET endpoint
3. Reused `IndicatorService` for MA50 calculation
4. Filtered watchlist items by `WatchlistTag.HOMEPAGE` label
5. Integrated with DynamoDB client for watchlist retrieval
6. Added TradingView URL fetching from asset_details table

**Key Design Decisions**:
- Reused existing watchlist infrastructure (no new tables)
- Limited to 6 assets via slice operation
- MA50 calculated on-demand using existing CandlesService
- Supported both Saxo and Binance exchanges

### Phase 2: Frontend Implementation

**Commits**: b630051, de19264, 3627e4b, 020891c

1. Created `Home.tsx` page component with grid layout
2. Created `HomepageCard.tsx` reusable card component
3. Added `homepageService` to `api.ts` with TypeScript interfaces
4. Implemented responsive grid (3 columns desktop, 1 column mobile)
5. Added navigation to asset detail pages via React Router
6. Styled with component-specific CSS files

**Key Design Decisions**:
- Card-based UI pattern for consistency
- Grid layout for responsive design
- Click-through navigation to asset detail
- Color-coded variation % (green/red)
- MA50 indicator with visual "above/below" status

## Verification

**Manual Testing Performed**:
- ✅ Homepage displays tagged assets
- ✅ Prices and variation % accurate
- ✅ MA50 calculation matches TradingView
- ✅ Navigation to asset detail works
- ✅ Responsive on mobile viewports
- ✅ Both Saxo and Binance assets supported

**Integration Points Tested**:
- ✅ DynamoDB watchlist query
- ✅ Saxo/Binance price fetching
- ✅ Candles service for MA50 calculation
- ✅ TradingView URL retrieval
- ✅ Frontend API service communication
