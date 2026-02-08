# Quickstart: SLWIN Tag Implementation

**Feature**: 007-slwin-tag - Stop Loss Win Tag for Watchlist
**Estimated Time**: 2-3 hours
**Difficulty**: Moderate

## Prerequisites

- [x] Specification completed and clarified (`spec.md`)
- [x] Implementation plan created (`plan.md`)
- [x] Research decisions documented (`research.md`)
- [x] Data model defined (`data-model.md`)
- [x] API contracts documented (`contracts/watchlist-slwin.yaml`)

**Development Environment**:
- Python 3.11+ with poetry installed
- Node.js 18+ with npm installed
- Backend running: `poetry run python run_api.py`
- Frontend running: `cd frontend && npm run dev`

## Implementation Checklist

### Phase 1: Backend Model (15 minutes)

#### 1.1 Add SLWIN enum value

**File**: `api/models/watchlist.py`

**Change**:
```python
class WatchlistTag(str, Enum):
    SHORT_TERM = "short-term"
    LONG_TERM = "long-term"
    CRYPTO = "crypto"
    HOMEPAGE = "homepage"
    SLWIN = "slwin"  # ADD THIS LINE
```

**Test**:
```bash
poetry run python -c "from api.models.watchlist import WatchlistTag; print(WatchlistTag.SLWIN.value)"
# Expected output: slwin
```

### Phase 2: Backend Service Logic (45 minutes)

#### 2.1 Update sorting logic

**File**: `api/services/watchlist_service.py`

**Location**: `_enrich_and_sort_watchlist` method, find the `sort_key` function

**Current code**:
```python
def sort_key(item: WatchlistItem) -> tuple:
    has_short_term = WatchlistTag.SHORT_TERM.value in item.labels
    description = item.description.lower() if item.description else ""
    return (0 if has_short_term else 1, description)
```

**Updated code**:
```python
def sort_key(item: WatchlistItem) -> tuple:
    has_short_term = WatchlistTag.SHORT_TERM.value in item.labels
    has_slwin = WatchlistTag.SLWIN.value in item.labels
    description = item.description.lower() if item.description else ""

    # Priority: 0=short-term, 1=slwin, 2=other
    if has_short_term:
        priority = 0
    elif has_slwin:
        priority = 1
    else:
        priority = 2

    return (priority, description)
```

#### 2.2 Update crypto filtering logic

**File**: `api/services/watchlist_service.py`

**Location**: `get_watchlist` method, find the crypto filtering section

**Current code** (around line 208):
```python
# Exclude crypto assets WITHOUT short-term tag
has_crypto = WatchlistTag.CRYPTO.value in labels
has_short_term = WatchlistTag.SHORT_TERM.value in labels
if has_crypto and not has_short_term:
    continue
```

**Updated code**:
```python
# Exclude crypto assets WITHOUT short-term OR slwin tag
has_crypto = WatchlistTag.CRYPTO.value in labels
has_short_term = WatchlistTag.SHORT_TERM.value in labels
has_slwin = WatchlistTag.SLWIN.value in labels
if has_crypto and not has_short_term and not has_slwin:
    continue
```

#### 2.3 Add mutual exclusivity enforcement

**File**: `api/services/watchlist_service.py`

**Location**: Add new private method near other helper methods

**New method**:
```python
def _enforce_tag_mutual_exclusivity(self, labels: List[str]) -> List[str]:
    """
    Enforce mutual exclusivity between SLWIN and SHORT_TERM tags.

    Args:
        labels: Requested labels array

    Returns:
        Filtered labels array with only one of SLWIN or SHORT_TERM
    """
    has_slwin = WatchlistTag.SLWIN.value in labels
    has_short_term = WatchlistTag.SHORT_TERM.value in labels

    # If both present, remove short-term (SLWIN takes precedence)
    if has_slwin and has_short_term:
        labels = [l for l in labels if l != WatchlistTag.SHORT_TERM.value]

    return labels
```

**Note**: This method should be called in the update labels flow. Check if `api/routers/watchlist.py` or `api/services/watchlist_service.py` has a method that handles label updates and add the call there. If the service already has a method like `update_labels`, add:

```python
# In update_labels or similar method
new_labels = self._enforce_tag_mutual_exclusivity(new_labels)
```

**Test backend**:
```bash
poetry run pytest tests/api/services/test_watchlist_service.py -v
```

### Phase 3: Frontend State Management (30 minutes)

#### 3.1 Add SLWIN state variable

**File**: `frontend/src/pages/AssetDetail.tsx`

**Location**: Find the state declarations (around line 37-40)

**Add after existing tag state variables**:
```typescript
const [isSLWIN, setIsSLWIN] = useState(false);
```

#### 3.2 Initialize SLWIN state from API

**File**: `frontend/src/pages/AssetDetail.tsx`

**Location**: In `checkWatchlistStatus` function (around line 130-137)

**Current code**:
```typescript
if (item) {
  setIsShortTerm(item.labels.includes('short-term'));
  setIsLongTerm(item.labels.includes('long-term'));
  setIsHomepage(item.labels.includes('homepage'));
}
```

**Updated code**:
```typescript
if (item) {
  setIsShortTerm(item.labels.includes('short-term'));
  setIsSLWIN(item.labels.includes('slwin'));
  setIsLongTerm(item.labels.includes('long-term'));
  setIsHomepage(item.labels.includes('homepage'));
}
```

#### 3.3 Reset SLWIN state when removing from watchlist

**File**: `frontend/src/pages/AssetDetail.tsx`

**Location**: In `handleToggleWatchlist` function (around line 346)

**Current code**:
```typescript
setIsShortTerm(false);
setIsLongTerm(false);
setIsHomepage(false);
```

**Updated code**:
```typescript
setIsShortTerm(false);
setIsSLWIN(false);
setIsLongTerm(false);
setIsHomepage(false);
```

### Phase 4: Frontend Toggle Button (30 minutes)

#### 4.1 Add SLWIN toggle handler

**File**: `frontend/src/pages/AssetDetail.tsx`

**Location**: Add after `handleToggleHomepage` function (around line 472)

**New function**:
```typescript
const handleToggleSLWIN = async () => {
  if (!symbol) return;

  try {
    setUpdatingLabel(true);
    setWatchlistError(null);
    setWatchlistSuccess(null);

    const [code] = symbol.split(':');
    const assetName = indicatorData?.description || symbol;

    // Build labels array: exclude short-term, toggle slwin, keep others
    const newLabels: string[] = [];
    if (isLongTerm) newLabels.push('long-term');
    if (isHomepage) newLabels.push('homepage');
    if (!isSLWIN) newLabels.push('slwin');

    await watchlistService.updateLabels(code, newLabels);

    setIsSLWIN(!isSLWIN);
    if (isShortTerm) setIsShortTerm(false);  // Update UI for mutual exclusivity

    const action = isSLWIN ? 'Removed from' : 'Added to';
    setWatchlistSuccess(`${action} SLWIN positions: ${assetName}`);

    setTimeout(() => setWatchlistSuccess(null), 3000);
  } catch (err: any) {
    const errorMessage = err.response?.data?.detail || 'Failed to update label';
    setWatchlistError(errorMessage);
    console.error('Label toggle error:', err);
    setTimeout(() => setWatchlistError(null), 5000);
  } finally {
    setUpdatingLabel(false);
  }
};
```

#### 4.2 Update short-term toggle to enforce mutual exclusivity

**File**: `frontend/src/pages/AssetDetail.tsx`

**Location**: In `handleToggleShortTerm` function (around line 386-389)

**Find this code**:
```typescript
// Build labels array keeping long-term if it exists, toggling short-term
const newLabels: string[] = [];
if (isLongTerm) newLabels.push('long-term');
if (!isShortTerm) newLabels.push('short-term');
```

**Update to**:
```typescript
// Build labels array: exclude slwin, toggle short-term, keep others
const newLabels: string[] = [];
if (isLongTerm) newLabels.push('long-term');
if (isHomepage) newLabels.push('homepage');
if (!isShortTerm) newLabels.push('short-term');
```

**Then after `setIsShortTerm(!isShortTerm);` add**:
```typescript
if (isSLWIN) setIsSLWIN(false);  // Update UI for mutual exclusivity
```

#### 4.3 Add SLWIN button to UI

**File**: `frontend/src/pages/AssetDetail.tsx`

**Location**: In the JSX return, find the button group (around line 544-570)

**Insert after the short-term button**:
```tsx
<button
  onClick={handleToggleSLWIN}
  disabled={updatingLabel || checkingWatchlist}
  className={`slwin-btn ${isSLWIN ? 'active' : ''}`}
>
  {updatingLabel
    ? isSLWIN
      ? 'Removing...'
      : 'Adding...'
    : isSLWIN
    ? '⭐ Close SLWIN Position'
    : '⭐ SLWIN Position'}
</button>
```

**Test frontend**:
1. Start backend: `poetry run python run_api.py`
2. Start frontend: `cd frontend && npm run dev`
3. Navigate to an asset detail page
4. Click SLWIN button, verify tag added
5. Click short-term button, verify SLWIN removed

### Phase 5: Sidebar Display (30 minutes)

#### 5.1 Update sidebar sorting detection

**File**: `frontend/src/components/Sidebar.tsx`

**Location**: In the watchlist items rendering (around line 184-188)

**Current code**:
```tsx
const isShortTerm = item.labels.includes('short-term');
const prevItem = index > 0 ? watchlistItems[index - 1] : null;
const prevIsShortTerm = prevItem?.labels.includes('short-term');
const showDivider = prevIsShortTerm && !isShortTerm;
```

**Updated code**:
```tsx
const isShortTerm = item.labels.includes('short-term');
const isSLWIN = item.labels.includes('slwin');
const prevItem = index > 0 ? watchlistItems[index - 1] : null;
const prevIsShortTerm = prevItem?.labels.includes('short-term');
const prevIsSLWIN = prevItem?.labels.includes('slwin');

// Show divider when transitioning from short-term to SLWIN or other
// OR when transitioning from SLWIN to other
const showDivider = (prevIsShortTerm && !isShortTerm) ||
                    (prevIsSLWIN && !isSLWIN && !isShortTerm);
```

**Test sidebar**:
1. Add SLWIN tag to multiple assets via asset detail page
2. Navigate to any page with sidebar
3. Verify SLWIN assets appear after short-term
4. Verify dividers appear correctly

### Phase 6: Testing (30 minutes)

#### 6.1 Backend unit tests

**File**: `tests/api/models/test_watchlist.py`

**Add test**:
```python
def test_watchlist_tag_enum_includes_slwin():
    """Test that SLWIN tag value exists in enum."""
    assert hasattr(WatchlistTag, 'SLWIN')
    assert WatchlistTag.SLWIN.value == 'slwin'
```

**File**: `tests/api/services/test_watchlist_service.py`

**Add tests**:
```python
def test_sort_key_with_slwin(self):
    """Test that SLWIN assets sort between short-term and untagged."""
    short_term_item = WatchlistItem(..., labels=['short-term'])
    slwin_item = WatchlistItem(..., labels=['slwin'])
    untagged_item = WatchlistItem(..., labels=[])

    items = [untagged_item, slwin_item, short_term_item]
    sorted_items = sorted(items, key=self.service._sort_key)

    assert sorted_items[0] == short_term_item
    assert sorted_items[1] == slwin_item
    assert sorted_items[2] == untagged_item

def test_mutual_exclusivity_enforcement(self):
    """Test that SLWIN and short-term cannot coexist."""
    labels = ['slwin', 'short-term', 'long-term']
    result = self.service._enforce_tag_mutual_exclusivity(labels)

    assert 'slwin' in result
    assert 'short-term' not in result
    assert 'long-term' in result
```

**Run tests**:
```bash
poetry run pytest tests/api/ -v
```

#### 6.2 Manual integration testing

**Test Scenario 1: Add SLWIN tag**
1. Navigate to asset detail page
2. Click "⭐ SLWIN Position" button
3. ✓ Button shows "⭐ Close SLWIN Position"
4. ✓ Success message appears
5. ✓ Asset appears in sidebar between short-term and untagged

**Test Scenario 2: Mutual exclusivity (SLWIN → Short-Term)**
1. Asset has SLWIN tag
2. Click "⭐ Short Term Position" button
3. ✓ SLWIN button reverts to "⭐ SLWIN Position"
4. ✓ Short-term button shows "⭐ Close Short Term Position"
5. ✓ Asset moves to short-term section in sidebar

**Test Scenario 3: Mutual exclusivity (Short-Term → SLWIN)**
1. Asset has short-term tag
2. Click "⭐ SLWIN Position" button
3. ✓ Short-term button reverts to "⭐ Short Term Position"
4. ✓ SLWIN button shows "⭐ Close SLWIN Position"
5. ✓ Asset moves to SLWIN section in sidebar

**Test Scenario 4: Crypto with SLWIN**
1. Navigate to crypto asset (e.g., Bitcoin)
2. Click "⭐ SLWIN Position" button
3. ✓ Asset appears in sidebar (not excluded)
4. ✓ Asset in SLWIN section, not hidden

**Test Scenario 5: Sidebar dividers**
1. Create mix of short-term, SLWIN, and untagged assets
2. View sidebar
3. ✓ Divider between short-term and SLWIN sections
4. ✓ Divider between SLWIN and untagged sections

### Phase 7: Code Quality (15 minutes)

#### 7.1 Format and lint backend

```bash
poetry run black api/ tests/api/
poetry run isort api/ tests/api/
poetry run mypy api/
poetry run flake8 api/
```

#### 7.2 Format and lint frontend

```bash
cd frontend
npm run lint
npm run build  # Verify TypeScript compiles
cd ..
```

#### 7.3 Run full test suite

```bash
poetry run pytest --cov=api tests/api/
```

## Deployment

### Local Testing

1. **Start backend**: `poetry run python run_api.py`
2. **Start frontend**: `cd frontend && npm run dev`
3. **Test all scenarios** from Phase 6.2

### Production Deployment

```bash
# Commit changes
git add .
git commit -m "feat: add SLWIN tag to watchlist

- Add SLWIN (Stop Loss Win) enum value to WatchlistTag
- Implement mutual exclusivity with short-term tag
- Update sorting to place SLWIN between short-term and untagged
- Add SLWIN toggle button on asset detail page
- Update crypto filtering to include SLWIN override
- Add sidebar dividers for SLWIN section

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# Deploy to production
./deploy.sh
```

## Troubleshooting

### Issue: Button doesn't toggle

**Symptom**: Clicking SLWIN button shows loading state but doesn't update

**Solution**:
- Check browser console for API errors
- Verify backend is running: `curl http://localhost:8000/api/watchlist`
- Check `updatingLabel` state isn't stuck as `true`

### Issue: Tags conflict persists

**Symptom**: Both SLWIN and short-term buttons show active

**Solution**:
- Check backend mutual exclusivity logic is called
- Verify frontend re-fetches watchlist status after update
- Clear browser cache and reload

### Issue: Sidebar sorting wrong

**Symptom**: SLWIN assets appear in wrong position

**Solution**:
- Verify backend `sort_key` function updated correctly
- Check backend returns items in correct order: `GET /api/watchlist`
- Verify frontend doesn't re-sort after receiving data

### Issue: Crypto asset not appearing

**Symptom**: Crypto asset with SLWIN tag hidden in sidebar

**Solution**:
- Check backend crypto filtering logic includes `has_slwin` check
- Verify asset has both 'crypto' and 'slwin' labels
- Check asset doesn't have 'long-term' tag (takes precedence)

## Success Criteria

- ✅ Backend tests pass
- ✅ Frontend builds without TypeScript errors
- ✅ SLWIN button toggles tag on/off
- ✅ Mutual exclusivity enforced (SLWIN ↔ Short-Term)
- ✅ Sidebar displays SLWIN assets in correct position
- ✅ Dividers appear between tag sections
- ✅ Crypto assets with SLWIN tag appear in sidebar
- ✅ Code formatted and linted
- ✅ All manual test scenarios pass

## Estimated Time Breakdown

| Phase | Task | Time |
|-------|------|------|
| 1 | Backend Model | 15 min |
| 2 | Backend Service Logic | 45 min |
| 3 | Frontend State Management | 30 min |
| 4 | Frontend Toggle Button | 30 min |
| 5 | Sidebar Display | 30 min |
| 6 | Testing | 30 min |
| 7 | Code Quality | 15 min |
| **Total** | | **~3 hours** |

## Next Steps

After completing implementation:

1. ✅ Run `/speckit.tasks` to generate task breakdown
2. ✅ Create pull request with changes
3. ✅ Request code review
4. ✅ Deploy to production via `./deploy.sh`
5. Monitor user feedback and usage patterns

## Related Documentation

- Feature Spec: `specs/007-slwin-tag/spec.md`
- Implementation Plan: `specs/007-slwin-tag/plan.md`
- Research: `specs/007-slwin-tag/research.md`
- Data Model: `specs/007-slwin-tag/data-model.md`
- API Contract: `specs/007-slwin-tag/contracts/watchlist-slwin.yaml`
