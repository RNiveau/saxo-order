from datetime import date
from typing import Optional, Tuple
from unittest.mock import MagicMock

import pytest

from client.ouinex_client import OuinexClient
from model.enum import AssetType, Currency, Direction, Exchange
from utils.exception import OuinexException


def make_response(
    status_code: int = 200, json_data: Optional[dict] = None
) -> MagicMock:
    """Build a fake requests.Response with the given status and JSON body."""
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data or {}
    response.text = ""
    if status_code >= 400:
        import requests

        response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            f"{status_code} error"
        )
    else:
        response.raise_for_status.return_value = None
    return response


@pytest.fixture
def client_and_session() -> Tuple[OuinexClient, MagicMock]:
    """OuinexClient with a mocked GraphQL transport session."""
    ouinex = OuinexClient(
        key="api-key",
        secret="secret-key",
        graphql_url="https://live-api.ouinex.com/graphql",
    )
    session = MagicMock()
    ouinex.session = session
    return ouinex, session


SIGN_IN_OK = {
    "data": {
        "service_signin": {
            "jwt": "jwt-token",
            "expires_at": 1848430166000,
        }
    }
}


class TestOuinexClientAuth:
    def test_sign_in_stores_access_token(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.return_value = make_response(200, SIGN_IN_OK)

        client._sign_in()

        assert client._access_token == "jwt-token"
        assert client._token_expiry == 1848430166

    def test_sign_in_sends_service_signin_credentials(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.return_value = make_response(200, SIGN_IN_OK)

        client._sign_in()

        body = session.post.call_args.kwargs["json"]
        assert "service_signin(" in body["query"]
        assert body["variables"] == {"key": "api-key", "secret": "secret-key"}

    def test_parse_expires_at_accepts_seconds(self):
        assert OuinexClient._parse_expires_at(1848430166) == 1848430166

    def test_sign_in_raises_on_missing_token(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.return_value = make_response(
            200, {"data": {"service_signin": {}}}
        )

        with pytest.raises(OuinexException):
            client._sign_in()

    def test_sign_in_raises_on_graphql_error(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.return_value = make_response(
            200, {"errors": [{"message": "bad credentials"}]}
        )

        with pytest.raises(OuinexException):
            client._sign_in()

    def test_ensure_token_signs_in_when_missing(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.return_value = make_response(200, SIGN_IN_OK)

        client._ensure_token()

        assert client._access_token == "jwt-token"
        assert session.post.call_count == 1

    def test_ensure_token_reuses_valid_token(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.return_value = make_response(200, SIGN_IN_OK)
        client._ensure_token()
        session.post.reset_mock()

        client._ensure_token()

        session.post.assert_not_called()


class TestOuinexClientExecute:
    def test_execute_sends_bearer_and_returns_data(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.side_effect = [
            make_response(200, SIGN_IN_OK),
            make_response(200, {"data": {"instruments": []}}),
        ]

        result = client._execute("query { instruments { instrument_id } }")

        assert result == {"instruments": []}
        auth_call = session.post.call_args_list[-1]
        assert (
            auth_call.kwargs["headers"]["Authorization"] == "Bearer jwt-token"
        )

    def test_execute_refreshes_token_on_401(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.side_effect = [
            make_response(200, SIGN_IN_OK),
            make_response(401, {}),
            make_response(200, SIGN_IN_OK),
            make_response(200, {"data": {"ok": True}}),
        ]

        result = client._execute("query { ok }")

        assert result == {"ok": True}

    def test_execute_raises_on_graphql_error(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.side_effect = [
            make_response(200, SIGN_IN_OK),
            make_response(200, {"errors": [{"message": "boom"}]}),
        ]

        with pytest.raises(OuinexException):
            client._execute("query { ok }")


def instrument(instrument_id: str, base: str, quote: str) -> dict:
    return {
        "instrument_id": instrument_id,
        "name": f"{base}/{quote}",
        "base_currency": {"currency_id": base},
        "quote_currency": {"currency_id": quote},
    }


INSTRUMENTS_OK = {
    "data": {
        "instruments": [
            instrument("BTCUSD", "BTC", "USD"),
            instrument("ETHUSD", "ETH", "USD"),
            instrument("BTCUSD_CONV", "BTC", "USD"),
        ]
    }
}


class TestOuinexClientSearch:
    def test_search_returns_crypto_assets(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.return_value = make_response(200, INSTRUMENTS_OK)

        results = client.search("btc")

        assert len(results) == 1
        asset = results[0]
        assert asset.symbol == "BTCUSD"
        assert asset.description == "BTC/USD"
        assert asset.exchange == Exchange.OUINEX
        assert asset.asset_type == AssetType.CRYPTO
        assert asset.identifier is None

    def test_search_matches_quote_currency(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.return_value = make_response(200, INSTRUMENTS_OK)

        results = client.search("usd")

        assert {asset.symbol for asset in results} == {"BTCUSD", "ETHUSD"}
        assert all(asset.exchange == Exchange.OUINEX for asset in results)

    def test_search_does_not_sign_in(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.return_value = make_response(200, INSTRUMENTS_OK)

        client.search("btc")

        assert session.post.call_count == 1
        assert session.post.call_args.kwargs["headers"] == {}
        assert client._access_token is None


def closed_order(
    base: str,
    quote: str,
    side: str,
    price: float,
    quantity: float,
    total: float,
    fee: float,
    fee_currency: str,
    filled_at: str = "2026-09-07T12:09:43.000Z",
    status: str = "completed",
) -> dict:
    return {
        "order_id": f"{base}-{side}",
        "side": side,
        "status": status,
        "price": price,
        "quantity": quantity,
        "total": total,
        "created_at": "1788782983000",
        "updated_at": "1788782983000",
        "trades": [{"created_at_iso": filled_at}],
        "instrument": {
            "base_currency": {"currency_id": base},
            "quote_currency": {"currency_id": quote},
        },
        "fees": [{"currency_id": fee_currency, "amount": fee}],
    }


CLOSED_ORDERS_OK = {
    "data": {
        "closed_orders": [
            closed_order(
                "BTC", "USDC", "buy", 50000, 0.1, 0.099, 0.001, "BTC"
            ),
            closed_order("ETH", "USDC", "sell", 3000, 2, 5998.5, 1.5, "USDC"),
        ]
    }
}


NO_CONVERSIONS: dict = {"data": {"conversions": []}}


def conversion(
    source: str,
    source_amount: float,
    target: str,
    target_amount: float,
    price: float,
    created_at: str = "2026-08-07T09:37:50.000Z",
    status: str = "completed",
) -> dict:
    return {
        "conversion_id": f"{source}-{target}",
        "source_currency_id": source,
        "source_currency_amount": source_amount,
        "target_currency_id": target,
        "target_currency_amount": target_amount,
        "price": price,
        "status": status,
        "created_at_iso": created_at,
    }


class TestOuinexClientReport:
    def test_get_report_all_maps_trades(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.side_effect = [
            make_response(200, SIGN_IN_OK),
            make_response(200, CLOSED_ORDERS_OK),
            make_response(200, NO_CONVERSIONS),
        ]

        orders = client.get_report_all("2023-01-01", usdeur_rate=0.5)

        assert len(orders) == 2
        variables = session.post.call_args_list[1].kwargs["json"]["variables"]
        assert variables["dateRange"]["time_from"] == "2022-10-03T00:00:00Z"
        assert variables["pager"] == {"limit": 200, "offset": 0}

        buy = orders[0]
        assert buy.code == "BTC"
        assert buy.direction == Direction.BUY
        assert buy.asset_type == AssetType.CRYPTO
        assert buy.currency == Currency.USD
        # Buy fee paid in base asset reduces quantity
        assert buy.quantity == pytest.approx(0.099)
        assert buy.taxes is not None
        assert buy.taxes.cost == pytest.approx(0.001 * (50000 * 0.5))

        sell = orders[1]
        assert sell.direction == Direction.SELL
        # Sell fee paid in quote currency -> EUR cost
        assert sell.taxes is not None
        assert sell.taxes.cost == pytest.approx(1.5 * 0.5)

    def test_buy_fee_in_base_asset_reduces_quantity_and_costs_eur(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        # Real example: buy 550 XRP @ 1.1430 USDC, fee 0.5390 XRP.
        # `total` is the net quantity received (550 - 0.539 = 549.461 XRP)
        # and the fee is reported in EUR at the trade price.
        client, session = client_and_session
        xrp_trade = {
            "data": {
                "closed_orders": [
                    closed_order(
                        "XRP",
                        "USDC",
                        "buy",
                        1.1430,
                        550,
                        549.461,
                        0.539,
                        "XRP",
                    )
                ]
            }
        }
        session.post.side_effect = [
            make_response(200, SIGN_IN_OK),
            make_response(200, xrp_trade),
            make_response(200, NO_CONVERSIONS),
        ]

        orders = client.get_report_all("2023-01-01", usdeur_rate=0.9)

        order = orders[0]
        assert order.price == pytest.approx(1.1430)
        assert order.quantity == pytest.approx(549.461)
        assert order.taxes is not None
        assert order.taxes.cost == pytest.approx(0.5390 * 1.1430 * 0.9)

    def test_amount_based_buy_rebuilds_quantity_and_price(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        # Real example: market buy for 115 USDC of BTC. `quantity` is the
        # quote amount spent and `total` the net BTC received.
        client, session = client_and_session
        btc_trade = {
            "data": {
                "closed_orders": [
                    closed_order(
                        "BTC",
                        "USDC",
                        "buy",
                        79492.9,
                        115,
                        0.001445252314,
                        1.417686e-06,
                        "BTC",
                    )
                ]
            }
        }
        session.post.side_effect = [
            make_response(200, SIGN_IN_OK),
            make_response(200, btc_trade),
            make_response(200, NO_CONVERSIONS),
        ]

        order = client.get_report_all("2023-01-01", usdeur_rate=0.9)[0]

        assert order.price == pytest.approx(115 / 0.00144667, rel=1e-6)
        assert order.quantity == pytest.approx(0.001445252314)
        assert order.taxes is not None
        assert order.taxes.cost == pytest.approx(
            1.417686e-06 * order.price * 0.9
        )

    def test_report_uses_fill_date_and_skips_non_completed(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        payload = {
            "data": {
                "closed_orders": [
                    closed_order(
                        "XRP",
                        "USDC",
                        "sell",
                        1.41,
                        225,
                        316.92,
                        0.33,
                        "USDC",
                        filled_at="2026-08-21T09:49:21.000Z",
                    ),
                    closed_order(
                        "ETH",
                        "USDC",
                        "sell",
                        3000,
                        1,
                        2999,
                        1,
                        "USDC",
                        filled_at="2026-07-01T09:00:00.000Z",
                    ),
                    closed_order(
                        "SOL",
                        "USDC",
                        "buy",
                        150,
                        1,
                        0,
                        0,
                        "SOL",
                        status="cancelled",
                    ),
                ]
            }
        }
        session.post.side_effect = [
            make_response(200, SIGN_IN_OK),
            make_response(200, payload),
            make_response(200, NO_CONVERSIONS),
        ]

        orders = client.get_report_all("2026-08-08", usdeur_rate=0.9)

        assert [order.code for order in orders] == ["XRP"]
        assert orders[0].date.date() == date(2026, 8, 21)

    def test_report_paginates_closed_orders(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        full_page = [
            closed_order("BTC", "USDC", "buy", 1, 1, 1, 0, "BTC")
            for _ in range(200)
        ]
        session.post.side_effect = [
            make_response(200, SIGN_IN_OK),
            make_response(200, {"data": {"closed_orders": full_page}}),
            make_response(200, {"data": {"closed_orders": full_page[:1]}}),
            make_response(200, NO_CONVERSIONS),
        ]

        orders = client.get_report_all("2023-01-01", usdeur_rate=0.9)

        assert len(orders) == 201
        offsets = [
            call.kwargs["json"]["variables"]["pager"]["offset"]
            for call in session.post.call_args_list[1:3]
        ]
        assert offsets == [0, 200]

    def test_conversions_are_reported_as_buys_and_sells(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        # Real example: recurring buy of 115 USDC of BTC quoted at 65219.86,
        # 0.00176 BTC received - the spread is the commission.
        client, session = client_and_session
        conversions = {
            "data": {
                "conversions": [
                    conversion("USDC", 115, "BTC", 0.00176, 65219.86),
                    conversion(
                        "XRP",
                        100,
                        "USDC",
                        140.5,
                        1.41,
                        created_at="2026-08-21T09:49:21.000Z",
                    ),
                    conversion("EUR", 1000, "USDC", 1080, 1.08),
                    conversion("BTC", 0.01, "ETH", 0.2, 20),
                    conversion(
                        "USDC", 50, "SOL", 0.3, 150, status="cancelled"
                    ),
                ]
            }
        }
        session.post.side_effect = [
            make_response(200, SIGN_IN_OK),
            make_response(200, {"data": {"closed_orders": []}}),
            make_response(200, conversions),
        ]

        orders = client.get_report_all("2026-06-01", usdeur_rate=0.9)

        assert [(o.code, o.direction) for o in orders] == [
            ("XRP", Direction.SELL),
            ("BTC", Direction.BUY),
        ]
        sell, buy = orders
        assert buy.price == pytest.approx(65219.86)
        assert buy.quantity == pytest.approx(0.00176)
        assert buy.taxes is not None
        assert buy.taxes.cost == pytest.approx(
            (115 / 65219.86 - 0.00176) * 65219.86 * 0.9
        )
        assert sell.quantity == pytest.approx(100)
        assert sell.taxes is not None
        assert sell.taxes.cost == pytest.approx((141 - 140.5) * 0.9)

    def test_report_merges_orders_and_conversions_newest_first(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.side_effect = [
            make_response(200, SIGN_IN_OK),
            make_response(200, CLOSED_ORDERS_OK),
            make_response(
                200,
                {
                    "data": {
                        "conversions": [
                            conversion(
                                "USDC",
                                115,
                                "BTC",
                                0.00182,
                                62944.68,
                                created_at="2026-07-05T13:29:18.000Z",
                            )
                        ]
                    }
                },
            ),
        ]

        orders = client.get_report_all("2026-06-01", usdeur_rate=0.9)

        assert len(orders) == 3
        assert orders[-1].price == pytest.approx(62944.68)
        assert orders[0].date >= orders[1].date >= orders[2].date

    def test_get_report_filters_by_symbol(
        self, client_and_session: Tuple[OuinexClient, MagicMock]
    ):
        client, session = client_and_session
        session.post.side_effect = [
            make_response(200, SIGN_IN_OK),
            make_response(200, CLOSED_ORDERS_OK),
            make_response(200, NO_CONVERSIONS),
        ]

        orders = client.get_report("ETH", "2023-01-01", usdeur_rate=0.5)

        assert len(orders) == 1
        assert orders[0].code == "ETH"
