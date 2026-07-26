"""Golden (characterization) tests for the backtest service.

Runs every registered backtest definition over a fixed synthetic market
(tests.api.services.backtest.market_fixture) and compares the full result -
range summary, per-day rows, and every trade of a traded day - against a
committed snapshot. Unlike the unit tests, this asserts nothing about *how*
the service is structured, so it stays valid across the refactor and is the
net that proves behavior is unchanged.

Regenerate the snapshot only when a behavior change is intended:

    poetry run python -m tests.api.services.backtest.test_backtest_golden
"""

import dataclasses
import datetime
import json
from pathlib import Path
from typing import Any, Dict

import pytest

from api.services.backtest import (
    BACKTEST_DEFINITIONS,
    BacktestService,
    resolve_parameters,
)
from client.aws_client import DynamoDBClient
from tests.api.services.backtest.market_fixture import (
    GOLDEN_END,
    GOLDEN_START,
    golden_candles_service,
)

GOLDEN_FILE = (
    Path(__file__).resolve().parents[1] / "files" / "backtest_golden.json"
)

# A DynamoDBClient with no active resource: every cache call degrades to a
# miss/no-op, so the golden run always exercises the fetch path.
NO_CACHE_CLIENT = DynamoDBClient(dynamodb_resource=None)

# Day the detail snapshot is taken on. Picked because every definition
# resolves it to a traded day, so the per-trade detail is non-trivial.
DETAIL_DATE = datetime.date(2026, 3, 3)


def _service() -> BacktestService:
    return BacktestService(golden_candles_service(), NO_CACHE_CLIENT)


def _plain(value: Any) -> Any:
    """Dataclasses, enums, dates and floats as JSON-comparable values."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _plain(getattr(value, field.name))
            for field in dataclasses.fields(value)
        }
    if isinstance(value, list):
        return [_plain(item) for item in value]
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if isinstance(value, float):
        return round(value, 6)
    if hasattr(value, "value"):
        return value.value
    return value


async def _exit_reason_histogram(
    service: BacktestService, definition, params
) -> Dict[str, Any]:
    """Count and summed points per exit reason across the whole range.
    The range summary alone would not notice a trade being reclassified
    from, say, a time cut to an end-of-day exit at the same points."""
    histogram: Dict[str, Any] = {}
    current = GOLDEN_START
    while current <= GOLDEN_END:
        if current.weekday() < 5:
            day = await service.evaluate_day(definition, current, params)
            for trade in day.trades:
                entry = histogram.setdefault(
                    trade.exit_reason.value, {"count": 0, "points": 0.0}
                )
                entry["count"] += 1
                entry["points"] = round(entry["points"] + trade.points, 4)
        current += datetime.timedelta(days=1)
    return histogram


_SNAPSHOT_CACHE: Dict[str, Any] = {}


async def _snapshot() -> Dict[str, Any]:
    """The full snapshot, computed once per session - every assertion
    reads the same run rather than re-running four range backtests."""
    if not _SNAPSHOT_CACHE:
        _SNAPSHOT_CACHE.update(await _build_snapshot())
    return _SNAPSHOT_CACHE


async def _build_snapshot() -> Dict[str, Any]:
    snapshot: Dict[str, Any] = {}
    for definition in BACKTEST_DEFINITIONS:
        params = resolve_parameters(definition)
        service = _service()
        run = await service.run_range(
            definition, GOLDEN_START, GOLDEN_END, params
        )
        day = await service.evaluate_day(definition, DETAIL_DATE, params)
        snapshot[definition.code] = {
            "run": _plain(run),
            "exit_reasons": await _exit_reason_histogram(
                service, definition, params
            ),
            "day_detail": {
                "date": day.date.isoformat(),
                "status": day.status.value,
                "h1_high": _plain(day.h1_high),
                "h1_low": _plain(day.h1_low),
                "h1_open": _plain(day.h1_open),
                "candle_count": len(day.candles),
                "trades": _plain(day.trades),
            },
        }
    return snapshot


@pytest.fixture(scope="module")
def golden() -> Dict[str, Any]:
    if not GOLDEN_FILE.exists():
        pytest.fail(
            f"Missing golden snapshot {GOLDEN_FILE}. Regenerate with "
            "python -m tests.api.services.backtest.test_backtest_golden"
        )
    return json.loads(GOLDEN_FILE.read_text())


@pytest.mark.parametrize(
    "code", [definition.code for definition in BACKTEST_DEFINITIONS]
)
async def test_definition_matches_golden_snapshot(code, golden):
    """Every definition's full range run and detail day are byte-identical
    to the snapshot."""
    assert (
        code in golden
    ), f"No golden entry for definition {code} - regenerate the snapshot"
    actual = (await _snapshot())[code]
    assert actual == golden[code]


async def test_golden_market_actually_produces_trades():
    """Guards the net itself: a snapshot of all-zero runs would pass every
    comparison while testing nothing."""
    snapshot = await _snapshot()
    for code, entry in snapshot.items():
        assert entry["run"]["summary"]["number_of_trades"] > 0, (
            f"{code} produced no trades - the golden market is not "
            "exercising the strategy"
        )
        assert entry["day_detail"][
            "trades"
        ], f"{code} has no trades on the detail day {DETAIL_DATE}"

    # Each variant's own path must be reached, otherwise the snapshot
    # would happily lock in behavior the variant never exercises.
    assert "time_cut" in snapshot["B9HTC"]["exit_reasons"]
    assert any(
        day["status"] == "no_trade" for day in snapshot["B9HWS"]["run"]["days"]
    ), "the wide-range filter never rejected a day"
    assert any(
        trade["points"] > 0
        and trade["points"] != trade["exit_price"] - trade["entry_price"]
        for trade in snapshot["G9H"]["day_detail"]["trades"]
    ), "no two-lot aggregate trade in the double take-profit detail day"


def _regenerate() -> None:
    import asyncio

    GOLDEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    snapshot = asyncio.run(_snapshot())
    GOLDEN_FILE.write_text(json.dumps(snapshot, indent=2, sort_keys=True))
    print(f"Wrote {GOLDEN_FILE}")
    for code, entry in snapshot.items():
        summary = entry["run"]["summary"]
        print(
            f"  {code}: {summary['number_of_days']} days, "
            f"{summary['number_of_trades']} trades, "
            f"result {summary['final_result']}, "
            f"exits {sorted(entry['exit_reasons'])}"
        )


if __name__ == "__main__":
    _regenerate()
