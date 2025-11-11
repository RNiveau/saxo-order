from typing import Optional

from client.saxo_client import SaxoClient
from model import (
    Account,
    ConditionalOrder,
    Currency,
    Direction,
    Order,
    OrderType,
    Signal,
    Strategy,
)
from saxo_order.service import apply_rules, calculate_taxes
from utils.configuration import Configuration
from utils.exception import SaxoException
from utils.logger import Logger

logger = Logger.get_logger("order_service")


class OrderService:
    """Service layer for order management, shared by CLI and API."""

    def __init__(self, client: SaxoClient, configuration: Configuration):
        self.client = client
        self.configuration = configuration

    def create_order(
        self,
        code: str,
        price: float,
        quantity: float,
        order_type: str,
        direction: str,
        country_code: str = "xpar",
        conditional_order: Optional[ConditionalOrder] = None,
        stop: Optional[float] = None,
        objective: Optional[float] = None,
        strategy: Optional[str] = None,
        signal: Optional[str] = None,
        comment: Optional[str] = None,
        account_key: Optional[str] = None,
    ) -> dict:
        """
        Create and place a single order.

        Args:
            code: Stock/asset code
            price: Order price
            quantity: Number of units
            order_type: Order type (limit, stop, open_stop, market)
            direction: Buy or sell
            country_code: Market code (default: xpar)
            conditional_order: Optional conditional order
            stop: Optional stop price
            objective: Optional objective price
            strategy: Optional strategy (string value)
            signal: Optional signal (string value)
            comment: Optional comment
            account_key: Optional account key

        Returns:
            dict: Order placement result

        Raises:
            SaxoException: If validation fails
        """
        asset = self.client.get_asset(code=code, market=country_code)

        order_type_enum = OrderType.get_value(order_type)
        if order_type_enum == OrderType.MARKET:
            price = self.client.get_price(
                asset["Identifier"], asset["AssetType"]
            )

        order = Order(
            code=code,
            name=asset["Description"],
            price=price,
            quantity=quantity,
            asset_type=asset["AssetType"],
            type=order_type_enum,
            direction=Direction.get_value(direction),
            currency=Currency.get_value(asset["CurrencyCode"]),
            stop=stop,
            objective=objective,
            strategy=Strategy.get_value(strategy) if strategy else None,
            signal=Signal.get_value(signal) if signal else None,
            comment=comment,
        )

        if order.taxes is None:
            order.taxes = calculate_taxes(order)

        account = self._get_account(account_key)

        if Direction.BUY == order.direction:
            self._validate_buy_order(account, order)

        result = self.client.set_order(
            account=account,
            order=order,
            saxo_uic=asset["Identifier"],
            conditional_order=conditional_order,
        )

        return {
            "success": True,
            "order": order,
            "account": account,
            "result": result,
        }

    def create_oco_order(
        self,
        code: str,
        quantity: float,
        limit_price: float,
        limit_direction: str,
        stop_price: float,
        stop_direction: str,
        country_code: str = "xpar",
        stop: Optional[float] = None,
        objective: Optional[float] = None,
        strategy: Optional[str] = None,
        signal: Optional[str] = None,
        comment: Optional[str] = None,
        account_key: Optional[str] = None,
    ) -> dict:
        """
        Create and place an OCO (One-Cancels-Other) order.

        Args:
            code: Stock/asset code
            quantity: Number of units
            limit_price: Limit order price
            limit_direction: Limit order direction (buy/sell)
            stop_price: Stop order price
            stop_direction: Stop order direction (buy/sell)
            country_code: Market code (default: xpar)
            stop: Optional stop price for risk management
            objective: Optional objective price
            strategy: Optional strategy
            signal: Optional signal
            comment: Optional comment
            account_key: Optional account key

        Returns:
            dict: Order placement result

        Raises:
            SaxoException: If validation fails or order placement fails
        """
        asset = self.client.get_asset(code=code, market=country_code)

        limit_order = Order(
            code=code,
            name=asset["Description"],
            price=limit_price,
            quantity=quantity,
            direction=Direction.get_value(limit_direction),
            asset_type=asset["AssetType"],
            type=OrderType.OCO,
            currency=Currency.get_value(asset["CurrencyCode"]),
        )

        stop_order = Order(
            code=code,
            name=asset["Description"],
            price=stop_price,
            quantity=quantity,
            direction=Direction.get_value(stop_direction),
            asset_type=asset["AssetType"],
            type=OrderType.OCO,
            currency=Currency.get_value(asset["CurrencyCode"]),
            stop=stop,
            objective=objective,
            strategy=Strategy.get_value(strategy) if strategy else None,
            signal=Signal.get_value(signal) if signal else None,
            comment=comment,
        )

        if stop_order.taxes is None:
            stop_order.taxes = calculate_taxes(stop_order)

        account = self._get_account(account_key)

        if stop_order.direction == Direction.BUY:
            self._validate_buy_order(account, stop_order)

        result = self.client.set_oco_order(
            account=account,
            limit_order=limit_order,
            stop_order=stop_order,
            saxo_uic=asset["Identifier"],
        )

        return {
            "success": True,
            "limit_order": limit_order,
            "stop_order": stop_order,
            "account": account,
            "result": result,
        }

    def create_stop_limit_order(
        self,
        code: str,
        quantity: float,
        limit_price: float,
        stop_price: float,
        country_code: str = "xpar",
        stop: Optional[float] = None,
        objective: Optional[float] = None,
        strategy: Optional[str] = None,
        signal: Optional[str] = None,
        comment: Optional[str] = None,
        account_key: Optional[str] = None,
    ) -> dict:
        """
        Create and place a stop-limit order.

        Args:
            code: Stock/asset code
            quantity: Number of units
            limit_price: Limit price
            stop_price: Stop trigger price
            country_code: Market code (default: xpar)
            stop: Optional stop price for risk management
            objective: Optional objective price
            strategy: Optional strategy
            signal: Optional signal
            comment: Optional comment
            account_key: Optional account key

        Returns:
            dict: Order placement result

        Raises:
            SaxoException: If validation fails or order placement fails
        """
        asset = self.client.get_asset(code=code, market=country_code)
        account = self._get_account(account_key)

        order = Order(
            code=code,
            name=asset["Description"],
            price=limit_price,
            quantity=quantity,
            asset_type=asset["AssetType"],
            type=OrderType.STOP_LIMIT,
            direction=Direction.BUY,
            currency=Currency.get_value(asset["CurrencyCode"]),
            stop=stop,
            objective=objective,
            strategy=Strategy.get_value(strategy) if strategy else None,
            signal=Signal.get_value(signal) if signal else None,
            comment=comment,
        )

        if order.taxes is None:
            order.taxes = calculate_taxes(order)

        self._validate_buy_order(account, order)

        result = self.client.set_order(
            account=account,
            stop_price=stop_price,
            order=order,
            saxo_uic=asset["Identifier"],
        )

        return {
            "success": True,
            "order": order,
            "account": account,
            "result": result,
        }

    def _get_account(self, account_key: Optional[str] = None) -> Account:
        """
        Get account by key or return the first available account.

        Args:
            account_key: Optional account key

        Returns:
            Account object

        Raises:
            SaxoException: If account not found
        """
        accounts = self.client.get_accounts()

        if account_key:
            matching_accounts = [
                acc
                for acc in accounts["Data"]
                if acc["AccountKey"] == account_key
            ]
            if not matching_accounts:
                raise SaxoException(f"Account {account_key} not found")
            return self.client.get_account(matching_accounts[0]["AccountKey"])

        if not accounts["Data"]:
            raise SaxoException("No accounts available")

        return self.client.get_account(accounts["Data"][0]["AccountKey"])

    def _validate_buy_order(self, account: Account, order: Order) -> None:
        """
        Validate buy order against rules.

        Args:
            account: Account to validate against
            order: Order to validate

        Raises:
            SaxoException: If validation fails
        """
        open_orders = self.client.get_open_orders()
        total_amount = self.client.get_total_amount()
        error = apply_rules(account, order, total_amount, open_orders)
        if error is not None:
            raise SaxoException(error)
