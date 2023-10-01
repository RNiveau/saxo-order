import pytest

from client.saxo_client import SaxoClient
from model import OrderType, Direction
import saxo_order.commands.set_order as command
from click.testing import CliRunner


class TestSetOrder:
    @pytest.mark.parametrize(
        "price, code, quantity, order_type, direction, expected",
        [
            (10, "aca", 100, "limit", "buy", [1, 1, 1, 0, 1]),
            (10, "aca", 100, "limit", "sell", [0, 0, 0, 0, 0]),
            (10, "aca", 100, "market", "buy", [1, 1, 1, 1, 1]),
            (10, "aca", 100, "market", "sell", [0, 0, 0, 1, 0]),
        ],
    )
    def test_set_order(
        self,
        price: float,
        code: str,
        quantity: int,
        order_type: OrderType,
        direction: Direction,
        expected: dict,
        mocker,
    ):
        runner = CliRunner()
        saxo_service = mocker.Mock()
        gsheet_service = mocker.Mock()
        mocker.patch(
            "saxo_order.commands.set_order.Configuration", return_value=mocker.Mock()
        )
        mocker.patch(
            "saxo_order.commands.set_order.GSheetClient", return_value=gsheet_service
        )
        mocker.patch(
            "saxo_order.commands.set_order.SaxoClient", return_value=saxo_service
        )
        mocker.patch("saxo_order.commands.set_order.select_account", return_value={})
        validate_buy_order = mocker.patch(
            "saxo_order.commands.set_order.validate_buy_order", return_value={}
        )
        confirm_order = mocker.patch(
            "saxo_order.commands.set_order.confirm_order", return_value={}
        )
        update_order = mocker.patch(
            "saxo_order.commands.set_order.update_order", return_value={}
        )
        mocker.patch.object(
            saxo_service,
            "get_asset",
            return_value={"Description": "", "AssetType": "Stock", "Identifier": 12345},
        )
        get_price = mocker.patch.object(saxo_service, "get_price", return_value=10.2)
        save_order = mocker.patch.object(
            gsheet_service, "save_order", return_value={"updates": {"updatedRange": 1}}
        )
        result = runner.invoke(
            command.set_order,
            [
                "--code",
                code,
                "--quantity",
                quantity,
                "--price",
                price,
                "--order-type",
                order_type,
                "--direction",
                direction,
            ],
        )
        assert result.exit_code == 0
        assert validate_buy_order.call_count == expected[0]
        assert update_order.call_count == expected[1]
        assert save_order.call_count == expected[2]
        assert get_price.call_count == expected[3]
        assert confirm_order.call_count == expected[4]
