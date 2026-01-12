# Quickstart Guide: On-Demand Alerts Execution

**Feature**: 003-on-demand-alerts
**Created**: 2026-01-12
**Audience**: Traders using the saxo-order web application

## What is On-Demand Alerts?

On-demand alerts allow you to manually trigger alert detection for any asset you're viewing, giving you immediate feedback on market signals without waiting for the scheduled alert generation (which runs periodically).

**When to use**:
- You're watching live price action and want to check for new signals
- You want fresh analysis before making a trading decision
- You've just received a price alert notification and want to see all technical signals

**Alert Types Detected**:
- **COMBO**: Buy/sell signals based on Bollinger Bands, Moving Averages, and MACD
- **CONGESTION20**: Congestion zones (20-candle window, 2+ touch points)
- **CONGESTION100**: Congestion zones (100-candle window, 3+ touch points)
- **DOUBLE_TOP**: Double top chart patterns
- **DOUBLE_INSIDE_BAR**: Double inside bar candle patterns
- **CONTAINING_CANDLE**: Containing/engulfing candle patterns

## How to Use

### Step 1: Navigate to Asset Detail Page

1. Go to the asset you want to analyze (e.g., `/asset/ITP:xpar`)
2. The asset detail page shows indicators, alerts, and workflows

### Step 2: Run Alert Detection

1. Scroll to the **Alerts** section (between Indicators and Workflows)
2. Click the **"Run Alerts"** button
3. You'll see:
   - Button text changes to "Running..." with a spinner
   - Button becomes disabled during execution
   - Loading message: "Analyzing asset for signals..."

### Step 3: View Results

**If new alerts are detected**:
- Success message appears: "Detected X new alerts"
- Alerts section automatically refreshes
- New alerts appear with a **"NEW"** badge (visible for 60 seconds)
- Message fades after 3 seconds

**If no new alerts are detected**:
- Message appears: "No new alerts detected"
- Existing alerts (from scheduled detection) remain visible
- Message fades after 3 seconds

**If an error occurs**:
- Error message explains the issue (see Troubleshooting below)
- Button re-enables after 3 seconds (unless cooldown active)

### Step 4: Cooldown Period

After successfully running alerts:
- Button stays disabled for **5 minutes**
- Countdown timer shows: "Next run in 4:32" (MM:SS format)
- You cannot trigger detection again until cooldown expires
- Countdown updates every second
- Button automatically re-enables when cooldown ends

## What Happens Behind the Scenes

1. **Candle Data Fetch**: System retrieves 250 daily candles + 10 hourly candles from Saxo API
2. **Detection Algorithms**: Runs all 6 alert detection algorithms on the candle data
3. **Deduplication**: Filters out duplicate alerts (only one alert per type per day)
4. **Storage**: Saves new alerts to DynamoDB with 7-day expiration
5. **Response**: Returns execution results and cooldown timestamp to frontend

**Typical execution time**: 3-10 seconds

## Cooldown Behavior

**Why cooldown?**
- Prevents system overload (detection is computationally expensive)
- Encourages thoughtful use (not spam-clicking button)
- Protects Saxo API rate limits

**Cooldown details**:
- **Duration**: 5 minutes per asset
- **Scope**: Per asset (running alerts on ITP doesn't block alerts on SAN)
- **Enforcement**: Backend validates cooldown (frontend timer is UX-only)
- **Bypass**: Not possible - cooldown enforced server-side

**If you try to run alerts during cooldown**:
- Error message: "Alerts recently run. Please wait X minutes before running again."
- Countdown timer shows remaining time
- Button stays disabled until cooldown expires

## Troubleshooting

### "Alerts recently run. Please wait X minutes..."

**Cause**: You (or someone else viewing the same asset) ran alerts within the last 5 minutes.

**Solution**: Wait for the cooldown timer to reach 0:00, then try again.

**Note**: If you see this immediately after page load, someone else recently triggered detection for this asset.

---

### "Alert service is currently unavailable. Please try again later."

**Cause**: Backend alert detection service or DynamoDB is unreachable.

**Solution**:
1. Wait 30 seconds and try again
2. If problem persists, check system status page
3. Contact support if issue continues >5 minutes

---

### "Alert detection timed out. Please try again."

**Cause**: Detection took longer than 60 seconds (usually due to Saxo API slowness).

**Solution**:
1. Try again immediately (no cooldown on timeouts)
2. If timeout repeats, Saxo API may be experiencing issues
3. Check Saxo API status or try during off-peak hours

---

### "Network error. Unable to complete alert execution."

**Cause**: Your internet connection dropped mid-execution.

**Solution**:
1. Check your internet connection
2. Refresh the page and try again
3. Detection may have completed server-side despite error (check alerts section)

---

### "Invalid asset data"

**Cause**: Asset information (code, exchange) is missing or malformed.

**Solution**:
1. Refresh the page
2. If error persists, the asset may not support alert detection
3. Report to support with asset code and exchange

---

### Button is disabled but no countdown timer

**Cause**: Detection is currently running in another browser tab or window.

**Solution**: Wait for the other execution to complete (up to 60 seconds), then button will re-enable with cooldown.

---

## Tips & Best Practices

**When to run alerts**:
- ✅ After significant price movement (breakout, breakdown)
- ✅ Before placing an order (get fresh signals)
- ✅ When watching live candles (check for pattern formation)
- ❌ Don't spam-click every few minutes (cooldown will block you)
- ❌ Don't rely solely on on-demand (scheduled detection runs automatically)

**Understanding results**:
- **"NEW" badge**: Alerts detected in the last on-demand run (last 60 seconds)
- **No badge**: Alerts from scheduled detection (may be hours old)
- **Age label**: "2 hours ago", "1 day ago" - time since alert was created
- **Empty state**: "No active alerts" means no signals detected in last 7 days

**Performance expectations**:
- **Fast assets** (crypto): 3-5 seconds (fewer candles to analyze)
- **Standard assets** (Saxo stocks): 5-8 seconds (250 daily + 10 hourly candles)
- **Slow executions**: 10-30 seconds (during Saxo API peak hours)
- **Timeout threshold**: 60 seconds (automatic timeout, no cooldown penalty)

**Deduplication behavior**:
- If scheduled detection already found a COMBO alert today, on-demand won't create a duplicate
- Only **new** alert types (not detected today) will be added
- Example: If scheduled found COMBO at 9am, on-demand at 2pm won't add another COMBO (unless different parameters)

---

## Frequently Asked Questions

### Q: Can I run alerts on multiple assets at once?

**A**: No. On-demand execution is per-asset only. To analyze multiple assets, visit each asset detail page and run alerts individually.

### Q: Does on-demand execution affect scheduled alerts?

**A**: No. Scheduled alert detection (Lambda-based) continues running independently. On-demand is an additional capability, not a replacement.

### Q: What if I navigate away while alerts are running?

**A**: The browser cancels the request. No alerts are saved. You can try again after returning to the page.

### Q: Can I customize which alert types to detect?

**A**: No. All 6 alert types run every time. Custom detection is out of scope for this feature.

### Q: How long are alerts stored?

**A**: 7 days. Alerts automatically expire via DynamoDB TTL. After 7 days, they're permanently deleted.

### Q: Can I run alerts for historical dates?

**A**: No. On-demand detection analyzes current/recent candle data only. Historical analysis is not supported.

### Q: What if detection finds 0 alerts?

**A**: You'll see "No new alerts detected" message. Existing alerts (from scheduled detection) remain visible. This is normal - not every candle pattern indicates a trading signal.

---

## Related Features

- **Feature 002: Asset Detail Alerts Display** - View alerts directly on asset detail page
- **Feature 001: Alerts UI Page** - Browse all alerts across all assets

---

## Support

- **Documentation**: See `specs/003-on-demand-alerts/` for technical details
- **API Contract**: `contracts/run-alerts.yaml` for endpoint specification
- **Data Model**: `data-model.md` for request/response structures
