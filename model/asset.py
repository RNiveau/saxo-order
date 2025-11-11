from dataclasses import dataclass
from typing import Optional

from model.enum import AssetType, Exchange


@dataclass
class Asset:
    """
    Unified asset model for both Saxo and Binance instruments.
    """

    symbol: str
    description: str
    asset_type: AssetType
    exchange: Exchange
    identifier: Optional[int] = None
