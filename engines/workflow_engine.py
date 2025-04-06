import logging
from typing import List, Optional

from slack_sdk import WebClient

from client.saxo_client import SaxoClient
from engines.workflows import (
    AbstractWorkflow,
    BBWorkflow,
    ComboWorkflow,
    MA50Workflow,
    PolariteWorkflow,
    ZoneWorkflow,
)
from model import (
    Candle,
    Direction,
    EUMarket,
    Indicator,
    IndicatorType,
    Order,
    OrderType,
    UnitTime,
    USMarket,
    Workflow,
    WorkflowDirection,
    WorkflowElement,
    WorkflowLocation,
    WorkflowSignal,
)
from model.enum import AssetType
from services.candles_service import CandlesService
from utils.exception import SaxoException
from utils.helper import get_date_utc0
from utils.logger import Logger


class WorkflowEngine:

    def __init__(
        self,
        workflows: List[Workflow],
        slack_client: WebClient,
        candles_service: CandlesService,
        saxo_client: SaxoClient,
    ) -> None:
        self.logger = Logger.get_logger("workflow_engine", logging.DEBUG)
        self.workflows = workflows
        self.slack_client = slack_client
        self.candles_service = candles_service
        self.saxo_client = saxo_client

    def run(self) -> None:
        results = []
        for workflow in self.workflows:
            if workflow.enable and (
                workflow.end_date is None
                or workflow.end_date >= get_date_utc0().date()
            ):
                self.logger.info(f"Run workflow {workflow.name}")
                condition = workflow.conditions[0]
                try:
                    candles = self._get_candles_from_indicator_ut(
                        workflow, condition.indicator
                    )
                except SaxoException as e:
                    self.logger.error(
                        f"Can't get candles for {workflow.name} {e}"
                    )
                    continue
                if len(candles) > 0:
                    self.logger.debug(
                        f"first candle for this indicator is {candles[0]}"
                    )
                match workflow.conditions[0].indicator.name:
                    case IndicatorType.MA50:
                        results.append(
                            (
                                workflow,
                                self._run_workflow(
                                    workflow, candles, MA50Workflow()
                                ),
                            )
                        )
                    case IndicatorType.COMBO:
                        results.append(
                            (
                                workflow,
                                self._run_workflow(
                                    workflow, candles, ComboWorkflow()
                                ),
                            )
                        )
                    case IndicatorType.BBB | IndicatorType.BBH:
                        results.append(
                            (
                                workflow,
                                self._run_workflow(
                                    workflow, candles, BBWorkflow()
                                ),
                            )
                        )
                    case IndicatorType.POL:
                        results.append(
                            (
                                workflow,
                                self._run_workflow(
                                    workflow, candles, PolariteWorkflow()
                                ),
                            )
                        )
                    case IndicatorType.ZONE:
                        results.append(
                            (
                                workflow,
                                self._run_workflow(
                                    workflow, candles, ZoneWorkflow()
                                ),
                            )
                        )
                    case _:
                        self.logger.error(
                            "indicator "
                            f"{workflow.conditions[0].indicator.name}"
                            " is not handle"
                        )
                        raise SaxoException()
            else:
                self.logger.info(f"Workflow {workflow.name} will not run")

        for order in results:
            if order[1] is not None:
                asset = self.saxo_client.get_asset(order[1][1].code)
                log = (
                    f"Workflow `{order[0].name}` will trigger an order "
                    f"{order[1][1].direction} for {order[1][1].quantity} "
                    f"{order[1][1].code} at {order[1][1].price}: last price "
                    f"{order[1][0].close}"
                )
                self.logger.debug(log)
                channel = (
                    "#workflows-stock"
                    if asset["AssetType"] == AssetType.STOCK
                    else "#workflows"
                )
                self.slack_client.chat_postMessage(channel=channel, text=log)

    def _get_candles_from_indicator_ut(
        self, workflow: Workflow, indicator: Indicator
    ) -> List[Candle]:
        market = EUMarket() if workflow.is_us is False else USMarket()
        multiplicator = 1
        if indicator.ut == UnitTime.H4:
            multiplicator = 4
        elif indicator.ut == UnitTime.D:
            multiplicator = 8
        match indicator.name:
            case IndicatorType.MA50:
                nbr_hour = 55 * multiplicator
            case IndicatorType.COMBO:
                nbr_hour = 750 * multiplicator
            case IndicatorType.BBH | IndicatorType.BBB:
                nbr_hour = 21 * multiplicator
            case IndicatorType.POL | IndicatorType.ZONE:
                nbr_hour = 1
            case _:
                self.logger.error(f"indicator {indicator.name} isn't managed")
                return []
        self.logger.debug(
            f"get candles for {indicator.name} {indicator.ut}, "
            f"we need {nbr_hour} candles"
        )
        return self.candles_service.build_hour_candles(
            code=workflow.index,
            cfd_code=workflow.cfd,
            ut=indicator.ut,
            open_hour_utc0=market.open_hour,
            close_hour_utc0=market.close_hour,
            nbr_hours=nbr_hour * 3,
            open_minutes=market.open_minutes,
            date=get_date_utc0(),
        )

    def _get_price_from_element(
        self, candle: Candle, element: Optional[WorkflowElement]
    ) -> Optional[float]:
        match element:
            case WorkflowElement.CLOSE:
                return candle.close
            case WorkflowElement.HIGH:
                return candle.higher
            case WorkflowElement.LOW:
                return candle.lower
            case None:
                return None
            case _:
                raise SaxoException(f"We don't handle {element} price")

    def _run_workflow(
        self, workflow: Workflow, candles: List[Candle], run: AbstractWorkflow
    ) -> Optional[tuple[Candle, Order]]:
        run.init_workflow(workflow.conditions[0].indicator, candles)

        close_candle = self.candles_service.get_candle_per_hour(
            workflow.cfd, workflow.conditions[0].close.ut, get_date_utc0()
        )
        if close_candle is None:
            self.logger.error(
                f"can't retrive close candle for {workflow.cfd} "
                f"{workflow.name}"
            )
            raise SaxoException("Can't retrive candle")

        element = self._get_price_from_element(
            close_candle, workflow.conditions[0].element
        )
        price = 0.0
        trigger = workflow.trigger
        trigger_candle = self._get_trigger_candle(workflow)
        if workflow.conditions[0].close.direction == WorkflowDirection.BELOW:
            if run.below_condition(
                close_candle, workflow.conditions[0].close.spread, element
            ):
                if (
                    trigger.location == WorkflowLocation.LOWER
                    and trigger.signal == WorkflowSignal.BREAKOUT
                ):
                    price = trigger_candle.lower - 1
                    order_type = (
                        OrderType.OPEN_STOP
                        if trigger.order_direction == Direction.SELL
                        else OrderType.LIMIT
                    )
                    return close_candle, Order(
                        code=workflow.cfd,
                        price=price,
                        quantity=trigger.quantity,
                        direction=trigger.order_direction,
                        type=order_type,
                    )
                self.logger.warning(
                    f"we don't manage order {trigger.location}, "
                    f"signal: {trigger.signal}"
                )
        elif workflow.conditions[0].close.direction == WorkflowDirection.ABOVE:
            if run.above_condition(
                close_candle, workflow.conditions[0].close.spread, element
            ):
                if (
                    trigger.location == WorkflowLocation.HIGHER
                    and trigger.signal == WorkflowSignal.BREAKOUT
                ):
                    price = trigger_candle.higher + 1
                    order_type = (
                        OrderType.OPEN_STOP
                        if trigger.order_direction == Direction.BUY
                        else OrderType.LIMIT
                    )
                    return close_candle, Order(
                        code=workflow.cfd,
                        price=price,
                        quantity=trigger.quantity,
                        direction=trigger.order_direction,
                        type=order_type,
                    )
                self.logger.warning(
                    f"we don't manage order {trigger.location}, "
                    f"signal: {trigger.signal}"
                )
        return None

    def _get_trigger_candle(self, workflow: Workflow) -> Candle:
        # we use the cdf here to run the workflow even in index off hours
        # TODO manage the cfd spread for some index
        self.logger.debug(
            f"get trigger candle for {workflow.cfd} {workflow.trigger.ut}"
        )
        trigger_candle = self.candles_service.get_candle_per_hour(
            workflow.cfd, workflow.trigger.ut, get_date_utc0()
        )
        if trigger_candle is None:
            self.logger.error(
                f"can't retrive trigger candle for {workflow.cfd}"
            )
            raise SaxoException("Can't retrive candle")
        return trigger_candle
