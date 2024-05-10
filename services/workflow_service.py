import logging
from datetime import datetime

from client.saxo_client import SaxoClient
from model import IndicatorType, UnitTime
from utils.exception import SaxoException


class WorkflowService:

    def __init__(self, saxo_client: SaxoClient):
        self.saxo_client = saxo_client

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
        for d in data:
            d["Time"] = datetime.strptime(d["Time"], "%Y-%m-%dT%H:%M:%S.%fZ")
        data = sorted(data, key=lambda x: x["Time"], reverse=True)
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
