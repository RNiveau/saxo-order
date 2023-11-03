import os
import json
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from typing import Dict, List, Any
from model import Order, ReportOrder, Account, Taxes, Direction
from datetime import datetime
import locale


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
        locale.setlocale(locale.LC_ALL, "fr_FR")
        date = (
            order.date.strftime("%d/%m/%Y")
            if type(order) == ReportOrder
            else datetime.now().strftime("%d/%m/%Y")
        )
        number_rows = self._get_number_rows() + 1
        row = [
            order.name,
            order.code.upper(),
            order.price,
            order.quantity,
            f"=C{number_rows}*D{number_rows}",
        ]
        row.append("" if order.underlying is None else order.underlying.price)
        row += ["", 0]
        row.append(order.stop if order.underlying is None else order.underlying.stop)
        row.append("")
        row.append("")
        row.append(
            order.objective if order.underlying is None else order.underlying.objective
        )
        if order.underlying is None:
            row.append(
                f"=(L{number_rows}-C{number_rows})/(C{number_rows}-I{number_rows})"
            )
        else:
            row.append(
                f"=(L{number_rows}-F{number_rows})/(F{number_rows}-I{number_rows})"
            )
        row += [
            "",
            "",
            order.taxes.cost,
            order.taxes.taxes,
            f"=E{number_rows}+O{number_rows}+P{number_rows}",
            date,
            "CASH",
            "",
            "",
            "",
            "",
            "",
            "Achat",
            f"{account.name}",
            order.strategy,
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

    def update_order(self, account: Account, order: Order, line_to_update: int) -> Any:
        locale.setlocale(locale.LC_ALL, "fr_FR")
        if order.taxes is None:
            order.taxes = Taxes(0, 0)
        if order.direction == Direction.SELL:
            requests = [
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
                    "range": f"{self.sheet_name}!AC{line_to_update}:AG{line_to_update}",
                    "values": [
                        [
                            f"=W{line_to_update}-E{line_to_update}",
                            f"=AC{line_to_update}/E{line_to_update}",
                            f"=X{line_to_update}-R{line_to_update}",
                            f"=AE{line_to_update}/E{line_to_update}",
                            f"=Y{line_to_update}-S{line_to_update}",
                        ]
                    ],
                },
            ]

            # Batch update the specified ranges with new values
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
