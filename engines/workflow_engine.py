import logging
from typing import List, Optional

from slack_sdk import WebClient

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
from services.candles_service import CandlesService
from services.indicator_service import mobile_average
from utils.exception import SaxoException
from utils.helper import get_date_utc0
from utils.logger import Logger


class WorkflowEngine:

    def __init__(
        self,
        workflows: List[Workflow],
        slack_client: WebClient,
        candles_service: CandlesService,
    ) -> None:
        self.logger = Logger.get_logger("workflow_engine", logging.DEBUG)
        self.workflows = workflows
        self.slack_client = slack_client
        self.candles_service = candles_service

    def run(self) -> None:
        orders = []
        for workflow in self.workflows:
            if workflow.enable and workflow.end_date >= get_date_utc0().date():
                self.logger.info(f"Run workflow {workflow.name}")
                condition = workflow.conditions[0]
                candles = self._get_candles_from_indicator_ut(
                    workflow, condition.indicator
                )
                match workflow.conditions[0].indicator.name:
                    case IndicatorType.MA50:
                        orders.append((workflow, self._ma_workflow(workflow, candles)))
                    case IndicatorType.BBB:
                        pass
                    case IndicatorType.BBH:
                        pass
                    case _:
                        self.logger.error(
                            f"indicator {workflow.conditions[0].indicator.name} is not handle"
                        )
                        raise SaxoException()
            else:
                self.logger.info(f"Workflow {workflow.name} will not run")
        for order in orders:
            if order[1] is not None:
                log = f"Workflow `{order[0].name}` will trigger an order {order[1].direction} for {order[1].quantity} {order[1].code} at {order[1].price}"
                self.logger.debug(log)
                self.slack_client.chat_postMessage(channel="#stock", text=log)

    def _get_candles_from_indicator_ut(
        self, workflow: Workflow, indicator: Indicator
    ) -> List[Candle]:
        market = EUMarket() if workflow.is_us is False else USMarket()
        match indicator.name:
            case IndicatorType.MA50:
                nbr_hour = 55 if indicator.ut == UnitTime.H1 else 55 * 4
                self.logger.debug(
                    f"get candles for ma50 {indicator.ut}, we need {nbr_hour} candles"
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
            case _:
                self.logger.error(f"indicator {indicator.name} isn't managed")
        return []

    def _get_price_from_element(
        self, candle: Candle, element: WorkflowElement
    ) -> float:
        match element:
            case WorkflowElement.CLOSE:
                return candle.close
            case WorkflowElement.HIGH:
                return candle.higher
            case WorkflowElement.LOW:
                return candle.lower
            case _:
                raise SaxoException(f"We don't handle {element} price")

    def _ma_workflow(
        self, workflow: Workflow, candles: List[Candle]
    ) -> Optional[Order]:
        ma = mobile_average(candles, 50)
        self.logger.debug(
            f"get indicator {ma}, ut {workflow.conditions[0].indicator.ut}"
        )
        candle = self.candles_service.get_candle_per_hour(
            workflow.cfd, workflow.conditions[0].close.ut, get_date_utc0()
        )
        if candle is None:
            self.logger.error(f"can't retrive candle for {workflow.cfd}")
            raise SaxoException("Can't retrive candle")

        element = self._get_price_from_element(candle, workflow.conditions[0].element)
        price = 0.0
        trigger = workflow.trigger
        trigger_candle = self._get_trigger_candle(workflow)
        if workflow.conditions[0].close.direction == WorkflowDirection.BELOW:
            if element <= ma and element >= ma - workflow.conditions[0].close.spread:
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
                    return Order(
                        code=workflow.cfd,
                        price=price,
                        quantity=trigger.quantity,
                        direction=trigger.order_direction,
                        type=order_type,
                    )
                self.logger.warn(
                    f"we don't manage order {trigger.location}, signal: {trigger.signal}"
                )
        elif workflow.conditions[0].close.direction == WorkflowDirection.ABOVE:
            if element >= ma and element <= ma + workflow.conditions[0].close.spread:
                if (
                    trigger.location == WorkflowLocation.HIGHER
                    and trigger.signal == WorkflowSignal.BREAKOUT
                ):
                    price = trigger_candle.lower + 1
                    order_type = (
                        OrderType.OPEN_STOP
                        if trigger.order_direction == Direction.BUY
                        else OrderType.STOP
                    )
                    return Order(
                        code=workflow.cfd,
                        price=price,
                        quantity=trigger.quantity,
                        direction=trigger.order_direction,
                        type=order_type,
                    )
                self.logger.warn(
                    f"We don't manage order {trigger.location}, signal: {trigger.signal}"
                )
        return None

    def _get_trigger_candle(self, workflow):
        # we use the cdf here to run the workflow even in index off hours
        # TODO manage the cfd spread for some index
        trigger_candle = self.candles_service.get_candle_per_hour(
            workflow.cfd, workflow.trigger.ut, get_date_utc0()
        )
        if trigger_candle is None:
            self.logger.error(f"can't retrive candle for {workflow.cfd}")
            raise SaxoException("Can't retrive candle")
        return trigger_candle
