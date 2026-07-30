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


class DaxCfdMarket(Market):
    """The DAX index CFD session: 02:00-22:00 Paris local.

    GER40.I quotes from 02:00, twenty hours before the 22:00 close and
    seven before the 09:00 Xetra cash open, so a strategy that reads the
    instrument continuously rather than off a session reference range
    sees a materially longer day than EuCfdMarket describes.

    Kept separate from EuCfdMarket rather than widening it: the "bougie
    de 9h" backtests derive their 09:00-10:00 reference window from
    open_hour, so moving that market's open to 02:00 would silently
    relocate their reference candle to the middle of the night.

    close_hour/end_minute follow the EuCfdMarket convention (21 + 60 for
    a literal 22:00 close - close_hour labels the last full H1 candle).
    02:00 local is also the earliest open this Market can express: it
    resolves to 00:00 UTC under CEST, and an earlier one would put the
    session's UTC open on the previous calendar day, which market_in_utc
    documents it does not handle.
    """

    def __init__(self) -> None:
        super().__init__(
            open_hour=2,
            close_hour=21,
            open_minutes=0,
            h4_blocks=[4, 4, 4, 4, 4],
            timezone="Europe/Paris",
            end_minute=60,
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
