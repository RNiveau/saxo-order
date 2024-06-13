import datetime
import logging

from client.client_helper import *
from client.saxo_client import SaxoClient
from model import Candle, IndicatorType, UnitTime
from utils.exception import SaxoException

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class WorkflowService:

    def __init__(self, saxo_client: SaxoClient):
        self.saxo_client = saxo_client

    def get_candle_per_minutes(
        self,
        code: str,
        duration: int,
        ut: UnitTime,
        date: Optional[datetime.datetime] = None,
    ) -> List[Candle]:
        date = datetime.datetime.now(datetime.UTC) if date is None else date
        logger.debug(f"get_candle_per_minutes({code}, {duration}, {date})")
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
                "We don't get the expected number of elements, don't treat them"
            )
        data = map_data_to_candle(data, None)
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
            # sometime, some points are missing, so we need to hardcode end and open candle
            date = minute.date if minute.date is not None else datetime.datetime.now()
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

    def get_candle_per_hours(
        self, code: str, ut: UnitTime, date: datetime.datetime
    ) -> Optional[Candle]:
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
                return Candle(
                    get_low_from_saxo_data(data[0]),
                    get_high_from_saxo_data(data[0]),
                    get_open_from_saxo_data(data[0]),
                    get_price_from_saxo_data(data[0]),
                    ut,
                )
            case UnitTime.H4:
                for d in data:
                    if d["Time"].hour in (9, 13, 15):
                        return Candle(
                            get_low_from_saxo_data(d),
                            get_high_from_saxo_data(d),
                            get_open_from_saxo_data(d),
                            get_price_from_saxo_data(d),
                            ut,
                        )
            case _:
                logging.error(f"We don't handle this ut : {ut}")
                raise SaxoException(f"We don't handle this ut : {ut}")
        return None

    def calculate_ma(
        self, code: str, ut: UnitTime, indicator: IndicatorType, date: datetime.datetime
    ) -> float:
        horizon = 60
        logging.info(f"Calculate {indicator}, code:{code} ut: {ut}, date: {date}")
        match indicator:
            case IndicatorType.MA50:
                denominator = 50
                match ut:
                    case UnitTime.H4:
                        count = 200
                    case UnitTime.H1:
                        count = 50
                    case _:
                        raise SaxoException(f"We don't handle this ut {ut}")
            case _:
                raise SaxoException(f"We don't handle this indicator type {indicator}")
        # hours need to be utc0
        asset = self.saxo_client.get_asset(code)
        data = self.saxo_client.get_historical_data(
            saxo_uic=asset["Identifier"],
            asset_type=asset["AssetType"],
            horizon=horizon,
            count=count,
            date=date,
        )
        if len(data) != denominator and len(data) != count:
            raise SaxoException(
                f"We should got {count} or {denominator} elements but we get {len(data)}"
            )
        avg: float = 0
        hit: int = 0
        for d in data:
            if UnitTime.H4 == ut:
                if d["Time"].hour in (9, 13, 15):
                    if hit < denominator:
                        avg += float(d["Close"])
                        hit += 1
                    else:
                        break
            else:
                avg += float(d["Close"])
        avg /= denominator
        return avg
