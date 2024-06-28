import pytest
from click.testing import CliRunner

import saxo_order.commands.k_order as command


class TestSetOrder:
    @pytest.mark.parametrize(
        "price, code, quantity, order_type, direction, conditional, expected",
        [
            (10, "aca", 100, "limit", "buy", "n", [1, 1, 1, 0, 1, 0]),
            (10, "aca", 100, "limit", "sell", "n", [0, 0, 0, 0, 0, 0]),
            (10, "aca", 100, "market", "buy", "n", [1, 1, 1, 1, 1, 0]),
            (10, "aca", 100, "market", "sell", "n", [0, 0, 0, 1, 0, 0]),
            (10, "aca", 100, "market", "buy", "y", [1, 1, 1, 1, 1, 1]),
        ],
    )
    def test_set_order(
        self,
        price: float,
        code: str,
        quantity: float,
        order_type: str,
        direction: str,
        conditional: str,
        expected: dict,
        mocker,
    ):
        runner = CliRunner()
        saxo_service = mocker.Mock()
        gsheet_service = mocker.Mock()
        mocker.patch(
            "saxo_order.commands.set_order.Configuration",
            return_value=mocker.Mock(),
        )
        mocker.patch(
            "saxo_order.commands.set_order.GSheetClient",
            return_value=gsheet_service,
        )
        mocker.patch(
            "saxo_order.commands.set_order.SaxoClient",
            return_value=saxo_service,
        )
        mocker.patch(
            "saxo_order.commands.set_order.select_account", return_value={}
        )
        validate_buy_order = mocker.patch(
            "saxo_order.commands.set_order.validate_buy_order", return_value={}
        )
        confirm_order = mocker.patch(
            "saxo_order.commands.set_order.confirm_order", return_value={}
        )
        update_order = mocker.patch(
            "saxo_order.commands.set_order.update_order", return_value={}
        )
        get_conditional_order = mocker.patch(
            "saxo_order.commands.set_order.get_conditional_order",
            return_value={},
        )
        mocker.patch.object(
            saxo_service,
            "get_asset",
            return_value={
                "Description": "",
                "AssetType": "Stock",
                "Identifier": 12345,
                "CurrencyCode": "EUR",
            },
        )
        get_price = mocker.patch.object(
            saxo_service, "get_price", return_value=10.2
        )
        create_order = mocker.patch.object(
            gsheet_service,
            "create_order",
            return_value={"updates": {"updatedRange": 1}},
        )
        result = runner.invoke(
            command.k_order,
            [
                "--config",
                "test.yml",
                "set",
                "--code",
                code,
                "--quantity",
                str(quantity),
                "order",
                "--price",
                str(price),
                "--order-type",
                order_type,
                "--direction",
                direction,
                "--conditional",
                conditional,
            ],
        )
        assert result.exit_code == 0
        assert validate_buy_order.call_count == expected[0]
        assert update_order.call_count == expected[1]
        assert create_order.call_count == expected[2]
        assert get_price.call_count == expected[3]
        assert confirm_order.call_count == expected[4]
        assert get_conditional_order.call_count == expected[5]
