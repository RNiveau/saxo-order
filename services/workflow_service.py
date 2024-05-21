import logging
from datetime import datetime

from client.client_helper import *
from client.saxo_client import SaxoClient
from model import Candle, IndicatorType, UnitTime
from utils.exception import SaxoException


class WorkflowService:

    def __init__(self, saxo_client: SaxoClient):
        self.saxo_client = saxo_client

    def get_candle(self, code: str, ut: UnitTime, date: datetime) -> Optional[Candle]:
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
        self, code: str, ut: UnitTime, indicator: IndicatorType, date: datetime
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
