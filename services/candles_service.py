import datetime
import logging
from typing import List, Optional, Union

from client.client_helper import map_data_to_candle, map_data_to_candles
from client.mock_saxo_client import MockSaxoClient
from client.saxo_client import SaxoClient
from model import Candle, Market, UnitTime
from utils.exception import SaxoException
from utils.helper import (
    build_current_weekly_candle_from_daily,
    build_daily_candles_from_h1,
    build_h4_candles_from_h1,
    get_date_utc0,
)
from utils.logger import Logger


class CandlesService:

    def __init__(self, saxo_client: Union[SaxoClient, MockSaxoClient]):
        self.logger = Logger.get_logger("candles_service", logging.DEBUG)
        self.saxo_client = saxo_client

    def get_latest_candle(
        self,
        code: str,
        market: Optional[str] = None,
        asset_identifier: Optional[int] = None,
        asset_type: Optional[str] = None,
    ) -> Candle:
        """
        Get the most recent candle (1-minute) for an asset.

        This is used to get the current price when the market is open
        or the most recent close when the market is closed.

        Args:
            code: Asset code (e.g., 'itp')
            market: Market/exchange code (e.g., 'xpar')
            asset_identifier: Optional cached Saxo UIC to skip get_asset call
            asset_type: Optional cached asset type to skip get_asset call

        Returns:
            The most recent 1-minute candle

        Raises:
            SaxoException: If unable to fetch the latest candle
        """
        self.logger.debug(f"get_latest_candle({code}, {market})")

        # Use cached metadata if available, otherwise fetch from API
        if asset_identifier is not None and asset_type is not None:
            saxo_uic = asset_identifier
            saxo_asset_type = asset_type
        else:
            asset = self.saxo_client.get_asset(code, market)
            saxo_uic = asset["Identifier"]
            saxo_asset_type = asset["AssetType"]

        data = self.saxo_client.get_historical_data(
            saxo_uic=saxo_uic,
            asset_type=saxo_asset_type,
            horizon=1,
            count=1,
            date=datetime.datetime.now(datetime.UTC),
        )
        if not data:
            raise SaxoException(
                f"No data returned for latest candle of {code}"
            )
        candles = map_data_to_candles(data, None)
        if not candles:
            raise SaxoException(
                f"No candles after mapping for latest candle of {code}"
            )
        return candles[0]

    def get_candles_per_minutes(
        self,
        code: str,
        duration: int,
        ut: UnitTime,
        date: Optional[datetime.datetime] = None,
    ) -> List[Candle]:
        """Build x ut candles for the duration minutes per minutes"""
        date = datetime.datetime.now(datetime.UTC) if date is None else date
        self.logger.debug(
            f"get_candle_per_minutes({code}, {duration}, {date})"
        )
        asset = self.saxo_client.get_asset(code)
        data = self.saxo_client.get_historical_data(
            saxo_uic=asset["Identifier"],
            asset_type=asset["AssetType"],
            horizon=1,
            count=duration,
            date=date,
        )
        if len(data) != duration:
            raise SaxoException(
                "We don't get the expected number of elements, "
                "don't treat them"
            )
        data = map_data_to_candles(data, None)
        slice = 0 if data[0].date is None else data[0].date.minute
        if ut == UnitTime.M15 and slice % 15 != 0:
            data = data[(slice % 15) + 1 :]
        else:
            data = data[(slice % 60) + 1 :]
        match ut:
            case UnitTime.M15:
                modulo = 15
            case UnitTime.H1:
                modulo = 60
            case _:
                self.logger.error(
                    f"get_candles_per_minutes: We don't handle this ut {ut}"
                )
                raise SaxoException(
                    f"get_candles_per_minutes: We don't handle this ut {ut}"
                )
        candles = []
        add_new_candle = True
        last_minute: Candle = Candle(-1, -1, -1, -1, ut)
        for minute in data:
            # sometime, some points are missing,
            # so we need to hardcode end and open candle
            date = (
                minute.date
                if minute.date is not None
                else datetime.datetime.now()
            )
            last_date = (
                last_minute.date
                if last_minute.date is not None
                else datetime.datetime.now()
            )
            if add_new_candle is True:
                candles.append(
                    Candle(
                        lower=minute.lower,
                        higher=minute.higher,
                        open=-1,
                        close=minute.close,
                        ut=ut,
                    )
                )
                add_new_candle = False
            elif date.minute % modulo == 0:
                candles[-1].open = minute.open
                candles[-1].date = date
                add_new_candle = True
            elif (
                ut == UnitTime.M15
                and date.minute in [14, 29, 44, 59]
                and abs(date.minute - last_date.minute) > 1
            ):
                candles[-1].open = last_minute.open
                candles[-1].date = last_date
                candles.append(
                    Candle(
                        lower=minute.lower,
                        higher=minute.higher,
                        open=-1,
                        close=minute.close,
                        ut=ut,
                    )
                )
                add_new_candle = False
            elif (
                ut == UnitTime.H1
                and date.minute in [58, 59]
                and abs(date.minute - last_date.minute) > 1
            ):
                candles[-1].open = last_minute.open
                candles[-1].date = last_date
                candles.append(
                    Candle(
                        lower=minute.lower,
                        higher=minute.higher,
                        open=-1,
                        close=minute.close,
                        ut=ut,
                    )
                )
                add_new_candle = False
            if candles[-1].lower > minute.lower:
                candles[-1].lower = minute.lower
            if candles[-1].higher < minute.higher:
                candles[-1].higher = minute.higher
            last_minute = minute
        if candles[-1].open == -1:
            candles.pop()
        return candles

    def _build_h1_from_30m(
        self, data: list, market: Market, ut: UnitTime
    ) -> List[Candle]:
        candles = []
        i = 0
        while i < len(data):
            open_hour_ok = data[i]["Time"].hour >= market.open_hour
            close_hour_ok = (
                data[i]["Time"].hour <= market.close_hour
                if market.open_minutes == 0
                else data[i]["Time"].hour <= market.close_hour + 1
            )
            minutes_ok = (
                data[i]["Time"].minute == 30
                if market.open_minutes == 0
                else data[i]["Time"].minute == 0
            )
            if open_hour_ok and close_hour_ok and minutes_ok:
                if i + 1 < len(data):
                    last = map_data_to_candle(data[i], ut)
                    first = map_data_to_candle(data[i + 1], ut)
                    last.open = first.open
                    last.date = first.date
                    if first.lower < last.lower:
                        last.lower = first.lower
                    if first.higher > last.higher:
                        last.higher = first.higher
                    candles.append(last)
                    i += 2
                    continue
                else:
                    break
            i += 1
        return candles

    def build_candles(
        self,
        code: str,
        ut: UnitTime,
        market: Market,
        count: int,
        date: datetime.datetime,
    ) -> List[Candle]:
        """Build candles of any UT (H1, H4, D) from 30m Saxo API data.

        Args:
            code: Asset code (e.g., 'DAX.I')
            ut: Target unit time (H1, H4, D)
            market: Market definition with hours and h4_blocks
            count: Number of target-UT candles to produce
            date: Reference date
        """
        self.logger.info(f"Build candles for {code}, ut: {ut}, date: {date}")
        if market.open_minutes not in [0, 30]:
            raise SaxoException(
                f"Wrong parameter {market.open_minutes}, we handle only 0 and 30"
            )
        nbr_30m = count * 2 * 3
        if ut == UnitTime.H4:
            nbr_30m = count * 8 * 3
        elif ut == UnitTime.D:
            num_h1 = (
                market.close_hour
                - market.open_hour
                + (1 if market.open_minutes == 0 else 0)
            )
            nbr_30m = count * num_h1 * 2 * 3
        asset = self.saxo_client.get_asset(code)
        data = self.saxo_client.get_historical_data(
            saxo_uic=asset["Identifier"],
            asset_type=asset["AssetType"],
            horizon=30,
            count=nbr_30m,
            date=date,
        )
        if len(data) == 0:
            raise SaxoException(
                f"No data returned for {code}"
            )
        if data[0]["Time"].minute == market.open_minutes:
            data = data[1:]
        candles = self._build_h1_from_30m(data, market, ut)
        if ut == UnitTime.H4:
            return build_h4_candles_from_h1(candles, market)
        elif ut == UnitTime.D:
            return build_daily_candles_from_h1(candles, market)
        return candles

    def build_weekly_candles(
        self,
        code: str,
        market: Market,
        nbr_weeks: int,
        date: datetime.datetime,
    ) -> List[Candle]:
        """
        Build weekly candles for a given asset.

        Fetches weekly candles from Saxo API (horizon 10080) and builds
        the current incomplete week from daily candles if needed.

        Args:
            code: Asset code (e.g., 'DAX.I')
            market: Market definition
            nbr_weeks: Number of weekly candles needed
            date: Reference date

        Returns:
            List of weekly candles (newest first)
        """
        self.logger.info(
            f"Build weekly candles for {code}, nbr_weeks: {nbr_weeks}"
        )

        asset = self.saxo_client.get_asset(code)
        weekly_data = self.saxo_client.get_historical_data(
            saxo_uic=asset["Identifier"],
            asset_type=asset["AssetType"],
            horizon=10080,
            count=nbr_weeks,
            date=date,
        )
        weekly_candles = map_data_to_candles(weekly_data, ut=UnitTime.W)

        today = get_date_utc0()
        if (
            len(weekly_candles) > 0
            and weekly_candles[0].date is not None
            and today.isocalendar()[:2]
            != weekly_candles[0].date.isocalendar()[:2]
            and today.weekday() < 5
        ):
            daily_candles = self.build_candles(
                code=code,
                ut=UnitTime.D,
                market=market,
                count=5,
                date=date,
            )
            current_weekly = build_current_weekly_candle_from_daily(
                daily_candles
            )
            if current_weekly is not None:
                weekly_candles.insert(0, current_weekly)

        return weekly_candles
