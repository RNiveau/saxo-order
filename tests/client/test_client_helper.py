import pytest

from client.client_helper import get_tick_size


class TestClientHelper:

    def test_get_tick_size(self):
        data = {
            "DefaultTickSize": 100.0,
            "Elements": [
                {"HighPrice": 0.0999, "TickSize": 0.0001},
                {"HighPrice": 0.1998, "TickSize": 0.0002},
                {"HighPrice": 0.4995, "TickSize": 0.0005},
                {"HighPrice": 0.999, "TickSize": 0.001},
                {"HighPrice": 1.998, "TickSize": 0.002},
                {"HighPrice": 4.995, "TickSize": 0.005},
                {"HighPrice": 9.99, "TickSize": 0.01},
                {"HighPrice": 19.98, "TickSize": 0.02},
                {"HighPrice": 49.95, "TickSize": 0.05},
                {"HighPrice": 99.9, "TickSize": 0.1},
                {"HighPrice": 199.8, "TickSize": 0.2},
                {"HighPrice": 499.5, "TickSize": 0.5},
                {"HighPrice": 999.0, "TickSize": 1.0},
                {"HighPrice": 1998.0, "TickSize": 2.0},
                {"HighPrice": 4995.0, "TickSize": 5.0},
                {"HighPrice": 9990.0, "TickSize": 10.0},
                {"HighPrice": 19980.0, "TickSize": 20.0},
                {"HighPrice": 49950.0, "TickSize": 50.0},
            ],
        }
        assert 0.0001 == get_tick_size(data, 0.01)
        assert 0.0005 == get_tick_size(data, 0.49)
        assert 0.1 == get_tick_size(data, 90.6)
        assert 0.5 == get_tick_size(data, 207)
