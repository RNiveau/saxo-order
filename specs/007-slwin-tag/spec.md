# Feature Specification: SLWIN Tag for Watchlist

**Feature Branch**: `007-slwin-tag`
**Created**: 2026-02-08
**Status**: Draft
**Input**: User description: "analyse the sort term tag behavior. Based on this one, I want a SLWIN new tag. When I select it, it desactives the short term tag if it exists. In the side bar watchlist, SLWIN assets are after short term and before the other"

## Clarifications

### Session 2026-02-08

- Q: What does the acronym "SLWIN" stand for or represent? → A: Stop loss win
- Q: How should the API handle direct attempts to add short-term when SLWIN exists (or vice versa)? → A: API auto-removes conflicting tag (enforces rule server-side). Everything is managed in the backend, nothing in the frontend
- Q: What strategy should handle concurrent tag updates on the same asset? → A: Last write wins (database transaction handles conflicts)
- Q: Should crypto assets with SLWIN tag be included or excluded from the sidebar? → A: Include crypto assets with SLWIN (SLWIN overrides crypto exclusion)
- Q: What should the SLWIN toggle button display? → A: "⭐ SLWIN Position" (active) / "⭐ Close SLWIN Position" (inactive)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Add SLWIN Tag to Asset (Priority: P1)

As a trader, I want to mark assets with a SLWIN (Stop Loss Win) tag so I can categorize and track a specific subset of positions separate from short-term positions.

**Why this priority**: Core functionality that enables the primary use case - categorizing assets with a new SLWIN classification. Without this, the feature provides no value.

**Independent Test**: Can be fully tested by navigating to an asset detail page, clicking the SLWIN toggle button, and verifying the asset is tagged with SLWIN label in the database.

**Acceptance Scenarios**:

1. **Given** an asset is in the watchlist without any tags, **When** I click the SLWIN toggle button, **Then** the asset receives the SLWIN label
2. **Given** an asset is in the watchlist with the short-term tag, **When** I click the SLWIN toggle button, **Then** the asset receives the SLWIN label AND the short-term tag is automatically removed
3. **Given** an asset is in the watchlist with the long-term tag, **When** I click the SLWIN toggle button, **Then** the asset receives the SLWIN label AND the long-term tag is preserved
4. **Given** an asset has the SLWIN tag, **When** I click the SLWIN toggle button again, **Then** the SLWIN tag is removed from the asset
5. **Given** an asset has the SLWIN tag, **When** I click the short-term toggle button, **Then** the SLWIN tag is removed from the asset

---

### User Story 2 - View SLWIN Assets in Sidebar (Priority: P2)

As a trader, I want SLWIN-tagged assets to appear in a specific section of the sidebar watchlist so I can quickly identify them between short-term positions and other assets.

**Why this priority**: Provides visual organization and quick access to SLWIN assets. Depends on P1 to have SLWIN-tagged assets to display.

**Independent Test**: Can be fully tested by tagging multiple assets with SLWIN, navigating to any page with the sidebar, and verifying SLWIN assets appear after short-term assets but before untagged assets.

**Acceptance Scenarios**:

1. **Given** the watchlist contains short-term, SLWIN, and untagged assets, **When** I view the sidebar, **Then** assets appear in this order: short-term first, SLWIN second, untagged last
2. **Given** the watchlist contains only SLWIN-tagged assets, **When** I view the sidebar, **Then** all SLWIN assets are visible in alphabetical order
3. **Given** a visual separator exists between short-term and other assets, **When** SLWIN assets are present, **Then** a separator appears between SLWIN and untagged assets

---

### User Story 3 - Mutually Exclusive Short-Term and SLWIN Tags (Priority: P1)

As a trader, I want the SLWIN tag to be mutually exclusive with the short-term tag so assets can only belong to one of these primary categories at a time.

**Why this priority**: Enforces business logic that prevents confusion and maintains clear asset categorization. Critical for data integrity.

**Independent Test**: Can be fully tested by attempting to add both tags to the same asset and verifying the system only allows one at a time.

**Acceptance Scenarios**:

1. **Given** an asset has the short-term tag, **When** I add the SLWIN tag, **Then** the short-term tag is automatically removed
2. **Given** an asset has the SLWIN tag, **When** I add the short-term tag, **Then** the SLWIN tag is automatically removed
3. **Given** an asset has both long-term and SLWIN tags, **When** I add the short-term tag, **Then** the long-term tag is preserved but SLWIN is removed

---

### Edge Cases

- **Direct API calls with conflicting tags**: When an asset has SLWIN tag and the API receives a request to add short-term tag (or vice versa), the backend automatically removes the conflicting tag before adding the new one
- **Concurrent tag updates**: When multiple requests attempt to modify tags on the same asset simultaneously, the system uses a last-write-wins strategy with database transaction handling to resolve conflicts
- What happens when an asset with SLWIN tag is removed from the watchlist and re-added?
- How does the sorting behave when no assets have any tags?
- What happens if an asset has SLWIN tag but the frontend doesn't recognize it in an older version?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support a new "SLWIN" tag that can be assigned to watchlist assets
- **FR-002**: System MUST provide a UI toggle button on the asset detail page to add/remove the SLWIN tag (button displays "⭐ SLWIN Position" when inactive, "⭐ Close SLWIN Position" when active)
- **FR-003**: System MUST automatically remove the short-term tag when the SLWIN tag is added to an asset (enforced at API/backend level)
- **FR-004**: System MUST automatically remove the SLWIN tag when the short-term tag is added to an asset (enforced at API/backend level)
- **FR-014**: Backend API MUST enforce mutual exclusivity between SLWIN and short-term tags for all label update operations, regardless of client source
- **FR-015**: System MUST handle concurrent tag updates using last-write-wins strategy with database transaction management
- **FR-005**: System MUST allow SLWIN and long-term tags to coexist on the same asset
- **FR-006**: System MUST allow SLWIN and homepage tags to coexist on the same asset
- **FR-007**: System MUST allow SLWIN and crypto tags to coexist on the same asset
- **FR-008**: System MUST display SLWIN-tagged assets in the sidebar watchlist after short-term assets but before untagged assets
- **FR-009**: System MUST sort SLWIN-tagged assets alphabetically by description within their section
- **FR-010**: System MUST visually indicate the SLWIN tag status on the asset detail page through button state (active/inactive styling consistent with other tag buttons)
- **FR-011**: System MUST persist SLWIN tag changes to the database
- **FR-012**: System MUST include SLWIN-tagged assets in the main watchlist view unless they also have the long-term tag
- **FR-013**: System MUST include crypto assets with SLWIN tag in the sidebar (SLWIN tag overrides the standard crypto exclusion rule)

### Key Entities

- **WatchlistTag**: Enumeration of available tags including the new SLWIN tag value
- **WatchlistItem**: Representation of an asset in the watchlist with associated labels/tags
- **Label Update**: Operation that modifies the set of tags on a watchlist asset, enforcing mutual exclusivity rules

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can successfully toggle the SLWIN tag on any watchlist asset within 2 seconds
- **SC-002**: SLWIN-tagged assets consistently appear in the correct position in the sidebar watchlist (after short-term, before untagged)
- **SC-003**: Short-term and SLWIN tags are never simultaneously present on the same asset
- **SC-004**: Tag updates persist correctly with 100% reliability across sessions
- **SC-005**: The SLWIN toggle button provides clear visual feedback of the current state (active/inactive)

## Assumptions

1. The SLWIN tag follows the same UI/UX patterns as existing tags (short-term, long-term, homepage)
2. SLWIN stands for "Stop Loss Win" and represents positions where stop-loss has been triggered with a winning outcome
3. SLWIN tag overrides crypto exclusion rules - crypto assets with SLWIN tag are included in the sidebar (unlike standard crypto filtering)
4. The existing visual separator pattern between tag groups can be reused for SLWIN sections
5. The SLWIN tag does not require any special icons or colors beyond standard tag styling
6. The mutual exclusivity rule only applies between SLWIN and short-term, not other tags
7. Backend API already supports adding arbitrary string labels without schema changes

## Out of Scope

- Bulk operations to convert short-term assets to SLWIN or vice versa
- Historical tracking of when assets switched between SLWIN and short-term categories
- Custom sorting options for SLWIN assets beyond alphabetical
- Migration tools to automatically categorize existing assets as SLWIN
- Analytics or reporting on SLWIN asset performance
- Different visual styling or icons for SLWIN compared to other tags
