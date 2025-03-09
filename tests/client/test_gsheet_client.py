from datetime import datetime

from client.gsheet_client import GSheetClient
from model import (
    Account,
    AssetType,
    Currency,
    Direction,
    Order,
    ReportOrder,
    Taxes,
    Underlying,
)


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
                currency=Currency.JPY,
            ),
            Order(
                code="code",
                name="name",
                price=1,
                quantity=11,
                stop=0.9,
                comment="comment",
                objective=1.2,
                taxes=Taxes(5, 10),
                currency=Currency.JPY,
            ),
        )
        assert row[0] == "name"
        assert row[1] == "CODE"
        assert row[2] == 10
        assert row[3] == 1
        assert row[4] == 11
        assert row[5] == "=C2*E2"
        assert row[6] == ""
        assert row[9] == 9
        assert row[12] == 12
        assert row[13] == "0.9000 / 1.2000"
        assert row[14] == "=(M2-C2)/(C2-J2)"
        assert row[17] == 5
        assert row[18] == 10
        assert row[19] == "=F2+R2+S2"
        assert row[29] == "name"
        assert row[31] is None
        assert row[41] == "comment"

    def test_underlying_generate_row(self):
        client = MockGsheetClient()
        order = Order(
            code="code",
            name="name",
            price=10,
            quantity=11,
            stop=9,
            comment="comment",
            objective=12,
            taxes=Taxes(5, 10),
            underlying=Underlying(price=1000, stop=999, objective=2000),
        )
        row = client._generate_row(
            Account(key="key", name="name"),
            order,
            order,
        )
        assert row[0] == "name"
        assert row[1] == "CODE"
        assert row[2] == 10
        assert row[3] == ""
        assert row[4] == 11
        assert row[5] == "=C2*E2"
        assert row[6] == 1000
        assert row[9] == 999
        assert row[12] == 2000
        assert row[13] == ""
        assert row[14] == "=(M2-G2)/(G2-J2)"
        assert row[17] == 5
        assert row[18] == 10
        assert row[19] == "=F2+R2+S2"
        assert row[29] == "name"
        assert row[31] is None
        assert row[41] == "comment"

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
                currency=Currency.JPY,
            ),
            ReportOrder(
                code="code",
                name="name",
                price=0.1,
                quantity=11,
                stop=0.9,
                comment="comment",
                objective=1.2,
                taxes=Taxes(5, 10),
                date=datetime.strptime("2023/01/10", "%Y/%m/%d"),
                open_position=True,
                currency=Currency.JPY,
            ),
            1,
        )
        assert len(requests) == 4
        assert requests[0]["values"][0][0] == 10
        assert requests[0]["values"][0][1] == 0.1
        assert requests[0]["values"][0][2] == 11
        assert requests[0]["values"][0][3] == "=C1*E1"
        assert requests[0]["values"][0][4] == ""

        assert requests[1]["values"][0][0] == 5
        assert requests[1]["values"][0][1] == 10
        assert requests[1]["values"][0][2] == "=F1+R1+S1"
        assert requests[1]["values"][0][3] == "10/01/2023"
        assert requests[1]["values"][0][4] == "CASH"

        assert requests[2]["values"][0][0] == 12
        assert requests[2]["values"][0][1] == "0.9000 / 1.2000"
        assert requests[2]["values"][0][2] == "=(M1-C1)/(C1-J1)"

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
                currency=Currency.USD,
            ),
            ReportOrder(
                code="code",
                name="name",
                price=5,
                quantity=11.11,
                comment="comment",
                taxes=Taxes(5, 10),
                date=datetime.strptime("2023/01/10", "%Y/%m/%d"),
                open_position=True,
                currency=Currency.USD,
            ),
            1,
        )
        assert len(requests) == 2
        assert requests[0]["values"][0][0] == 10
        assert requests[0]["values"][0][1] == 5
        assert requests[0]["values"][0][2] == 11.11
        assert requests[0]["values"][0][3] == "=C1*E1"
        assert requests[0]["values"][0][4] == ""

        assert requests[1]["values"][0][0] == 5
        assert requests[1]["values"][0][1] == 10
        assert requests[1]["values"][0][2] == "=F1+R1+S1"
        assert requests[1]["values"][0][3] == "10/01/2023"
        assert requests[1]["values"][0][4] == "CASH"

    def test_update_order_cdf_open_sell(self):
        client = MockGsheetClient()
        order = ReportOrder(
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
        )
        requests = client._generate_open_position_update(
            order,
            order,
            1,
        )
        assert len(requests) == 4
        assert requests[1]["values"][0][4] == "CFD"

    def test_update_order_close_sell(self):
        client = MockGsheetClient()
        order = ReportOrder(
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
        )
        requests = client._generate_close_position_update(
            order,
            order,
            1,
        )
        assert len(requests) == 3
        assert requests[0]["values"][0][0] == 1
        assert requests[0]["values"][0][1] is None

        assert requests[1]["values"][0][0] == 10
        assert requests[1]["values"][0][1] == ""
        assert requests[1]["values"][0][2] == 5
        assert requests[1]["values"][0][3] == "=W1*E1"
        assert requests[1]["values"][0][4] == "=W1*E1-Y1"
        assert requests[1]["values"][0][5] == "10/01/2023"

        assert requests[2]["values"][0][0] == "=Z1-F1"
        assert requests[2]["values"][0][1] == "=AG1/F1"
        assert requests[2]["values"][0][2] == "=AA1-T1"
        assert requests[2]["values"][0][3] == "=AI1/F1"
        assert requests[2]["values"][0][4] == "=AB1-U1"

    def test_update_order_close_buy(self):
        client = MockGsheetClient()
        order = ReportOrder(
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
        )
        requests = client._generate_close_position_update(
            order,
            order,
            1,
        )
        assert len(requests) == 3
        assert requests[0]["values"][0][0] is None
        assert requests[0]["values"][0][1] == 1

        assert requests[1]["values"][0][0] == 10
        assert requests[1]["values"][0][1] == ""
        assert requests[1]["values"][0][2] == 5
        assert requests[1]["values"][0][3] == "=W1*E1"
        assert requests[1]["values"][0][4] == "=W1*E1-Y1"
        assert requests[1]["values"][0][5] == "10/01/2023"

        assert requests[2]["values"][0][0] == "=F1-Z1"
        assert requests[2]["values"][0][1] == "=AG1/F1"
        assert requests[2]["values"][0][2] == "=T1-AA1"
        assert requests[2]["values"][0][3] == "=AI1/F1"
        assert requests[2]["values"][0][4] == "=AB1-U1"
