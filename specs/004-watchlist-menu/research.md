# Research Findings: Long-Term Positions Menu

**Date**: 2026-01-18
**Feature**: Long-Term Positions Menu
**Purpose**: Resolve Technical Context unknowns and establish implementation patterns

## Overview

This research consolidates findings on frontend component patterns, routing configuration, and UI conventions to enable implementation of the long-term positions menu with maximum code reuse.

---

## Research Task 1: Frontend Watchlist Component Patterns

**Question**: What patterns does Watchlist.tsx use for rendering items, handling tag filters, and auto-refresh?

### Decision: Reuse Watchlist Component Structure with Simplifications

**Rationale**: The existing `Watchlist.tsx` component (`frontend/src/pages/Watchlist.tsx`) provides proven patterns for asset list rendering, auto-refresh, and tag filtering. The long-term positions menu can reuse 80% of this structure with the following simplifications:
1. Remove client-side tag filter UI (backend already filters)
2. Add stale data warning indicators (new requirement FR-012)
3. Add crypto asset badges (new requirement FR-013)

### State Management Pattern (Reusable)

```typescript
const [items, setItems] = useState<WatchlistItem[]>([]);
const [loading, setLoading] = useState(false);
const [error, setError] = useState<string | null>(null);
```

**Alternatives Considered**:
- Redux/Context API: Rejected - overkill for single-page state, adds complexity
- React Query: Not currently used in project, introduces new dependency

### Auto-Refresh Pattern (Reusable)

**Decision**: Implement visibility-aware polling with 60-second interval

**Implementation** (from `Watchlist.tsx` lines 45-80):
```typescript
useEffect(() => {
  loadData();

  let intervalId: NodeJS.Timeout | null = null;

  const handleVisibilityChange = () => {
    if (document.visibilityState === 'visible') {
      // Reload immediately when tab becomes visible
      if (isMarketOpen()) {
        loadData();
      }
      // Start auto-refresh
      if (!intervalId) {
        intervalId = setInterval(() => {
          if (isMarketOpen()) {
            loadData();
          }
        }, 60000);
      }
    } else {
      // Stop polling when hidden (resource optimization)
      if (intervalId) {
        clearInterval(intervalId);
        intervalId = null;
      }
    }
  };

  handleVisibilityChange();
  document.addEventListener('visibilitychange', handleVisibilityChange);

  return () => {
    if (intervalId) clearInterval(intervalId);
    document.removeEventListener('visibilitychange', handleVisibilityChange);
  };
}, []);
```

**Key Features**:
- Pauses polling when tab hidden (reduces backend load)
- Resumes immediately when tab becomes visible
- Checks market hours before each refresh via `isMarketOpen()` utility

**Alternatives Considered**:
- Simple setInterval without visibility: Rejected - wastes resources when tab hidden
- WebSocket for real-time updates: Rejected - adds infrastructure complexity, overkill for 60s refresh

### Asset Rendering Pattern (Reusable)

**Decision**: Use table-based layout with clickable rows

```typescript
{items.map((item) => (
  <tr
    key={item.id}
    onClick={() => navigate(`/asset/${item.asset_symbol}?exchange=${item.exchange}`)}
    className="watchlist-row"
  >
    <td className="description">
      <div className="description-with-tags">
        <span>{item.description || item.asset_symbol}</span>
        {/* Inline tag badges */}
        {item.labels?.map((label, idx) => (
          <span key={idx} className={`tag ${label === 'crypto' ? 'crypto' : ''}`}>
            {label}
          </span>
        ))}
      </div>
    </td>
    <td className="price">{formatPrice(item.current_price)}</td>
    <td className={item.variation_pct >= 0 ? 'positive' : 'negative'}>
      {formatVariation(item.variation_pct)}
    </td>
  </tr>
))}
```

**Alternatives Considered**:
- Card-based layout: Rejected - table provides better density for portfolio views
- Virtualized list: Rejected - not needed for target scale (100 items), adds complexity

---

## Research Task 2: React Router DOM v7+ Route Configuration

**Question**: How are routes configured in App.tsx for existing pages?

### Decision: Add Declarative Route in Routes Component

**Rationale**: Project uses React Router DOM v7+ with declarative routing. All routes are defined in `App.tsx` using `<Route>` elements within a single `<Routes>` wrapper.

### Implementation Pattern (from `App.tsx`):

```typescript
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import LongTermPositions from './pages/LongTermPositions';

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Navigation />
        <div className="app-container">
          <Sidebar />
          <main className="app-main">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/watchlist" element={<Watchlist />} />
              {/* ADD THIS LINE */}
              <Route path="/long-term" element={<LongTermPositions />} />
              <Route path="/alerts" element={<Alerts />} />
              {/* ... other routes */}
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  )
}
```

### Navigation Pattern

**Decision**: Add navigation link in Sidebar component (assuming it exists)

```typescript
import { useNavigate } from 'react-router-dom';

const navigate = useNavigate();

// Simple navigation to long-term positions page
navigate('/long-term');
```

**Path Convention**: Use `/long-term` (kebab-case, descriptive, aligns with existing `/available-funds`)

**Alternatives Considered**:
- `/watchlist/long-term`: Rejected - nesting implies parent-child relationship, not sibling views
- `/positions/long-term`: Rejected - creates new namespace, "positions" not used elsewhere
- `/ltm`: Rejected - abbreviation reduces discoverability

---

## Research Task 3: Stale Data Warning UI Patterns

**Question**: What's the best practice for displaying "stale data" warning indicators in asset lists?

### Decision: Icon + Tooltip Warning Indicator Next to Price

**Rationale**: Project uses emoji icons throughout (no external icon library). Stale data warnings should be:
1. Visually distinct but not alarming (info-level, not error-level)
2. Inline with the price field (contextual placement)
3. Include tooltip explaining the issue

### Implementation Pattern

**Visual Design**:
```typescript
{item.current_price !== null ? (
  <td className="price">
    {formatPrice(item.current_price)}
    {isStalePrice(item.added_at) && (
      <span className="stale-indicator" title="Price data may be outdated">
        ⚠️
      </span>
    )}
  </td>
) : (
  <td className="price">N/A</td>
)}
```

**CSS Styling** (following project's GitHub-dark theme):
```css
.stale-indicator {
  margin-left: 0.5rem;
  color: #d29922;
  font-size: 0.9rem;
  cursor: help;
  opacity: 0.8;
}

.stale-indicator:hover {
  opacity: 1;
}
```

**Stale Detection Logic**:
```typescript
const isStalePrice = (lastUpdated: string): boolean => {
  const now = new Date();
  const updated = new Date(lastUpdated);
  const diffMinutes = (now.getTime() - updated.getTime()) / (1000 * 60);
  return diffMinutes > 15; // 15 minutes threshold
};
```

**Alternatives Considered**:
- Red error icon: Rejected - too alarming, stale data is expected (delisted stocks, API outages)
- Background color change: Rejected - less accessible, harder to notice
- Toast notification: Rejected - transient, user might miss it
- Separate "Stale Data" section: Rejected - segregates assets unnecessarily

**Color Choice**: `#d29922` (warning orange) - matches project's dry-run status badges

---

## Research Task 4: Crypto Asset Badge UI Patterns

**Question**: How to display inline badges for asset differentiation?

### Decision: Inline Emoji Badge Next to Asset Description

**Rationale**: Project already uses inline tag badges in `Watchlist.tsx` with CSS styling. Crypto assets should display a recognizable badge that:
1. Uses emoji (consistent with project convention: 📊 for long-term, 📈 for TradingView)
2. Positioned inline with asset description
3. Uses project's established badge styling

### Implementation Pattern

**Visual Design**:
```typescript
<td className="description">
  <div className="description-with-tags">
    <span className="description-text">{item.description}</span>
    {/* Crypto badge for items with 'crypto' label */}
    {item.labels?.includes('crypto') && (
      <span className="badge badge-crypto">₿ Crypto</span>
    )}
    {/* Other inline tags */}
    <div className="tags-container">
      {item.labels
        ?.filter(label => label !== 'crypto') // Don't duplicate crypto badge
        .map((label, idx) => (
          <span key={idx} className={`tag ${label}`}>{label}</span>
        ))
      }
    </div>
  </div>
</td>
```

**CSS Styling** (extending existing `.badge` pattern):
```css
.badge-crypto {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
  border: 1px solid #f59e0b;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  margin-left: 0.5rem;
}
```

**Alternatives Considered**:
- Icon only (₿): Rejected - less clear for non-crypto users
- Text only ("Crypto"): Rejected - missing visual cue
- Pill badge: Rejected - existing tag styling uses rounded rectangles, not pills
- Separate column: Rejected - wastes horizontal space, crypto flag is secondary info

**Icon Choice**: ₿ (Bitcoin symbol) - universally recognizable for cryptocurrency

---

## Technology Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Component Structure** | Copy Watchlist.tsx, simplify | 80% code reuse, proven patterns |
| **State Management** | useState hooks | Simple, no global state needed |
| **Auto-Refresh** | Visibility-aware polling (60s) | Resource-efficient, proven pattern |
| **Routing** | Declarative route in App.tsx | Follows React Router v7+ conventions |
| **Route Path** | `/long-term` | Descriptive, follows kebab-case convention |
| **Stale Data UI** | ⚠️ icon + tooltip | Inline, accessible, info-level warning |
| **Crypto Badge UI** | ₿ Crypto inline badge | Follows existing badge pattern |
| **Stale Threshold** | 15 minutes | Balances sensitivity vs. false positives |
| **Icon Library** | Emoji (no external library) | Consistent with project convention |

---

## Implementation Checklist

### Frontend Component (LongTermPositions.tsx)

```typescript
// Essential imports (reuse from Watchlist.tsx)
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { watchlistService } from '../services/api';
import { isMarketOpen, formatPrice, formatVariation } from '../utils/marketHours';

// State structure
const [items, setItems] = useState<WatchlistItem[]>([]);
const [loading, setLoading] = useState(false);
const [error, setError] = useState<string | null>(null);

// Load function
const loadLongTermPositions = async () => {
  try {
    setLoading(true);
    const response = await watchlistService.getLongTermPositions();
    setItems(response.items);
    setError(null);
  } catch (err: any) {
    setError('Failed to load long-term positions');
    console.error(err);
  } finally {
    setLoading(false);
  }
};

// Auto-refresh with visibility detection (copy from Watchlist.tsx)
useEffect(() => { /* ... visibility pattern ... */ }, []);

// Render table with:
// - Stale price indicators (⚠️ icon when > 15 min old)
// - Crypto badges (₿ Crypto for items with 'crypto' label)
// - Clickable rows navigating to /asset/:symbol
```

### API Service Addition (api.ts)

```typescript
// Add to watchlistService object
getLongTermPositions: async (): Promise<WatchlistResponse> => {
  const response = await axios.get<WatchlistResponse>(
    `${API_BASE_URL}/api/watchlist/long-term`
  );
  return response.data;
},
```

### CSS Additions

**New classes needed**:
- `.stale-indicator`: Warning icon styling (color: `#d29922`)
- `.badge-crypto`: Crypto badge styling (color: `#f59e0b`)
- `.long-term-positions-page`: Page-specific wrapper (if needed)

**Reusable classes** (from existing CSS):
- `.watchlist-row`: Table row styling
- `.description-with-tags`: Layout for description + badges
- `.tags-container`: Tag list wrapper
- `.tag`: Individual tag styling
- `.positive` / `.negative`: Variation color classes

---

## Risks Identified & Mitigations

| Risk | Mitigation |
|------|-----------|
| Stale price threshold (15 min) too sensitive | Make threshold configurable via frontend constant; adjust based on user feedback |
| Crypto badge clutters UI with many labels | Test with mock data containing 3+ labels; adjust layout if needed |
| Visibility API not supported in old browsers | Graceful degradation: polling continues regardless (minor resource impact) |
| Auto-refresh conflicts with user interactions | Maintain scroll position after refresh (not implemented in current Watchlist.tsx, acceptable tradeoff) |

---

## Next Steps

1. **Phase 1 - Design**: Generate `data-model.md` and `contracts/long-term-positions.yaml`
2. **Phase 1 - Quickstart**: Generate `quickstart.md` with development instructions
3. **Phase 2 - Tasks**: Run `/speckit.tasks` to generate dependency-ordered implementation tasks
4. **Implementation**: Follow tasks.md step-by-step
5. **Testing**: Backend unit tests + manual frontend smoke test
6. **Deployment**: Deploy backend via `./deploy.sh`, build frontend with `npm run build`

---

## References

- **Existing Patterns**: `frontend/src/pages/Watchlist.tsx`, `frontend/src/pages/AssetDetail.tsx`
- **Router Configuration**: `frontend/src/App.tsx`
- **Styling**: `frontend/src/shared.css`, `frontend/src/pages/AssetDetail.css`
- **API Service**: `frontend/src/services/api.ts`
- **Utilities**: `frontend/src/utils/marketHours.ts`
- **Backend Service**: `api/services/watchlist_service.py` (lines 183-215 for filtering pattern)
- **Backend Router**: `api/routers/watchlist.py` (lines 74-88 for endpoint pattern)
