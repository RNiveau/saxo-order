from datetime import datetime
from unittest.mock import MagicMock

from client.gsheet_client import GSheetClient
from model import (
    Account,
    AssetType,
    Currency,
    Direction,
    Order,
    ReportOrder,
    Taxes,
    TradeRepublicTransaction,
    Underlying,
)


class MockGsheetClient(GSheetClient):
    def __init__(self) -> None:
        self.sheet_name = ""

    def _get_number_rows(self) -> int:
        return 1


class MockEtfDcaGsheetClient(GSheetClient):
    def __init__(self, starting_row_count: int = 5) -> None:
        self.trade_republic_sheet_name = "ETF / DCA"
        self.spreadsheet_id = "spreadsheet-id"
        self.client = MagicMock()
        self._starting_row_count = starting_row_count

    def _get_number_rows_for_sheet(self, sheet_name: str) -> int:
        return self._starting_row_count


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


def _make_transaction(**overrides) -> TradeRepublicTransaction:
    defaults = dict(
        date=datetime.strptime("2026-03-02", "%Y-%m-%d").date(),
        datetime=datetime.strptime("2026-03-02T09:15:00", "%Y-%m-%dT%H:%M:%S"),
        account_type="DEFAULT",
        category="TRADE",
        type="BUY",
        amount=-300.5,
        currency=Currency.EURO,
        transaction_id="tx-1",
        asset_class=AssetType.STOCK,
        name="Apple Inc.",
        symbol="US0378331005",
        shares=2,
        price=150.25,
        fee=-1.0,
    )
    defaults.update(overrides)
    return TradeRepublicTransaction(**defaults)


class TestAppendEtfDcaRows:
    def test_single_batched_append_call(self):
        client = MockEtfDcaGsheetClient(starting_row_count=5)
        transactions = [
            _make_transaction(transaction_id="tx-1"),
            _make_transaction(transaction_id="tx-2"),
        ]

        client.append_etf_dca_rows(transactions)

        client.client.spreadsheets().values().append.assert_called_once()
        call_kwargs = (
            client.client.spreadsheets().values().append.call_args.kwargs
        )
        assert call_kwargs["range"] == "ETF / DCA!A:A"
        assert len(call_kwargs["body"]["values"]) == 2

    def test_row_content_matches_fr013_mapping(self):
        client = MockEtfDcaGsheetClient(starting_row_count=5)
        transactions = [
            _make_transaction(
                transaction_id="tx-1",
                date=datetime.strptime("2026-03-02", "%Y-%m-%d").date(),
                amount=-300.5,
                name="Apple Inc.",
                symbol="US0378331005",
                price=150.25,
                shares=2,
                fee=-1.0,
            ),
            _make_transaction(
                transaction_id="tx-2",
                date=datetime.strptime("2026-03-03", "%Y-%m-%d").date(),
                type="SELL",
                amount=442.0,
                name="iShares Core MSCI World",
                symbol="IE00B4L5Y983",
                price=88.40,
                shares=5,
                fee=-1.0,
            ),
        ]

        client.append_etf_dca_rows(transactions)

        rows = (
            client.client.spreadsheets()
            .values()
            .append.call_args.kwargs["body"]["values"]
        )

        assert rows[0] == [
            "Apple Inc.",
            "US0378331005",
            "02/03/2026",
            "Achat",
            150.25,
            2,
            -1.0,
            "=E6*F6",
            "=H6+G6",
        ]
        assert rows[1] == [
            "iShares Core MSCI World",
            "IE00B4L5Y983",
            "03/03/2026",
            "Vente",
            88.40,
            5,
            -1.0,
            "=E7*F7",
            "=H7+G7",
        ]

    def test_sens_blank_for_non_trade_types(self):
        client = MockEtfDcaGsheetClient(starting_row_count=5)
        transactions = [
            _make_transaction(transaction_id="tx-1", type="DIVIDEND"),
            _make_transaction(transaction_id="tx-2", type="INTEREST_PAYMENT"),
            _make_transaction(transaction_id="tx-3", type="TRANSFER_INBOUND"),
            _make_transaction(transaction_id="tx-4", type="IPO_SUBSCRIPTION"),
        ]

        client.append_etf_dca_rows(transactions)

        rows = (
            client.client.spreadsheets()
            .values()
            .append.call_args.kwargs["body"]["values"]
        )

        assert [row[3] for row in rows] == ["", "", "", ""]
