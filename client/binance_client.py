import logging
from datetime import datetime
from typing import Dict, List

import requests
from binance.error import ClientError
from binance.spot import Spot  # type: ignore

from model import AssetType, Currency, Direction, ReportOrder, Taxes
from model.asset import Asset
from model.enum import Exchange
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

    def search(self, keyword: str) -> List[Asset]:
        """
        Search for trading pairs on Binance by keyword.

        Args:
            keyword: Search keyword to match against symbol, baseAsset,
                     or quoteAsset

        Returns:
            List of Asset objects for matching trading pairs
        """
        try:
            response = requests.get(
                "https://api.binance.com/api/v3/exchangeInfo", timeout=10
            )
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch Binance exchange info: {e}")
            return []

        keyword_lower = keyword.lower()
        results = []

        for symbol_data in data.get("symbols", []):
            if symbol_data.get("status") != "TRADING":
                continue

            symbol = symbol_data.get("symbol", "")
            base_asset = symbol_data.get("baseAsset", "")
            quote_asset = symbol_data.get("quoteAsset", "")

            if (
                keyword_lower in symbol.lower()
                or keyword_lower in base_asset.lower()
                or keyword_lower in quote_asset.lower()
            ):
                asset = Asset(
                    symbol=symbol,
                    description=f"{base_asset}/{quote_asset}",
                    asset_type=AssetType.CRYPTO,
                    exchange=Exchange.BINANCE,
                    identifier=None,
                )
                results.append(asset)

        return results
