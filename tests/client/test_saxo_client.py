import pytest
from typing import List

from client.saxo_client import SaxoClient
from tests.utils.configuration import MockConfiguration
from model import Account, Order, OrderType, Direction
import requests


class TestSaxoClient:
    @pytest.mark.parametrize(
        "stock_code, price, quantity, type, direction, stop_price, expected",
        [
            (
                12345,
                10,
                9,
                OrderType.LIMIT,
                Direction.BUY,
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
                {
                    "Amount": 9,
                    "OrderPrice": 10,
                    "Uic": 12345,
                    "OrderType": "StopIfTraded",
                    "OrderDuration": {"DurationType": "GoodTillCancel"},
                    "BuySell": "Buy",
                },
            ),
            (
                12345,
                10,
                9,
                OrderType.STOP,
                Direction.SELL,
                None,
                {
                    "Amount": 9,
                    "OrderPrice": 10,
                    "Uic": 12345,
                    "OrderType": "Stop",
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
                {
                    "Amount": 9,
                    "Uic": 12345,
                    "OrderType": "Market",
                    "OrderDuration": {"DurationType": "DayOrder"},
                    "BuySell": "Buy",
                },
            ),
        ],
    )
    def test_set_order(
        self,
        stock_code: int,
        price: float,
        quantity: int,
        type: OrderType,
        direction: Direction,
        stop_price: float,
        expected: dict,
        mocker,
    ):
        mock_response = mocker.Mock()
        mock_response.status_code = 200
        mock_response.json = lambda: {}
        mocker.patch.object(requests.Session, "post", return_value=mock_response)
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
        )

        requests.Session.post.assert_called_once_with(mocker.ANY, json=expected)
