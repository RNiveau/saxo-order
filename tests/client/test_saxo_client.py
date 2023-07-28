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
                "aca",
                10,
                9,
                OrderType.LIMIT,
                Direction.BUY,
                None,
                {
                    "Amount": 9,
                    "OrderPrice": 10,
                    "Uic": "aca",
                    "OrderType": "Limit",
                    "BuySell": "Buy",
                },
            ),
            (
                "aca",
                10,
                9,
                OrderType.STOP,
                Direction.BUY,
                100,
                {
                    "Amount": 9,
                    "OrderPrice": 10,
                    "Uic": "aca",
                    "OrderType": "StopIfTraded",
                    "BuySell": "Buy",
                },
            ),
            (
                "aca",
                10,
                9,
                OrderType.STOP,
                Direction.SELL,
                None,
                {
                    "Amount": 9,
                    "OrderPrice": 10,
                    "Uic": "aca",
                    "OrderType": "Stop",
                    "BuySell": "Sell",
                },
            ),
            (
                "aca",
                10,
                9,
                OrderType.STOP_LIMIT,
                Direction.BUY,
                8,
                {
                    "Amount": 9,
                    "OrderPrice": 8,
                    "Uic": "aca",
                    "OrderType": "StopLimit",
                    "BuySell": "Buy",
                    "StopLimitPrice": 10,
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
                "OrderDuration": {"DurationType": "GoodTillCancel"},
                "ManualOrder": True,
            }
        )
        order = Order(
            asset_type="Stock",
            code=stock_code,
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
