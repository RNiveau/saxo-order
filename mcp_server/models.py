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

from pydantic import BaseModel, Field

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

    provenance: Provenance
    exchange: Exchange
    unit_time: UnitTime
    last_bar_date: Optional[datetime.datetime] = None
    truncated: bool = False
    forming_period_included: bool = True
    """Whether the period now trading is part of this answer.

    False means the instrument's session hours were not known, so the
    forming bar was left out rather than assembled against guessed ones -
    the series ends at the last completed period and the price with it.
    """


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
    columns: List[str] = Field(default_factory=lambda: list(BAR_COLUMNS))
    rows: List[List[Union[str, float, None]]] = Field(default_factory=list)
    current_incomplete: bool = False
    count: int = 0


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
