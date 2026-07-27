"""Trading-session definitions (Model Layer, no external deps).

These live in their own module rather than in ``model/__init__.py`` because
``model/__init__.py`` imports ``model.backtest`` before it defines anything
of its own, and a ``BacktestDefinition`` carries the market its session
runs on - importing it from the package root would be circular. Every name
here is re-exported from ``model``, so ``from model import EUMarket`` keeps
working.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class Market:
    open_hour: int
    open_minutes: int
    close_hour: int
    h4_blocks: List[int] = None  # type: ignore[assignment]
    timezone: str = "UTC"
    # Minutes past close_hour:00 at which the regular session actually
    # ends (e.g. 30 for Euronext Paris's 17:30 close). close_hour itself
    # stays the last-full-H1-candle-label hour used by the H4/daily
    # candle builders in utils/helper.py, so this can exceed 59 when
    # close_hour is a full hour short of the literal close (see
    # USMarket, whose true 16:00 close is 60 minutes past its 15:00
    # close_hour label).
    end_minute: int = 0


class USMarket(Market):
    def __init__(self) -> None:
        super().__init__(
            open_hour=9,
            close_hour=15,
            open_minutes=30,
            h4_blocks=[4, 3],
            timezone="America/New_York",
            end_minute=60,
        )


class EUMarket(Market):
    def __init__(self) -> None:
        super().__init__(
            open_hour=9,
            close_hour=17,
            open_minutes=0,
            h4_blocks=[3, 4, 2],
            timezone="Europe/Paris",
            end_minute=30,
        )


class EuCfdMarket(Market):
    """The European index CFD session: 09:00-22:00 Paris local.

    The same instruments EUMarket covers (FRA40.I, GER40.I) keep trading
    as CFDs long after the 17:30 Euronext/Xetra cash close. close_hour is
    21 with end_minute 60 rather than 22/0 because close_hour is the
    last-full-H1-candle label hour, not the literal close - the same
    convention USMarket uses for its true 16:00 close.
    """

    def __init__(self) -> None:
        super().__init__(
            open_hour=9,
            close_hour=21,
            open_minutes=0,
            h4_blocks=[3, 4, 4, 2],
            timezone="Europe/Paris",
            end_minute=60,
        )
