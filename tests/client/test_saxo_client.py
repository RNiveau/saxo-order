import pytest
from typing import List

from client.saxo_client import SaxoClient
from tests.utils.configuration import MockConfiguration
from model import Account, Order
import requests


class TestSaxoClient:
    @pytest.mark.parametrize(
        "stock_code, price, quantity, order, direction, stop_price, expected",
        [
            (
                "aca",
                10,
                9,
                "limit",
                "buy",
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
                "stop",
                "buy",
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
                "stop",
                "sell",
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
                "other",
                "buy",
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
        order: str,
        direction: str,
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
        client.set_order(
            account_key="account",
            direction=direction,
            order=order,
            price=price,
            quantity=quantity,
            stock_code=stock_code,
            stop_price=stop_price,
        )
        requests.Session.post.assert_called_once_with(mocker.ANY, json=expected)
