# Quickstart: Ouinex crypto provider

How to configure, run, and verify the Ouinex provider once implemented. Mirrors the Binance setup.

## 1. Credentials

Add Ouinex API credentials to `secrets.yml` (gitignored):

```yaml
ouinex_api_key: "<your-ouinex-api-key>"
ouinex_secret_key: "<your-ouinex-secret>"
```

Optionally override the GraphQL endpoint in `config.yml` (defaults to `https://live-api.ouinex.com/graphql`):

```yaml
ouinex_graphql_url: "https://live-api.ouinex.com/graphql"
```

## 2. Run backend + frontend

```bash
poetry run python run_api.py        # API on :8000
cd frontend && npm run dev          # Vite on :5173
```

## 3. Verify each user story

**US1 — provider recognized**
```bash
curl "http://localhost:8000/api/fund/accounts" | grep ouinex_main
```
Expect an `ouinex_main` account alongside `binance_main`.

**US2 — search & watchlist**
```bash
curl "http://localhost:8000/api/search?keyword=btc" | jq '.results[] | select(.exchange=="ouinex")'
```
Expect at least one Ouinex crypto result. Add it via the Watchlist UI and confirm it is tagged crypto (USD price), like a Binance item.

**US3 — indicators**
```bash
curl "http://localhost:8000/api/indicator/asset/BTCUSD?exchange=ouinex&unit_time=daily" | jq '.moving_averages, .current_price'
```
Expect MAs (7/20/50/200) and a current price. (Weekly/monthly: see research VERIFY item.)
Note: crypto **alerts** are not produced — parity with Binance, which has no crypto alert detection today.

**US4 — report as binance**
```bash
curl "http://localhost:8000/api/report/orders?account_id=ouinex_main&from_date=2026-07-01" | jq '.orders | length'
```
Then, in the Report UI, pick the **Ouinex** account, write a trade to the journal, and open the Google Sheet:
- The provider column shows the **same value as Binance rows** ("Coinbase"). The row is indistinguishable from a native Binance entry (SC-002).

## 4. Failure isolation check (FR-012 / SC-005)

Temporarily set an invalid `ouinex_api_key`, then:
```bash
curl "http://localhost:8000/api/search?keyword=btc" | jq '.results[] | select(.exchange=="saxo" or .exchange=="binance") | .symbol' | head
```
Expect Saxo/Binance results still returned; only Ouinex results are absent, with an Ouinex-specific error logged.

## 5. Quality gates

```bash
poetry run black . && poetry run isort . && poetry run mypy . && poetry run flake8
poetry run pytest tests/client/test_ouinex_client.py tests/api/services/test_ouinex_report_service.py
cd frontend && npm run build
```
