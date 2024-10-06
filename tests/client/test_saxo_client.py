import datetime

import pytest
import requests

from client.saxo_client import SaxoClient
from model import (
    Account,
    ConditionalOrder,
    Direction,
    Order,
    OrderType,
    TriggerOrder,
)
from tests.utils.configuration import MockConfiguration


class TestSaxoClient:
    @pytest.mark.parametrize(
        "stock_code, price, quantity, type, direction, stop_price,"
        "conditional_order, expected",
        [
            (
                12345,
                10,
                9,
                OrderType.LIMIT,
                Direction.BUY,
                None,
                None,
                {
                    "Amount": 9,
                    "OrderPrice": 10,
                    "Uic": 12345,
                    "OrderType": "Limit",
                    "OrderDuration": {"DurationType": "GoodTillCancel"},
                    "BuySell": "Buy",
                },
            ),
            (
                12345,
                10,
                9,
                OrderType.STOP,
                Direction.BUY,
                100,
                None,
                {
                    "Amount": 9,
                    "OrderPrice": 10,
                    "Uic": 12345,
                    "OrderType": "Stop",
                    "OrderDuration": {"DurationType": "GoodTillCancel"},
                    "BuySell": "Buy",
                },
            ),
            (
                12345,
                10,
                9,
                OrderType.OPEN_STOP,
                Direction.SELL,
                None,
                None,
                {
                    "Amount": 9,
                    "OrderPrice": 10,
                    "Uic": 12345,
                    "OrderType": "StopIfTraded",
                    "OrderDuration": {"DurationType": "GoodTillCancel"},
                    "BuySell": "Sell",
                },
            ),
            (
                12345,
                10,
                9,
                OrderType.STOP_LIMIT,
                Direction.BUY,
                8,
                None,
                {
                    "Amount": 9,
                    "OrderPrice": 8,
                    "Uic": 12345,
                    "OrderType": "StopLimit",
                    "BuySell": "Buy",
                    "OrderDuration": {"DurationType": "GoodTillCancel"},
                    "StopLimitPrice": 10,
                },
            ),
            (
                12345,
                10,
                9,
                OrderType.MARKET,
                Direction.BUY,
                8,
                None,
                {
                    "Amount": 9,
                    "Uic": 12345,
                    "OrderType": "Market",
                    "OrderDuration": {"DurationType": "DayOrder"},
                    "BuySell": "Buy",
                },
            ),
            (
                12345,
                10,
                9.5,
                OrderType.MARKET,
                Direction.BUY,
                8,
                ConditionalOrder(
                    1,
                    trigger=TriggerOrder.BELLOW,
                    price=40.7,
                    asset_type="ETF",
                ),
                {
                    "Amount": 9.5,
                    "Uic": 12345,
                    "OrderType": "Market",
                    "OrderDuration": {"DurationType": "DayOrder"},
                    "BuySell": "Buy",
                    "Orders": [
                        {
                            "AccountKey": "account",
                            "AssetType": "ETF",
                            "ManualOrder": True,
                            "BuySell": "Buy",
                            "OrderType": "TriggerLimit",
                            "Uic": 1,
                            "OrderDuration": {
                                "DurationType": "GoodTillCancel"
                            },
                            "TriggerOrderData": {
                                "LowerPrice": 40.7,
                                "PriceType": "LastTraded",
                            },
                        }
                    ],
                },
            ),
            (
                12345,
                10,
                9,
                OrderType.LIMIT,
                Direction.BUY,
                8,
                ConditionalOrder(
                    1, trigger=TriggerOrder.ABOVE, price=40, asset_type="ETF"
                ),
                {
                    "Amount": 9,
                    "Uic": 12345,
                    "OrderPrice": 10,
                    "OrderType": "Limit",
                    "OrderDuration": {"DurationType": "GoodTillCancel"},
                    "BuySell": "Buy",
                    "Orders": [
                        {
                            "AccountKey": "account",
                            "AssetType": "ETF",
                            "ManualOrder": True,
                            "BuySell": "Sell",
                            "OrderType": "TriggerLimit",
                            "Uic": 1,
                            "OrderDuration": {
                                "DurationType": "GoodTillCancel"
                            },
                            "TriggerOrderData": {
                                "LowerPrice": 40,
                                "PriceType": "LastTraded",
                            },
                        }
                    ],
                },
            ),
        ],
    )
    def test_set_order(
        self,
        stock_code: int,
        price: float,
        quantity: float,
        type: OrderType,
        direction: Direction,
        stop_price: float,
        conditional_order: ConditionalOrder,
        expected: dict,
        mocker,
    ):
        mock_response = mocker.Mock()
        mock_response.status_code = 200
        mock_response.json = lambda: {}
        mock_response.headers = {}
        mocker.patch.object(
            requests.Session, "post", return_value=mock_response
        )
        client = SaxoClient(configuration=MockConfiguration())
        expected.update(
            {
                "AccountKey": "account",
                "AssetType": "Stock",
                "ManualOrder": True,
            }
        )
        order = Order(
            asset_type="Stock",
            code=str(stock_code),
            direction=direction,
            type=type,
            price=price,
            quantity=quantity,
        )
        client.set_order(
            account=Account(key="account", name="account"),
            order=order,
            saxo_uic=stock_code,
            stop_price=stop_price,
            conditional_order=conditional_order,
        )

        requests.Session.post.assert_called_once_with(  # type: ignore
            mocker.ANY, json=expected  # type: ignore
        )

    def test_is_day_open(self, mocker):
        client = SaxoClient(configuration=MockConfiguration())
        mocker.patch.object(
            client,
            "get_historical_data",
            return_value=[{"Time": datetime.datetime(2023, 11, 11, 0, 0, 0)}],
        )
        assert (
            client.is_day_open(
                "DAX.I", "STOCK", datetime.datetime(2023, 11, 11)
            )
            is True
        )
        assert (
            client.is_day_open(
                "DAX.I", "STOCK", datetime.datetime(2023, 11, 12)
            )
            is False
        )
