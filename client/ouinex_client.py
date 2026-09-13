import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

from model import Currency, Direction, ReportOrder, Taxes
from model.asset import Asset
from model.enum import AssetType, Exchange
from model.workflow import Candle, UnitTime
from utils.exception import OuinexException
from utils.logger import Logger

SIGN_IN_MUTATION = """
mutation ServiceSignIn($key: String!, $secret: String!) {
  service_signin(service_api_key: $key, service_api_secret: $secret) {
    jwt
    expires_at
  }
}
"""

INSTRUMENTS_QUERY = """
query Instruments {
  instruments {
    instrument_id
    name
    base_currency {
      currency_id
    }
    quote_currency {
      currency_id
    }
  }
}
"""

CLOSED_ORDERS_QUERY = """
query ClosedOrders($dateRange: DateRangeInput, $pager: PagerInput) {
  closed_orders(wallet_id: "", dateRange: $dateRange, pager: $pager) {
    order_id
    side
    status
    price
    quantity
    total
    created_at
    updated_at
    trades {
      created_at_iso
    }
    instrument {
      base_currency {
        currency_id
      }
      quote_currency {
        currency_id
      }
    }
    fees {
      currency_id
      amount
    }
  }
}
"""

CLOSED_ORDERS_PAGE_SIZE = 200
ORDER_STATUS_COMPLETED = "completed"
# `dateRange` filters on the order placement time; a limit order can be filled
# long after it was placed, so the query window is widened backwards and the
# result is filtered on the fill date instead.
CLOSED_ORDERS_LOOKBACK_DAYS = 90

# UNVERIFIED (research R1): the Ouinex landing docs only expose OHLC via the
# `instrument_price_bar` WebSocket subscription; a historical-bars *query* is
# assumed here (Option A) so indicators can backfill. Field/query names stay
# isolated in the candle helpers for easy correction once the schema is known.
PRICE_BARS_QUERY = """
query PriceBars($instrumentId: String!, $periodicity: String!, $limit: Int!) {
  priceBars(
    instrument_id: $instrumentId
    periodicity: $periodicity
    limit: $limit
  ) {
    open
    high
    low
    close
    timestamp
  }
}
"""

CONVERSION_SUFFIX = "_CONV"


class OuinexClient:
    """
    GraphQL + JWT client for the Ouinex crypto provider.

    Exposes the same public method surface the app already relies on for
    Binance (search / get_candles / get_report*), added incrementally by the
    user stories. This foundational layer provides the GraphQL transport and
    the JWT sign-in / refresh lifecycle every operation depends on.
    """

    TOKEN_REFRESH_MARGIN = 30

    # Native Ouinex periodicities (research: 1m/5m/15m/1h/4h/1d, no 1w/1M).
    NATIVE_PERIODICITY = {
        UnitTime.M5: "5m",
        UnitTime.M15: "15m",
        UnitTime.H1: "1h",
        UnitTime.H4: "4h",
        UnitTime.D: "1d",
    }
    # Weekly/monthly are aggregated from daily bars (research R2): how many
    # daily bars to request per target period.
    DAILY_PER_PERIOD = {UnitTime.W: 7, UnitTime.M: 32}

    def __init__(self, key: str, secret: str, graphql_url: str) -> None:
        self.logger = Logger.get_logger("ouinex_client", logging.INFO)
        self.key = key
        self.secret = secret
        self.graphql_url = graphql_url
        self.session = requests.Session()
        self._access_token: Optional[str] = None
        self._token_expiry: float = 0.0

    def _sign_in(self) -> None:
        response = self.session.post(
            self.graphql_url,
            json={
                "query": SIGN_IN_MUTATION,
                "variables": {"key": self.key, "secret": self.secret},
            },
            timeout=10,
        )
        try:
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise OuinexException(
                f"Ouinex sign-in request failed: {e} - {response.text}"
            )

        payload = response.json()
        if payload.get("errors"):
            raise OuinexException(f"Ouinex sign-in error: {payload['errors']}")

        data = (payload.get("data") or {}).get("service_signin")
        if not data or not data.get("jwt"):
            raise OuinexException("Ouinex sign-in returned no access token")

        self._access_token = data["jwt"]
        self._token_expiry = self._parse_expires_at(data.get("expires_at"))

    @staticmethod
    def _parse_expires_at(value: Any) -> float:
        """Ouinex returns an epoch timestamp, in seconds or milliseconds."""
        expires_at = float(value or 0)
        return expires_at / 1000 if expires_at >= 1e12 else expires_at

    def _ensure_token(self) -> None:
        if (
            self._access_token is None
            or time.time() >= self._token_expiry - self.TOKEN_REFRESH_MARGIN
        ):
            self._sign_in()

    def _execute(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        authenticated: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute a GraphQL query/mutation against the Ouinex endpoint.

        Authenticated operations sign in first and refresh the token once on an
        authentication failure. Public operations (`authenticated=False`, e.g.
        `instruments`) are sent without a bearer token and never sign in, but a
        401 still triggers one signed retry.
        """
        if authenticated:
            self._ensure_token()

        def _post() -> requests.Response:
            headers = (
                {"Authorization": f"Bearer {self._access_token}"}
                if self._access_token
                else {}
            )
            return self.session.post(
                self.graphql_url,
                json={"query": query, "variables": variables or {}},
                headers=headers,
                timeout=10,
            )

        response = _post()
        if response.status_code == 401:
            self._sign_in()
            response = _post()

        try:
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise OuinexException(
                f"Ouinex request failed: {e} - {response.text}"
            )

        payload = response.json()
        if payload.get("errors"):
            raise OuinexException(f"Ouinex GraphQL error: {payload['errors']}")

        return payload.get("data") or {}

    @staticmethod
    def _currencies(instrument: Dict[str, Any]) -> tuple:
        base = (instrument.get("base_currency") or {}).get("currency_id", "")
        quote = (instrument.get("quote_currency") or {}).get("currency_id", "")
        return base, quote

    def _map_instrument_to_asset(self, instrument: Dict[str, Any]) -> Asset:
        base, quote = self._currencies(instrument)
        symbol = instrument.get("instrument_id") or f"{base}{quote}"
        return Asset(
            symbol=symbol,
            description=instrument.get("name") or f"{base}/{quote}",
            asset_type=AssetType.CRYPTO,
            exchange=Exchange.OUINEX,
            identifier=None,
        )

    def search(self, keyword: str) -> List[Asset]:
        """
        Search Ouinex instruments by keyword.

        Fetches the instrument list via the public `instruments` GraphQL query
        and filters client-side against the symbol and base/quote currencies,
        mirroring the Binance search behavior. Conversion pairs (`*_CONV`) are
        excluded — they are not tradable instruments.

        Args:
            keyword: Search keyword to match against symbol or currencies

        Returns:
            List of Asset objects tagged Exchange.OUINEX / AssetType.CRYPTO
        """
        data = self._execute(INSTRUMENTS_QUERY, authenticated=False)
        keyword_lower = keyword.lower()

        results = []
        for instrument in data.get("instruments", []):
            base, quote = self._currencies(instrument)
            symbol = instrument.get("instrument_id") or f"{base}{quote}"

            if symbol.endswith(CONVERSION_SUFFIX):
                continue

            if (
                keyword_lower in symbol.lower()
                or keyword_lower in base.lower()
                or keyword_lower in quote.lower()
            ):
                results.append(self._map_instrument_to_asset(instrument))

        return results

    def _parse_timestamp(self, value: Any) -> datetime:
        if isinstance(value, str) and value.isdigit():
            value = int(value)
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value / 1000)
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone().replace(tzinfo=None)

    def _map_bar_to_candle(
        self, bar: Dict[str, Any], unit_time: UnitTime
    ) -> Candle:
        return Candle(
            open=round(float(bar["open"]), 4),
            higher=round(float(bar["high"]), 4),
            lower=round(float(bar["low"]), 4),
            close=round(float(bar["close"]), 4),
            ut=unit_time,
            date=self._parse_timestamp(bar["timestamp"]),
        )

    def _fetch_price_bars(
        self, symbol: str, periodicity: str, limit: int, unit_time: UnitTime
    ) -> List[Candle]:
        """Fetch bars at a native periodicity, newest-first (0=latest)."""
        data = self._execute(
            PRICE_BARS_QUERY,
            {
                "instrumentId": symbol,
                "periodicity": periodicity,
                "limit": limit,
            },
        )
        candles = [
            self._map_bar_to_candle(bar, unit_time)
            for bar in data.get("priceBars", [])
        ]
        candles.sort(
            key=lambda candle: candle.date or datetime.min, reverse=True
        )
        return candles

    def _aggregate_candles(
        self, daily: List[Candle], unit_time: UnitTime
    ) -> List[Candle]:
        """
        Aggregate daily candles (newest-first) into weekly/monthly candles.

        Used because Ouinex exposes no native 1w/1M periodicity (research R2).
        """

        def period_key(moment: datetime) -> tuple:
            if unit_time == UnitTime.W:
                return moment.isocalendar()[:2]
            return (moment.year, moment.month)

        dated: List[Tuple[datetime, Candle]] = []
        for candle in daily:
            if candle.date is not None:
                dated.append((candle.date, candle))

        aggregated: List[Candle] = []
        last_key: Optional[tuple] = None
        # Oldest-first so each group's open/close land chronologically.
        for moment, candle in sorted(dated, key=lambda pair: pair[0]):
            current_key = period_key(moment)
            if aggregated and current_key == last_key:
                current = aggregated[-1]
                current.higher = max(current.higher, candle.higher)
                current.lower = min(current.lower, candle.lower)
                current.close = candle.close
                current.date = moment
            else:
                aggregated.append(
                    Candle(
                        open=candle.open,
                        higher=candle.higher,
                        lower=candle.lower,
                        close=candle.close,
                        ut=unit_time,
                        date=moment,
                    )
                )
                last_key = current_key
        aggregated.reverse()
        return aggregated

    def get_candles(
        self, symbol: str, unit_time: UnitTime, limit: int = 200
    ) -> List[Candle]:
        """
        Get historical candles for a Ouinex instrument, newest-first.

        Native periodicities (15m/1h/4h/1d) are fetched directly; weekly and
        monthly are aggregated from daily bars (research R2).

        Args:
            symbol: Ouinex instrument id (e.g. "BTCUSD")
            unit_time: Time unit (D, W, M, H1, H4, M15)
            limit: Number of candles to return (default 200)

        Returns:
            List of Candle objects, sorted newest first (index 0 = latest)
        """
        if unit_time in self.NATIVE_PERIODICITY:
            return self._fetch_price_bars(
                symbol, self.NATIVE_PERIODICITY[unit_time], limit, unit_time
            )

        if unit_time in self.DAILY_PER_PERIOD:
            daily = self._fetch_price_bars(
                symbol,
                self.NATIVE_PERIODICITY[UnitTime.D],
                limit * self.DAILY_PER_PERIOD[unit_time],
                UnitTime.D,
            )
            return self._aggregate_candles(daily, unit_time)[:limit]

        raise OuinexException(
            f"Unsupported unit_time for Ouinex candles: {unit_time.value}"
        )

    def get_latest_candle(self, symbol: str) -> Candle:
        """
        Get the most recent fine-grained candle for the current price.

        Args:
            symbol: Ouinex instrument id (e.g. "BTCUSD")

        Returns:
            Latest 1-minute Candle
        """
        candles = self._fetch_price_bars(symbol, "1m", 1, UnitTime.M15)
        if not candles:
            raise OuinexException(f"No price bar returned for {symbol}")
        return candles[0]

    def _apply_commission(
        self,
        fee: float,
        fee_currency: str,
        order: ReportOrder,
        usdeur_rate: float,
    ) -> None:
        if fee <= 0:
            order.taxes = Taxes(cost=0, taxes=0)
            return

        if fee_currency == order.name:
            # Fee charged in the base asset (e.g. 0.539 XRP on an XRP buy):
            # it reduces the quantity actually received and is valued in EUR
            # at the trade price.
            if order.direction == Direction.BUY:
                order.quantity -= fee
            order.taxes = Taxes(cost=fee * order.price * usdeur_rate, taxes=0)
        else:
            # Fee charged in the quote/cash currency: already a cash amount.
            order.taxes = Taxes(cost=fee * usdeur_rate, taxes=0)

    def _map_closed_order_to_report(
        self, closed_order: Dict[str, Any], usdeur_rate: float
    ) -> ReportOrder:
        """
        Map an Ouinex closed order to a ReportOrder.

        `total` is the net amount received (base on a buy, quote on a sell)
        with the fee already deducted. On a buy, `quantity` is either the base
        quantity or, for amount-based market orders, the quote amount spent;
        the gross base quantity is therefore rebuilt from `total` and the fee.
        The order date is the fill time (`created_at` is the placement time).
        """
        base, quote = self._currencies(closed_order.get("instrument") or {})
        side = (closed_order.get("side") or "").lower()
        direction = Direction.BUY if side == "buy" else Direction.SELL
        fees = closed_order.get("fees") or []
        fee = sum(float(f.get("amount") or 0) for f in fees)
        fee_currency = fees[0].get("currency_id", "") if fees else ""
        quantity = float(closed_order["quantity"])
        price = float(closed_order["price"])
        total = float(closed_order.get("total") or 0)

        if direction == Direction.BUY and total > 0:
            gross_base = total + (fee if fee_currency == base else 0)
            if abs(quantity - gross_base) > gross_base * 0.01:
                quote_spent = quantity
            else:
                quote_spent = quantity * price
            quantity = gross_base
            price = quote_spent / gross_base

        order = ReportOrder(
            code=base,
            name=base,
            price=price,
            quantity=quantity,
            direction=direction,
            asset_type=AssetType.CRYPTO,
            date=self._fill_date(closed_order),
            currency=Currency.USD,
        )
        self._apply_commission(fee, fee_currency, order, usdeur_rate)
        return order

    def _fill_date(self, closed_order: Dict[str, Any]) -> datetime:
        trades = closed_order.get("trades") or []
        fills = [
            t["created_at_iso"] for t in trades if t.get("created_at_iso")
        ]
        if fills:
            return self._parse_timestamp(max(fills))
        return self._parse_timestamp(
            closed_order.get("updated_at") or closed_order["created_at"]
        )

    def _fetch_closed_orders(self, date: str) -> List[Dict[str, Any]]:
        time_from = (
            datetime.fromisoformat(date)
            - timedelta(days=CLOSED_ORDERS_LOOKBACK_DAYS)
        ).strftime("%Y-%m-%dT00:00:00Z")
        time_to = (datetime.now(timezone.utc) + timedelta(days=1)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        closed_orders: List[Dict[str, Any]] = []
        offset = 0
        while True:
            data = self._execute(
                CLOSED_ORDERS_QUERY,
                {
                    "dateRange": {"time_from": time_from, "time_to": time_to},
                    "pager": {
                        "limit": CLOSED_ORDERS_PAGE_SIZE,
                        "offset": offset,
                    },
                },
            )
            page = data.get("closed_orders") or []
            closed_orders.extend(page)
            if len(page) < CLOSED_ORDERS_PAGE_SIZE:
                return closed_orders
            offset += CLOSED_ORDERS_PAGE_SIZE

    def get_report_all(
        self, date: str, usdeur_rate: float
    ) -> List[ReportOrder]:
        """
        Get all completed Ouinex orders since `date`, mapped to ReportOrder.

        Args:
            date: Start date in YYYY-MM-DD format
            usdeur_rate: USD→EUR rate used for commission conversion

        Returns:
            List of ReportOrder objects (asset_type=CRYPTO, currency=USD)
        """
        from_date = datetime.fromisoformat(date)
        orders = [
            self._map_closed_order_to_report(closed_order, usdeur_rate)
            for closed_order in self._fetch_closed_orders(date)
            if closed_order.get("status") == ORDER_STATUS_COMPLETED
        ]
        return [order for order in orders if order.date >= from_date]

    def get_report(
        self, symbol: str, date: str, usdeur_rate: float
    ) -> List[ReportOrder]:
        """
        Get closed Ouinex orders for a single symbol since `date`.

        Args:
            symbol: Base currency code to filter on (e.g. "BTC")
            date: Start date in YYYY-MM-DD format
            usdeur_rate: USD→EUR rate used for commission conversion

        Returns:
            List of ReportOrder objects for the given symbol
        """
        return [
            order
            for order in self.get_report_all(date, usdeur_rate)
            if order.code == symbol
        ]
