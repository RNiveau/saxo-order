import json
import locale
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from model import (
    Account,
    AssetType,
    Currency,
    Direction,
    Order,
    ReportOrder,
    Taxes,
    helper,
)


class GSheetClient:
    def __init__(self, key_path: str, spreadsheet_id: str) -> None:
        credentials = Credentials.from_service_account_file(
            key_path, scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        self.client = build("sheets", "v4", credentials=credentials)
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = "Liste d’ordre"

    def _get_sheet_id(self):
        spreadsheet = (
            self.client.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
        )
        sheets = spreadsheet.get("sheets", [])
        for sheet in sheets:
            if sheet["properties"]["title"] == self.sheet_name:
                return sheet["properties"]["sheetId"]
        return None

    def _generate_r_v_block(self, order: Order, number_rows: int) -> List:
        taxes = Taxes(0, 0) if order.taxes is None else order.taxes
        locale.setlocale(locale.LC_ALL, "fr_FR")
        date = (
            order.date.strftime("%d/%m/%Y")
            if type(order) == ReportOrder
            else datetime.now().strftime("%d/%m/%Y")
        )
        typ = (
            "CASH"
            if order.asset_type not in [AssetType.CFDINDEX, AssetType.CFDFUTURE]
            else "CFD"
        )
        return [
            taxes.cost,
            taxes.taxes,
            f"=F{number_rows}+Q{number_rows}+R{number_rows}",
            date,
            typ,
        ]

    def _generate_c_g_block(
        self, order: Order, original_order: Order, number_rows: int
    ) -> List:
        original_price = "" if order.currency == Currency.EURO else original_order.price
        return [
            order.price,
            original_price,
            order.quantity,
            f"=C{number_rows}*E{number_rows}",
            "" if order.underlying is None else order.underlying.price,
        ]

    def _generate_j_cell(self, order: Order) -> List[Optional[float]]:
        return [helper.get_stop(order)]

    def _generate_m_o_block(
        self, order: Order, original_order: Order, number_rows: int
    ) -> List:
        block: List[Any] = [helper.get_objective(order)]
        n_cell = ""
        if (
            order.currency != Currency.EURO
            and helper.get_stop(original_order) is not None
        ):
            n_cell = f"{helper.get_stop(original_order):.4f}"
        if (
            order.currency != Currency.EURO
            and helper.get_objective(original_order) is not None
        ):
            n_cell = f"{n_cell} / {helper.get_objective(original_order):.4f}"
        block.append(n_cell)
        if (
            helper.get_objective(order) is not None
            and helper.get_stop(order) is not None
        ):
            if order.underlying is None:
                block.append(
                    f"=(M{number_rows}-C{number_rows})/(C{number_rows}-J{number_rows})"
                )
            else:
                block.append(
                    f"=(M{number_rows}-G{number_rows})/(G{number_rows}-J{number_rows})"
                )
        else:
            block.append(None)
        return block

    def _get_number_rows(self):
        spreadsheet = (
            self.client.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
        )
        sheets = spreadsheet.get("sheets", [])
        for sheet in sheets:
            if sheet["properties"]["title"] == self.sheet_name:
                return sheet["properties"]["gridProperties"]["rowCount"]
        return None

    def _generate_row(
        self, account: Account, order: Order, original_order: Order
    ) -> List:
        if order.taxes is None:
            order.taxes = Taxes(0, 0)
        number_rows = self._get_number_rows() + 1
        row: List[Any] = [
            order.name,
            order.code.upper(),
        ]
        row += self._generate_c_g_block(order, original_order, number_rows)
        row += ["", 0]
        row += self._generate_j_cell(order)
        row.append("")
        row.append("")
        row += self._generate_m_o_block(order, original_order, number_rows)
        row += ["", ""]
        row += self._generate_r_v_block(order, number_rows)
        row += [
            "",
            "",
            "",
            "",
            "",
            "",
            "Achat" if order.direction == Direction.BUY else "Vente",
            f"{account.name}",
            order.strategy,
            order.signal,
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            order.comment,
        ]
        return row

    def update_order(
        self, order: ReportOrder, original_order: ReportOrder, line_to_update: int
    ) -> Any:
        if order.taxes is None:
            order.taxes = Taxes(0, 0)
        if order.open_position is False:
            requests = self._generate_close_position_update(
                order, original_order, line_to_update
            )
        else:
            requests = self._generate_open_position_update(
                order, original_order, line_to_update
            )

        batch_update_request = {
            "valueInputOption": "USER_ENTERED",
            "data": requests,
        }

        result = (
            self.client.spreadsheets()
            .values()
            .batchUpdate(spreadsheetId=self.spreadsheet_id, body=batch_update_request)  # type: ignore
            .execute()
        )
        return result

    def _generate_open_position_update(
        self, order: ReportOrder, original_order: ReportOrder, line_to_update: int
    ) -> List:
        requests = [
            {
                "range": f"{self.sheet_name}!C{line_to_update}:G{line_to_update}",
                "values": [
                    self._generate_c_g_block(order, original_order, line_to_update)
                ],
            },
            {
                "range": f"{self.sheet_name}!R{line_to_update}:V{line_to_update}",
                "values": [self._generate_r_v_block(order, line_to_update)],
            },
        ]
        if order.stop is not None and order.objective is not None:
            requests.append(
                {
                    "range": f"{self.sheet_name}!M{line_to_update}:O{line_to_update}",
                    "values": [
                        self._generate_m_o_block(order, original_order, line_to_update)
                    ],
                }
            )
            requests.append(
                {
                    "range": f"{self.sheet_name}!J{line_to_update}",
                    "values": [self._generate_j_cell(order)],
                }
            )
        return requests

    def _generate_close_position_update(
        self, order: ReportOrder, original_order: ReportOrder, line_to_update: int
    ) -> List:
        original_price = "" if order.currency == Currency.EURO else original_order.price
        return [
            {
                "range": f"{self.sheet_name}!K{line_to_update}:L{line_to_update}",
                "values": [
                    [
                        1 if order.stopped else None,
                        1 if order.be_stopped else None,
                    ]
                ],
            },
            {
                "range": f"{self.sheet_name}!W{line_to_update}:AB{line_to_update}",
                "values": [
                    [
                        order.price,
                        original_price,
                        helper.get_taxes(order).cost,
                        f"=W{line_to_update}*E{line_to_update}",
                        f"=W{line_to_update}*E{line_to_update}-Y{line_to_update}",
                        order.date.strftime("%d/%m/%Y"),
                    ]
                ],
            },
            {
                "range": f"{self.sheet_name}!AG{line_to_update}:AK{line_to_update}",
                "values": [
                    [
                        (
                            f"=Z{line_to_update}-F{line_to_update}"
                            if order.direction == Direction.SELL
                            else f"=F{line_to_update}-Z{line_to_update}"
                        ),
                        f"=AG{line_to_update}/F{line_to_update}",
                        (
                            f"=T{line_to_update}-AA{line_to_update}"
                            if order.direction == Direction.BUY
                            else f"=AA{line_to_update}-T{line_to_update}"
                        ),
                        f"=AI{line_to_update}/F{line_to_update}",
                        f"=AB{line_to_update}-U{line_to_update}",
                    ]
                ],
            },
        ]

    def create_order(
        self, account: Account, order: Order, original_order: Order
    ) -> Any:
        result = (
            self.client.spreadsheets()
            .values()
            .append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self.sheet_name}!A:A",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body={"values": [self._generate_row(account, order, original_order)]},
            )
            .execute()
        )

        new_row_index = (
            int(result["updates"]["updatedRange"].split(":")[0].split("A")[1]) - 1
        )
        sheet_id = self._get_sheet_id()
        background_color = (
            None if type(order) == ReportOrder else {"red": 1, "green": 1, "blue": 0}
        )
        requests: Any = [
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": new_row_index,
                        "endRowIndex": new_row_index + 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": 1,
                    },
                    "cell": {
                        "userEnteredFormat": {"backgroundColor": background_color}
                    },
                    "fields": "userEnteredFormat.backgroundColor",
                }
            }
        ]
        self.client.spreadsheets().batchUpdate(
            spreadsheetId=self.spreadsheet_id, body={"requests": requests}
        ).execute()
        return result
