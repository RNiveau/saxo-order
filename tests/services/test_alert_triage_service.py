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
    SignalStrength,
    TriagedAsset,
    WorkflowTrigger,
)
from services.alert_triage_service import (
    TRIAGE_SYSTEM_PROMPT,
    TriageAgent,
    current_run_date,
    format_slack_digest,
)
from utils.exception import AnthropicException


class FakeAnthropicClient(AnthropicClient):
    def __init__(self, response: Dict[str, Any]) -> None:
        self._response = response
        self._model = "test-model"
        self.calls = 0

    def complete_json(
        self,
        system: str,
        user_payload: str,
        output_schema: Optional[Dict[str, Any]] = None,
        max_tokens: int = 16000,
    ) -> Dict[str, Any]:
        self.calls += 1
        self.last_payload = user_payload
        return self._response


class RaisingAnthropicClient(AnthropicClient):
    def __init__(self) -> None:
        self._model = "test-model"

    def complete_json(
        self,
        system: str,
        user_payload: str,
        output_schema: Optional[Dict[str, Any]] = None,
        max_tokens: int = 16000,
    ) -> Dict[str, Any]:
        raise AssertionError("complete_json must not be called")


class FailingAnthropicClient(AnthropicClient):
    def __init__(self) -> None:
        self._model = "test-model"

    def complete_json(
        self,
        system: str,
        user_payload: str,
        output_schema: Optional[Dict[str, Any]] = None,
        max_tokens: int = 16000,
    ) -> Dict[str, Any]:
        raise AnthropicException("boom")


def _alert(
    code: str,
    alert_type: AlertType,
    slope: float,
    country_code: str = "xpar",
) -> Alert:
    return Alert(
        alert_type=alert_type,
        date=datetime.datetime.now(),
        data={"ma50_slope": slope},
        asset_code=code,
        asset_description=f"{code} SA",
        exchange="saxo",
        country_code=country_code,
    )


def _directional_alert(
    code: str,
    alert_type: AlertType,
    slope: float,
    direction: Direction,
    country_code: str = "xpar",
) -> Alert:
    alert = _alert(code, alert_type, slope, country_code)
    alert.data["direction"] = direction.value
    return alert


def _by_code(triaged: List) -> Dict[str, Any]:
    return {t.asset_code: t for t in triaged}


def test_synthesize_maps_tiers_ranks_and_rationale() -> None:
    alerts = [
        _alert("SAN", AlertType.DOUBLE_TOP, -2.3),
        _alert("SAN", AlertType.MM50_TOUCH, -2.3),
        _alert("AIR", AlertType.CONGESTION20, 0.1),
    ]
    client = FakeAnthropicClient(
        {
            "summary": "Two setups today.",
            "assets": [
                {
                    "id": "SAN_xpar",
                    "conviction": "high",
                    "rank": 1,
                    "rationale": "double top + MA50 rejection, trend agrees",
                },
                {
                    "id": "AIR_xpar",
                    "conviction": "noise",
                    "rank": None,
                    "rationale": "",
                },
            ],
        }
    )
    digest = TriageAgent(client).synthesize(alerts)

    assert digest.model == "test-model"
    assert digest.fallback_used is False
    assert digest.summary == "Two setups today."
    assert digest.counts == {"high": 1, "watch": 0, "noise": 1}

    triaged = _by_code(digest.triaged_assets)
    san = triaged["SAN"]
    assert san.conviction == Conviction.HIGH
    assert san.rank == 1
    assert "double top" in san.rationale
    assert set(san.patterns) == {AlertType.DOUBLE_TOP, AlertType.MM50_TOUCH}
    assert san.ma50_slope == -2.3
    assert triaged["AIR"].conviction == Conviction.NOISE
    assert triaged["AIR"].rank is None


def test_scanned_asset_dropped_by_model_becomes_noise() -> None:
    alerts = [
        _alert("SAN", AlertType.DOUBLE_TOP, -2.3),
        _alert("AIR", AlertType.CONGESTION20, 0.1),
    ]
    client = FakeAnthropicClient(
        {
            "summary": "One setup.",
            "assets": [
                {"id": "SAN_xpar", "conviction": "high", "rank": 1},
            ],
        }
    )
    digest = TriageAgent(client).synthesize(alerts)

    triaged = _by_code(digest.triaged_assets)
    assert triaged["AIR"].conviction == Conviction.NOISE
    assert digest.counts["noise"] == 1
    assert len(digest.triaged_assets) == 2


def test_unknown_asset_from_model_is_ignored() -> None:
    alerts = [_alert("SAN", AlertType.DOUBLE_TOP, -2.3)]
    client = FakeAnthropicClient(
        {
            "assets": [
                {"id": "SAN_xpar", "conviction": "high", "rank": 1},
                {"id": "GHOST_xpar", "conviction": "high", "rank": 2},
            ]
        }
    )
    digest = TriageAgent(client).synthesize(alerts)

    codes = {t.asset_code for t in digest.triaged_assets}
    assert codes == {"SAN"}


def test_noise_rank_is_dropped_even_if_model_returns_one() -> None:
    alerts = [_alert("SAN", AlertType.DOUBLE_TOP, -2.3)]
    client = FakeAnthropicClient(
        {"assets": [{"id": "SAN_xpar", "conviction": "noise", "rank": 5}]}
    )
    digest = TriageAgent(client).synthesize(alerts)

    assert digest.triaged_assets[0].rank is None


def test_empty_alerts_returns_empty_digest_without_calling_model() -> None:
    digest = TriageAgent(RaisingAnthropicClient()).synthesize([])

    assert digest.triaged_assets == []
    assert digest.counts == {"high": 0, "watch": 0, "noise": 0}
    assert digest.fallback_used is False
    assert "No signals" in digest.summary


def test_missing_summary_falls_back_to_default() -> None:
    alerts = [_alert("SAN", AlertType.DOUBLE_TOP, -2.3)]
    client = FakeAnthropicClient(
        {"assets": [{"id": "SAN_xpar", "conviction": "watch", "rank": 1}]}
    )
    digest = TriageAgent(client).synthesize(alerts)

    assert "1 watch" in digest.summary


def test_reasoning_failure_falls_back_to_deterministic() -> None:
    alerts = [_alert("SAN", AlertType.DOUBLE_TOP, -2.3)]
    digest = TriageAgent(FailingAnthropicClient()).synthesize(alerts)

    assert digest.fallback_used is True
    assert digest.model == "deterministic-fallback"
    assert len(digest.triaged_assets) == 1


def test_fallback_ranks_by_confluence_then_slope() -> None:
    alerts = [
        _alert("SAN", AlertType.DOUBLE_TOP, -2.3),
        _alert("SAN", AlertType.MM50_TOUCH, -2.3),
        _alert("TTE", AlertType.CONGESTION20, 3.0),
        _alert("AIR", AlertType.CONGESTION20, 0.2),
    ]
    digest = TriageAgent(FailingAnthropicClient()).synthesize(alerts)

    triaged = _by_code(digest.triaged_assets)
    assert triaged["SAN"].conviction == Conviction.HIGH
    assert triaged["SAN"].rank == 1
    assert "double_top" in triaged["SAN"].rationale
    assert triaged["TTE"].conviction == Conviction.WATCH
    assert triaged["TTE"].rank == 2
    assert triaged["AIR"].conviction == Conviction.NOISE
    assert triaged["AIR"].rank is None
    assert digest.counts == {"high": 1, "watch": 1, "noise": 1}


def test_fallback_treats_congestion20_and_100_as_one_family() -> None:
    # congestion20 and congestion100 are the same detector at two lookback
    # windows - they must not count as two distinct patterns toward
    # confluence, or a purely redundant hit gets wrongly promoted to HIGH.
    alerts = [
        _alert("SAN", AlertType.CONGESTION20, 0.5),
        _alert("SAN", AlertType.CONGESTION100, 0.5),
    ]
    digest = TriageAgent(
        FailingAnthropicClient(), slope_threshold=1.0
    ).synthesize(alerts)

    asset = digest.triaged_assets[0]
    assert asset.conviction == Conviction.NOISE
    assert asset.rank is None


def test_payload_carries_the_strength_of_a_directional_pattern() -> None:
    # The prompt ranks combo_weekly above combo. Without the strength beside
    # it, a weekly combo that met none of its criteria would present to the
    # model as the strongest signal on the board.
    alert = _directional_alert(
        "SAN", AlertType.COMBO_WEEKLY, 20.0, Direction.BUY
    )
    alert.data["strength"] = SignalStrength.WEAK.value

    agent = TriageAgent(FailingAnthropicClient())
    payload = json.loads(
        agent._build_payload(agent._group_by_asset([alert], {}))
    )

    asset = payload["assets"][0]
    assert asset["pattern_strengths"] == {"combo_weekly": "weak"}


def test_payload_omits_strength_when_no_detector_published_one() -> None:
    alert = _alert("SAN", AlertType.DOUBLE_TOP, 2.0)

    agent = TriageAgent(FailingAnthropicClient())
    payload = json.loads(
        agent._build_payload(agent._group_by_asset([alert], {}))
    )

    assert "pattern_strengths" not in payload["assets"][0]


def test_prompt_explains_what_a_strength_means() -> None:
    # The prompt is wrapped, so compare against collapsed whitespace rather
    # than guessing where a line breaks.
    prompt = " ".join(TRIAGE_SYSTEM_PROMPT.split())

    assert "pattern_strengths" in prompt
    assert "AT FULL STRENGTH" in prompt
    assert "met NONE of its scoring criteria" in prompt
    assert "reports that as no combo at all" in prompt


def test_fallback_treats_daily_and_weekly_combo_as_one_family() -> None:
    # combo and combo_weekly are one detector at two timeframes. Counted
    # separately they reach HIGH on one detector's word, and the fallback
    # reads no direction at all - so a Sell on both timeframes would rank as
    # the strongest kind of asset, which the long-only brief forbids.
    both = [
        _directional_alert("SAN", AlertType.COMBO, 4.0, Direction.SELL),
        _directional_alert("SAN", AlertType.COMBO_WEEKLY, 4.0, Direction.SELL),
    ]
    daily_only = [
        _directional_alert("TTE", AlertType.COMBO, 4.0, Direction.SELL),
    ]

    agent = TriageAgent(FailingAnthropicClient(), slope_threshold=1.0)
    both_asset = agent.synthesize(both).triaged_assets[0]
    daily_asset = agent.synthesize(daily_only).triaged_assets[0]

    assert both_asset.conviction == daily_asset.conviction
    assert both_asset.conviction != Conviction.HIGH


def test_fallback_does_not_let_mm7_break_promote_to_high() -> None:
    # mm7_break is a short-term timing trigger, and crossing the MM7 is
    # ordinary - if it counted toward confluence it would promote every
    # single-pattern WATCH asset that happened to cross, inflating the tier
    # the prompt explicitly tells the reasoning path not to inflate.
    alerts = [
        _alert("SAN", AlertType.CONGESTION20, 3.0),
        _alert("SAN", AlertType.MM7_BREAK, 3.0),
    ]
    digest = TriageAgent(
        FailingAnthropicClient(), slope_threshold=1.0
    ).synthesize(alerts)

    asset = digest.triaged_assets[0]
    assert asset.conviction == Conviction.WATCH
    assert "mm7_break" in asset.rationale


def test_fallback_treats_a_lone_mm7_break_as_noise() -> None:
    alerts = [_alert("SAN", AlertType.MM7_BREAK, 8.0)]
    digest = TriageAgent(
        FailingAnthropicClient(), slope_threshold=1.0
    ).synthesize(alerts)

    asset = digest.triaged_assets[0]
    assert asset.conviction == Conviction.NOISE
    assert asset.rank is None


def test_fallback_still_promotes_two_structural_patterns() -> None:
    alerts = [
        _alert("SAN", AlertType.DOUBLE_TOP, -2.3),
        _alert("SAN", AlertType.MM50_TOUCH, -2.3),
        _alert("SAN", AlertType.MM7_BREAK, -2.3),
    ]
    digest = TriageAgent(FailingAnthropicClient()).synthesize(alerts)

    assert digest.triaged_assets[0].conviction == Conviction.HIGH


def test_fallback_slope_threshold_is_configurable() -> None:
    alerts = [_alert("TTE", AlertType.CONGESTION20, 1.5)]

    strict = TriageAgent(
        FailingAnthropicClient(), slope_threshold=2.0
    ).synthesize(alerts)
    assert strict.triaged_assets[0].conviction == Conviction.NOISE

    lenient = TriageAgent(
        FailingAnthropicClient(), slope_threshold=1.0
    ).synthesize(alerts)
    assert lenient.triaged_assets[0].conviction == Conviction.WATCH


def _triaged_asset(
    code: str, conviction: Conviction, rank: int | None = None
) -> TriagedAsset:
    return TriagedAsset(
        asset_code=code,
        asset_description=f"{code} SA",
        exchange="saxo",
        conviction=conviction,
        rationale="double top + MA50 rejection",
        patterns=[AlertType.DOUBLE_TOP],
        ma50_slope=-2.3,
        rank=rank,
        country_code="xpar",
    )


def test_format_slack_digest_no_signals_returns_summary() -> None:
    digest = AlertDigest(
        run_date="2026-07-16",
        created_at=1768579200,
        summary="No signals detected today.",
        counts={"high": 0, "watch": 0, "noise": 0},
        triaged_assets=[],
        model="claude-sonnet-5",
        fallback_used=False,
    )

    message = format_slack_digest(digest, "https://app.example.com")

    assert message == "No signals detected today."


def test_format_slack_digest_includes_counts_top_names_and_link() -> None:
    digest = AlertDigest(
        run_date="2026-07-16",
        created_at=1768579200,
        summary="28 signals across 22 stocks.",
        counts={"high": 2, "watch": 1, "noise": 20},
        triaged_assets=[
            _triaged_asset("SAN", Conviction.HIGH, rank=1),
            _triaged_asset("TTE", Conviction.HIGH, rank=2),
            _triaged_asset("AIR", Conviction.WATCH, rank=3),
        ],
        model="claude-sonnet-5",
        fallback_used=False,
    )

    message = format_slack_digest(digest, "https://app.example.com")

    assert "2 high, 1 watch, 20 filtered" in message
    assert "SAN" in message
    assert "TTE" in message
    assert message.index("SAN") < message.index("TTE")
    assert "AIR" not in message.split("\n")[1]
    assert message.endswith("https://app.example.com")
    assert "fallback" not in message


def test_format_slack_digest_flags_fallback() -> None:
    digest = AlertDigest(
        run_date="2026-07-16",
        created_at=1768579200,
        summary="1 high",
        counts={"high": 1, "watch": 0, "noise": 0},
        triaged_assets=[_triaged_asset("SAN", Conviction.HIGH, rank=1)],
        model="deterministic-fallback",
        fallback_used=True,
    )

    message = format_slack_digest(digest, "https://app.example.com")

    assert "fallback ranking" in message


def test_format_slack_digest_handles_no_high_assets() -> None:
    digest = AlertDigest(
        run_date="2026-07-16",
        created_at=1768579200,
        summary="1 watch",
        counts={"high": 0, "watch": 1, "noise": 0},
        triaged_assets=[_triaged_asset("SAN", Conviction.WATCH, rank=1)],
        model="claude-sonnet-5",
        fallback_used=False,
    )

    message = format_slack_digest(digest, "https://app.example.com")

    assert "Top:" not in message
    assert "0 high, 1 watch, 0 filtered" in message


def _trigger(
    workflow_name: str = "SAN breakout H1",
    direction: Direction = Direction.BUY,
    dry_run: bool = False,
    placed_at: int = 1785412200,
) -> WorkflowTrigger:
    return WorkflowTrigger(
        workflow_name=workflow_name,
        direction=direction,
        order_price=158.4,
        placed_at=placed_at,
        dry_run=dry_run,
        trigger_close=157.9,
    )


def _payload_assets(client: FakeAnthropicClient) -> Dict[str, Any]:
    return {
        asset["id"]: asset
        for asset in json.loads(client.last_payload)["assets"]
    }


def test_payload_omits_pattern_directions_when_no_directional_pattern_fired() -> (  # noqa: E501
    None
):
    client = FakeAnthropicClient({"summary": "s", "assets": []})
    agent = TriageAgent(client)

    agent.synthesize([_alert("SAN", AlertType.CONGESTION20, 3.0)])

    assert "pattern_directions" not in _payload_assets(client)["SAN_xpar"]


def test_payload_carries_the_direction_of_directional_patterns() -> None:
    client = FakeAnthropicClient({"summary": "s", "assets": []})
    agent = TriageAgent(client)

    agent.synthesize(
        [
            _directional_alert("SAN", AlertType.COMBO, -2.0, Direction.SELL),
            _directional_alert(
                "SAN", AlertType.MM7_BREAK, -2.0, Direction.BUY
            ),
            _alert("SAN", AlertType.CONGESTION20, -2.0),
        ]
    )

    directions = _payload_assets(client)["SAN_xpar"]["pattern_directions"]
    assert directions == {
        AlertType.COMBO.value: Direction.SELL.value,
        AlertType.MM7_BREAK.value: Direction.BUY.value,
    }


def test_payload_ignores_a_direction_on_a_non_directional_pattern() -> None:
    client = FakeAnthropicClient({"summary": "s", "assets": []})
    agent = TriageAgent(client)

    agent.synthesize(
        [_directional_alert("SAN", AlertType.DOUBLE_TOP, -2.0, Direction.SELL)]
    )

    assert "pattern_directions" not in _payload_assets(client)["SAN_xpar"]


def test_payload_marks_a_directional_pattern_that_published_no_direction() -> (
    None
):
    client = FakeAnthropicClient({"summary": "s", "assets": []})
    agent = TriageAgent(client)

    agent.synthesize([_alert("SAN", AlertType.COMBO, -4.0)])

    directions = _payload_assets(client)["SAN_xpar"]["pattern_directions"]
    assert directions == {AlertType.COMBO.value: "unknown"}


def test_payload_marks_an_unparseable_direction_unknown() -> None:
    client = FakeAnthropicClient({"summary": "s", "assets": []})
    agent = TriageAgent(client)
    alert = _alert("SAN", AlertType.MM7_BREAK, -4.0)
    alert.data["direction"] = "sideways"

    agent.synthesize([alert])

    directions = _payload_assets(client)["SAN_xpar"]["pattern_directions"]
    assert directions == {AlertType.MM7_BREAK.value: "unknown"}


def test_a_missing_direction_is_logged_rather_than_absorbed(caplog) -> None:
    client = FakeAnthropicClient({"summary": "s", "assets": []})
    agent = TriageAgent(client)

    with caplog.at_level(logging.WARNING):
        agent.synthesize([_alert("SAN", AlertType.COMBO, -4.0)])

    assert "published no usable direction" in caplog.text


def test_payload_omits_workflow_triggers_when_there_are_none() -> None:
    client = FakeAnthropicClient({"summary": "s", "assets": []})
    agent = TriageAgent(client)

    agent.synthesize([_alert("SAN", AlertType.COMBO, 3.0)])

    assert "workflow_triggers" not in _payload_assets(client)["SAN_xpar"]


def test_payload_carries_workflow_triggers_when_present() -> None:
    client = FakeAnthropicClient({"summary": "s", "assets": []})
    agent = TriageAgent(client)

    agent.synthesize(
        [_alert("SAN", AlertType.COMBO, 3.0)],
        {"SAN_xpar": [_trigger()]},
    )

    payload_trigger = _payload_assets(client)["SAN_xpar"]["workflow_triggers"][
        0
    ]
    assert payload_trigger["workflow"] == "SAN breakout H1"
    assert payload_trigger["direction"] == Direction.BUY.value
    assert payload_trigger["dry_run"] is False
    assert "hour" in payload_trigger


def test_payload_marks_dry_run_triggers() -> None:
    client = FakeAnthropicClient({"summary": "s", "assets": []})
    agent = TriageAgent(client)

    agent.synthesize(
        [_alert("SAN", AlertType.COMBO, 3.0)],
        {"SAN_xpar": [_trigger(dry_run=True)]},
    )

    assert (
        _payload_assets(client)["SAN_xpar"]["workflow_triggers"][0]["dry_run"]
        is True
    )


def test_triggers_are_reattached_even_though_the_model_never_echoes_them() -> (
    None
):
    client = FakeAnthropicClient(
        {
            "summary": "s",
            "assets": [
                {
                    "id": "SAN_xpar",
                    "conviction": "high",
                    "rank": 1,
                    "rationale": "combo plus the SAN breakout H1 workflow",
                }
            ],
        }
    )
    agent = TriageAgent(client)

    digest = agent.synthesize(
        [_alert("SAN", AlertType.COMBO, 3.0)],
        {"SAN_xpar": [_trigger()]},
    )

    asset = _by_code(digest.triaged_assets)["SAN"]
    assert [t.workflow_name for t in asset.workflow_triggers] == [
        "SAN breakout H1"
    ]
    assert asset.workflow_triggers[0].direction == Direction.BUY


def test_assets_without_triggers_get_an_empty_list() -> None:
    client = FakeAnthropicClient({"summary": "s", "assets": []})
    agent = TriageAgent(client)

    digest = agent.synthesize(
        [
            _alert("SAN", AlertType.COMBO, 3.0),
            _alert("AI", AlertType.COMBO, 3.0),
        ],
        {"SAN_xpar": [_trigger()]},
    )

    by_code = _by_code(digest.triaged_assets)
    assert by_code["AI"].workflow_triggers == []
    assert len(by_code["SAN"].workflow_triggers) == 1


def test_triggers_never_introduce_an_asset_into_the_digest() -> None:
    client = FakeAnthropicClient({"summary": "s", "assets": []})
    agent = TriageAgent(client)

    digest = agent.synthesize(
        [_alert("SAN", AlertType.COMBO, 3.0)],
        {"GLE_xpar": [_trigger("GLE breakout")]},
    )

    assert [t.asset_code for t in digest.triaged_assets] == ["SAN"]


def test_several_triggers_on_one_asset_are_all_carried() -> None:
    client = FakeAnthropicClient({"summary": "s", "assets": []})
    agent = TriageAgent(client)

    digest = agent.synthesize(
        [_alert("SAN", AlertType.COMBO, 3.0)],
        {
            "SAN_xpar": [
                _trigger("first"),
                _trigger("second", direction=Direction.SELL),
            ]
        },
    )

    asset = _by_code(digest.triaged_assets)["SAN"]
    assert [t.workflow_name for t in asset.workflow_triggers] == [
        "first",
        "second",
    ]


def test_synthesize_without_triggers_matches_pre_feature_behaviour() -> None:
    response = {
        "summary": "one setup",
        "assets": [
            {
                "id": "SAN_xpar",
                "conviction": "high",
                "rank": 1,
                "rationale": "combo on a rising trend",
            }
        ],
    }
    alerts = [
        _alert("SAN", AlertType.COMBO, 3.0),
        _alert("AI", AlertType.CONGESTION20, 0.1),
    ]

    without = TriageAgent(FakeAnthropicClient(dict(response))).synthesize(
        alerts
    )
    with_empty = TriageAgent(FakeAnthropicClient(dict(response))).synthesize(
        alerts, {}
    )

    assert without.summary == with_empty.summary
    assert without.counts == with_empty.counts
    for left, right in zip(without.triaged_assets, with_empty.triaged_assets):
        assert left.asset_code == right.asset_code
        assert left.conviction == right.conviction
        assert left.rank == right.rank
        assert left.rationale == right.rationale
        assert left.workflow_triggers == [] == right.workflow_triggers


def test_prompt_documents_the_payload_keys_it_will_receive() -> None:
    assert "workflow_triggers" in TRIAGE_SYSTEM_PROMPT
    assert "dry_run" in TRIAGE_SYSTEM_PROMPT
    assert "pattern_directions" in TRIAGE_SYSTEM_PROMPT


def test_prompt_states_the_long_only_mandate() -> None:
    assert "LONG-ONLY MANDATE" in TRIAGE_SYSTEM_PROMPT
    assert "It never shorts." in TRIAGE_SYSTEM_PROMPT


def test_prompt_documents_the_unknown_direction_marker() -> None:
    assert "DISQUALIFYING UNTIL PROVEN BULLISH" in TRIAGE_SYSTEM_PROMPT


def test_prompt_tiers_an_early_bullish_signal_on_a_falling_trend() -> None:
    assert "an EARLY bullish signal on a still-falling 50-MA" in (
        TRIAGE_SYSTEM_PROMPT
    )
    assert "on a flat, falling or unknown trend" in TRIAGE_SYSTEM_PROMPT


def test_prompt_caps_a_bearish_read_below_high() -> None:
    assert "a bearish read never reaches this tier" in TRIAGE_SYSTEM_PROMPT
    assert 'Its ceiling is "watch"' in TRIAGE_SYSTEM_PROMPT


def test_prompt_documents_every_alert_type_it_can_receive() -> None:
    for alert_type in AlertType:
        assert alert_type.value in TRIAGE_SYSTEM_PROMPT


def test_fallback_carries_triggers_onto_the_triaged_asset() -> None:
    agent = TriageAgent(FailingAnthropicClient())

    digest = agent.synthesize(
        [_alert("SAN", AlertType.COMBO, 3.0)],
        {"SAN_xpar": [_trigger()]},
    )

    asset = _by_code(digest.triaged_assets)["SAN"]
    assert digest.fallback_used is True
    assert len(asset.workflow_triggers) == 1


def test_run_date_is_computed_in_paris_not_utc() -> None:
    paris_today = datetime.datetime.now(ZoneInfo("Europe/Paris")).strftime(
        "%Y-%m-%d"
    )

    assert current_run_date() == paris_today


def test_synthesize_honours_an_explicit_run_date() -> None:
    client = FakeAnthropicClient({"summary": "s", "assets": []})
    agent = TriageAgent(client)

    digest = agent.synthesize(
        [_alert("SAN", AlertType.COMBO, 3.0)], None, run_date="2026-01-15"
    )

    assert digest.run_date == "2026-01-15"


def test_synthesize_falls_back_to_the_paris_run_date() -> None:
    client = FakeAnthropicClient({"summary": "s", "assets": []})
    agent = TriageAgent(client)

    digest = agent.synthesize([_alert("SAN", AlertType.COMBO, 3.0)])

    assert digest.run_date == current_run_date()


def _triaged(
    code: str,
    conviction: Conviction,
    rank: int,
    triggers: Optional[List[WorkflowTrigger]] = None,
) -> TriagedAsset:
    return TriagedAsset(
        asset_code=code,
        asset_description=f"{code} SA",
        exchange="saxo",
        conviction=conviction,
        rationale="r",
        patterns=[AlertType.COMBO],
        ma50_slope=3.0,
        rank=rank,
        country_code="xpar",
        workflow_triggers=triggers or [],
    )


def _slack_digest(assets: List[TriagedAsset]) -> AlertDigest:
    counts = {c.value: 0 for c in Conviction}
    for asset in assets:
        counts[asset.conviction.value] += 1
    return AlertDigest(
        run_date="2026-08-01",
        created_at=1,
        summary="s",
        counts=counts,
        triaged_assets=assets,
        model="test-model",
    )


def test_slack_digest_marks_corroborated_high_assets() -> None:
    digest = _slack_digest(
        [
            _triaged("SAN", Conviction.HIGH, 1, [_trigger()]),
            _triaged("AI", Conviction.HIGH, 2),
        ]
    )

    message = format_slack_digest(digest, "http://app")

    assert "SAN SA (SAN) ⚡" in message
    assert "AI SA (AI)" in message
    assert message.count("⚡") == 1
    assert "Also corroborated" not in message


def test_slack_digest_names_corroborated_watch_assets() -> None:
    digest = _slack_digest(
        [
            _triaged("SAN", Conviction.HIGH, 1, [_trigger()]),
            _triaged("AI", Conviction.WATCH, 2, [_trigger("AI rule")]),
        ]
    )

    message = format_slack_digest(digest, "http://app")

    # Every bolt in the message points at a named asset: SAN carries one in
    # the Top line, AI is named on its own line rather than folded into a
    # count the reader cannot resolve.
    assert "SAN SA (SAN) ⚡" in message
    assert "⚡ Also corroborated: AI SA (AI)" in message
    assert message.count("⚡") == 2


def test_slack_digest_ignores_triggers_on_noise_assets() -> None:
    digest = _slack_digest(
        [
            _triaged("SAN", Conviction.HIGH, 1),
            _triaged("AI", Conviction.NOISE, 0, [_trigger("AI rule")]),
        ]
    )

    message = format_slack_digest(digest, "http://app")

    assert "Also corroborated" not in message
    assert "⚡" not in message


def test_slack_digest_unchanged_when_nothing_is_corroborated() -> None:
    digest = _slack_digest([_triaged("SAN", Conviction.HIGH, 1)])

    message = format_slack_digest(digest, "http://app")

    assert "⚡" not in message
    assert "Top: SAN SA (SAN)" in message


def test_fallback_counts_a_trigger_as_one_confluence_point() -> None:
    # One structural pattern alone is at most WATCH; the trigger supplies the
    # second independent point that lifts it to HIGH.
    agent = TriageAgent(FailingAnthropicClient())

    digest = agent.synthesize(
        [_alert("SAN", AlertType.COMBO, 3.0)],
        {"SAN_xpar": [_trigger()]},
    )

    assert _by_code(digest.triaged_assets)["SAN"].conviction == (
        Conviction.HIGH
    )


def test_fallback_without_a_trigger_stays_watch() -> None:
    agent = TriageAgent(FailingAnthropicClient())

    digest = agent.synthesize([_alert("SAN", AlertType.COMBO, 3.0)])

    assert _by_code(digest.triaged_assets)["SAN"].conviction == (
        Conviction.WATCH
    )


def test_fallback_counts_several_triggers_as_one_point() -> None:
    # A-004: corroboration breaks ties, it does not multiply. Two triggers on
    # an asset with no structural pattern must not reach HIGH.
    agent = TriageAgent(FailingAnthropicClient())

    digest = agent.synthesize(
        [_alert("SAN", AlertType.MM7_BREAK, 3.0)],
        {"SAN_xpar": [_trigger("first"), _trigger("second")]},
    )

    assert _by_code(digest.triaged_assets)["SAN"].conviction == (
        Conviction.WATCH
    )


def test_fallback_ranks_a_corroborated_asset_above_an_equivalent_one() -> None:
    agent = TriageAgent(FailingAnthropicClient())

    digest = agent.synthesize(
        [
            _alert("AI", AlertType.COMBO, 3.0),
            _alert("SAN", AlertType.COMBO, 3.0),
        ],
        {"SAN_xpar": [_trigger()]},
    )

    by_code = _by_code(digest.triaged_assets)
    assert by_code["SAN"].rank == 1
    assert by_code["AI"].rank == 2


def test_fallback_rationale_names_the_workflow() -> None:
    agent = TriageAgent(FailingAnthropicClient())

    digest = agent.synthesize(
        [_alert("SAN", AlertType.COMBO, 3.0)],
        {"SAN_xpar": [_trigger()]},
    )

    rationale = _by_code(digest.triaged_assets)["SAN"].rationale
    assert "workflow SAN breakout H1 (BUY)" in rationale
    assert digest.fallback_used is True


def test_fallback_rationale_marks_a_dry_run_workflow() -> None:
    agent = TriageAgent(FailingAnthropicClient())

    digest = agent.synthesize(
        [_alert("SAN", AlertType.COMBO, 3.0)],
        {"SAN_xpar": [_trigger(dry_run=True)]},
    )

    rationale = _by_code(digest.triaged_assets)["SAN"].rationale
    assert "dry run" in rationale


def test_fallback_rationale_unchanged_when_nothing_is_corroborated() -> None:
    agent = TriageAgent(FailingAnthropicClient())

    digest = agent.synthesize([_alert("SAN", AlertType.COMBO, 3.0)])

    rationale = _by_code(digest.triaged_assets)["SAN"].rationale
    assert rationale == "1 pattern(s): combo, slope 3.0%"
    assert "workflow" not in rationale


def test_fallback_withholds_the_point_from_a_contradicting_trigger() -> None:
    # The prompt calls a trigger against the read a red flag, not confluence.
    # The fallback must not invert that: a bullish combo on a rising trend,
    # with the trader's own rule firing Sell, is not a stronger case than the
    # same setup with no trigger at all.
    agent = TriageAgent(FailingAnthropicClient())

    digest = agent.synthesize(
        [_alert("SAN", AlertType.COMBO, 3.0)],
        {"SAN_xpar": [_trigger(direction=Direction.SELL)]},
    )

    assert _by_code(digest.triaged_assets)["SAN"].conviction == (
        Conviction.WATCH
    )


def test_fallback_credits_a_sell_trigger_on_a_falling_trend() -> None:
    agent = TriageAgent(FailingAnthropicClient())

    digest = agent.synthesize(
        [_alert("SAN", AlertType.COMBO, -3.0)],
        {"SAN_xpar": [_trigger(direction=Direction.SELL)]},
    )

    assert _by_code(digest.triaged_assets)["SAN"].conviction == (
        Conviction.HIGH
    )


def test_fallback_contradicting_trigger_does_not_outrank_a_clean_read() -> (
    None
):
    agent = TriageAgent(FailingAnthropicClient())

    digest = agent.synthesize(
        [
            _alert("SAN", AlertType.COMBO, 3.0),
            _alert("AI", AlertType.COMBO, 3.0),
        ],
        {"SAN_xpar": [_trigger(direction=Direction.SELL)]},
    )

    by_code = _by_code(digest.triaged_assets)
    assert by_code["SAN"].conviction == by_code["AI"].conviction


def test_fallback_withholds_the_point_from_a_dry_run_trigger() -> None:
    # "One step lower than a live trigger" in an integer tally means no point:
    # paper capital must not lift an asset into the top tier.
    agent = TriageAgent(FailingAnthropicClient())

    digest = agent.synthesize(
        [_alert("SAN", AlertType.COMBO, 3.0)],
        {"SAN_xpar": [_trigger(dry_run=True)]},
    )

    assert _by_code(digest.triaged_assets)["SAN"].conviction == (
        Conviction.WATCH
    )


def test_fallback_withholds_the_point_from_conflicting_triggers() -> None:
    agent = TriageAgent(FailingAnthropicClient())

    digest = agent.synthesize(
        [_alert("SAN", AlertType.COMBO, 3.0)],
        {
            "SAN_xpar": [
                _trigger("first", direction=Direction.BUY),
                _trigger("second", direction=Direction.SELL),
            ]
        },
    )

    assert _by_code(digest.triaged_assets)["SAN"].conviction == (
        Conviction.WATCH
    )


def test_fallback_withholds_the_point_when_the_trend_is_unknown() -> None:
    agent = TriageAgent(FailingAnthropicClient())
    alert = _alert("SAN", AlertType.COMBO, 0.0)
    alert.data = {}

    digest = agent.synthesize([alert], {"SAN_xpar": [_trigger()]})

    assert _by_code(digest.triaged_assets)["SAN"].conviction == (
        Conviction.NOISE
    )


def test_fallback_rationale_says_timing_only_instead_of_zero_patterns() -> (
    None
):
    agent = TriageAgent(FailingAnthropicClient())

    digest = agent.synthesize(
        [_alert("SAN", AlertType.MM7_BREAK, 3.0)],
        {"SAN_xpar": [_trigger()]},
    )

    rationale = _by_code(digest.triaged_assets)["SAN"].rationale
    assert rationale.startswith("timing only: mm7_break")
    assert "0 pattern(s)" not in rationale


def test_fallback_rationale_uses_the_stored_direction_casing() -> None:
    # Slack and the Daily Brief both render the stored BUY/SELL form; the
    # rationale sits beside them on the same screen.
    agent = TriageAgent(FailingAnthropicClient())

    digest = agent.synthesize(
        [_alert("SAN", AlertType.COMBO, 3.0)],
        {"SAN_xpar": [_trigger()]},
    )

    assert "(BUY)" in _by_code(digest.triaged_assets)["SAN"].rationale


class TestWeeklyComboReachesTheReasoningPath:
    """
    What the model concludes is not deterministic, so these pin the two
    halves that are: the payload carries everything the ranking rules need,
    and the prompt states those rules. Between them they are what SC-006
    rests on.
    """

    def _agent_and_payload(self, alerts):
        client = FakeAnthropicClient({"summary": "s", "assets": []})
        TriageAgent(client).synthesize(alerts)
        return _payload_assets(client)

    def test_a_buy_weekly_arrives_with_its_direction_and_strength(self):
        alert = _directional_alert(
            "SAN", AlertType.COMBO_WEEKLY, 20.0, Direction.BUY
        )
        alert.data["strength"] = SignalStrength.STRONG.value

        assets = self._agent_and_payload([alert])

        asset = assets["SAN_xpar"]
        assert "combo_weekly" in asset["patterns"]
        assert asset["pattern_directions"]["combo_weekly"] == "Buy"
        assert asset["pattern_strengths"]["combo_weekly"] == "strong"

    def test_a_sell_weekly_arrives_as_a_sell(self):
        """The long-only gate is applied by the model, so the payload has to
        show it a Sell rather than leave it inferring one from the slope."""
        alert = _directional_alert(
            "SAN", AlertType.COMBO_WEEKLY, -20.0, Direction.SELL
        )

        assets = self._agent_and_payload([alert])

        assert assets["SAN_xpar"]["pattern_directions"]["combo_weekly"] == (
            "Sell"
        )

    def test_a_timeframe_disagreement_arrives_as_two_directions(self):
        """FR-009 asks the rationale to name the conflict; it can only do
        that if both directions reach the model separately."""
        alerts = [
            _directional_alert(
                "SAN", AlertType.COMBO_WEEKLY, 20.0, Direction.BUY
            ),
            _directional_alert("SAN", AlertType.COMBO, 20.0, Direction.SELL),
        ]

        assets = self._agent_and_payload(alerts)

        directions = assets["SAN_xpar"]["pattern_directions"]
        assert directions["combo_weekly"] == "Buy"
        assert directions["combo"] == "Sell"

    def test_the_prompt_states_the_rules_the_payload_serves(self):
        prompt = " ".join(TRIAGE_SYSTEM_PROMPT.split())

        # Ranked above daily, and the timeframe named in the rationale.
        assert 'it ranks ABOVE a "Buy" combo' in prompt
        assert "say the signal is on the WEEKLY timeframe" in prompt
        # Long-only: a Sell disqualifies whichever timeframe it sits on.
        assert (
            '"Sell" combo_weekly disqualifies the asset as a long exactly as'
            in prompt
        )
        # The disagreement is named rather than silently resolved.
        assert (
            "When combo and combo_weekly disagree, NAME the disagreement"
            in prompt
        )
