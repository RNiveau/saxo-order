from typing import Any, Dict, List, Optional

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
