import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from model.backtest import (  # noqa: F401
    BacktestDefinition,
    BacktestParameters,
    BacktestRunResult,
    BacktestSummary,
    CachedDayCandles,
    DayResult,
    DayResultSummary,
    Trade,
)
from model.enum import (  # noqa: F401
    AlertType,
    AssetType,
    Conviction,
    Currency,
    DayStatus,
    Direction,
    ExitReason,
    IndicatorName,
    MarketName,
    OrderType,
    Provenance,
    Signal,
    Strategy,
    TriggerOrder,
)
from model.market import (  # noqa: F401
    DaxCfdMarket,
    EuCfdMarket,
    EUMarket,
    Market,
    USMarket,
)
from model.workflow import (  # noqa: F401
    BollingerBands,
    Candle,
    Close,
    ComboSignal,
    Condition,
    Indicator,
    IndicatorInclined,
    IndicatorType,
    Point,
    SignalStrength,
    Trigger,
    UnitTime,
    Workflow,
    WorkflowDirection,
    WorkflowElement,
    WorkflowLocation,
    WorkflowSignal,
)
from model.zone_bourse import ZoneBourseScore, ZoneBourseScrap  # noqa: F401


@dataclass
class Alert:
    alert_type: AlertType
    date: datetime.datetime
    data: Dict[str, Any]
    asset_code: str
    asset_description: str
    exchange: str = "saxo"
    country_code: Optional[str] = None

    @property
    def id(self) -> str:
        """Composite ID from asset code and country code"""
        if self.country_code:
            return f"{self.asset_code}_{self.country_code}"
        else:
            return self.asset_code

    @property
    def dedup_signature(self) -> tuple:
        """What makes this alert a repeat of one already stored."""
        return alert_dedup_signature(
            self.alert_type.value, self.date.isoformat(), self.data
        )


def alert_dedup_signature(
    alert_type: str, date: str, data: Optional[Dict[str, Any]]
) -> tuple:
    """
    What makes two alerts the same alert.

    Every type but one is a repeat when it fires again on the same scan date,
    which is the rule the alerts table has always applied. A weekly combo is
    different: the scan runs daily against a bar that lives for a week, so the
    same setup would be recorded five times under that rule. It is a repeat
    when it describes the same weekly bar in the same direction - and a
    direction that flips mid-bar is new information, not a repeat.

    Callers pass stored rows and freshly detected alerts through the same
    function, so the two sides cannot drift apart. A weekly alert missing
    either key falls back to the shared rule rather than raising: a row
    written by an older version is still comparable, just less precisely.
    """
    same_day = (
        alert_type,
        datetime.datetime.fromisoformat(date).date().isoformat(),
    )
    if alert_type != AlertType.COMBO_WEEKLY.value or not isinstance(
        data, dict
    ):
        return same_day
    bar_date = data.get("weekly_bar_date")
    direction = data.get("direction")
    if bar_date is None or direction is None:
        return same_day
    return (alert_type, str(bar_date), str(direction))


@dataclass
class WorkflowTrigger:
    workflow_name: str
    direction: Direction
    order_price: float
    placed_at: int
    dry_run: bool
    trigger_close: Optional[float] = None


@dataclass
class TriagedAsset:
    asset_code: str
    asset_description: str
    exchange: str
    conviction: Conviction
    rationale: str
    patterns: List[AlertType]
    ma50_slope: Optional[float] = None
    rank: Optional[int] = None
    country_code: Optional[str] = None
    workflow_triggers: List[WorkflowTrigger] = field(default_factory=list)


@dataclass
class AlertDigest:
    run_date: str
    created_at: int
    summary: str
    counts: Dict[str, int]
    triaged_assets: List[TriagedAsset]
    model: str
    fallback_used: bool = False


@dataclass
class Taxes:
    cost: float
    taxes: float


@dataclass
class Account:

    key: str
    name: str
    fund: float = 0
    available_fund: float = 0
    client_key: str = ""


def crypto_account() -> Account:
    """
    Single source of truth for the crypto journal identity.

    Both Binance and Ouinex trades are written to the Google Sheet under this
    same pseudo-account, so Ouinex rows are indistinguishable from Binance rows
    ("map as binance").
    """
    return Account(
        key="binance",
        name="Coinbase",
        fund=0,
        client_key="binance",
    )


@dataclass
class Underlying:
    price: float
    stop: float = 0
    objective: float = 0


@dataclass
class Order:

    code: str
    price: float
    name: str = ""
    quantity: float = 0
    objective: Optional[float] = None
    stop: Optional[float] = None
    comment: Optional[str] = None
    strategy: Optional[Strategy] = None
    direction: Optional[Direction] = None
    asset_type: str = "Stock"
    type: OrderType = OrderType.LIMIT
    taxes: Optional[Taxes] = None
    underlying: Optional[Underlying] = None
    conditional: bool = False
    currency: Currency = Currency.EURO
    signal: Optional[Signal] = None

    def __repr__(self) -> str:
        return f"{self.code}: {self.quantity} * {self.price} {self.currency}"


class ReportOrder(Order):
    def __init__(
        self,
        code: str,
        price: float,
        date: datetime.datetime,
        name: str = "",
        quantity: float = 0,
        objective: Optional[float] = None,
        stop: Optional[float] = None,
        comment: Optional[str] = None,
        strategy: Optional[Strategy] = None,
        direction: Optional[Direction] = None,
        asset_type: str = "Stock",
        type: OrderType = OrderType.LIMIT,
        taxes: Optional[Taxes] = None,
        underlying: Optional[Underlying] = None,
        conditional: bool = False,
        currency: Currency = Currency.EURO,
        stopped: bool = False,
        be_stopped: bool = False,
        open_position: bool = True,
    ) -> None:
        super().__init__(
            code,
            price,
            name,
            quantity,
            objective,
            stop,
            comment,
            strategy,
            direction,
            asset_type,
            type,
            taxes,
            underlying,
            conditional,
            currency,
        )
        self.date = date
        self.stopped = stopped
        self.be_stopped = be_stopped
        self.open_position = open_position


@dataclass
class ConditionalOrder:
    saxo_uic: int
    trigger: TriggerOrder
    price: float
    asset_type: str


@dataclass
class StackingReport:
    date: str
    asset: str
    quantity: float

    @property
    def id(self) -> str:
        return f"{self.date}{self.asset}"


@dataclass
class TradeRepublicTransaction:
    date: datetime.date
    datetime: datetime.datetime
    account_type: str
    category: str
    type: str
    amount: float
    currency: Union[Currency, str]
    transaction_id: str
    asset_class: Optional[AssetType] = None
    name: Optional[str] = None
    symbol: Optional[str] = None
    shares: Optional[float] = None
    price: Optional[float] = None
    fee: Optional[float] = None
    tax: Optional[float] = None
    original_amount: Optional[float] = None
    original_currency: Optional[Union[Currency, str]] = None
    fx_rate: Optional[float] = None
    description: Optional[str] = None
    counterparty_name: Optional[str] = None
    counterparty_iban: Optional[str] = None
    payment_reference: Optional[str] = None
    mcc_code: Optional[str] = None


@dataclass
class ParseError:
    row_number: int
    raw_line: str
    reason: str
