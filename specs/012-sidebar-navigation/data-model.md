# Data Model: Sidebar Navigation

**Feature**: 012-sidebar-navigation
**Date**: 2026-02-23

## Overview

This feature has no backend data model changes. The only persistent state is a single browser-side preference stored in `localStorage`.

---

## Browser Storage

### `localStorage` key: `nav_collapsed`

| Field | Type | Values | Default (key absent) |
|-------|------|--------|----------------------|
| `nav_collapsed` | string | `"true"` \| `"false"` | `"true"` (collapsed) |

**Reading**:
```ts
const navCollapsed: boolean = localStorage.getItem('nav_collapsed') !== 'false';
// absent key  → 'false' !== 'false' is false → wait, let me re-check
// absent key  → getItem returns null → null !== 'false' → true  ✓ (collapsed)
// stored 'false' → 'false' !== 'false' → false ✓ (expanded)
// stored 'true'  → 'true'  !== 'false' → true  ✓ (collapsed)
```

**Writing**:
```ts
localStorage.setItem('nav_collapsed', String(nextCollapsed));
```

---

## React Component State

### `Sidebar` component state additions

| State variable | Type | Source of truth | Notes |
|----------------|------|-----------------|-------|
| `navCollapsed` | `boolean` | `localStorage.nav_collapsed` | `true` by default (absent key) |

### Existing state (unchanged)

| State variable | Type | Notes |
|----------------|------|-------|
| `watchlistItems` | `WatchlistItem[]` | Unchanged |
| `loading` | `boolean` | Unchanged |
| `error` | `string \| null` | Unchanged |
| `lastLoadTime` | `number` | Unchanged |

---

## No backend / API model changes

This feature requires no:
- New DynamoDB tables or attributes
- New Pydantic models
- New TypeScript API interfaces
- Changes to `frontend/src/services/api.ts`
