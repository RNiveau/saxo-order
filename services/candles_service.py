import datetime
import logging
from typing import List, Optional

from client.client_helper import map_data_to_candle, map_data_to_candles
from client.saxo_client import SaxoClient
from model import Candle, UnitTime
from utils.exception import SaxoException
from utils.helper import build_h4_candles_from_h1, get_date_utc0
from utils.logger import Logger


class CandlesService:

    def __init__(self, saxo_client: SaxoClient):
        self.logger = Logger.get_logger("candles_service", logging.DEBUG)
        self.saxo_client = saxo_client

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
                raise SaxoException(f"We don't handle this ut {ut}")
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

    def get_candle_per_hour(
        self, code: str, ut: UnitTime, date: datetime.datetime
    ) -> Optional[Candle]:
        """Return last h1 or h4 candle"""
        asset = self.saxo_client.get_asset(code)
        data = self.saxo_client.get_historical_data(
            saxo_uic=asset["Identifier"],
            asset_type=asset["AssetType"],
            horizon=60,
            count=5,
            date=date,
        )
        match ut:
            case UnitTime.H1:
                return map_data_to_candle(data[0], ut)
            case UnitTime.H4:
                for d in data:
                    if d["Time"].hour in (9, 13, 15):
                        return map_data_to_candle(d, ut)
            case _:
                self.logger.error(f"We don't handle this ut : {ut}")
                raise SaxoException(f"We don't handle this ut : {ut}")
        return None

    def build_hour_candles(
        self,
        code: str,
        cfd_code: str,
        ut: UnitTime,
        open_hour_utc0: int,
        close_hour_utc0: int,
        nbr_hours: int,
        open_minutes: int,
        date: datetime.datetime,
    ) -> List[Candle]:
        """Build hour candles (or > UT) from a code and take
        in account open and close hour and world wide asset"""
        self.logger.info(f"Build candles for {code}, ut: {ut}, date: {date}")
        if open_minutes not in [0, 30]:
            raise SaxoException(
                f"Wrong parameter {open_minutes}, we handle only 0 and 30"
            )
        nbr_hours *= 2
        if nbr_hours > 1200:
            self.logger.debug(f"reduce nbr_hour from {nbr_hours} to 1200")
            nbr_hours = 1200
        asset = self.saxo_client.get_asset(code)
        data = self.saxo_client.get_historical_data(
            saxo_uic=asset["Identifier"],
            asset_type=asset["AssetType"],
            horizon=30,
            count=nbr_hours,
            date=date,
        )
        if len(data) < nbr_hours:
            raise SaxoException(
                f"We should got {nbr_hours} elements but we get {len(data)}"
            )
        delta = get_date_utc0() - data[0]["Time"].replace(
            tzinfo=datetime.timezone.utc
        )
        if (
            (
                delta.total_seconds() > 30 * 60
                and delta.total_seconds() < 45 * 60
            )
            or (
                delta.total_seconds() > 60 * 60
                and delta.total_seconds() < 75 * 60
            )
            and code != cfd_code
        ):
            self.logger.debug(f"Need to get the last cfd candles {cfd_code}")
            cfd = self.saxo_client.get_asset(cfd_code)
            data_cfd = self.saxo_client.get_historical_data(
                saxo_uic=cfd["Identifier"],
                asset_type=cfd["AssetType"],
                horizon=30,
                count=1,
                date=date,
            )
            if len(data) == 0 or data_cfd[0]["Time"] > data[0]["Time"]:
                data.insert(0, data_cfd[0])
        if (
            data[0]["Time"].minute == open_minutes
        ):  # it means we don't have the last 30 minutes of the current hour
            data = data[1:]
        i = 0
        candles = []
        while i < len(data):
            if (
                data[i]["Time"].hour >= open_hour_utc0
                and data[i]["Time"].hour <= close_hour_utc0
            ):
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
        if ut == UnitTime.H4:
            return build_h4_candles_from_h1(candles, open_hour_utc0)
        return candles
