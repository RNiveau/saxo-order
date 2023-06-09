import pytest
from typing import List

import saxo_order
from model import Account, Order


class TestValiderOrder:
    @pytest.mark.parametrize(
        "price, stop, objective, expected",
        [(10, 9, 12, True), (10, 9, 10.5, False), (10, 9.9, 11, True)],
    )
    def test_validate_ratio(
        self, price: float, stop: float, objective: float, expected: bool
    ):
        assert (
            saxo_order.validate_ratio(
                Order("", price=price, stop=stop, objective=objective)
            )
            == expected
        )

    @pytest.mark.parametrize(
        "price, quantity, total_amount, expected",
        [(10, 9, 1000, True), (10, 1, 100, False)],
    )
    def test_validate_max_order(
        self, price: float, quantity: int, total_amount: float, expected: bool
    ):
        assert (
            saxo_order.validate_max_order(
                Order("", price=price, quantity=quantity), total_amount
            )
            == expected
        )

    @pytest.mark.parametrize(
        "fund, price, quantity, open_orders, expected",
        [
            (1000, 9, 10, [], True),
            (1000, 10, 110, [], False),
            (
                1000,
                9,
                10,
                [{"AccountKey": "key", "BuySell": "Buy", "Amount": 10, "Price": 10}],
                True,
            ),
            (
                1000,
                9,
                100,
                [],
                True,
            ),
            (
                1000,
                9,
                100,
                [{"AccountKey": "key", "BuySell": "Buy", "Amount": 10, "Price": 10}],
                False,
            ),
            (
                1000,
                9,
                100,
                [{"AccountKey": "key2", "BuySell": "Buy", "Amount": 10, "Price": 10}],
                True,
            ),
            (
                1000,
                9,
                100,
                [
                    {"AccountKey": "key2", "BuySell": "Buy", "Amount": 10, "Price": 10},
                    {"AccountKey": "key", "BuySell": "Sell", "Amount": 10, "Price": 10},
                ],
                True,
            ),
            (
                1000,
                9,
                100,
                [
                    {"AccountKey": "key2", "BuySell": "Buy", "Amount": 10, "Price": 10},
                    {"AccountKey": "key", "BuySell": "Sell", "Amount": 10, "Price": 10},
                    {"AccountKey": "key", "BuySell": "Buy", "Amount": 10, "Price": 10},
                ],
                False,
            ),
        ],
    )
    def test_validate_fund(
        self,
        fund: float,
        price: float,
        quantity: int,
        open_orders: List,
        expected: bool,
    ):
        assert (
            saxo_order.validate_fund(
                Account("key", fund, 0),
                Order("", price=price, quantity=quantity),
                open_orders,
            )
            == expected
        )
