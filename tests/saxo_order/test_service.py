import pytest
from typing import List

import saxo_order.service as service
from model import Account, Order, Underlying


class TestValiderOrder:
    @pytest.mark.parametrize(
        "price, stop, objective, expected",
        [(10, 9, 12, True), (10, 9, 10.5, False), (10, 9.9, 11, True)],
    )
    def test_validate_ratio(
        self, price: float, stop: float, objective: float, expected: bool
    ):
        assert (
            service.validate_ratio(
                Order("", price=price, stop=stop, objective=objective)
            )[0]
            == expected
        )

    def test_validate_underlying_ratio(self):
        assert (
            service.validate_ratio(
                Order(
                    "",
                    price=12,
                    underlying=Underlying(price=10, stop=9, objective=12),
                    asset_type="Etf",
                )
            )[0]
            is True
        )

    @pytest.mark.parametrize(
        "price, quantity, total_amount, expected",
        [(10, 9, 1000, True), (10, 1, 100, False)],
    )
    def test_validate_max_order(
        self, price: float, quantity: int, total_amount: float, expected: bool
    ):
        assert (
            service.validate_max_order(
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
            service.validate_fund(
                Account("key", "name", fund, 0),
                Order("", price=price, quantity=quantity),
                open_orders,
            )
            == expected
        )
