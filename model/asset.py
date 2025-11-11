from dataclasses import dataclass
from typing import Optional

from model.enum import AssetType


@dataclass
class Asset:
    """
    Unified asset model for both Saxo and Binance instruments.
    """

    symbol: str
    description: str
    asset_type: AssetType
    exchange: str
    identifier: Optional[int] = None
