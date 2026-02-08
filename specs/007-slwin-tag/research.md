# Research: SLWIN Tag Implementation

**Feature**: 007-slwin-tag
**Date**: 2026-02-08
**Research Phase**: Phase 0

## Overview

This document captures research findings and technical decisions for implementing the SLWIN (Stop Loss Win) tag feature in the watchlist system.

## Technical Decisions

### Decision 1: Backend Tag Enforcement Strategy

**Decision**: Implement mutual exclusivity enforcement in the backend service layer using tag filtering before DynamoDB write operations.

**Rationale**:
- Backend enforcement ensures data integrity regardless of client source (web UI, API calls, scripts)
- Service layer is the appropriate place for business logic per Layered Architecture Discipline
- DynamoDB doesn't support conditional writes based on array element inspection
- Simple implementation: filter out conflicting tags before writing new labels array

**Alternatives Considered**:
- **Frontend-only validation**: Rejected because direct API calls would bypass the rule
- **DynamoDB conditional writes**: Rejected because DynamoDB conditions can't inspect array elements for specific values
- **API Gateway validation**: Rejected because business logic belongs in service layer, not gateway

**Implementation Pattern**:
```python
def update_labels(asset_id: str, new_labels: List[str]):
    # Remove conflicting tags
    if "slwin" in new_labels and "short-term" in new_labels:
        new_labels = [l for l in new_labels if l != "short-term"]
    elif "short-term" in new_labels and "slwin" in existing_labels:
        new_labels = [l for l in new_labels if l != "slwin"]

    # Write to DynamoDB
    dynamodb_client.update_watchlist_labels(asset_id, new_labels)
```

### Decision 2: Concurrency Handling Strategy

**Decision**: Use last-write-wins with DynamoDB's native transaction handling.

**Rationale**:
- DynamoDB automatically handles concurrent writes with last-write-wins semantics
- Tag toggle operations are idempotent (toggling same tag twice returns to original state)
- Race condition impact is minimal: worst case is one user's toggle gets overwritten by another
- Adds no complexity: relies on DynamoDB's built-in behavior
- Consistent with existing watchlist update behavior

**Alternatives Considered**:
- **Optimistic locking with version numbers**: Rejected as over-engineering for low-risk operations
- **Request queuing per asset**: Rejected as unnecessary complexity and potential performance bottleneck
- **First-write-wins with rejection**: Rejected because retry logic burden on clients

### Decision 3: Sidebar Sorting Algorithm

**Decision**: Extend existing sort_key function to include SLWIN as middle priority between short-term and untagged.

**Rationale**:
- Existing code uses tuple-based sorting: `(priority, description)`
- Clean extension: `(0 if short-term else 1 if slwin else 2, description)`
- Maintains alphabetical sorting within each category
- Single sort operation, no multiple passes
- Follows existing pattern from `watchlist_service.py`

**Implementation Pattern**:
```python
def sort_key(item: WatchlistItem) -> tuple:
    has_short_term = WatchlistTag.SHORT_TERM.value in item.labels
    has_slwin = WatchlistTag.SLWIN.value in item.labels
    description = item.description.lower() if item.description else ""

    # Priority: 0=short-term, 1=slwin, 2=untagged
    priority = 0 if has_short_term else (1 if has_slwin else 2)
    return (priority, description)
```

**Alternatives Considered**:
- **Multiple sort passes**: Rejected as inefficient and harder to maintain
- **Separate lists concatenated**: Rejected as more complex than single sort
- **Database-level sorting**: Rejected because DynamoDB doesn't support computed sort on labels array

### Decision 4: Crypto Asset Filtering with SLWIN

**Decision**: Modify existing crypto filter logic to include SLWIN-tagged crypto assets (in addition to short-term).

**Rationale**:
- Clarification result: SLWIN overrides crypto exclusion (like short-term does)
- Current logic: exclude crypto unless has short-term tag
- Updated logic: exclude crypto unless has short-term OR slwin tag
- Minimal change to existing filtering in `get_watchlist()` method

**Implementation Pattern**:
```python
# Current code:
has_crypto = WatchlistTag.CRYPTO.value in labels
has_short_term = WatchlistTag.SHORT_TERM.value in labels
if has_crypto and not has_short_term:
    continue

# Updated code:
has_crypto = WatchlistTag.CRYPTO.value in labels
has_short_term = WatchlistTag.SHORT_TERM.value in labels
has_slwin = WatchlistTag.SLWIN.value in labels
if has_crypto and not has_short_term and not has_slwin:
    continue
```

**Alternatives Considered**:
- **Separate crypto filtering flag**: Rejected as more complex than simple OR condition
- **New crypto+slwin tag combination**: Rejected as unnecessary new tag

### Decision 5: Frontend Button Styling

**Decision**: Reuse existing tag button styles with new class `.slwin-btn` for potential future customization.

**Rationale**:
- Existing buttons: `.short-term-btn`, `.long-term-btn`, `.homepage-btn`
- Consistent visual language maintains user experience
- CSS class naming pattern already established
- Active/inactive states follow same pattern: `active` class added when tag present

**Implementation Pattern**:
```tsx
<button
  onClick={handleToggleSLWIN}
  disabled={updatingLabel || checkingWatchlist}
  className={`slwin-btn ${isSLWIN ? 'active' : ''}`}
>
  {updatingLabel
    ? isSLWIN ? 'Removing...' : 'Adding...'
    : isSLWIN ? '⭐ Close SLWIN Position' : '⭐ SLWIN Position'}
</button>
```

**Alternatives Considered**:
- **Custom icon instead of ⭐**: Rejected for consistency with existing buttons
- **Different color scheme**: Rejected; keep consistent with other tag buttons
- **Tooltip with "Stop Loss Win" explanation**: Deferred to future enhancement

### Decision 6: Sidebar Visual Separator

**Decision**: Add divider between SLWIN and untagged sections using existing `.watchlist-divider` class.

**Rationale**:
- Existing divider already used between short-term and other assets
- Same visual pattern maintains consistency
- CSS class already defined in `Sidebar.css`
- Logic pattern: show divider when transitioning from SLWIN to non-SLWIN

**Implementation Pattern**:
```tsx
const isSLWIN = item.labels.includes('slwin');
const prevItem = index > 0 ? watchlistItems[index - 1] : null;
const prevIsSLWIN = prevItem?.labels.includes('slwin');
const showDivider = prevIsSLWIN && !isSLWIN && !isShortTerm;
```

**Alternatives Considered**:
- **No visual separator**: Rejected; users need visual grouping cues
- **Different divider style for SLWIN**: Rejected for consistency
- **Section headers instead of dividers**: Rejected as more visual clutter

## Technology Best Practices

### DynamoDB Label Updates

**Best Practice**: Use DynamoDB's `update_item` with SET operation on labels attribute.

**Reasoning**:
- Atomic operation ensures consistency
- SET operation replaces entire labels array (simpler than ADD/DELETE on sets)
- Existing `dynamodb_client.update_watchlist_labels()` method already implements this pattern
- No schema migration needed (labels already supports arbitrary strings)

### React State Management for Tags

**Best Practice**: Use separate boolean state variables for each tag (`isShortTerm`, `isSLWIN`, `isLongTerm`).

**Reasoning**:
- Existing pattern in `AssetDetail.tsx` already uses this approach
- Simple and readable: `setIsSLWIN(!isSLWIN)`
- Enables independent toggle logic for each tag
- No complex state reducer needed for this use case

### TypeScript Type Safety

**Best Practice**: Extend existing `WatchlistItem` interface (if `slwin` needs explicit typing) or rely on labels array.

**Reasoning**:
- Current interface uses `labels: string[]` for flexibility
- Backend enum provides type safety in Python
- Frontend validates by checking array membership: `labels.includes('slwin')`
- No TypeScript interface change needed

## Integration Patterns

### Backend-Frontend Contract

**Pattern**: Existing `updateLabels` API endpoint handles all label updates.

**Endpoint**: `PUT /api/watchlist/{asset_id}/labels`
**Request Body**: `{ "labels": ["slwin", "long-term"] }`
**Response**: `{ "message": "...", "asset_id": "...", "labels": [...] }`

**Integration Notes**:
- Frontend constructs full labels array client-side before sending
- Backend enforces mutual exclusivity during processing
- No new API endpoint needed
- Existing `watchlistService.updateLabels()` method in frontend services

### Testing Strategy

**Unit Tests (Backend)**:
- Test `WatchlistTag.SLWIN` enum value exists
- Test mutual exclusivity enforcement in service layer
- Test sorting algorithm with SLWIN assets in various positions
- Test crypto filtering includes SLWIN exception

**Integration Tests (Backend)**:
- Test API endpoint enforces mutual exclusivity on label updates
- Test concurrent updates handled correctly (last-write-wins)
- Test watchlist retrieval returns SLWIN assets in correct order

**Manual Testing (Frontend)**:
- Test button toggle adds/removes SLWIN tag
- Test button disabled during update
- Test sidebar displays SLWIN assets in correct position
- Test divider appears between SLWIN and untagged sections
- Test short-term toggle removes SLWIN tag and vice versa

## Migration & Rollout

### Data Migration

**Decision**: No data migration required.

**Reasoning**:
- New tag value, not a schema change
- Existing watchlist items without SLWIN tag continue working
- DynamoDB labels field already supports arbitrary strings
- Backward compatible: old code ignores unknown tag values

### Rollout Strategy

**Decision**: Standard deployment via `./deploy.sh`, no feature flag needed.

**Reasoning**:
- Low risk: purely additive feature
- No breaking changes to existing functionality
- Users opt-in by clicking new button
- Existing short-term/long-term tags unaffected

### Rollback Plan

**Plan**: If issues arise, remove SLWIN enum value and redeploy.

**Reasoning**:
- Existing assets with "slwin" label will be ignored (treated as untagged)
- No data corruption risk
- Simple code revert
- DynamoDB data can stay as-is (labels array with "slwin" harmless)

## Open Questions & Risks

### Resolved During Clarification

- ✅ SLWIN meaning: Stop Loss Win
- ✅ API enforcement: Backend auto-removes conflicting tags
- ✅ Concurrency: Last-write-wins with DynamoDB transactions
- ✅ Crypto filtering: SLWIN overrides exclusion
- ✅ Button labels: "⭐ SLWIN Position" / "⭐ Close SLWIN Position"

### Remaining Risks

**Low Risk**:
- Race condition between short-term and SLWIN toggles: Accepted (last write wins)
- User confusion about SLWIN acronym: Mitigated by clear button text
- Visual clutter with three tag types: Accepted (design constraint)

**Mitigation**:
- Add tooltip with "Stop Loss Win" definition (future enhancement)
- Monitor user feedback after rollout
- Consider A/B testing button text if confusion reported

## References

### Existing Code Patterns

- **Tag enumeration**: `api/models/watchlist.py` - `WatchlistTag` enum
- **Mutual exclusivity logic**: `frontend/src/pages/AssetDetail.tsx` - `handleToggleShortTerm`, `handleToggleLongTerm`
- **Sorting logic**: `api/services/watchlist_service.py` - `_enrich_and_sort_watchlist` method
- **Sidebar rendering**: `frontend/src/components/Sidebar.tsx` - divider logic at line 186-192
- **Backend service**: `api/services/watchlist_service.py` - `get_watchlist` method with crypto filtering

### External Documentation

- DynamoDB Update Item: https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_UpdateItem.html
- React useState Hook: https://react.dev/reference/react/useState
- TypeScript Arrays: https://www.typescriptlang.org/docs/handbook/2/everyday-types.html#arrays

## Summary

All technical decisions have been made based on existing code patterns, constitution principles, and clarification results. The implementation follows established conventions in the codebase:

- Backend service layer enforces business rules
- DynamoDB handles concurrency with last-write-wins
- Frontend follows existing toggle button patterns
- Sorting extends current tuple-based algorithm
- No schema migrations or infrastructure changes needed

**Ready for Phase 1**: Design & Contracts
