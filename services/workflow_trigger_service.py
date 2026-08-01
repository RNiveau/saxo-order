import datetime
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from model import Alert, Direction, WorkflowTrigger
from utils.exception import SaxoException
from utils.logger import Logger

PARIS = ZoneInfo("Europe/Paris")

logger = Logger.get_logger("workflow_trigger_service", logging.INFO)


def _session_window(run_date: str) -> Tuple[int, int]:
    day = datetime.datetime.strptime(run_date, "%Y-%m-%d").date()
    start = datetime.datetime.combine(
        day, datetime.time.min, tzinfo=PARIS
    ).timestamp()
    return int(start), int(datetime.datetime.now(PARIS).timestamp())


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _parse_direction(value: Any) -> Direction:
    try:
        return Direction[str(value)]
    except KeyError:
        raise SaxoException(f"Unknown order direction: {value!r}")


def _asset_keys(alert: Alert) -> List[str]:
    keys = [alert.asset_code.lower()]
    if alert.country_code:
        keys.append(f"{alert.asset_code}:{alert.country_code}".lower())
    return keys


def _index_to_alert_id(alerts: List[Alert]) -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    for alert in alerts:
        for key in _asset_keys(alert):
            lookup.setdefault(key, alert.id)
    return lookup


def _build_workflow_map(
    workflows: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    return {
        workflow["id"]: workflow
        for workflow in workflows
        if workflow.get("id")
    }


def _build_trigger(
    order: Dict[str, Any], workflow: Dict[str, Any]
) -> WorkflowTrigger:
    order_price = _to_float(order.get("order_price"))
    if order_price is None or order_price <= 0:
        raise SaxoException(f"Invalid order_price: {order.get('order_price')}")

    return WorkflowTrigger(
        workflow_name=order.get("workflow_name", workflow.get("name", "")),
        direction=_parse_direction(order.get("order_direction")),
        order_price=order_price,
        placed_at=int(order["placed_at"]),
        dry_run=bool(workflow.get("dry_run", False)),
        trigger_close=_to_float(order.get("trigger_close")),
    )


async def collect_todays_triggers(
    dynamodb_client: Any, run_date: str, alerts: List[Alert]
) -> Dict[str, List[WorkflowTrigger]]:
    """Resolve the day's workflow orders to the alert assets they corroborate.

    Returns an empty mapping on any failure: the digest must be identical to
    what it would have been without this enrichment.
    """
    try:
        return await _collect(dynamodb_client, run_date, alerts)
    except Exception as e:
        logger.warning(f"Workflow trigger collection failed, skipping: {e}")
        return {}


async def _collect(
    dynamodb_client: Any, run_date: str, alerts: List[Alert]
) -> Dict[str, List[WorkflowTrigger]]:
    if not alerts:
        return {}

    start, end = _session_window(run_date)
    orders = await dynamodb_client.get_all_workflow_orders()
    todays_orders = [
        order
        for order in orders
        if start <= int(order.get("placed_at", 0)) <= end
    ]
    if not todays_orders:
        return {}

    workflows = _build_workflow_map(await dynamodb_client.get_all_workflows())
    alert_ids = _index_to_alert_id(alerts)

    triggers: Dict[str, List[WorkflowTrigger]] = {}
    for order in todays_orders:
        workflow = workflows.get(order.get("workflow_id"))
        if workflow is None:
            logger.info(
                f"Dropping trigger for unknown workflow "
                f"{order.get('workflow_id')!r}"
            )
            continue

        index = workflow.get("index", "")
        alert_id = alert_ids.get(index.lower())
        if alert_id is None:
            logger.info(
                f"Dropping trigger: workflow index {index!r} "
                f"({workflow.get('name')!r}) matches no scanned asset"
            )
            continue

        try:
            trigger = _build_trigger(order, workflow)
        except SaxoException as e:
            logger.warning(f"Dropping malformed trigger: {e}")
            continue

        triggers.setdefault(alert_id, []).append(trigger)

    for trigger_list in triggers.values():
        trigger_list.sort(key=lambda t: t.placed_at)

    return triggers
