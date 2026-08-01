import datetime
from typing import Any, Dict, List, Optional

from client.anthropic_client import AnthropicClient
from model import Alert, AlertDigest, AlertType, Conviction, TriagedAsset
from services.alert_triage_service import TriageAgent, format_slack_digest
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
