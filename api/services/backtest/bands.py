"""The combo strategy's two take-profit levels, read from a candle.

Unlike every other backtest, whose targets are fixed at entry from the H1
range, the combo strategy exits at levels the indicator itself defines:
the mm20 for the first lot and the opposite bollinger band for the runner
(FR-C07). Both are recomputed from the window ending at the candle being
evaluated, so they move as the position runs.
"""

from dataclasses import dataclass
from typing import List, Optional

from api.services.backtest.side import Side
from model import Candle
from services.indicator_service import bollinger_bands
from utils.exception import SaxoException

# The deviation the combo indicator treats as its inner band. Entry and
# exit are read off the same band the signal is defined against, so this
# tracks indicator_service.combo's bb20 rather than standing alone.
COMBO_BAND_DEVIATION = 2.0

# bollinger_bands averages 20 closes; fewer and it has nothing to say.
MIN_BAND_CANDLES = 20


@dataclass(frozen=True)
class BandLevels:
    """Where a candle puts the two targets.

    mm20 is the middle band - the 20-period average of the closes - and
    is TP1 for both directions. The runner's target is whichever outer
    band faces away from the entry, which is what `opposite` picks.
    """

    mm20: float
    upper: float
    bottom: float

    def opposite(self, side: Side) -> float:
        return self.upper if side.is_long else self.bottom


def levels(window: List[Candle]) -> Optional[BandLevels]:
    """The band levels at the newest candle of `window` (newest first),
    or None when there are too few candles to define them.

    None rather than an exception: the warm-up candles at the head of a
    run legitimately have no bands yet, and that is not an error - it is
    a stretch of the series the strategy cannot act on.
    """
    if len(window) < MIN_BAND_CANDLES:
        return None
    bands = bollinger_bands(window, COMBO_BAND_DEVIATION)
    return BandLevels(mm20=bands.middle, upper=bands.up, bottom=bands.bottom)


def levels_or_raise(window: List[Candle]) -> BandLevels:
    """The band levels for a candle that must have them - one an open
    position is being managed against. A position cannot exist over a
    stretch of the series with no bands, so this is an invariant
    violation rather than a quiet None."""
    band_levels = levels(window)
    if band_levels is None:
        raise SaxoException(
            "an open combo position needs band levels, but the window "
            f"holds only {len(window)} candles"
        )
    return band_levels
