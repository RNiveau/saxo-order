from typing import List

from api.models.indicator import AssetIndicatorsResponse, MovingAverageInfo
from client.client_helper import map_data_to_candles
from client.saxo_client import SaxoClient
from model import Candle, UnitTime
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

    def __init__(self, saxo_client: SaxoClient):
        self.saxo_client = saxo_client

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

        # Current price is the close of the newest candle (index 0)
        current_price = candles[0].close

        # Variation from previous period (candles[1] is previous period)
        previous_close = candles[1].close
        variation_pct = round(
            ((current_price - previous_close) / previous_close) * 100, 2
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
            current_price=round(current_price, 4),
            variation_pct=variation_pct,
            unit_time=unit_time.value,
            moving_averages=moving_averages,
        )
