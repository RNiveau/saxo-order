import datetime
import json
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


def test_fallback_ignores_triggers_for_now() -> None:
    agent = TriageAgent(FailingAnthropicClient())

    digest = agent.synthesize(
        [_alert("SAN", AlertType.COMBO, 3.0)],
        {"SAN_xpar": [_trigger()]},
    )

    asset = _by_code(digest.triaged_assets)["SAN"]
    assert digest.fallback_used is True
    assert len(asset.workflow_triggers) == 1
    assert asset.conviction == Conviction.WATCH


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
