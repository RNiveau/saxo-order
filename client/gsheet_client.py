import os
import json
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from typing import Dict
from model import Order
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

    def save_order(self, order: Order) -> Dict:
        locale.setlocale(locale.LC_ALL, "fr_FR")
        now = datetime.now().strftime("%d/%m/%Y")
        row = [
            order.name,
            order.code.upper(),
            order.price,
            order.quantity,
            "",
            "",
            0,
            order.stop,
            "",
            order.objective,
            "",
            "",
            "",
            2.5,
            "",
            "",
            now,
            "",
            "",
            "",
            "",
            "",
            "",
            "Achat",
            "",
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
        result = (
            self.client.spreadsheets()
            .values()
            .append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self.sheet_name}!A:A",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": [row]},
            )
            .execute()
        )

        new_row_index = (
            int(result["updates"]["updatedRange"].split(":")[0].split("A")[1]) - 1
        )
        sheet_id = self._get_sheet_id()

        requests = [
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
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 1, "green": 1, "blue": 0}
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor",
                }
            }
        ]
        self.client.spreadsheets().batchUpdate(
            spreadsheetId=self.spreadsheet_id, body={"requests": requests}
        ).execute()
        return result
