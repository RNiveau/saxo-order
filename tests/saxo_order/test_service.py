from typing import List

import pytest

import saxo_order.service as service
from model import Account, Currency, Order, Underlying


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
                    price=1,
                    underlying=Underlying(price=100, stop=99, objective=120),
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
        self, price: float, quantity: float, total_amount: float, expected: bool
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
            (
                100,
                0.5,
                100,
                [
                    {"AccountKey": "key", "BuySell": "Buy", "Amount": 10, "Price": 4},
                ],
                True,
            ),
        ],
    )
    def test_validate_fund(
        self,
        fund: float,
        price: float,
        quantity: float,
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

    def test_get_lost(self):
        assert (
            service.get_lost(10000, Order(code="aca", price=10, stop=9, quantity=10))
            == "Lost: 10 (10.00 %) (0.10 % of funds)"
        )

    def test_get_earn(self):
        assert (
            service.get_earn(
                10000, Order(code="aca", price=10, objective=12, quantity=10)
            )
            == "Earn: 20 (20.00 %) (0.20 % of funds)"
        )

    def test_calculate_currency(self):
        order = service.calculate_currency(Order("", 10), {"usdeur": 0.5})
        assert order.price == 10

        order = service.calculate_currency(
            Order("", 10, currency=Currency.USD), {"usdeur": 0.5}
        )
        assert order.price == 5

        order = service.calculate_currency(
            Order("", 10, stop=5, objective=15, currency=Currency.USD), {"usdeur": 0.5}
        )
        assert order.price == 5
        assert order.stop == 2.5
        assert order.objective == 7.5

        order = Order(
            "",
            10,
            stop=5,
            objective=15,
            underlying=Underlying(100, 50, 150),
            currency=Currency.USD,
        )
        new_order = service.calculate_currency(
            order,
            {"usdeur": 0.5},
        )
        # it's not a bug, I want to call it twice
        new_order = service.calculate_currency(
            order,
            {"usdeur": 0.5},
        )

        assert order.price == 10
        assert order.stop == 5
        assert order.objective == 15
        assert order.underlying.price == 100
        assert order.underlying.stop == 50
        assert order.underlying.objective == 150

        assert new_order.price == 5
        assert new_order.stop == 2.5
        assert new_order.objective == 7.5
        assert new_order.underlying.price == 50
        assert new_order.underlying.stop == 25
        assert new_order.underlying.objective == 75
