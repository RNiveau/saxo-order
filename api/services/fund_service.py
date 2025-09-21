from typing import Dict, List, Optional

from client.saxo_client import SaxoClient
from model import Account
from saxo_order.service import get_account_open_orders
from utils.logger import Logger

logger = Logger.get_logger("fund_service")


class FundService:
    def __init__(self, client: SaxoClient):
        self.client = client

    def get_accounts(self) -> List[Dict]:
        """Get all accounts from Saxo."""
        accounts_data = self.client.get_accounts()
        return accounts_data.get("Data", [])

    def get_account_by_id(self, account_id: str) -> Optional[Account]:
        """Get a specific account by ID."""
        accounts = self.get_accounts()
        for acc_data in accounts:
            if acc_data["AccountId"] == account_id:
                # Use get_account method to fetch full account with balance
                return self.client.get_account(acc_data["AccountKey"])
        return None

    def get_default_account(self) -> Optional[Account]:
        """Get the first account as default."""
        accounts = self.get_accounts()
        if accounts:
            # Return the first account as default
            return self.client.get_account(accounts[0]["AccountKey"])
        return None

    def calculate_available_fund(
        self, account_id: Optional[str] = None
    ) -> Dict:
        """
        Calculate available funds using the same logic as the CLI command.
        This is the exact logic from available_funds command.
        """
        # Get account
        if account_id:
            account = self.get_account_by_id(account_id)
            if not account:
                return {"error": f"Account {account_id} not found"}
        else:
            # Use the first account as default
            account = self.get_default_account()
            if not account:
                return {"error": "No accounts found"}

        # Reuse exact logic from CLI available_funds command
        open_orders = self.client.get_open_orders()
        sum_open_order = get_account_open_orders(
            account=account, open_orders=open_orders
        )
        actual_available = account.available_fund - sum_open_order

        return {
            "account_id": account_id if account_id else account.key,
            "account_name": account.name,
            "total_fund": account.fund,
            "available_fund": account.available_fund,
            "open_orders_commitment": sum_open_order,
            "actual_available_fund": actual_available,
        }
