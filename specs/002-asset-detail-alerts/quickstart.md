# Quickstart Guide: Asset Detail Alerts Display

**Feature**: 002-asset-detail-alerts
**For**: Traders using the saxo-order web interface
**Updated**: 2026-01-11

## Overview

The asset detail page now displays all active alerts for the asset you're viewing. Alerts appear in a dedicated section between the indicators and workflows, allowing you to see recent market signals without leaving the asset detail view.

## Accessing Alerts

### Navigate to Asset Detail Page

1. **From Homepage**: Click on any asset card
2. **From Watchlist**: Click on an asset in your watchlist
3. **From Search**: Search for an asset and click the result
4. **Direct URL**: Navigate to `/asset/{symbol}` (e.g., `/asset/ITP:xpar`)

### Viewing Alerts

Once on the asset detail page:

1. **Scroll down** past the indicators section
2. You'll see an **"Alerts"** section header
3. **Recent alerts** (up to 3) are displayed immediately
4. If more than 3 alerts exist, click **"Show All"** to expand

## Understanding Alert Information

Each alert card displays:

### Alert Type Badge
- **COMBO**: Combined indicator signal (buy/sell opportunity)
- **CONGESTION20**: 20-period congestion zone detected
- **CONGESTION100**: 100-period congestion zone detected
- **DOUBLE TOP**: Double top candle pattern
- **DOUBLE INSIDE BAR**: Double inside bar pattern
- **CONTAINING CANDLE**: Containing candle pattern

### Timestamp
- **Relative time**: "2 hours ago", "3 days ago" (easy to scan)
- **Absolute time**: Hover over timestamp to see exact date/time

### Alert-Specific Data

Depending on the alert type, you'll see:

**COMBO Alerts**:
- **Price**: Entry price level
- **Direction**: Buy or Sell
- **Strength**: Strong, Medium, or Weak signal

**CONGESTION Alerts**:
- **Touch Points**: Number of price touches in the zone

**Candle Pattern Alerts**:
- **OHLC**: Open, High, Low, Close values

## Alert States

### Active Alerts
- Alerts less than 7 days old appear in this section
- Sorted by newest first (most recent at the top)

### No Alerts
If you see "No active alerts for this asset", it means:
- No alerts have been generated in the last 7 days
- The asset may not be monitored by the alerting system
- Alerts may have expired (older than 7 days)

### Loading State
- While fetching alerts, you'll see "Loading alerts..."
- Other page sections (indicators, workflows) continue to load independently

### Error State
If you see "Unable to load alerts...":
- The alerts service may be temporarily unavailable
- Refresh the page to retry
- Other page sections remain functional

## Expand/Collapse

### When to Expand
- If more than 3 alerts exist, you'll see a **"Show All"** button
- Click to view all alerts for the asset

### When to Collapse
- After expanding, click **"Show Less"** to return to the top 3 alerts
- Useful for reducing page length when many alerts exist

## Filtering Behavior

Alerts are **automatically filtered** by the asset you're viewing:

- **Saxo Assets**: Filters by both asset code and country code
  - Example: Viewing "ITP:xpar" shows only ITP alerts from xpar exchange

- **Assets Without Country Code**: Filters by asset code only
  - Example: Viewing "BTCUSDT" shows only BTCUSDT alerts

**No manual filtering needed** - alerts always match the current asset.

## Alert Retention

- Alerts are **retained for 7 days**
- After 7 days, alerts automatically expire and disappear
- You can see alerts up to 168 hours old (7 days × 24 hours)

## Mobile Usage

The alerts section is **fully responsive**:
- Alerts stack vertically on small screens
- Touch-friendly card interactions
- Timestamp hover works on tap (mobile devices)

## Tips

### Correlating Alerts with Indicators
1. Review the indicators section above
2. Scroll down to alerts
3. Compare alert prices with current price and indicator values
4. Make trading decisions based on combined signal strength

### Checking Recent Activity
- Look for alerts with "Less than 1 hour ago" or "2 hours ago"
- These are the most recent signals
- Consider correlation with current market conditions

### Understanding Alert Age
- **< 1 day old**: Very recent signal, likely still relevant
- **1-3 days old**: Recent signal, check if still valid
- **4-7 days old**: Older signal, use with caution

## Troubleshooting

### "No active alerts for this asset"
**Possible Causes**:
- Asset not monitored by alerting system
- No alerts triggered in last 7 days
- All alerts expired

**What to Do**:
- Check the alerts page (/alerts) to see all system alerts
- Verify asset is in your watchlist (monitored assets)
- Wait for next daily alert run

### "Unable to load alerts"
**Possible Causes**:
- Alerts API temporarily unavailable
- Network connectivity issue
- Backend service error

**What to Do**:
- Refresh the page
- Check network connection
- If persists, contact support

### Alerts Not Updating
**Possible Causes**:
- Page not refreshed after new alerts generated
- Browser cache holding old data

**What to Do**:
- Hard refresh the page (Ctrl+Shift+R or Cmd+Shift+R)
- Clear browser cache
- Check alerts page (/alerts) to verify new alerts exist

## Example Scenarios

### Scenario 1: Checking COMBO Alert

1. Navigate to asset detail page (e.g., `/asset/ITP:xpar`)
2. Scroll to Alerts section
3. See COMBO alert: "2 hours ago"
4. Review alert data:
   - Price: 150.25
   - Direction: Buy
   - Strength: Strong
5. Compare with current price in indicators above
6. Decide whether to act on signal

### Scenario 2: Reviewing Multiple Alerts

1. Navigate to asset with many alerts
2. See top 3 alerts displayed
3. Click "Show All" to expand
4. Review all 8 alerts chronologically
5. Identify patterns (multiple CONGESTION alerts)
6. Click "Show Less" to collapse

### Scenario 3: No Alerts Available

1. Navigate to new asset
2. See "No active alerts for this asset"
3. Check main alerts page (/alerts) - no alerts there either
4. Asset not yet monitored or no signals triggered
5. Continue using indicators and workflows for analysis

## Related Features

- **Alerts Page** (`/alerts`): View all alerts across all assets
- **Indicators Section**: Technical indicators for the current asset
- **Workflows Section**: Automated trading workflows for the asset
- **Watchlist**: Monitor your favorite assets

## Feedback

If you encounter issues or have suggestions:
- File a GitHub issue in the saxo-order repository
- Include the asset symbol and timestamp
- Attach screenshots if helpful
