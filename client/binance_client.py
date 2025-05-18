import logging
from datetime import datetime
from typing import Dict, List

from binance.error import ClientError
from binance.spot import Spot  # type: ignore

from model import AssetType, Currency, Direction, ReportOrder, Taxes
from utils.logger import Logger


class BinanceClient:
    ASSET_WITHLIST = [
        "ETH",
        "BTC",
        "XRP",
        "COTI",
        "SOL",
        "ADA",
        "ATOM",
        "NEAR",
        "RUNE",
        "INJ",
        "LINK",
        "MANA",
        "ORN",
        "ERN",
        "FTM",
        "LTC",
        "AR",
        "SNX",
        "ETC",
        "STX",
        "STORJ",
        "THETA",
        "OMG",
        "DGB",
        "AAVE",
        "SUPER",
    ]

    def __init__(self, key: str, secret: str) -> None:
        self.logger = Logger.get_logger("binance_client", logging.INFO)
        self.client = Spot(key, secret)

    def _merge_trades(self, trades: List) -> List:
        merged_trades = {}
        for trade in trades:
            if trade["orderId"] not in merged_trades:
                merged_trades[trade["orderId"]] = trade
            else:
                order_id = trade["orderId"]
                merged_trades[order_id]["qty"] = float(
                    merged_trades[order_id]["qty"]
                ) + float(trade["qty"])
                merged_trades[order_id]["commission"] = float(
                    merged_trades[order_id]["commission"]
                ) + float(trade["commission"])
        return list(merged_trades.values())

    def _apply_commmission(
        self, trade: Dict, order: ReportOrder, usdeur_rate: float
    ) -> None:
        if trade["isBuyer"] is True:
            commission = float(trade["commission"])
            if trade["commissionAsset"] != order.name and commission > 0:
                print(
                    f"Can't calculate commision for the trade: {order.name}:\
                    {trade['price']}$"
                )
                print(trade)
                return
            order.quantity -= commission
            cost = commission * (order.price * usdeur_rate)
            order.taxes = Taxes(cost=cost, taxes=0)
        else:
            if trade["commissionAsset"] not in ["BUSD", "USDT", "USDC"]:
                print(
                    f"Can't calculate commision for the trade: {order.name}: \
                    {trade['price']}$"
                )
                return
            order.taxes = Taxes(
                cost=float(trade["commission"]) * usdeur_rate, taxes=0
            )

    def get_report(
        self, symbol: str, date: str, usdeur_rate: float
    ) -> List[ReportOrder]:
        timestamp = datetime.strptime(date, "%Y/%m/%d").timestamp() * 1000
        try:
            trades = self.client.my_trades(
                f"{symbol}BUSD", startTime=int(timestamp)
            )
        except ClientError as e:
            self.logger.error(f"{symbol}BUSD {e}")
            return []
        try:
            trades += self.client.my_trades(
                f"{symbol}USDT", startTime=int(timestamp)
            )
            trades += self.client.my_trades(
                f"{symbol}USDC", startTime=int(timestamp)
            )
        except ClientError as e:
            self.logger.error(f"{symbol}USDC / USDT {e}")
        orders = []
        for trade in self._merge_trades(trades):
            direction = (
                Direction.BUY if trade["isBuyer"] is True else Direction.SELL
            )
            order = ReportOrder(
                code=symbol,
                name=symbol,
                price=float(trade["price"]),
                quantity=float(trade["qty"]),
                direction=direction,
                asset_type=AssetType.CRYPTO,
                date=datetime.fromtimestamp(int(trade["time"]) / 1000),
                currency=Currency.USD,
            )
            self._apply_commmission(trade, order, usdeur_rate)
            orders.append(order)
        return orders

    def get_report_all(
        self, date: str, usdeur_rate: float
    ) -> List[ReportOrder]:
        orders = []
        for coin in BinanceClient.ASSET_WITHLIST:
            orders += self.get_report(coin, date, usdeur_rate)
        return orders
