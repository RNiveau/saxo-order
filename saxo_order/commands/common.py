from slack_sdk import WebClient

from client.gsheet_client import GSheetClient
from saxo_order.service import calculate_currency


def logs_order(configuration, order, account):
    gsheet_client = GSheetClient(
        key_path=configuration.gsheet_creds_path,
        spreadsheet_id=configuration.spreadsheet_id,
    )
    new_order = calculate_currency(order, configuration.currencies_rate)
    result = gsheet_client.create_order(account, new_order, order)
    print(f"Row {result['updates']['updatedRange']} appended.")
    slack_client = WebClient(token=configuration.slack_token)
    slack_client.chat_postMessage(
        channel="#execution-logs",
        text=f"New order created: {new_order.name} "
        f"({new_order.code}) - {new_order.direction} "
        f"{new_order.quantity} at {new_order.price:.4f}$",
    )
