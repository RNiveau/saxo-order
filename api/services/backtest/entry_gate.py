"""Whether the engine may *open* a position on a given candle.

The exit chain answers "does this rule close an open position?". These
rules never close anything - they decide whether a confirmed breakout is
allowed to become a position at all, which is a different question with
different state behind it: the clock, and what the day has already lost.

They are not entry *validity* either. `is_valid_entry` judges a candidate
breakout against price levels and is deliberately stateless across
positions; the cut-off and the loss cap are properties of the run, so they
live here rather than being threaded into DirectionSearch.
"""

import datetime
from typing import Optional, Protocol

from api.services.backtest.calendar import PARIS_TZ
from model import Market, Trade
from utils.helper import market_in_utc


class EntryGate(Protocol):
    def allows(self, candle_time: datetime.datetime) -> bool:
        """Whether a position may open on the candle starting at
        `candle_time` (naive UTC, as the Saxo candles are)."""
        ...

    def record(self, trade: Trade) -> None:
        """Feed back a position that just closed, so the gate can count
        the day's losses."""
        ...


class AlwaysOpen:
    """The gate for a definition carrying neither filter: every candle is
    allowed and closed trades are of no interest. Keeps the engine free of
    a "does this definition have entry filters?" branch."""

    def allows(self, candle_time: datetime.datetime) -> bool:
        return True

    def record(self, trade: Trade) -> None:
        return None


class FilteredEntry:
    """The impulsive variant's gate (FR-G19/FR-G20).

    Two independent reasons to refuse an entry - either alone is enough:

    - the candle starts at or after the cut-off (16:00 market-local), so
      the last candle that can open a position is the one starting 15:55;
    - the day has already closed `max_losses` positions with negative
      points.

    A loss is `points < 0` whatever the exit reason, matching how the run
    summary counts losing positions. Deliberately not "stop-loss exits":
    under an impulse stop a day can bleed away through end-of-day closes
    without a single stop firing, and a cap blind to those would not bound
    what it claims to. A trade closing at exactly 0 is not a loss.
    """

    def __init__(
        self,
        cutoff_utc: Optional[datetime.datetime],
        max_losses: Optional[int],
    ):
        self.cutoff_utc = cutoff_utc
        self.max_losses = max_losses
        self.losses = 0

    def allows(self, candle_time: datetime.datetime) -> bool:
        if self.cutoff_utc is not None and candle_time >= self.cutoff_utc:
            return False
        if self.max_losses is not None and self.losses >= self.max_losses:
            return False
        return True

    def record(self, trade: Trade) -> None:
        if trade.points < 0:
            self.losses += 1


def cutoff_utc(
    local_time: datetime.time, market: Market, trading_date: datetime.date
) -> datetime.datetime:
    """A market-local cut-off as a naive UTC datetime for `trading_date`.

    Resolved per date through the same DST-aware conversion the session
    windows use, so a 16:00 Paris cut-off is 14:00 UTC in summer and 15:00
    in winter rather than a hardcoded offset."""
    reference = datetime.datetime(
        trading_date.year,
        trading_date.month,
        trading_date.day,
        tzinfo=PARIS_TZ,
    )
    utc_market = market_in_utc(market, reference)
    hour_shift = utc_market.open_hour - market.open_hour
    return datetime.datetime(
        trading_date.year,
        trading_date.month,
        trading_date.day,
        local_time.hour,
        local_time.minute,
    ) + datetime.timedelta(hours=hour_shift)


ALWAYS_OPEN = AlwaysOpen()
