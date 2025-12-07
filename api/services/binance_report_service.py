from operator import attrgetter
from typing import Dict, List, Optional

from cachetools import TTLCache, cachedmethod

from client.binance_client import BinanceClient
from client.gsheet_client import GSheetClient
from model import Account, Currency, Direction, ReportOrder, Signal, Strategy
from saxo_order.service import calculate_currency, calculate_taxes
from utils.configuration import Configuration
from utils.logger import Logger

logger = Logger.get_logger("binance_report_service")


class BinanceReportService:
    """Service for handling Binance trading report operations."""

    def __init__(self, client: BinanceClient, configuration: Configuration):
        self.client = client
        self.configuration = configuration
        self.currencies_rate = configuration.currencies_rate
        self.gsheet_client = GSheetClient(
            key_path=configuration.gsheet_creds_path,
            spreadsheet_id=configuration.spreadsheet_id,
        )
        # Cache for report data with 5 min TTL
        self._report_cache: TTLCache[str, List[ReportOrder]] = TTLCache(
            maxsize=128, ttl=300
        )

    def _get_binance_account(self) -> Account:
        """
        Create pseudo-account for Binance.

        Returns:
            Account object with static Binance identifier
        """
        return Account(
            key="binance",
            name="Coinbase",
            fund=0,
            client_key="binance",
        )

    @cachedmethod(cache=attrgetter("_report_cache"))
    def get_orders_report(
        self, account_id: str, from_date: str
    ) -> List[ReportOrder]:
        """
        Get orders report for Binance from a given date.

        Args:
            account_id: Binance account ID (should be "binance_main")
            from_date: Start date in YYYY-MM-DD format

        Returns:
            List of ReportOrder objects
        """
        logger.debug(
            f"Cache MISS for get_orders_report({account_id}, {from_date}) "
            f"- fetching from Binance API"
        )
        # Convert date format from YYYY-MM-DD to YYYY/MM/DD for BinanceClient
        date_formatted = from_date.replace("-", "/")

        # Get orders from Binance
        orders = self.client.get_report_all(
            date_formatted, self.currencies_rate["usdeur"]
        )

        return orders

    def convert_order_to_eur(
        self, order: ReportOrder
    ) -> tuple[float, float, Optional[float], Optional[float]]:
        """
        Convert order prices to EUR if needed.

        Returns:
            Tuple of (price_eur, total_eur, price_original, total_original)
        """
        if order.currency == Currency.EURO:
            return (
                order.price,
                order.price * order.quantity,
                None,
                None,
            )

        # Convert to EUR
        converted_order = calculate_currency(order, self.currencies_rate)
        return (
            converted_order.price,
            converted_order.price * order.quantity,
            order.price,
            order.price * order.quantity,
        )

    def calculate_summary(self, orders: List[ReportOrder]) -> Dict:
        """
        Calculate summary statistics for orders.

        Args:
            orders: List of ReportOrder objects

        Returns:
            Dictionary with summary statistics
        """
        total_orders = len(orders)
        total_volume_eur = 0.0
        total_fees_eur = 0.0
        buy_orders = 0
        buy_volume_eur = 0.0
        sell_orders = 0
        sell_volume_eur = 0.0

        for order in orders:
            # Convert to EUR
            price_eur, total_eur, _, _ = self.convert_order_to_eur(order)
            total_volume_eur += total_eur

            # Binance already includes commission in the order
            # calculate_taxes works for Binance orders too
            taxes = calculate_taxes(order)
            total_fees_eur += taxes.cost + taxes.taxes

            # Count by direction
            if order.direction and order.direction == Direction.BUY:
                buy_orders += 1
                buy_volume_eur += total_eur
            else:
                sell_orders += 1
                sell_volume_eur += total_eur

        return {
            "total_orders": total_orders,
            "total_volume_eur": round(total_volume_eur, 2),
            "total_fees_eur": round(total_fees_eur, 2),
            "buy_orders": buy_orders,
            "buy_volume_eur": round(buy_volume_eur, 2),
            "sell_orders": sell_orders,
            "sell_volume_eur": round(sell_volume_eur, 2),
        }

    def create_gsheet_order(
        self,
        account_id: str,
        order: ReportOrder,
        stop: Optional[float] = None,
        objective: Optional[float] = None,
        strategy: Strategy = None,  # type: ignore
        signal: Signal = None,  # type: ignore
        comment: Optional[str] = None,
    ):
        """
        Create a new order entry in Google Sheets.

        Args:
            account_id: Binance account ID (should be "binance_main")
            order: ReportOrder object
            stop: Stop loss price
            objective: Target price
            strategy: Trading strategy (required)
            signal: Trading signal (required)
            comment: Additional comment

        Raises:
            ValueError: If strategy or signal is not provided
        """
        if not strategy:
            raise ValueError(
                "Strategy is required when creating a new position"
            )
        if not signal:
            raise ValueError("Signal is required when creating a new position")

        # Get Binance pseudo-account
        account = self._get_binance_account()

        # Update order with user inputs
        order.stop = stop
        order.objective = objective
        order.strategy = strategy.value  # type: ignore
        order.signal = signal.value  # type: ignore
        order.comment = comment
        order.open_position = True

        # Calculate taxes
        order.taxes = calculate_taxes(order)

        # Convert to EUR if needed
        report_order = calculate_currency(order, self.currencies_rate)
        assert isinstance(report_order, ReportOrder)

        # Create in Google Sheets
        self.gsheet_client.create_order(
            account=account, order=report_order, original_order=order
        )

    def update_gsheet_order(
        self,
        account_id: str,
        order: ReportOrder,
        line_number: int,
        close: bool = False,
        stopped: bool = False,
        be_stopped: bool = False,
        stop: Optional[float] = None,
        objective: Optional[float] = None,
        strategy: Optional[Strategy] = None,
        signal: Optional[Signal] = None,
        comment: Optional[str] = None,
    ):
        """
        Update an existing order entry in Google Sheets.

        Args:
            account_id: Binance account ID (should be "binance_main")
            order: ReportOrder object
            line_number: Sheet row number to update
            close: Whether to close the position
            stopped: Whether order was stopped out
            be_stopped: Whether order was break-even stopped
            stop: Optional updated stop loss
            objective: Optional updated target
            strategy: Optional updated strategy enum
            signal: Optional updated signal enum
            comment: Optional updated comment
        """
        # Update order with user inputs
        if stop is not None:
            order.stop = stop
        if objective is not None:
            order.objective = objective
        if strategy is not None:
            order.strategy = strategy.value  # type: ignore
        if signal is not None:
            order.signal = signal.value  # type: ignore
        if comment is not None:
            order.comment = comment

        # Position is closed if close=True, regardless of stopped/be_stopped
        order.open_position = not close
        order.stopped = stopped
        order.be_stopped = be_stopped
        order.taxes = calculate_taxes(order)

        # Convert to EUR if needed
        report_order = calculate_currency(order, self.currencies_rate)
        assert isinstance(report_order, ReportOrder)

        # Update in Google Sheets
        self.gsheet_client.update_order(
            order=report_order,
            original_order=order,
            line_to_update=line_number,
        )
