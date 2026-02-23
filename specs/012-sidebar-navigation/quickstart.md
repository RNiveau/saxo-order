# Quickstart: Sidebar Navigation (012)

## Prerequisites

- Node 20+ installed
- Backend API running (for watchlist data — optional for testing the toggle itself)

## Run the frontend

```bash
cd frontend
npm install        # if not already done
npm run dev        # starts Vite dev server on http://localhost:5173
```

## Manual test checklist

### US3 — Nav section collapse

1. **Default state**: Open the app in a fresh browser (or clear localStorage). The nav link list should be **hidden** and the watchlist section should occupy most of the sidebar.

2. **Expand nav**: Click the "Navigation ▼" header. The nav link list animates open, revealing all 9 links.

3. **Collapse nav**: Click the header again. The nav list animates closed.

4. **Persistence**: Expand the nav, then reload the page (`F5`). The nav section should remain expanded (localStorage stores `"false"`). Collapse it, reload — it should remain collapsed.

5. **Watchlist unaffected**: While toggling the nav section, verify the Live Watchlist section continues to refresh (check network tab — a `GET /watchlist` request fires every 60 seconds while market is open regardless of nav state).

6. **Layout check**: Toggling the nav section should not change the sidebar width (inspect element → always 300 px) and the main content area margin should stay at 300 px.

7. **Keyboard**: Tab to the "Navigation" toggle button, press `Enter` or `Space` — nav should toggle. Focus should remain on the button.

### localStorage verification

Open DevTools → Application → Local Storage → `http://localhost:5173`:

| Action | Expected `nav_collapsed` value |
|--------|-------------------------------|
| Fresh load (key absent) | *(not set)* — nav is collapsed |
| Click to expand | `"false"` |
| Click to collapse | `"true"` |

### Existing behaviour smoke test

1. Each of the 9 nav links navigates to the correct page
2. Active link is highlighted (blue left border + blue text)
3. Watchlist items display price, variation, and stale indicator (⏰) when data > 60s old
4. Short-term / slwin divider renders correctly

## Build verification

```bash
cd frontend
npm run build    # TypeScript must compile without errors
npm run lint     # ESLint must pass
```
