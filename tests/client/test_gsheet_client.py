from datetime import datetime

import pytest

from client.gsheet_client import GSheetClient
from model import Account, AssetType, Direction, Order, ReportOrder, Taxes, Underlying


class MockGsheetClient(GSheetClient):
    def __init__(self) -> None:
        self.sheet_name = ""

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
        assert row[12] == "=(L2-C2)/(C2-I2)"
        assert row[15] == 5
        assert row[16] == 10
        assert row[17] == "=E2+O2+P2"
        assert row[26] == "name"
        assert row[27] is None
        assert row[38] == "comment"

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
        assert row[12] == "=(L2-F2)/(F2-I2)"
        assert row[15] == 5
        assert row[16] == 10
        assert row[17] == "=E2+O2+P2"
        assert row[26] == "name"
        assert row[27] is None
        assert row[38] == "comment"

    def test_update_order_open_buy(self):
        client = MockGsheetClient()
        requests = client._generate_open_position_update(
            ReportOrder(
                code="code",
                name="name",
                price=10,
                quantity=11,
                stop=9,
                comment="comment",
                objective=12,
                taxes=Taxes(5, 10),
                date=datetime.strptime("2023/01/10", "%Y/%m/%d"),
                open_position=True,
            ),
            1,
        )
        assert len(requests) == 4
        assert requests[0]["values"][0][0] == 10
        assert requests[0]["values"][0][1] == 11
        assert requests[0]["values"][0][2] == "=C1*D1"
        assert requests[0]["values"][0][3] == ""

        assert requests[1]["values"][0][0] == 5
        assert requests[1]["values"][0][1] == 10
        assert requests[1]["values"][0][2] == "=E1+O1+P1"
        assert requests[1]["values"][0][3] == "10/01/2023"
        assert requests[1]["values"][0][4] == "CASH"

        assert requests[2]["values"][0][0] == 12
        assert requests[2]["values"][0][1] == "=(L1-C1)/(C1-I1)"

        assert requests[3]["values"][0][0] == 9

    def test_update_order_open_buy_without_stop(self):
        client = MockGsheetClient()
        requests = client._generate_open_position_update(
            ReportOrder(
                code="code",
                name="name",
                price=10,
                quantity=11.11,
                comment="comment",
                taxes=Taxes(5, 10),
                date=datetime.strptime("2023/01/10", "%Y/%m/%d"),
                open_position=True,
            ),
            1,
        )
        assert len(requests) == 2
        assert requests[0]["values"][0][0] == 10
        assert requests[0]["values"][0][1] == 11.11
        assert requests[0]["values"][0][2] == "=C1*D1"
        assert requests[0]["values"][0][3] == ""

        assert requests[1]["values"][0][0] == 5
        assert requests[1]["values"][0][1] == 10
        assert requests[1]["values"][0][2] == "=E1+O1+P1"
        assert requests[1]["values"][0][3] == "10/01/2023"
        assert requests[1]["values"][0][4] == "CASH"

    def test_update_order_cdf_open_sell(self):
        client = MockGsheetClient()
        requests = client._generate_open_position_update(
            ReportOrder(
                code="code",
                name="name",
                price=10,
                quantity=11,
                stop=9,
                comment="comment",
                objective=12,
                taxes=Taxes(5, 10),
                date=datetime.strptime("2023/01/10", "%Y/%m/%d"),
                open_position=True,
                direction=Direction.SELL,
                asset_type=AssetType.CFDINDEX,
            ),
            1,
        )
        assert len(requests) == 4
        assert requests[1]["values"][0][4] == "CFD"

    def test_update_order_close_sell(self):
        client = MockGsheetClient()
        requests = client._generate_close_position_update(
            ReportOrder(
                code="code",
                name="name",
                price=10,
                quantity=11,
                stop=9,
                comment="comment",
                objective=12,
                taxes=Taxes(5, 10),
                date=datetime.strptime("2023/01/10", "%Y/%m/%d"),
                open_position=False,
                direction=Direction.SELL,
                stopped=True,
            ),
            1,
        )
        assert len(requests) == 3
        assert requests[0]["values"][0][0] == 1
        assert requests[0]["values"][0][1] == None

        assert requests[1]["values"][0][0] == 10
        assert requests[1]["values"][0][1] == 5
        assert requests[1]["values"][0][2] == "=U1*D1"
        assert requests[1]["values"][0][3] == "=U1*D1-V1"
        assert requests[1]["values"][0][4] == "10/01/2023"

        assert requests[2]["values"][0][0] == "=W1-E1"
        assert requests[2]["values"][0][1] == "=AD1/E1"
        assert requests[2]["values"][0][2] == "=X1-R1"
        assert requests[2]["values"][0][3] == "=AF1/E1"
        assert requests[2]["values"][0][4] == "=Y1-S1"

    def test_update_order_close_buy(self):
        client = MockGsheetClient()
        requests = client._generate_close_position_update(
            ReportOrder(
                code="code",
                name="name",
                price=10,
                quantity=11,
                stop=9,
                comment="comment",
                objective=12,
                taxes=Taxes(5, 10),
                date=datetime.strptime("2023/01/10", "%Y/%m/%d"),
                open_position=False,
                direction=Direction.BUY,
                be_stopped=True,
            ),
            1,
        )
        assert len(requests) == 3
        assert requests[0]["values"][0][0] == None
        assert requests[0]["values"][0][1] == 1

        assert requests[1]["values"][0][0] == 10
        assert requests[1]["values"][0][1] == 5
        assert requests[1]["values"][0][2] == "=U1*D1"
        assert requests[1]["values"][0][3] == "=U1*D1-V1"
        assert requests[1]["values"][0][4] == "10/01/2023"

        assert requests[2]["values"][0][0] == "=E1-W1"
        assert requests[2]["values"][0][1] == "=AD1/E1"
        assert requests[2]["values"][0][2] == "=R1-X1"
        assert requests[2]["values"][0][3] == "=AF1/E1"
        assert requests[2]["values"][0][4] == "=Y1-S1"
