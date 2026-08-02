import datetime
import json
import logging
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from client.anthropic_client import AnthropicClient
from model import (
    Alert,
    AlertDigest,
    AlertType,
    Conviction,
    TriagedAsset,
    WorkflowTrigger,
)
from utils.exception import AnthropicException
from utils.logger import Logger

PARIS = ZoneInfo("Europe/Paris")


def current_run_date() -> str:
    """Today's date in Paris, the timezone the whole scan reasons in.

    A naive now() is UTC inside Lambda, which disagrees with the Paris
    session window for any run between midnight Paris and midnight UTC.
    """
    return datetime.datetime.now(PARIS).strftime("%Y-%m-%d")


TRIAGE_SYSTEM_PROMPT = """You are a trading-desk analyst triaging the day's \
technical alerts on French stocks.

You receive a JSON object with an "assets" array. Each asset has:
- id: opaque identifier you MUST echo back unchanged
- patterns: the chart patterns that fired today on this asset
- ma50_slope: percent slope of the 50-period moving average (medium-term \
trend); positive = uptrend, negative = downtrend, null = unknown
- workflow_triggers: PRESENT ONLY when one of the trader's own registered \
workflows fired on this asset today. Absent on most assets. Each entry has \
the workflow name, its order "direction" ("Buy"/"Sell"), a "dry_run" flag, \
and the "hour" it fired.

Workflow triggers - the one input that does NOT come from the chart-pattern \
detectors:
Every pattern above is computed by the same scanner, on the same candles, at \
the same moment. A workflow trigger is different in kind: it is a rule the \
trader WROTE IN ADVANCE, which fired intraday and produced a real directional \
order. Treat it accordingly:
- It is genuinely INDEPENDENT evidence. Unlike congestion20 + congestion100 \
(one detector, two windows), a trigger and a pattern are two different \
mechanisms agreeing - that is real convergence. Count it as ONE point of \
convergence.
- Its "direction" carries directional authority AT LEAST equal to combo. \
When a trigger and the patterns point the same way, that is the strongest \
agreement this system can produce; say so.
- A trigger pointing AGAINST the pattern-and-trend read is a RED FLAG on \
that read, exactly like mm50_touch on a bearish thesis - not "confluence \
that overrides a conflict". The trader's own rule disagreeing with your \
reading is evidence your reading is wrong, not evidence to discount.
- SEVERAL triggers on one asset still count as ONE point of convergence, not \
one each. Two triggers disagreeing with each other on direction is an \
internally inconsistent signal, not doubled conviction.
- dry_run: true means the rule fired but NO capital was committed. Still \
independent directional evidence, but weigh it ONE STEP LOWER than a live \
trigger.
- A trigger cannot by itself carry an asset that has nothing else going for \
it: it sharpens convergence, it does not replace the OPPORTUNITY axis. An \
asset riding a flat or unknown trend is not "high" merely because a workflow \
fired on it.

Pattern semantics - know what each pattern actually means before reasoning \
about confluence or trend alignment:
- combo: the only pattern with an explicit computed direction. Treat it as \
the primary source of directional bias.
- mm50_touch: can ONLY fire when the 50-MA is already rising strongly (its \
detector requires ma50_slope >= +3%). It is a bullish continuation signal \
(price pulling back to a rising average) - NEVER cite it as confirming a \
bearish thesis or as "trend-aligned" with a negative slope. If you see \
mm50_touch alongside a claimed bearish setup, that combination is internally \
inconsistent, not "confluence that overrides a conflict" - treat it as a red \
flag on the bearish read, not a supporting signal.
- mm7_break: the close crossing through the 7-period moving average, with a \
direction ("Buy" = reclaim from below, "Sell" = breakdown from above). This \
is a SHORT-TERM TIMING trigger, not a thesis: it says the last few days \
changed character, nothing about where the stock is headed over weeks. Weigh \
it by how it sits against ma50_slope: a break in the SAME direction as the \
slope is a \
continuation trigger and counts as real directional evidence; a break AGAINST \
the slope is an early warning on an intact trend, NOT a reversal - do not \
promote it to a reversal thesis on its own. mm7_break alone, with no other \
directional pattern, is never enough for "high" no matter how clean the break.
- congestion20 and congestion100: the SAME underlying consolidation detector \
run at two different lookback windows (20 vs 100 candles). If both fire \
together, count them as ONE point of confluence, not two - they are not \
independent evidence. Congestion itself has no inherent direction (price is \
range-bound, could break either way).
- double_top: a geometric match of two similar recent highs. It is only a \
meaningful bearish reversal signal when it interrupts a PRIOR uptrend (the \
stock was rising, then topped out). If the stock is already in an \
established downtrend (strongly negative ma50_slope), a "double_top" is not \
a fresh reversal - it is just noise inside an ongoing decline, and should \
NOT be described as "confirming" or "reinforcing" the bearish bias.
- containing_candle and double_inside_bar: pure geometric consolidation / \
indecision patterns. They carry no directional meaning on their own and \
should not be described as bearish or bullish by themselves.

Rank the day's opportunities on TWO orthogonal axes, applied with the \
pattern semantics above (not just pattern names or counts):

1. CONVERGENCE - how much the evidence agrees with itself. Genuinely \
independent patterns pointing the same direction, AND agreeing with the \
DIRECTION (sign) of ma50_slope, are strong. Count convergence by \
independent, directional evidence - not by raw pattern count:
   - congestion20 + congestion100 together = ONE point (same detector, two \
windows).
   - patterns with no inherent direction (containing_candle, \
double_inside_bar, congestion) add breadth but cannot themselves converge \
on a direction.
   - a pattern that structurally cannot occur against the claimed trend \
(e.g. mm50_touch during a "bearish" read) is a red flag, NOT convergence.
   - a workflow trigger agreeing with the patterns = ONE point, and the \
strongest kind (independent mechanism); several triggers on one asset still \
= ONE point.

2. OPPORTUNITY - given the evidence agrees, how strong is the move it is \
riding. This is about the MAGNITUDE of ma50_slope (and its momentum), not \
its sign: a signal aligned with a steep, strongly-inclined trend is a bigger \
opportunity than the same signal riding a shallow, near-flat trend. A large \
|ma50_slope| in the signal's direction = high opportunity; a slope near zero \
(or null/unknown) = low opportunity regardless of how many patterns fired.

These are independent: many patterns can converge on a direction (high \
convergence) while the trend they ride is nearly flat (low opportunity), and \
a single clean directional pattern can ride a very strong trend (low \
convergence, high opportunity).

Conviction tiers combine the two axes:
- "high": strong on BOTH - independent patterns converging on a direction \
that also rides a strongly-inclined trend. A genuine, actionable setup worth \
looking at now.
- "watch": strong on ONE axis - either convergent evidence on a flat/weak \
trend, or a single clean directional signal riding a strong trend. Plausible, \
keep an eye on it.
- "noise": strong on NEITHER - isolated, redundant, non-directional, or \
internally-inconsistent hits on a flat or unknown trend.

RETURN ONLY the "high" and "watch" assets - the ones worth surfacing. Any \
asset you omit is treated as "noise", so never list noise assets. Rank the \
returned assets with a 1-based "rank" (1 = best) and give each a one-line \
"rationale" naming the patterns and the trend context.

Be selective: most days only a few assets are high or watch. Do not inflate \
tiers, do not pad convergence with redundant or non-directional patterns, and \
do not claim opportunity on a flat or unknown trend.

Rank the returned assets so that stronger on BOTH axes comes first; when two \
assets are close, prefer the one riding the stronger trend (opportunity).

"summary" is a one or two sentence headline of the day. "assets" is the \
ranked list of high/watch assets, each with its echoed "id", "conviction", \
1-based "rank", and a one-line "rationale" that names BOTH axes: which \
patterns converged (or why the evidence is thin) and the strength/direction \
of the trend they ride. If a workflow trigger influenced where you ranked an \
asset, NAME THE WORKFLOW in that asset's rationale - the trader must be able \
to see why it rose without going to look it up."""

# Enforced via output_config.format (structured outputs) so the response is
# always valid JSON matching this exact shape - no prose preamble, no code
# fences, no risk of triggering the deterministic fallback on a well-formed
# answer just because it wasn't formatted the way the prompt asked.
TRIAGE_RESPONSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "assets": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "conviction": {
                        "type": "string",
                        "enum": ["high", "watch"],
                    },
                    "rank": {"type": "integer"},
                    "rationale": {"type": "string"},
                },
                "required": ["id", "conviction", "rank", "rationale"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["summary", "assets"],
    "additionalProperties": False,
}


FALLBACK_MODEL = "deterministic-fallback"

# congestion20 and congestion100 are the same underlying detector run at two
# lookback windows, not independent signals - collapse them to one family
# when counting confluence in the deterministic fallback.
_PATTERN_FAMILY = {AlertType.CONGESTION100: AlertType.CONGESTION20}

# Short-term timing triggers. They say the last few candles changed character,
# not where the asset is headed, so they can sharpen a setup that other
# patterns already establish but must never be the pattern that promotes an
# asset to HIGH on their own account. The prompt tells the reasoning path the
# same thing; without this the fallback would quietly disagree with it and
# promote every WATCH asset that also happens to cross its MM7 - which, given
# how ordinary a cross is, would be most of them.
_TIMING_PATTERNS = {AlertType.MM7_BREAK}


class TriageAgent:
    def __init__(
        self,
        anthropic_client: AnthropicClient,
        slope_threshold: float = 1.0,
    ) -> None:
        self.anthropic_client = anthropic_client
        self.slope_threshold = slope_threshold
        self.logger = Logger.get_logger("triage_agent", logging.INFO)

    def synthesize(
        self,
        alerts: List[Alert],
        triggers: Optional[Dict[str, List[WorkflowTrigger]]] = None,
        run_date: Optional[str] = None,
    ) -> AlertDigest:
        grouped = self._group_by_asset(alerts, triggers or {})
        run_date = run_date or current_run_date()
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

        try:
            raw = self.anthropic_client.complete_json(
                TRIAGE_SYSTEM_PROMPT,
                self._build_payload(grouped),
                output_schema=TRIAGE_RESPONSE_SCHEMA,
            )
            triaged = self._parse_triaged(raw, grouped)
            counts = self._count_tiers(triaged)
            summary = str(
                raw.get("summary", "")
            ).strip() or self._default_summary(counts)
            return AlertDigest(
                run_date=run_date,
                created_at=created_at,
                summary=summary,
                counts=counts,
                triaged_assets=triaged,
                model=self.anthropic_client.model,
                fallback_used=False,
            )
        except AnthropicException as e:
            self.logger.warning(
                f"Triage reasoning failed, using deterministic fallback: {e}"
            )
            return self._fallback_digest(grouped, run_date, created_at)

    def _fallback_digest(
        self,
        grouped: Dict[str, Dict[str, Any]],
        run_date: str,
        created_at: int,
    ) -> AlertDigest:
        ordered = sorted(
            grouped.values(),
            key=lambda entry: (
                len(self._structural_families(entry["patterns"])),
                self._abs_slope(entry["ma50_slope"]),
            ),
            reverse=True,
        )
        triaged: List[TriagedAsset] = []
        rank = 1
        for entry in ordered:
            conviction = self._fallback_conviction(entry)
            if conviction == Conviction.NOISE:
                triaged.append(
                    self._build_triaged_asset(
                        entry, Conviction.NOISE, None, ""
                    )
                )
            else:
                triaged.append(
                    self._build_triaged_asset(
                        entry,
                        conviction,
                        rank,
                        self._fallback_rationale(entry),
                    )
                )
                rank += 1
        counts = self._count_tiers(triaged)
        return AlertDigest(
            run_date=run_date,
            created_at=created_at,
            summary=self._default_summary(counts),
            counts=counts,
            triaged_assets=triaged,
            model=FALLBACK_MODEL,
            fallback_used=True,
        )

    def _fallback_conviction(self, entry: Dict[str, Any]) -> Conviction:
        structural_count = len(self._structural_families(entry["patterns"]))
        if structural_count >= 2:
            return Conviction.HIGH
        if (
            structural_count >= 1
            and self._abs_slope(entry["ma50_slope"]) >= self.slope_threshold
        ):
            return Conviction.WATCH
        return Conviction.NOISE

    def _fallback_rationale(self, entry: Dict[str, Any]) -> str:
        patterns = ", ".join(p.value for p in entry["patterns"])
        slope = entry["ma50_slope"]
        slope_text = f", slope {slope:.1f}%" if slope is not None else ""
        structural_count = len(self._structural_families(entry["patterns"]))
        return f"{structural_count} pattern(s): {patterns}{slope_text}"

    def _pattern_families(self, patterns: List[AlertType]) -> set[AlertType]:
        return {_PATTERN_FAMILY.get(p, p) for p in patterns}

    def _structural_families(
        self, patterns: List[AlertType]
    ) -> set[AlertType]:
        return self._pattern_families(patterns) - _TIMING_PATTERNS

    def _abs_slope(self, slope: Optional[float]) -> float:
        return abs(slope) if slope is not None else 0.0

    def _group_by_asset(
        self,
        alerts: List[Alert],
        triggers: Dict[str, List[WorkflowTrigger]],
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
                    "workflow_triggers": triggers.get(alert.id, []),
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
        assets = []
        for asset_id, entry in grouped.items():
            asset: Dict[str, Any] = {
                "id": asset_id,
                "patterns": [p.value for p in entry["patterns"]],
                "ma50_slope": entry["ma50_slope"],
            }
            if entry["workflow_triggers"]:
                asset["workflow_triggers"] = [
                    self._payload_trigger(t)
                    for t in entry["workflow_triggers"]
                ]
            assets.append(asset)
        return json.dumps({"assets": assets})

    def _payload_trigger(self, trigger: WorkflowTrigger) -> Dict[str, Any]:
        placed_at = datetime.datetime.fromtimestamp(trigger.placed_at, PARIS)
        return {
            "workflow": trigger.workflow_name,
            "direction": trigger.direction.value,
            "dry_run": trigger.dry_run,
            "hour": placed_at.strftime("%H:%M"),
        }

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
            workflow_triggers=entry["workflow_triggers"],
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


def format_slack_digest(digest: AlertDigest, app_url: str) -> str:
    if len(digest.triaged_assets) == 0:
        return digest.summary

    high = digest.counts.get(Conviction.HIGH.value, 0)
    watch = digest.counts.get(Conviction.WATCH.value, 0)
    noise = digest.counts.get(Conviction.NOISE.value, 0)

    lines = [
        f"\U0001f4ca Daily brief ({digest.run_date}): "
        f"{high} high, {watch} watch, {noise} filtered"
    ]

    high_assets = sorted(
        (
            asset
            for asset in digest.triaged_assets
            if asset.conviction == Conviction.HIGH
        ),
        key=lambda asset: asset.rank or 0,
    )
    if high_assets:
        names = ", ".join(
            f"{asset.asset_description} ({asset.asset_code})"
            f"{' ⚡' if asset.workflow_triggers else ''}"
            for asset in high_assets
        )
        lines.append(f"Top: {names}")

    corroborated = sum(
        1
        for asset in digest.triaged_assets
        if asset.workflow_triggers and asset.conviction != Conviction.NOISE
    )
    if corroborated:
        lines.append(
            f"⚡ {corroborated} workflow-corroborated "
            f"{'asset' if corroborated == 1 else 'assets'}"
        )

    if digest.fallback_used:
        lines.append("(fallback ranking - reasoning was unavailable)")

    lines.append(app_url)
    return "\n".join(lines)
