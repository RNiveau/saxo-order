from operator import attrgetter
from typing import Dict, List, Optional

from cachetools import TTLCache, cachedmethod

from client.gsheet_client import GSheetClient
from client.saxo_client import SaxoClient
from model import Account, Currency, Direction, ReportOrder
from saxo_order.service import calculate_currency, calculate_taxes
from utils.configuration import Configuration
from utils.logger import Logger

logger = Logger.get_logger("report_service")


class ReportService:
    """Service for handling trading report operations."""

    def __init__(self, client: SaxoClient, configuration: Configuration):
        self.client = client
        self.configuration = configuration
        self.currencies_rate = configuration.currencies_rate
        # Cache for report data with 5 min TTL
        self._report_cache: TTLCache[str, List[ReportOrder]] = TTLCache(
            maxsize=128, ttl=300
        )

    def _find_account_dict(self, account_identifier: str) -> Dict:
        """
        Find account by either AccountId or DisplayName.

        Args:
            account_identifier: Either AccountId or DisplayName

        Returns:
            Account dictionary from Saxo API

        Raises:
            ValueError: If account not found
        """
        accounts_data = self.client.get_accounts()
        accounts = accounts_data.get("Data", [])

        # Try to find by AccountId first
        account_dict = next(
            (
                acc
                for acc in accounts
                if acc["AccountId"] == account_identifier
            ),
            None,
        )

        # If not found, try to find by DisplayName
        if not account_dict:
            for acc in accounts:
                try:
                    account_key = acc["AccountKey"]
                    full_account = self.client.get_account(account_key)
                    if full_account.name == account_identifier:
                        account_dict = acc
                        break
                except Exception:
                    continue

        if not account_dict:
            raise ValueError(f"Account {account_identifier} not found")

        return account_dict

    @cachedmethod(cache=attrgetter("_report_cache"))
    def get_orders_report(
        self, account_id: str, from_date: str
    ) -> List[ReportOrder]:
        """
        Get orders report for a specific account from a given date.

        Args:
            account_id: Saxo account ID or DisplayName
            from_date: Start date in YYYY-MM-DD format

        Returns:
            List of ReportOrder objects
        """
        # Get account details
        account_dict = self._find_account_dict(account_id)

        if not account_dict:
            raise ValueError(f"Account {account_id} not found")

        account = Account(
            key=account_dict["AccountKey"],
            name=account_dict["AccountId"],
            client_key=account_dict["ClientKey"],
        )

        # Get orders from Saxo
        orders = self.client.get_report(account, from_date)

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

            # Calculate taxes
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
        strategy: Optional[str] = None,
        signal: Optional[str] = None,
        comment: Optional[str] = None,
    ):
        """
        Create a new order entry in Google Sheets.

        Args:
            account_id: Saxo account ID
            order: ReportOrder object
            stop: Stop loss price
            objective: Target price
            strategy: Trading strategy
            signal: Trading signal
            comment: Additional comment
        """
        # Initialize GSheet client
        gsheet_client = GSheetClient(
            key_path=self.configuration.gsheet_creds_path,
            spreadsheet_id=self.configuration.spreadsheet_id,
        )

        # Get account
        account_dict = self._find_account_dict(account_id)

        account = Account(
            key=account_dict["AccountKey"],
            name=account_dict["AccountId"],
            client_key=account_dict["ClientKey"],
        )

        # Update order with user inputs
        order.stop = stop
        order.objective = objective
        order.strategy = strategy  # type: ignore
        order.signal = signal  # type: ignore
        order.comment = comment
        order.open_position = True

        # Calculate taxes
        order.taxes = calculate_taxes(order)

        # Convert to EUR if needed
        report_order = calculate_currency(order, self.currencies_rate)
        assert isinstance(report_order, ReportOrder)

        # Create in Google Sheets
        gsheet_client.create_order(
            account=account, order=report_order, original_order=order
        )

    def update_gsheet_order(
        self,
        account_id: str,
        order: ReportOrder,
        line_number: int,
        stopped: bool = False,
        be_stopped: bool = False,
        stop: Optional[float] = None,
        objective: Optional[float] = None,
        strategy: Optional[str] = None,
        signal: Optional[str] = None,
        comment: Optional[str] = None,
    ):
        """
        Update an existing order entry in Google Sheets.

        Args:
            account_id: Saxo account ID
            order: ReportOrder object
            line_number: Sheet row number to update
            stopped: Whether order was stopped out
            be_stopped: Whether order was break-even stopped
            stop: Optional updated stop loss
            objective: Optional updated target
            strategy: Optional updated strategy
            signal: Optional updated signal
            comment: Optional updated comment
        """
        # Initialize GSheet client
        gsheet_client = GSheetClient(
            key_path=self.configuration.gsheet_creds_path,
            spreadsheet_id=self.configuration.spreadsheet_id,
        )

        # Update order with user inputs
        if stop is not None:
            order.stop = stop
        if objective is not None:
            order.objective = objective
        if strategy is not None:
            order.strategy = strategy  # type: ignore
        if signal is not None:
            order.signal = signal  # type: ignore
        if comment is not None:
            order.comment = comment

        # If both stopped and be_stopped are False,
        # it's an update that keeps position open
        order.open_position = not (stopped or be_stopped)
        order.stopped = stopped
        order.be_stopped = be_stopped
        order.taxes = calculate_taxes(order)

        # Convert to EUR if needed
        report_order = calculate_currency(order, self.currencies_rate)
        assert isinstance(report_order, ReportOrder)

        # Update in Google Sheets
        gsheet_client.update_order(
            order=report_order,
            original_order=order,
            line_to_update=line_number,
        )
