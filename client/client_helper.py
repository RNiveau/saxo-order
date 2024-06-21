import logging
from typing import Any, Dict, List, Optional

from model import Candle, UnitTime
from utils.exception import SaxoException
from utils.logger import Logger


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
    Logger.get_logger("client_helper").error(f"Can't find {key} in {data}")
    raise SaxoException("Can't find the price")


def get_tick_size(data: Dict, price: float) -> float:
    tick_size = data["DefaultTickSize"]
    for tick in data["Elements"]:
        if price <= tick["HighPrice"]:
            return tick["TickSize"]
    return tick_size


def map_data_to_candles(
    data: List[Dict], ut: Optional[UnitTime] = None
) -> List[Candle]:
    return list(
        map(
            lambda x: map_data_to_candle(x, ut),
            data,
        )
    )


def map_data_to_candle(data: Dict, ut: Optional[UnitTime] = None) -> Candle:
    return Candle(
        lower=round(get_low_from_saxo_data(data), 4),
        higher=round(get_high_from_saxo_data(data), 4),
        open=round(get_open_from_saxo_data(data), 4),
        close=round(get_price_from_saxo_data(data), 4),
        ut=ut if ut is not None else UnitTime.D,
        date=data["Time"],
    )
