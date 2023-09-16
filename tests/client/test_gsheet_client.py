import pytest

from client.gsheet_client import GSheetClient
from model import Account, Order, OrderType, Direction, Taxes, Underlying


class MockGsheetClient(GSheetClient):
    def __init__(self) -> None:
        pass

    def _get_number_rows(self) -> int:
        return 1


class TestGsheetClient:
    def test_stock_generate_row(self):
        client = MockGsheetClient()
        row = client._generate_row(
            Account(key="key", name="name"),
            Order(
                code="code",
                name="name",
                price=10,
                quantity=11,
                stop=9,
                comment="comment",
                objective=12,
                taxes=Taxes(5, 10),
            ),
        )
        assert row[0] == "name"
        assert row[1] == "CODE"
        assert row[2] == 10
        assert row[3] == 11
        assert row[4] == "=C2*D2"
        assert row[5] == ""
        assert row[8] == 9
        assert row[11] == 12
        assert row[12] == "=(K2-C2)/(C2-I2)"
        assert row[15] == 5
        assert row[16] == 10
        assert row[17] == "=E2+O2+P2"
        assert row[26] == "name"
        assert row[27] is None
        assert row[37] == "comment"

    def test_underlying_generate_row(self):
        client = MockGsheetClient()
        row = client._generate_row(
            Account(key="key", name="name"),
            Order(
                code="code",
                name="name",
                price=10,
                quantity=11,
                stop=9,
                comment="comment",
                objective=12,
                taxes=Taxes(5, 10),
                underlying=Underlying(price=1000, stop=999, objective=2000),
            ),
        )
        assert row[0] == "name"
        assert row[1] == "CODE"
        assert row[2] == 10
        assert row[3] == 11
        assert row[4] == "=C2*D2"
        assert row[5] == 1000
        assert row[8] == 999
        assert row[11] == 2000
        assert row[12] == "=(K2-F2)/(F2-I2)"
        assert row[15] == 5
        assert row[16] == 10
        assert row[17] == "=E2+O2+P2"
        assert row[26] == "name"
        assert row[27] is None
        assert row[37] == "comment"
