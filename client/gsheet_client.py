import json
import locale
import os
from datetime import datetime
from typing import Any, Dict, List

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from model import Account, AssetType, Direction, Order, ReportOrder, Taxes, helper


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

    def _generate_p_t_block(self, order: Order, number_rows: int) -> List:
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
            order.taxes.cost,
            order.taxes.taxes,
            f"=E{number_rows}+O{number_rows}+P{number_rows}",
            date,
            typ,
        ]

    def _generate_c_f_block(self, order: Order, number_rows: int) -> List:
        return [
            order.price,
            order.quantity,
            f"=C{number_rows}*D{number_rows}",
            "" if order.underlying is None else order.underlying.price,
        ]

    def _generate_i_column(self, order: Order) -> List[float]:
        return [helper.get_stop(order)]

    def _generate_l_m_block(self, order: Order, number_rows: int) -> List[float]:
        block = [helper.get_objective(order)]
        if (
            helper.get_objective(order) is not None
            and helper.get_stop(order) is not None
        ):
            if order.underlying is None:
                block.append(
                    f"=(L{number_rows}-C{number_rows})/(C{number_rows}-I{number_rows})"
                )
            else:
                block.append(
                    f"=(L{number_rows}-F{number_rows})/(F{number_rows}-I{number_rows})"
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

    def _generate_row(self, account: Account, order: Order) -> List:
        if order.taxes is None:
            order.taxes = Taxes(0, 0)
        number_rows = self._get_number_rows() + 1
        row = [
            order.name,
            order.code.upper(),
        ]
        row += self._generate_c_f_block(order, number_rows)
        row += ["", 0]
        row += self._generate_i_column(order)
        row.append("")
        row.append("")
        row += self._generate_l_m_block(order, number_rows)
        row += ["", ""]
        row += self._generate_p_t_block(order, number_rows)
        row += [
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

    def update_order(self, order: ReportOrder, line_to_update: int) -> Any:
        if order.taxes is None:
            order.taxes = Taxes(0, 0)
        if order.open_position is False:
            requests = self._generate_close_position_update(order, line_to_update)
        else:
            requests = self._generate_open_position_update(order, line_to_update)

        batch_update_request = {
            "valueInputOption": "USER_ENTERED",
            "data": requests,
        }

        result = (
            self.client.spreadsheets()
            .values()
            .batchUpdate(spreadsheetId=self.spreadsheet_id, body=batch_update_request)
            .execute()
        )
        return result

    def _generate_open_position_update(self, order: ReportOrder, line_to_update: int):
        requests = [
            {
                "range": f"{self.sheet_name}!C{line_to_update}:F{line_to_update}",
                "values": [self._generate_c_f_block(order, line_to_update)],
            },
            {
                "range": f"{self.sheet_name}!P{line_to_update}:T{line_to_update}",
                "values": [self._generate_p_t_block(order, line_to_update)],
            },
        ]
        if order.stop is not None and order.objective is not None:
            requests.append(
                {
                    "range": f"{self.sheet_name}!L{line_to_update}:M{line_to_update}",
                    "values": [self._generate_l_m_block(order, line_to_update)],
                }
            )
            requests.append(
                {
                    "range": f"{self.sheet_name}!I{line_to_update}",
                    "values": [self._generate_i_column(order)],
                }
            )
        return requests

    def _generate_close_position_update(self, order, line_to_update):
        return [
            {
                "range": f"{self.sheet_name}!J{line_to_update}:K{line_to_update}",
                "values": [
                    [
                        1 if order.stopped else None,
                        1 if order.be_stopped else None,
                    ]
                ],
            },
            {
                "range": f"{self.sheet_name}!U{line_to_update}:Y{line_to_update}",
                "values": [
                    [
                        order.price,
                        order.taxes.cost,
                        f"=U{line_to_update}*D{line_to_update}",
                        f"=U{line_to_update}*D{line_to_update}-V{line_to_update}",
                        order.date.strftime("%d/%m/%Y"),
                    ]
                ],
            },
            {
                "range": f"{self.sheet_name}!AD{line_to_update}:AH{line_to_update}",
                "values": [
                    [
                        f"=W{line_to_update}-E{line_to_update}"
                        if order.direction == Direction.SELL
                        else f"=E{line_to_update}-W{line_to_update}",
                        f"=AD{line_to_update}/E{line_to_update}",
                        f"=R{line_to_update}-X{line_to_update}"
                        if order.direction == Direction.BUY
                        else f"=X{line_to_update}-R{line_to_update}",
                        f"=AF{line_to_update}/E{line_to_update}",
                        f"=Y{line_to_update}-S{line_to_update}",
                    ]
                ],
            },
        ]

    def create_order(self, account: Account, order: Order) -> Any:
        result = (
            self.client.spreadsheets()
            .values()
            .append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self.sheet_name}!A:A",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body={"values": [self._generate_row(account, order)]},
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
