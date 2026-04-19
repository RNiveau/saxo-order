import logging
from typing import Any, List, Optional

from client.saxo_client import SaxoClient
from model import Candle, ComboSignal, Direction, Indicator, IndicatorType
from model.workflow import IndicatorInclined
from services.indicator_service import (
    apply_linear_function,
    bollinger_bands,
    combo,
    mobile_average,
    number_of_day_between_dates,
)
from utils.exception import SaxoException
from utils.helper import get_date_utc0
from utils.logger import Logger


class AbstractWorkflow:

    logger: logging.Logger
    indicator_value: Any

    def init_workflow(
        self, indicator: Indicator, candles: List[Candle]
    ) -> None:
        self.logger.debug(
            f"get indicator {self.indicator_value}, ut {indicator.ut}"
        )

    def below_condition(
        self, candle: Candle, spread: float, element: Optional[float] = None
    ) -> bool:
        return False

    def above_condition(
        self, candle: Candle, spread: float, element: Optional[float] = None
    ) -> bool:
        return False

    def _is_within_indicator_range_minus_spread(
        self, value: float, spread: float
    ):
        return self.indicator_value - spread <= value <= self.indicator_value

    def _is_within_indicator_range_plus_spread(self, value, spread):
        return self.indicator_value <= value <= self.indicator_value + spread


class BBWorkflow(AbstractWorkflow):

    logger = Logger.get_logger("bb-workflow", logging.DEBUG)

    def init_workflow(
        self, indicator: Indicator, candles: List[Candle]
    ) -> None:
        bb = bollinger_bands(candles, 2.5, 20)
        self.indicator_value = (
            bb.up if indicator.name == IndicatorType.BBH else bb.bottom
        )
        super().init_workflow(indicator, candles)

    def below_condition(
        self, candle: Candle, spread: float, element: Optional[float] = None
    ) -> bool:
        if element is None:
            return self._is_within_indicator_range_minus_spread(
                candle.close, spread
            ) or self._is_within_indicator_range_minus_spread(
                candle.higher, spread
            )
        return self._is_within_indicator_range_minus_spread(element, spread)

    def above_condition(
        self, candle: Candle, spread: float, element: Optional[float] = None
    ) -> bool:
        if element is None:
            return self._is_within_indicator_range_plus_spread(
                candle.close, spread
            ) or self._is_within_indicator_range_plus_spread(
                candle.lower, spread
            )
        return self._is_within_indicator_range_plus_spread(element, spread)


class ZoneWorkflow(AbstractWorkflow):

    logger = Logger.get_logger("zone-workflow", logging.DEBUG)

    def init_workflow(
        self, indicator: Indicator, candles: List[Candle]
    ) -> None:
        if indicator.value is None or indicator.zone_value is None:
            self.logger.error(
                "can't run zone workflow with None value or zone_value"
            )
            raise SaxoException("indicator has none value or zone_value")
        value = indicator.value
        zone_value = indicator.zone_value
        if value > zone_value:
            tmp = value
            value = zone_value
            zone_value = tmp
        self.indicator_value = (value, zone_value)
        super().init_workflow(indicator, candles)

    def below_condition(
        self, candle: Candle, spread: float, element: Optional[float] = None
    ) -> bool:
        if element is None:
            return (
                candle.close >= self.indicator_value[0]
                and candle.close <= self.indicator_value[1]
            ) or (
                candle.higher >= self.indicator_value[0]
                and candle.higher <= self.indicator_value[1]
            )
        return (
            element >= self.indicator_value[0]
            and element <= self.indicator_value[1]
        )

    def above_condition(
        self, candle: Candle, spread: float, element: Optional[float] = None
    ) -> bool:
        if element is None:
            return (
                candle.close >= self.indicator_value[0]
                and candle.close <= self.indicator_value[1]
            ) or (
                candle.lower >= self.indicator_value[0]
                and candle.lower <= self.indicator_value[1]
            )
        return (
            element >= self.indicator_value[0]
            and element <= self.indicator_value[1]
        )


class MA50Workflow(AbstractWorkflow):

    logger = Logger.get_logger("ma50-workflow", logging.DEBUG)

    def init_workflow(
        self, indicator: Indicator, candles: List[Candle]
    ) -> None:
        self.indicator_value = mobile_average(candles, 50)
        super().init_workflow(indicator, candles)

    def below_condition(
        self, candle: Candle, spread: float, element: Optional[float] = None
    ) -> bool:
        if element is None:
            return self._is_within_indicator_range_minus_spread(
                candle.close, spread
            ) or self._is_within_indicator_range_minus_spread(
                candle.higher, spread
            )
        return self._is_within_indicator_range_minus_spread(element, spread)

    def above_condition(
        self, candle: Candle, spread: float, element: Optional[float] = None
    ) -> bool:
        if element is None:
            return self._is_within_indicator_range_plus_spread(
                candle.close, spread
            ) or self._is_within_indicator_range_plus_spread(
                candle.lower, spread
            )
        return self._is_within_indicator_range_plus_spread(element, spread)


class MA7Workflow(AbstractWorkflow):

    logger = Logger.get_logger("ma7-workflow", logging.DEBUG)

    def init_workflow(
        self, indicator: Indicator, candles: List[Candle]
    ) -> None:
        self.indicator_value = mobile_average(candles, 7)
        super().init_workflow(indicator, candles)

    def below_condition(
        self, candle: Candle, spread: float, element: Optional[float] = None
    ) -> bool:
        if element is None:
            return self._is_within_indicator_range_minus_spread(
                candle.close, spread
            ) or self._is_within_indicator_range_minus_spread(
                candle.higher, spread
            )
        return self._is_within_indicator_range_minus_spread(element, spread)

    def above_condition(
        self, candle: Candle, spread: float, element: Optional[float] = None
    ) -> bool:
        if element is None:
            return self._is_within_indicator_range_plus_spread(
                candle.close, spread
            ) or self._is_within_indicator_range_plus_spread(
                candle.lower, spread
            )
        return self._is_within_indicator_range_plus_spread(element, spread)


class PolariteWorkflow(AbstractWorkflow):

    logger = Logger.get_logger("polarite-workflow", logging.DEBUG)

    def init_workflow(
        self, indicator: Indicator, candles: List[Candle]
    ) -> None:
        if indicator.value is None:
            self.logger.error("can't run polarite workflow with None value")
            raise SaxoException("indicator has none value")
        self.indicator_value = indicator.value
        super().init_workflow(indicator, candles)

    def below_condition(
        self, candle: Candle, spread: float, element: Optional[float] = None
    ) -> bool:
        self.logger.debug(f"below condition {candle}")
        if element is not None:
            return (
                element <= self.indicator_value
                and element >= self.indicator_value - spread
            )
        if (
            candle.higher >= self.indicator_value
            and candle.close <= self.indicator_value
        ):
            return True
        if (
            candle.higher <= self.indicator_value
            and candle.higher >= self.indicator_value - spread
        ):
            return True
        return False

    def above_condition(
        self, candle: Candle, spread: float, element: Optional[float] = None
    ) -> bool:
        self.logger.debug(f"above condition {candle}")
        if element is not None:
            return (
                element >= self.indicator_value
                and element <= self.indicator_value + spread
            )
        if (
            candle.lower <= self.indicator_value
            and candle.close >= self.indicator_value
        ):
            return True
        if (
            candle.lower >= self.indicator_value
            and candle.lower <= self.indicator_value + spread
        ):
            return True
        return False


class ComboWorkflow(AbstractWorkflow):

    logger = Logger.get_logger("combo-workflow", logging.DEBUG)

    def init_workflow(
        self, indicator: Indicator, candles: List[Candle]
    ) -> None:
        self.indicator_value: Optional[ComboSignal] = combo(candles)
        super().init_workflow(indicator, candles)

    def below_condition(
        self, candle: Candle, spread: float, element: Optional[float] = None
    ) -> bool:
        return (
            self.indicator_value is not None
            and self.indicator_value.direction == Direction.SELL
        )

    def above_condition(
        self, candle: Candle, spread: float, element: Optional[float] = None
    ) -> bool:
        return (
            self.indicator_value is not None
            and self.indicator_value.direction == Direction.BUY
        )


class InclinedWorkflow(AbstractWorkflow):

    logger = Logger.get_logger("inclined-workflow", logging.DEBUG)

    def __init__(self, saxo_client: SaxoClient, index_code: str):
        self.saxo_client = saxo_client
        self.index_code = index_code

    def init_workflow(
        self, indicator: Indicator, candles: List[Candle]
    ) -> None:
        if not isinstance(indicator, IndicatorInclined):
            raise SaxoException("indicator must be IndicatorInclined")
        if indicator.x1 is None or indicator.x2 is None:
            raise SaxoException("inclined indicator requires x1 and x2")

        asset = self.saxo_client.get_asset(self.index_code)
        saxo_uic = asset["Identifier"]
        asset_type = asset["AssetType"]

        x1_to_x2 = number_of_day_between_dates(
            self.saxo_client,
            saxo_uic,
            asset_type,
            indicator.x1.x,
            indicator.x2.x,
        )
        x1_to_now = number_of_day_between_dates(
            self.saxo_client,
            saxo_uic,
            asset_type,
            indicator.x1.x,
            get_date_utc0(),
        )

        self.indicator_value = apply_linear_function(
            0, indicator.x1.y, x1_to_x2, indicator.x2.y, x1_to_now
        )
        super().init_workflow(indicator, candles)

    def below_condition(
        self, candle: Candle, spread: float, element: Optional[float] = None
    ) -> bool:
        if self.indicator_value is None:
            return False
        if element is not None:
            return self._is_within_indicator_range_plus_spread(element, spread)
        return self._is_within_indicator_range_plus_spread(
            candle.close, spread
        ) or self._is_within_indicator_range_plus_spread(candle.lower, spread)

    def above_condition(
        self, candle: Candle, spread: float, element: Optional[float] = None
    ) -> bool:
        if self.indicator_value is None:
            return False
        if element is not None:
            return self._is_within_indicator_range_minus_spread(
                element, spread
            )
        return self._is_within_indicator_range_minus_spread(
            candle.close, spread
        ) or self._is_within_indicator_range_minus_spread(
            candle.higher, spread
        )
