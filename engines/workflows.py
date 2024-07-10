import logging
from typing import Any, List, Optional

from model import Candle, Indicator, IndicatorType
from services.indicator_service import bollinger_bands, mobile_average
from utils.exception import SaxoException
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
                "can't run polarite workflow with None value or zone_value"
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
