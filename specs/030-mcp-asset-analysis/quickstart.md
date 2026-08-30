# Quickstart: Local MCP Server for Asset Analysis

**Feature**: 030-mcp-asset-analysis

## Prerequisites

```bash
poetry install
```

**Credentials** — both are the ones the CLI already uses; this feature adds no new secret.

| What | Needed for | Without it |
|---|---|---|
| Valid Saxo access token (`secrets.yml` / `access_token`) | Stories 1, 2, 3, 5 | Market-data tools **refuse** rather than answer from simulated data (FR-004a) |
| `AWS_PROFILE` exported | Story 4 (alerts, digest, watchlist, workflow orders) | Stored-context tools report themselves unavailable; market-data tools unaffected |

> `AwsClient.is_aws_context()` (`client/aws_client.py:110`) checks for `AWS_LAMBDA_FUNCTION_NAME` or `AWS_PROFILE`. Locally only the second applies — export it before starting the client, or Story 4's tools cannot reach DynamoDB:
>
> ```bash
> export AWS_PROFILE=your-profile
> ```

## Running

The server is normally launched by the MCP client, not by hand — `.mcp.json` in the repo root registers it, so an MCP client opened in this directory starts it automatically.

To run it directly (for debugging):

```bash
poetry run k-mcp
```

It speaks JSON-RPC on stdin/stdout and blocks. Logs go to **stderr** — stdout is the protocol wire.

## Verifying the install

```bash
poetry run pytest tests/mcp_server -v
poetry run mypy mcp_server
```

Then, from an MCP client in this repo:

1. **Story 1** — "What does Air Liquide look like on the daily?"
   Expect: resolution to a single instrument, then one snapshot with moving averages, Bollinger, ATR, ADX and MACD0lag, and a stated data source.
2. **Story 2** — "Show me the last 20 daily bars."
   Expect: newest-first rows with today's in-progress bar flagged.
3. **Story 3** — "Is anything firing on it?"
   Expect: named setups or an explicit empty result. Then check no alert rows were written.
4. **Story 4** — "Why was it flagged yesterday, and do I hold it?"
   Expect: the stored alert's recorded data plus watchlist labels and open workflow orders.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Every market tool refuses | No valid Saxo token — the server will not serve simulated data by default | Refresh the token, or pass `allow_simulated=true` on a request if you genuinely want mock data |
| Stored-context tools fail, market tools fine | `AWS_PROFILE` not exported | Export it and restart the server |
| Client fails to start the server | Protocol stream corrupted by stdout output | Nothing on the call path may `print()`. `utils/logger.py` is safe (stderr); the three `print()` calls in `client/saxo_client.py` are removed by this feature |
| `Error executing tool <name>` with no detail | An exception escaped without translation | Every tool needs `@tool_boundary` — the SDK masks unhandled exception messages (research.md §2) |
| One indicator missing from a snapshot | It shouldn't be — absence is a bug | Every requested indicator must appear, with `unavailable_reason` when not computable |

## What this does not do

Places no orders. Writes nothing — not alerts, not watchlist entries, not workflows. Runs locally only; it is not deployed to Lambda.
