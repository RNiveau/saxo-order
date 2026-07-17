import datetime
import json
import logging
from typing import Any, Dict, List, Optional

from client.anthropic_client import AnthropicClient
from model import Alert, AlertDigest, Conviction, TriagedAsset
from utils.logger import Logger

TRIAGE_SYSTEM_PROMPT = """You are a trading-desk analyst triaging the day's \
technical alerts on French stocks.

You receive a JSON object with an "assets" array. Each asset has:
- id: opaque identifier you MUST echo back unchanged
- patterns: the chart patterns that fired today on this asset
- ma50_slope: percent slope of the 50-period moving average (medium-term \
trend); positive = uptrend, negative = downtrend, null = unknown

Rank the day's opportunities using two ideas:
1. Confluence - an asset where several distinct patterns fired at once is \
stronger than one with a single isolated pattern.
2. Trend alignment - a bearish setup is higher conviction when ma50_slope is \
negative (trend agrees); a bullish setup is higher conviction when ma50_slope \
is positive. A signal fighting the trend is weaker.

Conviction tiers:
- "high": a genuine, actionable setup worth looking at now.
- "watch": a plausible setup to keep an eye on.
- "noise": low-signal, isolated, or trend-conflicting hits.

RETURN ONLY the "high" and "watch" assets - the ones worth surfacing. Any \
asset you omit is treated as "noise", so never list noise assets. Rank the \
returned assets with a 1-based "rank" (1 = best) and give each a one-line \
"rationale" naming the patterns and the trend context.

Be selective: most days only a few assets are high or watch. Do not inflate \
tiers.

Respond with ONLY a JSON object, no prose, no code fences:
{"summary": "<one or two sentence headline of the day>",
 "assets": [{"id": "<echoed id>", "conviction": "high|watch", \
"rank": <int>, "rationale": "<one line>"}]}"""


class TriageAgent:
    def __init__(self, anthropic_client: AnthropicClient) -> None:
        self.anthropic_client = anthropic_client
        self.logger = Logger.get_logger("triage_agent", logging.INFO)

    def synthesize(self, alerts: List[Alert]) -> AlertDigest:
        grouped = self._group_by_asset(alerts)
        run_date = datetime.datetime.now().strftime("%Y-%m-%d")
        created_at = int(
            datetime.datetime.now(datetime.timezone.utc).timestamp()
        )

        if not grouped:
            return AlertDigest(
                run_date=run_date,
                created_at=created_at,
                summary="No signals detected today.",
                counts={c.value: 0 for c in Conviction},
                triaged_assets=[],
                model=self.anthropic_client.model,
                fallback_used=False,
            )

        payload = self._build_payload(grouped)
        raw = self.anthropic_client.complete_json(
            TRIAGE_SYSTEM_PROMPT, payload
        )
        triaged = self._parse_triaged(raw, grouped)
        counts = self._count_tiers(triaged)
        summary = str(raw.get("summary", "")).strip() or self._default_summary(
            counts
        )
        return AlertDigest(
            run_date=run_date,
            created_at=created_at,
            summary=summary,
            counts=counts,
            triaged_assets=triaged,
            model=self.anthropic_client.model,
            fallback_used=False,
        )

    def _group_by_asset(
        self, alerts: List[Alert]
    ) -> Dict[str, Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}
        for alert in alerts:
            entry = grouped.setdefault(
                alert.id,
                {
                    "asset_code": alert.asset_code,
                    "asset_description": alert.asset_description,
                    "exchange": alert.exchange,
                    "country_code": alert.country_code,
                    "patterns": [],
                    "ma50_slope": None,
                },
            )
            if alert.alert_type not in entry["patterns"]:
                entry["patterns"].append(alert.alert_type)
            slope = (
                alert.data.get("ma50_slope")
                if isinstance(alert.data, dict)
                else None
            )
            if slope is not None and entry["ma50_slope"] is None:
                entry["ma50_slope"] = slope
        return grouped

    def _build_payload(self, grouped: Dict[str, Dict[str, Any]]) -> str:
        assets = [
            {
                "id": asset_id,
                "patterns": [p.value for p in entry["patterns"]],
                "ma50_slope": entry["ma50_slope"],
            }
            for asset_id, entry in grouped.items()
        ]
        return json.dumps({"assets": assets})

    def _parse_triaged(
        self, raw: Dict[str, Any], grouped: Dict[str, Dict[str, Any]]
    ) -> List[TriagedAsset]:
        triaged: List[TriagedAsset] = []
        seen: set = set()
        for item in raw.get("assets", []):
            if not isinstance(item, dict):
                continue
            asset_id = item.get("id")
            if asset_id not in grouped or asset_id in seen:
                continue
            seen.add(asset_id)
            conviction = self._parse_conviction(item.get("conviction"))
            triaged.append(
                self._build_triaged_asset(
                    grouped[asset_id],
                    conviction,
                    self._parse_rank(item.get("rank"), conviction),
                    str(item.get("rationale", "")).strip(),
                )
            )

        for asset_id, entry in grouped.items():
            if asset_id not in seen:
                triaged.append(
                    self._build_triaged_asset(
                        entry, Conviction.NOISE, None, ""
                    )
                )
        return triaged

    def _build_triaged_asset(
        self,
        entry: Dict[str, Any],
        conviction: Conviction,
        rank: Optional[int],
        rationale: str,
    ) -> TriagedAsset:
        return TriagedAsset(
            asset_code=entry["asset_code"],
            asset_description=entry["asset_description"],
            exchange=entry["exchange"],
            conviction=conviction,
            rationale=rationale,
            patterns=entry["patterns"],
            ma50_slope=entry["ma50_slope"],
            rank=rank,
            country_code=entry["country_code"],
        )

    def _parse_conviction(self, value: Any) -> Conviction:
        if isinstance(value, str):
            for conviction in Conviction:
                if conviction.value == value.lower():
                    return conviction
        return Conviction.NOISE

    def _parse_rank(self, value: Any, conviction: Conviction) -> Optional[int]:
        if conviction == Conviction.NOISE:
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return int(value)
        return None

    def _count_tiers(self, triaged: List[TriagedAsset]) -> Dict[str, int]:
        counts = {c.value: 0 for c in Conviction}
        for asset in triaged:
            counts[asset.conviction.value] += 1
        return counts

    def _default_summary(self, counts: Dict[str, int]) -> str:
        total = sum(counts.values())
        return (
            f"{total} assets scanned: {counts[Conviction.HIGH.value]} high, "
            f"{counts[Conviction.WATCH.value]} watch, "
            f"{counts[Conviction.NOISE.value]} noise."
        )
