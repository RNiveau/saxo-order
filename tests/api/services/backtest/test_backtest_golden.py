"""Golden (characterization) tests for the backtest service.

Runs every registered backtest definition over a fixed synthetic market
(tests.api.services.backtest.market_fixture) and compares the full result -
range summary, per-day rows, and every trade of a traded day - against a
committed snapshot. Unlike the unit tests, this asserts nothing about *how*
the service is structured, so it stays valid across the refactor and is the
net that proves behavior is unchanged.

Regenerate the snapshot only when a behavior change is intended:

    poetry run python -m tests.api.services.backtest.test_backtest_golden

That writes new definitions freely but REFUSES to change one already in
the file, printing what moved instead. Changing a shipped definition
needs its code named:

    ... test_backtest_golden --accept G9H,B9HTC

Regenerating makes this file pass by construction, so the gate is the
only thing standing between "I regenerated it" and a silent behavior
change nobody reviewed.
"""

import dataclasses
import datetime
import json
from pathlib import Path
from typing import Any, Dict

import pytest
import pytest_asyncio

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

# Day the detail snapshot is taken on. Picked because every definition -
# including the three combo ones, whose positions can span days - resolves
# it to a traded day, so the per-trade detail is non-trivial everywhere.
DETAIL_DATE = datetime.date(2026, 4, 10)


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


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def snapshot() -> Dict[str, Any]:
    """The freshly computed snapshot, built once for the module - every
    assertion reads the same run rather than re-running four range
    backtests per parametrized case."""
    return await _build_snapshot()


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
async def test_definition_matches_golden_snapshot(code, golden, snapshot):
    """Every definition's full range run and detail day are byte-identical
    to the committed snapshot."""
    assert (
        code in golden
    ), f"No golden entry for definition {code} - regenerate the snapshot"
    assert snapshot[code] == golden[code]


async def test_golden_market_actually_produces_trades(snapshot):
    """Guards the net itself: a snapshot of all-zero runs would pass every
    comparison while testing nothing."""
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


def _summary_line(code: str, entry: Dict[str, Any]) -> str:
    summary = entry["run"]["summary"]
    return (
        f"{code}: {summary['number_of_days']} days, "
        f"{summary['number_of_trades']} trades, "
        f"result {summary['final_result']}, "
        f"exits {sorted(entry['exit_reasons'])}"
    )


def _describe_change(
    code: str, before: Dict[str, Any], after: Dict[str, Any]
) -> str:
    """What moved for one definition, in the terms a reviewer judges a
    strategy change in: trade count, result and the exit mix."""
    old_summary = before["run"]["summary"]
    new_summary = after["run"]["summary"]
    fields = (
        "number_of_trades",
        "number_of_winning_positions",
        "number_of_losing_positions",
        "number_of_be",
        "final_result",
    )
    moved = [
        f"      {field}: {old_summary[field]} -> {new_summary[field]}"
        for field in fields
        if old_summary[field] != new_summary[field]
    ]
    if set(before["exit_reasons"]) != set(after["exit_reasons"]):
        moved.append(
            f"      exits: {sorted(before['exit_reasons'])} -> "
            f"{sorted(after['exit_reasons'])}"
        )
    if not moved:
        moved.append(
            "      summary identical - the per-day rows or per-trade "
            "detail moved"
        )
    return f"    {code}\n" + "\n".join(moved)


def _regenerate(accepted: set) -> int:
    """Rewrite the snapshot, refusing to change an existing definition
    that was not named on the command line.

    The whole value of this file is that it fails when behavior moves -
    and regenerating makes it pass by construction. So a regeneration
    that would silently rewrite a shipped definition's numbers is the one
    thing that must not be one keystroke away. Adding a definition is
    free; changing one has to be said out loud.
    """
    import asyncio
    import logging

    # NO_CACHE_CLIENT logs a warning per cache call, which is two per
    # definition per day - tens of thousands of lines burying the one
    # thing this command exists to show.
    logging.disable(logging.WARNING)

    snapshot = asyncio.run(_build_snapshot())
    golden = (
        json.loads(GOLDEN_FILE.read_text()) if GOLDEN_FILE.exists() else {}
    )

    added = sorted(set(snapshot) - set(golden))
    removed = sorted(set(golden) - set(snapshot))
    changed = sorted(
        code
        for code in set(golden) & set(snapshot)
        if golden[code] != snapshot[code]
    )
    unauthorized = [
        code
        for code in changed
        if code not in accepted and "all" not in accepted
    ]

    if unauthorized:
        print(
            "REFUSED: these definitions already exist in the snapshot and "
            "their results changed:\n"
        )
        for code in unauthorized:
            print(_describe_change(code, golden[code], snapshot[code]))
        print(
            "\nIf the change is intended, name them:\n"
            f"    python -m {__spec__.name} --accept "
            f"{','.join(unauthorized)}\n"
            "If it is not, this is the regression the snapshot exists to "
            "catch - fix the code, not the file."
        )
        return 1

    GOLDEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN_FILE.write_text(json.dumps(snapshot, indent=2, sort_keys=True))
    print(f"Wrote {GOLDEN_FILE}")
    if added:
        print(f"  added: {', '.join(added)}")
    if removed:
        print(f"  removed: {', '.join(removed)}")
    if changed:
        print(f"  changed (accepted): {', '.join(changed)}")
        for code in changed:
            print(_describe_change(code, golden[code], snapshot[code]))
    if not (added or removed or changed):
        print("  no change")
    for code, entry in snapshot.items():
        print(f"  {_summary_line(code, entry)}")
    return 0


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description=(
            "Regenerate the backtest golden snapshot. New definitions are "
            "written freely; changing an existing one requires naming it."
        )
    )
    parser.add_argument(
        "--accept",
        default="",
        help=(
            "Comma-separated definition codes whose results may change, "
            "or 'all'."
        ),
    )
    args = parser.parse_args()
    sys.exit(
        _regenerate(
            {code.strip() for code in args.accept.split(",") if code.strip()}
        )
    )
