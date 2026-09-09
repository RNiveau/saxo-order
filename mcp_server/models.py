"""Response shapes for the MCP asset-analysis tools.

Pydantic annotations are the wire contract: the SDK derives each tool's
output schema from them, so field names and enums here are what the model
actually sees.

Nothing in this module is persisted. Two conventions are load-bearing:
every asset-bearing model names its ``exchange`` explicitly rather than
letting anything infer it, and an absent value is always accompanied by a
reason - a field that is simply missing tells the reader nothing about
whether it failed or was flat.
"""

import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_serializer

from model import (
    AlertType,
    AssetType,
    Conviction,
    Direction,
    IndicatorName,
    Provenance,
    UnitTime,
)
from model.enum import Exchange

BAR_COLUMNS = ["date", "open", "high", "low", "close"]


class ResponseMeta(BaseModel):
    """What this answer describes, when, and how much it is worth."""

    provenance: Provenance = Field(
        description=(
            "Where the numbers came from. SIMULATED means fabricated data "
            "that was explicitly opted in to, and says nothing about the "
            "real instrument."
        )
    )
    exchange: Exchange = Field(description="The venue this answer describes.")
    unit_time: UnitTime = Field(
        description="The timeframe of the bars behind this answer."
    )
    last_bar_date: Optional[datetime.datetime] = Field(
        default=None,
        description=(
            "Timestamp of the newest bar, which is how current this answer "
            "is. None when there was no history at all."
        ),
    )
    truncated: bool = Field(
        default=False,
        description=(
            "True when the number of bars asked for exceeded the server's "
            "hard cap, so the request was overridden and both the fetch and "
            "the answer stop at the cap. Asking for fewer bars than that "
            "is a request being honoured and leaves this False, however "
            "much history came back."
        ),
    )
    forming_period_included: bool = Field(
        default=True,
        description=(
            "Whether the instrument's session hours were known, so the "
            "period now trading could be part of this answer. False means "
            "they were not, and the forming bar was left out rather than "
            "assembled against guessed hours - the series ends at the last "
            "completed period and the price with it. True does not by "
            "itself mean a period is currently trading: see "
            "current_incomplete on a bar series."
        ),
    )

    @field_serializer("last_bar_date")
    def _serialize_last_bar_date(
        self, value: Optional[datetime.datetime]
    ) -> Optional[str]:
        """Emit RFC 3339, which the tool schema's date-time format demands.

        Saxo's bar times are UTC, but the client parses the trailing Z as a
        literal, so they arrive naive and serialise without an offset -
        valid ISO 8601, rejected by an RFC 3339 validator. Restoring the
        offset the parse dropped is what makes the payload readable.
        """
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=datetime.timezone.utc)
        return value.isoformat()


class InstrumentRef(BaseModel):
    """A resolved instrument. The join key for every analysis tool."""

    code: str
    description: str
    exchange: Exchange
    asset_type: AssetType
    instrument_id: Optional[int] = None
    unavailable_reason: Optional[str] = Field(
        default=None,
        description=(
            "Set when the instrument exists but cannot be analysed, e.g. the "
            "venue returned no identifier for it."
        ),
    )


class BarSeries(BaseModel):
    """Price bars, newest first, columnar to keep the payload small."""

    meta: ResponseMeta
    instrument_id: int
    columns: List[str] = Field(
        default_factory=lambda: list(BAR_COLUMNS),
        description="The field each position in a row holds.",
    )
    rows: List[List[Union[str, float, None]]] = Field(
        default_factory=list,
        description=(
            "One bar per row, values in `columns` order, newest first: row "
            "0 is the most recent bar. Empty means the instrument has no "
            "history, which is an answer rather than a failure."
        ),
    )
    current_incomplete: bool = Field(
        default=False,
        description=(
            "True when row 0 is the period still trading, so its close, "
            "high and low can still move. False means every row is a "
            "closed bar."
        ),
    )
    count: int = Field(
        default=0,
        description=(
            "How many bars are actually in `rows`, which may be fewer than "
            "were asked for. meta.truncated says whether the cap is why."
        ),
    )


class IndicatorValue(BaseModel):
    """One indicator: a value, or the reason there isn't one."""

    name: IndicatorName
    value: Optional[Union[float, Dict[str, float]]] = None
    unavailable_reason: Optional[str] = None


class IndicatorSnapshot(BaseModel):
    """An instrument's technical state for one timeframe.

    Identified by what the caller passed in, not by a full InstrumentRef:
    the description and symbol would need another provider request to fill,
    and the caller already has them from the search that produced the id.
    """

    meta: ResponseMeta
    instrument_id: int
    asset_type: AssetType
    current_price: Optional[float] = None
    variation_pct: Optional[float] = None
    indicators: List[IndicatorValue] = Field(default_factory=list)
    bars_fetched: int = 0


class PatternHit(BaseModel):
    """A setup that fired, in the scan's own vocabulary."""

    alert_type: AlertType
    direction: Optional[Direction] = None
    data: Dict[str, Any] = Field(default_factory=dict)


class DetectorFailure(BaseModel):
    """A detector that could not run, and why."""

    alert_type: AlertType
    reason: str


class DetectionResult(BaseModel):
    """What fired, what was checked, and what could not be checked.

    ``hits == []`` with ``evaluated`` populated is a confident "nothing is
    firing" - which is only true if everything the scan runs was actually
    evaluated. A detector that failed belongs in ``failed``, never dropped
    silently from ``evaluated``.
    """

    meta: ResponseMeta
    instrument_id: int
    asset_type: AssetType
    hits: List[PatternHit] = Field(default_factory=list)
    evaluated: List[AlertType] = Field(default_factory=list)
    failed: List[DetectorFailure] = Field(default_factory=list)


class StoredAlert(BaseModel):
    """An alert the scheduled scan recorded, read back unchanged."""

    code: str
    description: str = ""
    exchange: Exchange
    alert_types: List[AlertType] = Field(default_factory=list)
    date: str
    data: Dict[str, Any] = Field(default_factory=dict)


class DigestEntry(BaseModel):
    """One asset's line in a stored triage digest."""

    run_date: str
    code: str
    exchange: Exchange
    conviction: Optional[Conviction] = None
    rank: Optional[int] = None
    rationale: str = ""
    summary: str = ""


class AssetContext(BaseModel):
    """The analyst's own relationship to an asset."""

    code: str
    exchange: Exchange
    in_watchlist: bool = False
    labels: List[str] = Field(default_factory=list)
    open_workflow_orders: List[Dict[str, Any]] = Field(default_factory=list)
