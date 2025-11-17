from datetime import datetime
from typing import Dict
from unittest.mock import MagicMock

import pytest
from binance.error import ClientError

from client.binance_client import BinanceClient
from model import Direction, ReportOrder, Taxes
from model.workflow import Candle, UnitTime


class MockBinanceClient(BinanceClient):
    def __init__(self) -> None:
        pass


class TestBinanceClient:
    @pytest.mark.parametrize(
        "trades, expected",
        [
            (
                [
                    {"orderId": 12, "qty": 15, "commission": 10},
                    {"orderId": 1, "qty": 11, "commission": 9},
                ],
                [
                    {"orderId": 12, "qty": 15, "commission": 10},
                    {"orderId": 1, "qty": 11, "commission": 9},
                ],
            ),
            (
                [
                    {"orderId": 12, "qty": 15, "commission": 10},
                    {"orderId": 12, "qty": 11, "commission": 9},
                ],
                [{"orderId": 12, "qty": 26, "commission": 19}],
            ),
            (
                [
                    {"orderId": 12, "qty": 15, "commission": 10},
                    {"orderId": 1, "qty": 111, "commission": 1},
                    {"orderId": 12, "qty": 11, "commission": 9},
                ],
                [
                    {"orderId": 12, "qty": 26, "commission": 19},
                    {"orderId": 1, "qty": 111, "commission": 1},
                ],
            ),
        ],
    )
    def test_merge_trades(self, trades, expected):
        assert expected == MockBinanceClient()._merge_trades(trades)

    @pytest.mark.parametrize(
        "trade, expected",
        [
            (
                {
                    "orderId": 12,
                    "qty": 15,
                    "commission": 10,
                    "commissionAsset": "SOL",
                    "isBuyer": True,
                    "price": 1.1,
                },
                ReportOrder(
                    code="SOL",
                    name="SOL",
                    price=1.1,
                    quantity=5,
                    direction=Direction.BUY,
                    taxes=Taxes(cost=5.5, taxes=0),
                    date=datetime.now(),
                ),
            ),
            (
                {
                    "orderId": 12,
                    "qty": 15.5,
                    "commission": 0.01,
                    "commissionAsset": "SOL",
                    "isBuyer": True,
                    "price": 1.11,
                },
                ReportOrder(
                    code="SOL",
                    name="SOL",
                    price=1.11,
                    quantity=15.49,
                    direction=Direction.BUY,
                    taxes=Taxes(cost=0.00555, taxes=0),
                    date=datetime.now(),
                ),
            ),
            (
                {
                    "orderId": 12,
                    "qty": 15.5,
                    "commission": 0.0123,
                    "commissionAsset": "USDT",
                    "isBuyer": False,
                    "price": 1.11,
                },
                ReportOrder(
                    code="SOL",
                    name="SOL",
                    price=1.11,
                    quantity=15.5,
                    direction=Direction.SELL,
                    taxes=Taxes(cost=0.00615, taxes=0),
                    date=datetime.now(),
                ),
            ),
        ],
    )
    def test_apply_commission(self, trade: Dict, expected: ReportOrder):
        order = ReportOrder(
            code="SOL",
            name="SOL",
            price=trade["price"],
            quantity=trade["qty"],
            date=datetime.now(),
        )
        MockBinanceClient()._apply_commmission(trade, order, 0.5)
        assert order.price == expected.price
        assert order.quantity == expected.quantity
        assert order.taxes is not None
        assert expected.taxes is not None
        assert order.taxes.cost == expected.taxes.cost

    def test_map_kline_to_candle(self):
        client = MockBinanceClient()
        kline = [
            1609459200000,
            "29000.12345678",
            "29500.98765432",
            "28900.11111111",
            "29300.55555555",
            "1234.56789",
            1609545599999,
            "35678901.23456789",
            5000,
            "617.28394",
            "17839450.61728395",
            "0",
        ]

        candle = client._map_kline_to_candle(kline, UnitTime.D)

        assert isinstance(candle, Candle)
        assert candle.open == 29000.1235
        assert candle.higher == 29500.9877
        assert candle.lower == 28900.1111
        assert candle.close == 29300.5556
        assert candle.ut == UnitTime.D
        assert candle.date == datetime.fromtimestamp(1609459200000 / 1000)

    def test_unit_time_to_binance_interval(self):
        """Test that UnitTime enums map correctly to Binance intervals."""
        client = MockBinanceClient()

        assert client._unit_time_to_binance_interval(UnitTime.M15) == "15m"
        assert client._unit_time_to_binance_interval(UnitTime.H1) == "1h"
        assert client._unit_time_to_binance_interval(UnitTime.H4) == "4h"
        assert client._unit_time_to_binance_interval(UnitTime.D) == "1d"
        assert client._unit_time_to_binance_interval(UnitTime.W) == "1w"
        assert client._unit_time_to_binance_interval(UnitTime.M) == "1M"

    def test_get_klines_success(self):
        """Test successful klines fetch from Binance API."""
        mock_api = MagicMock()
        mock_klines = [
            [
                1609459200000,
                "29000.00",
                "29500.00",
                "28900.00",
                "29300.00",
                "1234.56789",
                1609545599999,
                "35678901.23",
                5000,
                "617.28",
                "17839450.62",
                "0",
            ],
            [
                1609545600000,
                "29300.00",
                "29800.00",
                "29200.00",
                "29600.00",
                "2345.67890",
                1609631999999,
                "45678902.34",
                6000,
                "728.39",
                "28394506.17",
                "0",
            ],
        ]
        mock_api.klines.return_value = mock_klines

        client = MockBinanceClient()
        client.client = mock_api
        client.logger = MagicMock()

        result = client._get_klines("BTCUSDT", "1d", 2)

        assert result == mock_klines
        mock_api.klines.assert_called_once_with(
            symbol="BTCUSDT", interval="1d", limit=2
        )

    def test_get_candles_newest_first(self):
        """Test that candles are returned sorted newest first."""
        mock_api = MagicMock()
        mock_klines = [
            [
                1609459200000,
                "100.00",
                "101.00",
                "99.00",
                "100.50",
                "1000",
                1609545599999,
                "100500",
                100,
                "500",
                "50250",
                "0",
            ],
            [
                1609545600000,
                "100.50",
                "102.00",
                "100.00",
                "101.50",
                "2000",
                1609631999999,
                "203000",
                200,
                "1000",
                "101500",
                "0",
            ],
            [
                1609632000000,
                "101.50",
                "103.00",
                "101.00",
                "102.50",
                "3000",
                1609718399999,
                "307500",
                300,
                "1500",
                "153750",
                "0",
            ],
        ]
        mock_api.klines.return_value = mock_klines

        client = MockBinanceClient()
        client.client = mock_api
        client.logger = MagicMock()

        candles = client.get_candles("BTCUSDT", UnitTime.D, limit=3)

        assert len(candles) == 3
        assert candles[0].close == 102.5
        assert candles[1].close == 101.5
        assert candles[2].close == 100.5
        assert candles[0].date > candles[1].date
        assert candles[1].date > candles[2].date

    def test_get_latest_candle(self):
        """Test that get_latest_candle uses 1m interval and limit=1."""
        mock_api = MagicMock()
        mock_kline = [
            [
                1609459200000,
                "50000.00",
                "50100.00",
                "49900.00",
                "50050.00",
                "100",
                1609459259999,
                "5005000",
                50,
                "50",
                "2502500",
                "0",
            ]
        ]
        mock_api.klines.return_value = mock_kline

        client = MockBinanceClient()
        client.client = mock_api
        client.logger = MagicMock()

        candle = client.get_latest_candle("ETHUSDT")

        assert isinstance(candle, Candle)
        assert candle.close == 50050.0
        assert candle.ut == UnitTime.M15
        mock_api.klines.assert_called_once_with(
            symbol="ETHUSDT", interval="1m", limit=1
        )

    def test_get_candles_error_handling(self):
        """Test error handling for invalid symbols and API errors."""
        mock_api = MagicMock()
        mock_api.klines.side_effect = ClientError(
            status_code=400,
            error_code=-1121,
            error_message="Invalid symbol",
            header={},
        )

        client = MockBinanceClient()
        client.client = mock_api
        client.logger = MagicMock()

        with pytest.raises(ClientError):
            client._get_klines("INVALID", "1d", 100)

        client.logger.error.assert_called_once()
