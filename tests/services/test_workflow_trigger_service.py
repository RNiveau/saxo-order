import datetime
from decimal import Decimal
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

import pytest

from model import Alert, AlertType, Direction
from services.workflow_trigger_service import collect_todays_triggers

RUN_DATE = "2026-08-01"
PARIS = ZoneInfo("Europe/Paris")

# The scan runs at 18:15 Paris. Pinning "now" keeps the window bounds fixed:
# with a real clock these tests pass on RUN_DATE and start failing the next
# day, because the end bound moves while the fixtures do not.
FROZEN_NOW = datetime.datetime(2026, 8, 1, 18, 15, tzinfo=PARIS)


@pytest.fixture(autouse=True)
def frozen_clock(monkeypatch):
    monkeypatch.setattr(
        "services.workflow_trigger_service._now_paris", lambda: FROZEN_NOW
    )


def at_hour(hour: int, minute: int = 0) -> int:
    day = datetime.datetime.strptime(RUN_DATE, "%Y-%m-%d").date()
    return int(
        datetime.datetime.combine(
            day, datetime.time(hour, minute), tzinfo=PARIS
        ).timestamp()
    )


class FakeDynamoDBClient:
    def __init__(
        self,
        orders: List[Dict[str, Any]],
        workflows: List[Dict[str, Any]],
    ) -> None:
        self._orders = orders
        self._workflows = workflows

    async def get_all_workflow_orders(self) -> List[Dict[str, Any]]:
        return self._orders

    async def get_all_workflows(self) -> List[Dict[str, Any]]:
        return self._workflows


class RaisingDynamoDBClient:
    async def get_all_workflow_orders(self) -> List[Dict[str, Any]]:
        raise RuntimeError("DynamoDB unavailable")

    async def get_all_workflows(self) -> List[Dict[str, Any]]:
        raise RuntimeError("DynamoDB unavailable")


def alert(code: str = "AI", country_code: str = "xpar") -> Alert:
    return Alert(
        alert_type=AlertType.COMBO,
        date=datetime.datetime(2026, 8, 1, 18, 0),
        data={},
        asset_code=code,
        asset_description=f"{code} SA",
        country_code=country_code,
    )


def order(**overrides: Any) -> Dict[str, Any]:
    base = {
        "id": "order-1",
        "workflow_id": "wf-1",
        "workflow_name": "AI breakout H1",
        "placed_at": at_hour(14, 30),
        "order_code": "AIFP",
        "order_price": Decimal("158.4"),
        "order_quantity": Decimal("10"),
        "order_direction": "BUY",
        "order_type": "LIMIT",
        "trigger_close": Decimal("157.9"),
    }
    base.update(overrides)
    return base


def workflow(**overrides: Any) -> Dict[str, Any]:
    base = {
        "id": "wf-1",
        "name": "AI breakout H1",
        "index": "AI:xpar",
        "cfd": "AIFP",
        "enable": True,
        "dry_run": False,
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_resolves_trigger_to_the_alert_asset():
    client = FakeDynamoDBClient([order()], [workflow()])

    triggers = await collect_todays_triggers(client, RUN_DATE, [alert()])

    assert list(triggers) == ["AI_xpar"]
    trigger = triggers["AI_xpar"][0]
    assert trigger.workflow_name == "AI breakout H1"
    assert trigger.direction == Direction.BUY
    assert trigger.order_price == 158.4
    assert trigger.trigger_close == 157.9
    assert trigger.dry_run is False


@pytest.mark.asyncio
async def test_matches_bare_index_without_country_code():
    client = FakeDynamoDBClient([order()], [workflow(index="AI")])

    triggers = await collect_todays_triggers(client, RUN_DATE, [alert()])

    assert list(triggers) == ["AI_xpar"]


@pytest.mark.asyncio
async def test_matching_is_case_insensitive():
    client = FakeDynamoDBClient([order()], [workflow(index="ai:XPAR")])

    triggers = await collect_todays_triggers(client, RUN_DATE, [alert()])

    assert list(triggers) == ["AI_xpar"]


@pytest.mark.asyncio
async def test_drops_orders_placed_before_the_session():
    yesterday = at_hour(14, 30) - 24 * 3600
    client = FakeDynamoDBClient([order(placed_at=yesterday)], [workflow()])

    triggers = await collect_todays_triggers(client, RUN_DATE, [alert()])

    assert triggers == {}


@pytest.mark.asyncio
async def test_drops_orders_placed_after_now():
    tomorrow = at_hour(14, 30) + 24 * 3600
    client = FakeDynamoDBClient([order(placed_at=tomorrow)], [workflow()])

    triggers = await collect_todays_triggers(client, RUN_DATE, [alert()])

    assert triggers == {}


@pytest.mark.asyncio
async def test_drops_trigger_when_workflow_was_deleted():
    client = FakeDynamoDBClient([order(workflow_id="gone")], [workflow()])

    triggers = await collect_todays_triggers(client, RUN_DATE, [alert()])

    assert triggers == {}


@pytest.mark.asyncio
async def test_matches_on_order_code_when_index_does_not():
    client = FakeDynamoDBClient(
        [order(order_code="AI:xpar")], [workflow(index="something-else")]
    )

    triggers = await collect_todays_triggers(client, RUN_DATE, [alert()])

    assert list(triggers) == ["AI_xpar"]


@pytest.mark.asyncio
async def test_matches_on_bare_order_code():
    client = FakeDynamoDBClient(
        [order(order_code="AI")], [workflow(index="something-else")]
    )

    triggers = await collect_todays_triggers(client, RUN_DATE, [alert()])

    assert list(triggers) == ["AI_xpar"]


@pytest.mark.asyncio
async def test_order_code_matching_is_case_insensitive():
    client = FakeDynamoDBClient(
        [order(order_code="ai:XPAR")], [workflow(index="something-else")]
    )

    triggers = await collect_todays_triggers(client, RUN_DATE, [alert()])

    assert list(triggers) == ["AI_xpar"]


@pytest.mark.asyncio
async def test_drops_trigger_when_neither_code_nor_index_matches():
    client = FakeDynamoDBClient(
        [order(order_code="GER40.I")], [workflow(index="GER40.I")]
    )

    triggers = await collect_todays_triggers(client, RUN_DATE, [alert()])

    assert triggers == {}


@pytest.mark.asyncio
async def test_never_introduces_an_asset_outside_the_alert_set():
    client = FakeDynamoDBClient([order()], [workflow()])

    triggers = await collect_todays_triggers(
        client, RUN_DATE, [alert(code="SAN")]
    )

    assert triggers == {}


@pytest.mark.asyncio
async def test_direction_is_parsed_from_the_stored_enum_name():
    client = FakeDynamoDBClient([order(order_direction="SELL")], [workflow()])

    triggers = await collect_todays_triggers(client, RUN_DATE, [alert()])

    assert triggers["AI_xpar"][0].direction == Direction.SELL


@pytest.mark.asyncio
async def test_direction_also_accepts_the_enum_value_form():
    client = FakeDynamoDBClient([order(order_direction="Buy")], [workflow()])

    triggers = await collect_todays_triggers(client, RUN_DATE, [alert()])

    assert triggers["AI_xpar"][0].direction == Direction.BUY


@pytest.mark.asyncio
async def test_drops_trigger_with_unknown_direction():
    client = FakeDynamoDBClient([order(order_direction="HOLD")], [workflow()])

    triggers = await collect_todays_triggers(client, RUN_DATE, [alert()])

    assert triggers == {}


@pytest.mark.asyncio
async def test_drops_trigger_with_missing_direction():
    client = FakeDynamoDBClient([order(order_direction=None)], [workflow()])

    triggers = await collect_todays_triggers(client, RUN_DATE, [alert()])

    assert triggers == {}


@pytest.mark.asyncio
async def test_dry_run_is_read_from_the_workflow_not_the_order():
    client = FakeDynamoDBClient([order()], [workflow(dry_run=True)])

    triggers = await collect_todays_triggers(client, RUN_DATE, [alert()])

    assert triggers["AI_xpar"][0].dry_run is True


@pytest.mark.asyncio
async def test_several_triggers_on_one_asset_are_ordered_by_time():
    orders = [
        order(id="order-2", placed_at=at_hour(16, 0)),
        order(id="order-1", placed_at=at_hour(9, 30)),
    ]
    client = FakeDynamoDBClient(orders, [workflow()])

    triggers = await collect_todays_triggers(client, RUN_DATE, [alert()])

    assert [t.placed_at for t in triggers["AI_xpar"]] == [
        at_hour(9, 30),
        at_hour(16, 0),
    ]


@pytest.mark.asyncio
async def test_conflicting_directions_are_both_kept():
    orders = [
        order(id="order-1", order_direction="BUY"),
        order(id="order-2", order_direction="SELL", placed_at=at_hour(16)),
    ]
    client = FakeDynamoDBClient(orders, [workflow()])

    triggers = await collect_todays_triggers(client, RUN_DATE, [alert()])

    assert [t.direction for t in triggers["AI_xpar"]] == [
        Direction.BUY,
        Direction.SELL,
    ]


@pytest.mark.asyncio
async def test_drops_trigger_with_non_positive_price():
    client = FakeDynamoDBClient(
        [order(order_price=Decimal("0"))], [workflow()]
    )

    triggers = await collect_todays_triggers(client, RUN_DATE, [alert()])

    assert triggers == {}


@pytest.mark.asyncio
async def test_missing_trigger_close_is_tolerated():
    client = FakeDynamoDBClient([order(trigger_close=None)], [workflow()])

    triggers = await collect_todays_triggers(client, RUN_DATE, [alert()])

    assert triggers["AI_xpar"][0].trigger_close is None


@pytest.mark.asyncio
async def test_returns_empty_when_storage_is_unavailable():
    triggers = await collect_todays_triggers(
        RaisingDynamoDBClient(), RUN_DATE, [alert()]
    )

    assert triggers == {}


@pytest.mark.asyncio
async def test_returns_empty_when_there_are_no_alerts():
    client = FakeDynamoDBClient([order()], [workflow()])

    triggers = await collect_todays_triggers(client, RUN_DATE, [])

    assert triggers == {}


@pytest.mark.asyncio
async def test_window_start_follows_the_run_date():
    # A manual or retried run passes its own date, and the window's START
    # moves with it rather than assuming the scheduled day (spec edge case:
    # off-schedule run). Note the END stays "now", so an earlier run_date
    # widens the window rather than sliding it - the bounds are only a single
    # session when run_date is today, which is the only way it is called.
    yesterday = at_hour(14, 30) - 24 * 3600
    client = FakeDynamoDBClient([order(placed_at=yesterday)], [workflow()])

    for_today = await collect_todays_triggers(client, RUN_DATE, [alert()])
    for_yesterday = await collect_todays_triggers(
        client, "2026-07-31", [alert()]
    )

    assert for_today == {}
    assert list(for_yesterday) == ["AI_xpar"]
