# Plan for Issue #451: Bad TradingView Link

## Problem Analysis
The TradingView link generation currently uses a simple mapping of Saxo country codes to TradingView exchanges (in `frontend/src/utils/tradingview.ts`). However, some assets have different trigrams between Saxo and TradingView, leading to incorrect links.

## Solution Architecture

### Infrastructure Changes ✅ COMPLETED

1. ✅ **Create new DynamoDB table** (`pulumi/dynamodb.py`)
   - Add `asset_details_table()` function
   - Table name: `asset_details`
   - Hash key: `asset_id` (string) - the Saxo asset code
   - Attributes: asset_id, asset_symbol, tradingview_url, updated_at
   - Billing mode: PAY_PER_REQUEST (like existing tables)

2. ✅ **Update Pulumi stack** (`pulumi/__main__.py`)
   - Import and create the asset_details table
   - Export table name/ARN if needed

3. ✅ **Update IAM policies** (`pulumi/iam.py`)
   - Grant Lambda read/write access to asset_details table
   - Add to existing DynamoDB policy statements

**Commit:** `5b5cee9` - feat: add asset_details DynamoDB table for TradingView links

---

### Backend Changes - Data Layer ✅ COMPLETED

4. ✅ **Extend AWS client** (`client/aws_client.py`)
   - Added methods to DynamoDBClient class:
     - `set_asset_detail()` - Store/update TradingView link with timestamp
     - `get_asset_detail()` - Returns full detail dict or None
     - `get_tradingview_link()` - Convenience method to get just the URL

---

### Backend Changes - API Layer ✅ COMPLETED

5. ✅ **Add data models** (`api/models/tradingview.py` - new file)
   - `SetTradingViewLinkRequest` - Request body for setting URL
   - `SetTradingViewLinkResponse` - Success response
   - `AssetDetailResponse` - Asset details with optional TradingView URL

6. ✅ **Create router** (`api/routers/tradingview.py` - new file)
   - `PUT /api/asset-details/{asset_id}/tradingview` - set/update link
   - `GET /api/asset-details/{asset_id}` - get asset details

7. ✅ **Register router** (`api/main.py`)
   - Imported and included the tradingview router

8. ✅ **Update existing endpoints** to include tradingview_url:
   - `api/models/indicator.py`: Added optional `tradingview_url` field to `AssetIndicatorsResponse`
   - `api/services/indicator_service.py`: Query DynamoDB for link in `get_asset_indicators()`
   - `api/routers/indicator.py`: Pass DynamoDB client to service
   - `api/models/watchlist.py`: Added optional `tradingview_url` field to `WatchlistItem`
   - `api/services/watchlist_service.py`: Query DynamoDB for link in `_enrich_asset()`

**Commits:**
- `82171c3` - feat: add backend API for custom TradingView links
- `2dd695d` - refactor: move AssetDetailResponse to separate module
- `669d3c3` - refactor: separate asset_details and tradingview routers
- `f04ef93` - refactor: consolidate DynamoDB client dependencies

**PR:** https://github.com/RNiveau/saxo-order/pull/463

---

### Frontend Changes ✅ COMPLETED

9. ✅ **Update API client** (`frontend/src/services/api.ts`)
   - Added `tradingViewService.setTradingViewLink(assetId: string, url: string)` function
   - Updated `AssetIndicatorsResponse` interface to include optional `tradingview_url?: string`
   - Updated `WatchlistItem` interface to include optional `tradingview_url?: string`
   - Added `SetTradingViewLinkResponse` interface

10. ✅ **Update TradingView utility** (`frontend/src/utils/tradingview.ts`)
    - Modified signature: `getTradingViewUrl(assetSymbol: string, customUrl?: string)`
    - Returns customUrl if provided, otherwise falls back to default mapping logic

11. ✅ **Update IndicatorCard** (`frontend/src/components/IndicatorCard.tsx`)
    - Updated TradingView link to use `getTradingViewUrl(indicators.asset_symbol, indicators.tradingview_url)`
    - Added edit button (✏️) next to TradingView link
    - Created modal component for editing TradingView URL:
      - Input field for URL with placeholder
      - Save/Cancel buttons with loading states
      - API call to save the URL using `tradingViewService`
      - Error message display
    - Added CSS styling in `IndicatorCard.css` for modal and edit button

12. ✅ **Update AssetDetail page** (`frontend/src/pages/AssetDetail.tsx`)
    - Added `onTradingViewUrlUpdated` callback to IndicatorCard
    - Updates local state when URL is changed

13. ✅ **Update Watchlist** (`frontend/src/pages/Watchlist.tsx`)
    - Updated to use `getTradingViewUrl(item.asset_symbol, item.tradingview_url)` for TradingView links
    - Fixed CSS styling in `Watchlist.css` for proper table layout

---

## Implementation Order

1. ✅ **Infrastructure** (DynamoDB table, IAM policies, Pulumi deployment) - COMPLETED
2. ✅ **Backend data layer** (AWS client methods) - COMPLETED
3. ✅ **Backend API** (models, router, service updates) - COMPLETED
4. ✅ **Frontend API client** updates - COMPLETED
5. ✅ **Frontend UI** (modal, link updates) - COMPLETED

## Progress Summary

**Completed:**
- ✅ Infrastructure setup with DynamoDB table
- ✅ Complete backend API implementation
- ✅ All backend tests passing
- ✅ Backend PR created: https://github.com/RNiveau/saxo-order/pull/463
- ✅ Complete frontend implementation
  - API client with TradingView service
  - TradingView utility with custom URL support
  - IndicatorCard with edit modal
  - AssetDetail page integration
  - Watchlist custom URL support
  - All CSS styling completed

**Status:** Feature fully implemented and ready for testing

---

## Related Files

### Infrastructure
- `pulumi/dynamodb.py` - ✅ Table definition
- `pulumi/__main__.py` - ✅ Stack configuration
- `pulumi/iam.py` - ✅ IAM policies (already handles dynamic table list)

### Backend
- `client/aws_client.py` - ✅ DynamoDB client methods
- `api/models/tradingview.py` - ✅ New models file
- `api/routers/tradingview.py` - ✅ New router file
- `api/main.py` - ✅ Router registration
- `api/models/indicator.py` - ✅ Add tradingview_url field
- `api/services/indicator_service.py` - ✅ Query and include link
- `api/routers/indicator.py` - ✅ Pass DynamoDB client
- `api/models/watchlist.py` - ✅ Add tradingview_url field
- `api/services/watchlist_service.py` - ✅ Query and include link

### Frontend
- `frontend/src/services/api.ts` - ✅ API client with TradingView service
- `frontend/src/utils/tradingview.ts` - ✅ URL generation utility
- `frontend/src/components/IndicatorCard.tsx` - ✅ Display and edit modal
- `frontend/src/components/IndicatorCard.css` - ✅ Modal and edit button styling
- `frontend/src/pages/AssetDetail.tsx` - ✅ Pass data to IndicatorCard with callback
- `frontend/src/pages/Watchlist.tsx` - ✅ Use custom URLs
- `frontend/src/pages/Watchlist.css` - ✅ Fixed table layout styling

---

## Testing Notes

After implementation:
- Test setting a custom TradingView URL for an asset
- Verify the custom URL appears in AssetDetail page
- Verify the custom URL appears in Watchlist
- Verify fallback behavior when no custom URL is set
- Test editing and updating an existing custom URL
