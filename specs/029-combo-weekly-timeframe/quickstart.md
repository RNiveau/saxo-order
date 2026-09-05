# Quickstart: Weekly-Timeframe Combo Detection

**Feature**: 029-combo-weekly-timeframe | **Date**: 2026-08-23

How to run and verify the feature. Read [plan.md](./plan.md) for the design and
[research.md](./research.md) for why each decision was taken.

---

## Prerequisites

```bash
poetry install
```

`secrets.yml` with Saxo credentials, and AWS credentials for the `alerts` table, exactly as the
existing scan requires. Nothing further — no new table, no migration.

**Authenticate against the environment you mean to call.** `config.yml` points at the simulation
endpoints and `prod_config.yml` at production; the tokens on disk (or in S3, when `AWS_PROFILE` is
set) belong to one of them. Running `k-order auth` for one and then a command configured for the
other returns 401 on every asset, through a confusing gateway-401-then-refresh-401 pair rather than
a clear message.

---

## Run the scan against a single asset

The fastest loop. Weekly detection runs inside the existing scan, so there is no separate command.

```bash
poetry run k-order alerting --help
```

Scope a run to one asset by putting a single entry in `followup-stocks.json`, or by calling
`run_detection_for_asset` directly from a REPL with a `saxo_uic`. Look for these lines:

- `do we have a combo weekly at the date ...` — the weekly pass ran
- `not enough candles for a combo N, needed 60` — the asset is ineligible (routine, not an error)
- `Storing N unique alerts` / `No unique alerts to store` — whether the weekly alert was recorded

---

## Verify the acceptance criteria

### A weekly combo is detected (US1, SC-001)

Run the scan against an asset known to form a weekly combo and confirm one `combo_weekly` alert with
a direction, a strength, a price, a four-key `details` map, and `weekly_bar_date` set to the **first
session** of the current ISO week — Monday normally, Tuesday in a Monday-holiday week, since the
forming bar is dated from the earliest daily candle it found (`utils/helper.py:175-186`).

### Daily and weekly coexist (US1 scenario 3)

Find an asset forming both on the same day. Both alerts must be stored; neither suppresses the
other. This is what the separate `AlertType` buys.

### The setup is recorded once but surfaced all week (SC-002, SC-005, FR-013)

Run the scan on five consecutive days against an asset whose weekly combo holds:

- the `alerts` table gains **one** `combo_weekly` row, not five;
- the digest surfaces the asset on **each** of the five days.

Both are correct. The first is the de-dup signature; the second is detection re-running each scan.

### A signal that scored nothing is not reported at all (FR-015, SC-009)

```bash
poetry run pytest tests/services/test_indicator_service.py -k NoCriteriaIsNoCombo
```

Clearing the three structural gates and then meeting none of the scoring criteria means the setup
is absent, not faint — `combo()` returns `None`. A signal meeting one criterion **is** reported,
labelled weak. Both halves matter: the first keeps entries that say nothing out of the reasoning
payload, the second keeps a real observation from being discarded.

### A mid-week direction flip is recorded (FR-007)

Force the forming bar's direction to flip between two runs. A second `combo_weekly` row must appear
for the same `weekly_bar_date`.

### The de-dup change is inert for other alert types (FR-012, SC-007)

```bash
poetry run pytest tests/client/test_aws_client.py -k signature
```

Every alert type other than `combo_weekly` must produce the same signature tuple as before, and an
alert stored before this feature must still de-dupe unchanged. Once before release, also revert the
change locally and re-run the scan on the same assets and date: the stored alert set must match.

### The fallback does not over-promote (SC-008, FR-014)

Submit a payload with the LLM path unavailable for an asset carrying a daily **and** a weekly combo
and nothing else. It must land in the same conviction band as an asset carrying only the daily
combo — one confluence point, not two. If it comes back HIGH, `_PATTERN_FAMILY` is missing the
`COMBO_WEEKLY: COMBO` entry.

### The brief ranks it correctly (US2)

Submit a triage payload for an asset whose only pattern is a **Buy** `combo_weekly` — it must be
eligible for the top conviction band and the rationale must name the weekly timeframe. Repeat with
**Sell**: it must be disqualified as a long, exactly as a Sell daily combo is.

### It is distinguishable at a glance (US3)

Store one `combo_weekly` alert and open the alerts view. It must show:

- the label **Combo Weekly** (from `alertLabels.ts`, not the `titleCase` fallback);
- its Buy/Sell direction, rendered as other directional alerts are;
- a badge colour of its own — cyan, against the daily combo's blue.

The badge colour needs `data-alert-type` on the card element. It was missing before this feature,
which left *every* per-type colour rule in `AssetDetail.css` inert; adding it lights up the other
alert types' colours too, as that stylesheet always intended.

### It is reachable through the API (US3)

```bash
poetry run pytest tests/api/services/test_alerting_service.py -k WeeklyComboFiltering
```

`GET /api/alerts?alert_type=combo_weekly` returns only weekly combos, and `alert_type=combo` does
**not** return them — "combo" is a prefix of "combo_weekly", so a filter written with a substring
match instead of equality would fold the two timeframes together.

### The scan stays inside its budget (US4, SC-003)

Compare a full scan against the same scan with the weekly detection reverted. Provider requests
should grow by exactly one per asset — if they grow by three, the forming week is being fetched separately instead of built from
the daily candles already in hand (see R1).

---

## Calibrate the thresholds (release prerequisite)

```bash
poetry run python scripts/calibrate_weekly_combo.py
```

Fetches weekly history (`horizon=10080`) for the whole scanned universe by default (`--sample N`
narrows it), caches the raw responses locally so re-runs are free, and reports the distribution of `ma50_slope`, `bbh_slope` and
`bbb_slope` over those bars. The chosen values are committed into `COMBO_SETTINGS[UnitTime.W]`.

This costs provider requests, once, outside the scheduled scan. It cannot read the backtest candle
cache: that table holds H1 and 5-minute bars for two index CFDs, not weekly bars for the scanned
equities (R8).

**Do not ship the daily values on weekly.** A slope measured over 10 bars covers ten weeks rather
than ten days, so the daily floor admits nearly everything and the daily flatness ceiling admits
almost nothing.

The run also answers **SC-004** (the share of assets holding ≥60 weekly bars) and reports how many
would actually emit a weekly combo, by strength — the **SC-005** rate, which the slope distributions
alone do not give you.

---

## Quality gates

```bash
poetry run black . && poetry run isort .
poetry run mypy .
poetry run flake8
poetry run pytest
cd frontend && npm run lint && npm run build
```
