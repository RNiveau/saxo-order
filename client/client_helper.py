from typing import Any, Dict, List, Optional

from model import Candle, UnitTime
from utils.exception import SaxoException


def get_low_from_saxo_data(data: Dict) -> float:
    return _get_value_from_saxo_data(data, "Low")


def get_high_from_saxo_data(data: Dict) -> float:
    return _get_value_from_saxo_data(data, "High")


def get_open_from_saxo_data(data: Dict) -> float:
    return _get_value_from_saxo_data(data, "Open")


def get_price_from_saxo_data(data: Dict) -> float:
    return _get_value_from_saxo_data(data, "Close")


def _get_value_from_saxo_data(data: Dict, key: str) -> float:
    if key in data:
        return data[key]
    if f"{key}Ask" in data and f"{key}Bid" in data:
        return (data[f"{key}Ask"] + data[f"{key}Bid"]) / 2
    raise SaxoException("Can't find the price")


def get_tick_size(data: Dict, price: float) -> float:
    tick_size = data["DefaultTickSize"]
    for tick in data["Elements"]:
        if price <= tick["HighPrice"]:
            return tick["TickSize"]
    return tick_size


def map_data_to_candle(data: List[Dict], ut: Optional[UnitTime] = None) -> List[Candle]:
    return list(
        map(
            lambda x: Candle(
                lower=get_low_from_saxo_data(x),
                higher=get_high_from_saxo_data(x),
                open=get_open_from_saxo_data(x),
                close=get_price_from_saxo_data(x),
                ut=ut if ut is not None else UnitTime.D,
                date=x["Time"],
            ),
            data,
        )
    )
