import datetime
from typing import List

from api.models.indicator import AssetIndicatorsResponse, MovingAverageInfo
from client.client_helper import map_data_to_candles
from client.saxo_client import SaxoClient
from model import Candle, UnitTime
from services.candles_service import CandlesService
from services.indicator_service import mobile_average
from utils.exception import SaxoException
from utils.logger import Logger

logger = Logger.get_logger("indicator_api_service")


class IndicatorService:
    """Service for calculating and providing asset indicators via API."""

    MA_PERIODS = [7, 20, 50, 200]

    # Horizon mapping (in minutes) for unit times
    HORIZON_MAP = {
        UnitTime.D: 1440,  # 1 day = 1440 minutes
        UnitTime.W: 10080,  # 7 days = 10080 minutes
        UnitTime.M: 43200,  # 30 days = 43200 minutes
    }

    def __init__(
        self, saxo_client: SaxoClient, candles_service: CandlesService
    ):
        self.saxo_client = saxo_client
        self.candles_service = candles_service

    def _is_same_period(
        self,
        date1: datetime.datetime,
        date2: datetime.datetime,
        unit_time: UnitTime,
    ) -> bool:
        """
        Check if two dates are in the same period based on unit_time.

        Args:
            date1: First date
            date2: Second date
            unit_time: Unit time (D=daily, W=weekly, M=monthly)

        Returns:
            True if dates are in the same period, False otherwise
        """
        if unit_time == UnitTime.D:
            # Same day
            return date1.date() == date2.date()
        elif unit_time == UnitTime.W:
            # Same ISO week
            return date1.isocalendar()[:2] == date2.isocalendar()[:2]
        elif unit_time == UnitTime.M:
            # Same month
            return (date1.year, date1.month) == (date2.year, date2.month)
        else:
            return False

    def get_price_and_variation(
        self,
        code: str,
        country_code: str = "xpar",
        unit_time: UnitTime = UnitTime.D,
    ) -> tuple[float, float]:
        """
        Get current price and variation for an asset without calculating MAs.

        Args:
            code: Asset code (e.g., "itp", "DAX.I")
            country_code: Country code (e.g., "xpar")
            unit_time: Unit time for calculations
                (D=daily, W=weekly, M=monthly)

        Returns:
            Tuple of (current_price, variation_pct)

        Raises:
            SaxoException: If asset not found or insufficient data
        """
        symbol = f"{code}:{country_code}" if country_code else code
        asset = self.saxo_client.get_asset(code, country_code)

        # Get horizon based on unit_time
        horizon = self.HORIZON_MAP[unit_time]

        # Fetch only 3 candles (enough for current + previous)
        data = self.saxo_client.get_historical_data(
            saxo_uic=asset["Identifier"],
            asset_type=asset["AssetType"],
            horizon=horizon,
            count=3,
        )

        if len(data) < 2:
            raise SaxoException(
                f"Insufficient data for {symbol} ({unit_time.value}): "
                f"only {len(data)} candles available, need at least 2"
            )

        # Convert to Candle objects (newest first)
        candles: List[Candle] = map_data_to_candles(data, None)

        # Get current price from latest minute candle
        try:
            latest_candle = self.candles_service.get_latest_candle(
                code, country_code
            )
            current_price = latest_candle.close
        except SaxoException as e:
            logger.warning(
                f"Failed to get latest candle for {symbol}: {e}. "
                f"Using historical candle close."
            )
            current_price = candles[0].close
            latest_candle = candles[0]

        # Determine previous close for variation calculation
        if latest_candle.date and candles[0].date:
            same_period = self._is_same_period(
                latest_candle.date, candles[0].date, unit_time
            )
            previous_close = (
                candles[1].close if same_period else candles[0].close
            )
        else:
            previous_close = candles[0].close

        variation_pct = round(
            ((current_price - previous_close) / previous_close) * 100, 2
        )

        return current_price, variation_pct

    def get_asset_indicators(
        self,
        code: str,
        country_code: str = "xpar",
        unit_time: UnitTime = UnitTime.D,
    ) -> AssetIndicatorsResponse:
        """
        Get indicator data for an asset including MAs, current price,
        and variation.

        Args:
            code: Asset code (e.g., "itp", "DAX.I")
            country_code: Country code (e.g., "xpar")
            unit_time: Unit time for calculations
                (D=daily, W=weekly, M=monthly)

        Returns:
            AssetIndicatorsResponse with all indicator data

        Raises:
            SaxoException: If asset not found or insufficient data
        """
        # Get asset info
        symbol = f"{code}:{country_code}" if country_code else code
        asset = self.saxo_client.get_asset(code, country_code)

        # Get horizon based on unit_time
        horizon = self.HORIZON_MAP[unit_time]

        # Fetch candles (need at least 200 for MA200)
        data = self.saxo_client.get_historical_data(
            saxo_uic=asset["Identifier"],
            asset_type=asset["AssetType"],
            horizon=horizon,
            count=210,  # Get extra candles for safety
        )

        if len(data) < 200:
            raise SaxoException(
                f"Insufficient data for {symbol} ({unit_time.value}): "
                f"only {len(data)} candles available, need at least 200"
            )

        # Convert to Candle objects (newest first based on CLAUDE.md)
        candles: List[Candle] = map_data_to_candles(data, None)

        if len(candles) < 200:
            raise SaxoException(
                f"Insufficient candles after mapping for {symbol} "
                f"({unit_time.value}): {len(candles)}"
            )

        # Get current price and variation
        current_price, variation_pct = self.get_price_and_variation(
            code, country_code, unit_time
        )

        # Calculate moving averages
        moving_averages: List[MovingAverageInfo] = []
        for period in self.MA_PERIODS:
            try:
                ma_value = mobile_average(candles, period)
                is_above = current_price > ma_value

                moving_averages.append(
                    MovingAverageInfo(
                        period=period,
                        value=round(ma_value, 4),
                        is_above=is_above,
                        unit_time=unit_time.value,
                    )
                )
            except SaxoException as e:
                logger.warning(
                    f"Could not calculate MA{period} for {symbol} "
                    f"({unit_time.value}): {e}"
                )
                # Continue with other MAs even if one fails

        if not moving_averages:
            raise SaxoException(
                f"Could not calculate any moving averages for {symbol} "
                f"({unit_time.value})"
            )

        return AssetIndicatorsResponse(
            asset_symbol=symbol,
            description=asset["Description"],
            current_price=round(current_price, 4),
            variation_pct=variation_pct,
            unit_time=unit_time.value,
            moving_averages=moving_averages,
        )
