"""
Mock Saxo client for local development without authentication.
"""

import datetime
from typing import Any, Dict, List, Optional

from model import Account


class MockSaxoClient:
    """Mock Saxo client that returns demo data."""

    def __init__(self, *args, **kwargs):
        """Initialize mock client (accepts any args for compatibility)."""
        pass

    def get_accounts(self) -> Dict[str, Any]:
        """Return mock accounts list in Saxo API format."""
        return {
            "Data": [
                {
                    "AccountKey": "MOCK-ACC-001",
                    "AccountId": "LIVE-001",
                    "AccountType": "Normal",
                    "Active": True,
                    "Currency": "USD",
                },
                {
                    "AccountKey": "MOCK-ACC-002",
                    "AccountId": "LIVE-002",
                    "AccountType": "Trading",
                    "Active": True,
                    "Currency": "USD",
                },
            ]
        }

    def get_account(self, account_key: str) -> Account:
        """Return mock account with balance."""
        if account_key == "MOCK-ACC-002":
            return Account(
                key=account_key,
                name="Trading Account",
                fund=250000.00,
                available_fund=185000.00,
            )
        else:
            return Account(
                key=account_key,
                name="Main Account",
                fund=150000.00,
                available_fund=95000.00,
            )

    def get_orders(self, account_key: str) -> List[Dict[str, Any]]:
        """Return mock open orders."""
        if account_key == "MOCK-ACC-002":
            return [
                {
                    "OrderId": "ORDER-002-1",
                    "Symbol": "AAPL:xnas",
                    "BuySell": "Buy",
                    "Amount": 100,
                    "Price": 150.00,
                    "OrderType": "Limit",
                    "Status": "Working",
                },
                {
                    "OrderId": "ORDER-002-2",
                    "Symbol": "GOOGL:xnas",
                    "BuySell": "Buy",
                    "Amount": 50,
                    "Price": 100.00,
                    "OrderType": "Limit",
                    "Status": "Working",
                },
            ]
        else:
            return [
                {
                    "OrderId": "ORDER-001-1",
                    "Symbol": "MSFT:xnas",
                    "BuySell": "Buy",
                    "Amount": 75,
                    "Price": 200.00,
                    "OrderType": "Limit",
                    "Status": "Working",
                },
                {
                    "OrderId": "ORDER-001-2",
                    "Symbol": "TSLA:xnas",
                    "BuySell": "Buy",
                    "Amount": 25,
                    "Price": 180.00,
                    "OrderType": "Limit",
                    "Status": "Working",
                },
            ]

    def get_open_orders(self) -> List[Dict[str, Any]]:
        """Return all open orders (for calculating available funds)."""
        return [
            {
                "OrderId": "ORDER-001-1",
                "AccountKey": "MOCK-ACC-001",
                "Symbol": "MSFT:xnas",
                "BuySell": "Buy",
                "Amount": 75,
                "Price": 200.00,
                "OrderType": "Limit",
                "Status": "Working",
            },
            {
                "OrderId": "ORDER-001-2",
                "AccountKey": "MOCK-ACC-001",
                "Symbol": "TSLA:xnas",
                "BuySell": "Buy",
                "Amount": 25,
                "Price": 180.00,
                "OrderType": "Limit",
                "Status": "Working",
            },
            {
                "OrderId": "ORDER-002-1",
                "AccountKey": "MOCK-ACC-002",
                "Symbol": "AAPL:xnas",
                "BuySell": "Buy",
                "Amount": 100,
                "Price": 150.00,
                "OrderType": "Limit",
                "Status": "Working",
            },
            {
                "OrderId": "ORDER-002-2",
                "AccountKey": "MOCK-ACC-002",
                "Symbol": "GOOGL:xnas",
                "BuySell": "Buy",
                "Amount": 50,
                "Price": 100.00,
                "OrderType": "Limit",
                "Status": "Working",
            },
        ]

    def get_asset(self, code: str, market: Optional[str] = None) -> Dict:
        """Return mock asset data."""
        return {
            "Identifier": 12345,
            "Symbol": f"{code}:{market}" if market else code,
            "AssetType": "Stock",
        }

    def get_historical_data(
        self,
        saxo_uic: str | int,
        asset_type: str,
        horizon: int,
        count: int,
        date: Optional[datetime.datetime] = None,
    ) -> List:
        """Return mock historical data."""
        return []
