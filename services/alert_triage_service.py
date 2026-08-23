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
    Direction,
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
technical alerts on French stocks for a LONG-ONLY book.

You receive a JSON object with an "assets" array. Each asset has:
- id: opaque identifier you MUST echo back unchanged
- patterns: the chart patterns that fired today on this asset
- ma50_slope: percent slope of the 50-period moving average (medium-term \
trend); positive = uptrend, negative = downtrend, null = unknown
- pattern_directions: PRESENT ONLY when a directional pattern fired. Maps the \
pattern name to the direction its detector computed ("Buy" = bullish, "Sell" \
= bearish, "unknown" = the detector fired but published no usable direction). \
Only combo, combo_weekly and mm7_break can appear here; every other pattern \
is absent from this map because it has no computed direction of its own. \
Treat "unknown" as DISQUALIFYING UNTIL PROVEN BULLISH: you cannot tell \
whether it was a buy or a sell, so it earns no convergence point and cannot \
support "high" on its own. \
Only other, independent bullish evidence on the same asset can make it \
surfaceable, and never above "watch".
- workflow_triggers: PRESENT ONLY when one of the trader's own registered \
workflows fired on this asset today. Absent on most assets. Each entry has \
the workflow name, its order "direction" ("Buy"/"Sell"), a "dry_run" flag, \
and the "hour" it fired.

LONG-ONLY MANDATE - read this first, it governs every rule below:
This desk buys. It never shorts. A bearish read is therefore never an \
opportunity - at best it is a reason to stay out of a name, and the trader \
does not need a ranked brief to tell him about the hundreds of stocks he is \
not buying today. Concretely:
- The brief exists to surface BUYABLE setups. Bullish evidence - a "Buy" \
combo, a "Buy" mm7_break, mm50_touch, double_bottom, a "Buy" workflow \
trigger, a rising 50-MA - is what earns an asset a place in it.
- Bearish evidence - a "Sell" combo, a "Sell" combo_weekly, a "Sell" \
mm7_break, double_top, a "Sell" workflow trigger, a falling 50-MA - is NEVER \
convergence and NEVER opportunity. It counts only AGAINST a long thesis. \
Never describe a bearish setup as clean, strong, or actionable: there is no \
trade there for this desk.
- An asset whose net read is bearish can NEVER be "high", however much \
bearish evidence piles up and however steeply it is falling. Its ceiling is \
"watch", and only when the breakdown is genuinely worth a warning - a name \
the trader may already be long and should consider exiting. Every other \
bearish asset is "noise": omit it.
- Rank longs first. A buyable long always outranks a bearish "watch", \
whatever their relative evidence.
- A bearish "watch" rationale must read as a warning to avoid or exit, never \
as a setup to enter.

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
- Its "direction" carries directional authority AT LEAST equal to combo. A \
"Buy" trigger agreeing with bullish patterns is the strongest agreement this \
system can produce; say so. A "Sell" trigger is never convergence for this \
brief - the desk does not short, so it only tells you the trader's own rule \
wants OUT of this name.
- A trigger pointing AGAINST the bullish read is a RED FLAG on that read, \
exactly like mm50_touch on a bearish thesis - not "confluence that overrides \
a conflict". The trader's own rule disagreeing with your reading is evidence \
your reading is wrong, not evidence to discount.
- SEVERAL triggers on one asset still count as ONE point of convergence, not \
one each. Two triggers disagreeing with each other on direction is an \
internally inconsistent signal, not doubled conviction.
- dry_run: true means the rule fired but NO capital was committed. Still \
independent directional evidence, but weigh it ONE STEP LOWER than a live \
trigger.
- A trigger cannot by itself carry an asset that has nothing else going for \
it: it sharpens convergence, it does not replace the OPPORTUNITY axis. An \
asset riding a flat, falling or unknown trend is not "high" merely because a \
workflow fired on it.

Pattern semantics - know what each pattern actually means before reasoning \
about confluence or trend alignment:
- combo: the strongest directional pattern on the daily timeframe, and its \
direction is handed to you in pattern_directions. A "Buy" combo is a primary \
source of bullish bias - one of the best reasons to surface an asset. A \
"Sell" combo is the primary reason NOT to: it disqualifies the asset as a \
long, it never converges, and it can never contribute to "high".
- combo_weekly: the same setup measured on weekly bars, and it OUTRANKS \
combo. Its direction is handed to you in pattern_directions. It describes a \
position worth holding for weeks rather than a swing lasting days, so a \
"Buy" combo_weekly is the single strongest reason to surface an asset - it \
ranks ABOVE a "Buy" combo, not merely level with it, and the rationale must \
say the signal is on the WEEKLY timeframe. A "Sell" combo_weekly \
disqualifies the asset as a long exactly as a "Sell" combo does, and no \
amount of daily bullish evidence rescues it. When combo and combo_weekly \
disagree, NAME the disagreement rather than picking one silently: the \
bearish leg counts against the long thesis whichever timeframe it sits on. \
When they agree, that agreement is reinforcement of one detector reading two \
horizons, not two independent mechanisms.
- mm50_touch: can ONLY fire when the 50-MA is already rising strongly (its \
detector requires ma50_slope >= +3%). It is a bullish continuation signal \
(price pulling back to a rising average) - one of the cleanest long entries \
this scanner produces. NEVER cite it as confirming a bearish thesis or as \
"trend-aligned" with a negative slope. If you see mm50_touch alongside a \
claimed bearish setup, that combination is internally inconsistent - treat it \
as a red flag on the bearish read, not a supporting signal.
- mm7_break: the close crossing through the 7-period moving average, with a \
direction in pattern_directions ("Buy" = reclaim from below, "Sell" = \
breakdown from above). This is a SHORT-TERM TIMING trigger, not a thesis: it \
says the last few days changed character, nothing about where the stock is \
headed over weeks. A "Buy" break on a rising 50-MA is a bullish continuation \
trigger and counts as real evidence for a long. A "Buy" break against a \
falling 50-MA is an early sign the decline may be ending, NOT a reversal you \
can buy yet - "watch" at most. A "Sell" break is bearish: never evidence for \
a long, and on a rising 50-MA it is an early warning on an otherwise intact \
uptrend - mention it as a caveat, never as a reason to enter. mm7_break \
alone, with no other bullish pattern, is never enough for "high" no matter \
how clean the break.
- congestion20 and congestion100: the SAME underlying consolidation detector \
run at two different lookback windows (20 vs 100 candles). If both fire \
together, count them as ONE point of confluence, not two - they are not \
independent evidence. Congestion itself has no inherent direction (price is \
range-bound, could break either way).
- double_top: a geometric match of two similar recent highs - bearish, so \
always a strike AGAINST a long and never a setup of its own. On a rising \
50-MA it is the case that matters: the uptrend you would be buying may be \
topping out, so it downgrades or disqualifies an otherwise bullish read. On \
an already-falling 50-MA it is just noise inside an ongoing decline - no long \
to take and no short to take, so that asset is normally "noise".
- double_bottom: the bullish mirror of double_top, two similar recent lows. \
It matters most after a decline, as an early sign the downtrend is \
exhausting. On its own against a still-falling 50-MA it is "watch" at best - \
a bottom that has not yet become an uptrend is not a buyable setup. Confirmed \
by a "Buy" combo, a "Buy" mm7_break, or a 50-MA that has already turned up, \
it becomes real bullish evidence.
- containing_candle and double_inside_bar: pure geometric consolidation / \
indecision patterns. They carry no directional meaning on their own and \
should not be described as bearish or bullish by themselves.

Rank the day's opportunities on TWO orthogonal axes, applied with the \
pattern semantics above (not just pattern names or counts):

1. CONVERGENCE - how much the BULLISH evidence agrees with itself. Genuinely \
independent patterns pointing UP, on a rising (or at least turning-up) 50-MA, \
are strong. Bearish evidence never adds convergence; it subtracts from it. \
Count convergence by independent, bullish evidence - not by raw pattern count:
   - congestion20 + congestion100 together = ONE point (same detector, two \
windows).
   - patterns with no inherent direction (containing_candle, \
double_inside_bar, congestion) add breadth but cannot themselves converge \
on a direction.
   - a pattern that structurally cannot occur against the claimed trend \
(e.g. mm50_touch during a "bearish" read) is a red flag, NOT convergence.
   - a "Buy" workflow trigger agreeing with the bullish patterns = ONE point, \
and the strongest kind (independent mechanism); several triggers on one asset \
still = ONE point. A "Sell" trigger earns no point and counts against the \
long read.
   - any bearish pattern ("Sell" combo, "Sell" mm7_break, double_top) earns \
no point at all, however many of them fire.

2. OPPORTUNITY - given the bullish evidence agrees, how strong is the uptrend \
it is riding. Because the desk is long-only this axis is SIGNED, not \
absolute: only a POSITIVE ma50_slope carries opportunity. A large positive \
slope = high opportunity; a slope near zero, null/unknown, or NEGATIVE = no \
opportunity, regardless of how many patterns fired. A steeply falling stock \
is not "a big opportunity in the other direction" - for this desk it is no \
opportunity at all.

These are independent: many patterns can converge on the upside (high \
convergence) while the trend they ride is nearly flat (low opportunity), and \
a single clean bullish pattern can ride a very strong uptrend (low \
convergence, high opportunity).

Conviction tiers combine the two axes:
- "high": strong on BOTH - independent BULLISH patterns converging on a stock \
whose 50-MA is rising strongly. A genuine, actionable LONG worth looking at \
now. Reserved for longs: a bearish read never reaches this tier.
- "watch": not yet buyable, but worth keeping an eye on. Four cases qualify, \
and the rationale must make clear WHICH:
  (a) convergent bullish evidence on a flat or weak trend;
  (b) a single clean bullish signal riding a strong uptrend;
  (c) an EARLY bullish signal on a still-falling 50-MA - a "Buy" mm7_break or \
a double_bottom that hints the decline may be ending but has not turned the \
trend yet. Not buyable now; this is the "check back" tier, not an entry.
  (d) the ceiling for the rare bearish asset worth flagging: a notable \
breakdown in a name the trader may be long and should consider exiting.
- "noise": strong on NEITHER - isolated, redundant, non-directional, or \
internally-inconsistent hits on a flat, falling or unknown trend - and, by \
default, any bearish asset that is not a breakdown worth warning about.

RETURN ONLY the "high" and "watch" assets - the ones worth surfacing. Any \
asset you omit is treated as "noise", so never list noise assets. Rank the \
returned assets with a 1-based "rank" (1 = best) and give each a one-line \
"rationale" naming the patterns and the trend context.

Be selective: most days only a few assets are high or watch. Do not inflate \
tiers, do not pad convergence with redundant or non-directional patterns, and \
do not claim opportunity on a flat, falling or unknown trend. When in doubt \
about a bearish asset, leave it out.

Rank the returned assets so that stronger on BOTH axes comes first; when two \
assets are close, prefer the one riding the stronger uptrend (opportunity). \
Every buyable long ranks ahead of every bearish "watch".

"summary" is a one or two sentence headline of the day, written from a \
long-only seat: lead with the buyable longs, and mention a breakdown only \
when one is worth the warning. "assets" is the \
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
_PATTERN_FAMILY = {
    AlertType.CONGESTION100: AlertType.CONGESTION20,
    # combo and combo_weekly are one detector at two timeframes, exactly as
    # the congestion pair is one detector at two windows. Counted separately
    # they would reach HIGH on one detector's word, in a path that reads no
    # direction at all - so a Sell on both timeframes would rank as the
    # strongest kind of asset.
    AlertType.COMBO_WEEKLY: AlertType.COMBO,
}

# Short-term timing triggers. They say the last few candles changed character,
# not where the asset is headed, so they can sharpen a setup that other
# patterns already establish but must never be the pattern that promotes an
# asset to HIGH on their own account. The prompt tells the reasoning path the
# same thing; without this the fallback would quietly disagree with it and
# promote every WATCH asset that also happens to cross its MM7 - which, given
# how ordinary a cross is, would be most of them.
_TIMING_PATTERNS = {AlertType.MM7_BREAK}

# The detectors that publish a computed direction in their alert data. The
# desk is long-only, so a "Sell" here is disqualifying rather than merely
# informative - the reasoning path has to see it, not infer it from the slope.
_DIRECTIONAL_PATTERNS = {
    AlertType.COMBO,
    AlertType.COMBO_WEEKLY,
    AlertType.MM7_BREAK,
}

# What the payload says when a directional detector fired but published no
# usable direction - a stored alert from an older detector version, say.
# Omitting the pattern instead would read to the model as "no directional
# pattern fired", letting a Sell combo through the long-only gate as merely
# unknown, which is the inference this whole path exists to remove.
_UNKNOWN_DIRECTION = "unknown"


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
                self._confluence_points(entry),
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

    def _trigger_point(self, entry: Dict[str, Any]) -> int:
        """Whether the day's workflow triggers earn a confluence point.

        The reasoning path treats a trigger that contradicts the read as a red
        flag rather than as confluence. This mirrors that: the point is earned
        only by live triggers that agree with each other and with the
        direction of the trend they ride. It is never negative - the fallback
        withholds credit, it does not punish - and never more than one,
        however many fired (A-004).
        """
        live = [t for t in entry["workflow_triggers"] if not t.dry_run]
        if not live:
            # dry_run committed no capital: one step below a live trigger,
            # which in an integer tally means no point at all.
            return 0

        directions = {trigger.direction for trigger in live}
        if len(directions) > 1:
            return 0

        slope = entry["ma50_slope"]
        if not slope:
            return 0

        direction = directions.pop()
        agrees = (direction == Direction.BUY and slope > 0) or (
            direction == Direction.SELL and slope < 0
        )
        return 1 if agrees else 0

    def _confluence_points(self, entry: Dict[str, Any]) -> int:
        """Independent points of evidence backing this asset.

        A workflow trigger is a mechanism separate from the detectors, so an
        agreeing one adds a point. It cannot reach HIGH on its own: that still
        needs two structural patterns, or one plus a trigger.
        """
        return len(
            self._structural_families(entry["patterns"])
        ) + self._trigger_point(entry)

    def _fallback_conviction(self, entry: Dict[str, Any]) -> Conviction:
        points = self._confluence_points(entry)
        if points >= 2:
            return Conviction.HIGH
        if (
            points >= 1
            and self._abs_slope(entry["ma50_slope"]) >= self.slope_threshold
        ):
            return Conviction.WATCH
        return Conviction.NOISE

    def _fallback_rationale(self, entry: Dict[str, Any]) -> str:
        patterns = ", ".join(p.value for p in entry["patterns"])
        slope = entry["ma50_slope"]
        slope_text = f", slope {slope:.1f}%" if slope is not None else ""
        # Deliberately the structural pattern count, not _confluence_points:
        # on a day with no triggers this string must be byte-identical to the
        # pre-feature fallback (SC-004). The workflow is named in its own
        # clause instead.
        structural_count = len(self._structural_families(entry["patterns"]))
        trigger_text = ""
        if entry["workflow_triggers"]:
            # .name, not .value: Slack and the Daily Brief both render the
            # stored BUY/SELL form, and a fallback rationale sits beside them.
            trigger_text = "; workflow " + ", ".join(
                f"{trigger.workflow_name} ({trigger.direction.name}"
                f"{', dry run' if trigger.dry_run else ''})"
                for trigger in entry["workflow_triggers"]
            )
        # "0 pattern(s): mm7_break" would state a count of zero and then list
        # one. A zero structural count means every pattern was a timing
        # signal, so say that instead. Only reachable with a trigger attached
        # (nothing else promotes a timing-only asset), so the no-trigger
        # string stays byte-identical (SC-004).
        if structural_count == 0:
            return f"timing only: {patterns}{slope_text}{trigger_text}"
        return (
            f"{structural_count} pattern(s): "
            f"{patterns}{slope_text}{trigger_text}"
        )

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
                    "pattern_directions": {},
                    "ma50_slope": None,
                    "workflow_triggers": triggers.get(alert.id, []),
                },
            )
            if alert.alert_type not in entry["patterns"]:
                entry["patterns"].append(alert.alert_type)
            if alert.alert_type in _DIRECTIONAL_PATTERNS:
                entry["pattern_directions"][alert.alert_type] = (
                    self._alert_direction(alert)
                )
            slope = (
                alert.data.get("ma50_slope")
                if isinstance(alert.data, dict)
                else None
            )
            if slope is not None and entry["ma50_slope"] is None:
                entry["ma50_slope"] = slope
        return grouped

    def _alert_direction(self, alert: Alert) -> Optional[Direction]:
        """The direction a directional detector computed, if it published one.

        combo, combo_weekly and mm7_break are the only detectors that do.
        Without it the reasoning path can only guess a bullish or bearish
        read from the slope sign, which a long-only brief cannot afford -
        so a miss is logged rather than absorbed, and the payload marks the
        pattern unknown.
        """
        raw = (
            alert.data.get("direction")
            if isinstance(alert.data, dict)
            else None
        )
        for direction in Direction:
            if direction.value == raw:
                return direction
        self.logger.warning(
            f"{alert.alert_type.value} on {alert.asset_code} published no "
            f"usable direction ({raw!r}); the brief will treat it as unknown"
        )
        return None

    def _build_payload(self, grouped: Dict[str, Dict[str, Any]]) -> str:
        assets = []
        for asset_id, entry in grouped.items():
            asset: Dict[str, Any] = {
                "id": asset_id,
                "patterns": [p.value for p in entry["patterns"]],
                "ma50_slope": entry["ma50_slope"],
            }
            if entry["pattern_directions"]:
                asset["pattern_directions"] = {
                    pattern.value: (
                        direction.value
                        if direction is not None
                        else _UNKNOWN_DIRECTION
                    )
                    for pattern, direction in entry[
                        "pattern_directions"
                    ].items()
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

    also_corroborated = sorted(
        (
            asset
            for asset in digest.triaged_assets
            if asset.workflow_triggers and asset.conviction == Conviction.WATCH
        ),
        key=lambda asset: asset.rank or 0,
    )
    if also_corroborated:
        names = ", ".join(
            f"{asset.asset_description} ({asset.asset_code})"
            for asset in also_corroborated
        )
        lines.append(f"⚡ Also corroborated: {names}")

    if digest.fallback_used:
        lines.append("(fallback ranking - reasoning was unavailable)")

    lines.append(app_url)
    return "\n".join(lines)
