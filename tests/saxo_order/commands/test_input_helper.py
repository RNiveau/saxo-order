import pytest

from saxo_order.commands.input_helper import select_account
from model import Account


class TestInputHelper:
    @pytest.mark.parametrize(
        "accounts, called_input, input_str, account_key",
        [
            (
                [
                    {
                        "DisplayName": "Pea",
                        "AccountId": "1/1",
                        "AccountKey": "AccountKey",
                        "ClientKey": "ClientKey",
                    }
                ],
                0,
                None,
                "AccountKey",
            ),
            (
                [
                    {
                        "DisplayName": "Pea",
                        "AccountId": "1/1",
                        "AccountKey": "AccountKey",
                        "ClientKey": "ClientKey",
                    },
                    {
                        "DisplayName": "Peb",
                        "AccountId": "2/2",
                        "AccountKey": "AccountKey2",
                        "ClientKey": "ClientKey",
                    },
                ],
                1,
                "2/2",
                "AccountKey2",
            ),
            (
                [
                    {
                        "DisplayName": "Pea",
                        "AccountId": "1/1",
                        "AccountKey": "AccountKey",
                        "ClientKey": "ClientKey",
                    },
                    {
                        "DisplayName": "Peb",
                        "AccountId": "2/2",
                        "AccountKey": "AccountKey2",
                        "ClientKey": "ClientKey",
                    },
                ],
                1,
                "2",
                "AccountKey2",
            ),
            (
                [
                    {
                        "DisplayName": "Pea",
                        "AccountId": "1/1",
                        "AccountKey": "AccountKey",
                        "ClientKey": "ClientKey",
                    },
                    {
                        "DisplayName": "Peb",
                        "AccountId": "2/2",
                        "AccountKey": "AccountKey2",
                        "ClientKey": "ClientKey",
                    },
                    {
                        "AccountId": "3/3",
                        "AccountKey": "AccountKey3",
                        "ClientKey": "ClientKey",
                    },
                ],
                1,
                "3",
                "AccountKey3",
            ),
        ],
    )
    def test_input_helper(self, accounts, called_input, input_str, account_key, mocker):
        saxo_service = mocker.Mock()
        mocker.patch.object(
            saxo_service,
            "get_accounts",
            return_value={"Data": accounts},
        )
        get_account = mocker.patch.object(
            saxo_service,
            "get_account",
            return_value=Account("AccountKey", "Pea"),
        )
        input_mock = mocker.patch("builtins.input", return_value=input_str)
        select_account(saxo_service)
        get_account.assert_called_once_with(account_key, "ClientKey")
        assert input_mock.call_count == called_input
