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

**Commit:** `82171c3` - feat: add backend API for custom TradingView links
**PR:** https://github.com/RNiveau/saxo-order/pull/463

---

### Frontend Changes (TODO)

9. **Update API client** (`frontend/src/services/api.ts`)
   - Add `setTradingViewLink(assetId: string, url: string)` function
   - Update `AssetIndicatorsResponse` interface to include optional `tradingview_url?: string`
   - Update `WatchlistItem` interface to include optional `tradingview_url?: string`

10. **Update TradingView utility** (`frontend/src/utils/tradingview.ts`)
    - Modify signature: `getTradingViewUrl(assetSymbol: string, customUrl?: string)`
    - Return customUrl if provided, otherwise fall back to current mapping logic

11. **Update IndicatorCard** (`frontend/src/components/IndicatorCard.tsx`)
    - Use `getTradingViewUrl(indicators.asset_symbol, indicators.tradingview_url)`
    - Add small edit button (✏️) next to TradingView link when not in edit mode
    - Create modal component for editing TradingView URL:
      - Input field for URL
      - Save/Cancel buttons
      - Handle API call to save the URL
      - Show success/error messages

12. **Update AssetDetail page** (`frontend/src/pages/AssetDetail.tsx`)
    - Pass tradingview_url from indicatorData to IndicatorCard
    - (Already passed via indicators prop, just need to ensure it's in the data)

13. **Update Watchlist** (`frontend/src/pages/Watchlist.tsx`)
    - Use `getTradingViewUrl(item.asset_symbol, item.tradingview_url)` for sidebar links

---

## Implementation Order

1. ✅ **Infrastructure** (DynamoDB table, IAM policies, Pulumi deployment) - COMPLETED
2. ✅ **Backend data layer** (AWS client methods) - COMPLETED
3. ✅ **Backend API** (models, router, service updates) - COMPLETED
4. **Frontend API client** updates - TODO
5. **Frontend UI** (modal, link updates) - TODO

## Progress Summary

**Completed:**
- Infrastructure setup with DynamoDB table
- Complete backend API implementation
- All backend tests passing
- PR created: https://github.com/RNiveau/saxo-order/pull/463

**Remaining:**
- Frontend implementation (separate PR after backend is merged)

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
- `frontend/src/services/api.ts` - API client
- `frontend/src/utils/tradingview.ts` - URL generation utility
- `frontend/src/components/IndicatorCard.tsx` - Display and edit modal
- `frontend/src/pages/AssetDetail.tsx` - Pass data to IndicatorCard
- `frontend/src/pages/Watchlist.tsx` - Use custom URLs

---

## Testing Notes

After implementation:
- Test setting a custom TradingView URL for an asset
- Verify the custom URL appears in AssetDetail page
- Verify the custom URL appears in Watchlist
- Verify fallback behavior when no custom URL is set
- Test editing and updating an existing custom URL
