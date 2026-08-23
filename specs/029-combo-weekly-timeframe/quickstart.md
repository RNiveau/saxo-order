# Quickstart: Weekly-Timeframe Combo Detection

**Feature**: 029-combo-weekly-timeframe | **Date**: 2026-08-23

How to run, verify and switch off the feature. Read [plan.md](./plan.md) for the design and
[research.md](./research.md) for why each decision was taken.

---

## Prerequisites

```bash
poetry install
```

`secrets.yml` with Saxo credentials, and AWS credentials for the `alerts` table, exactly as the
existing scan requires. Nothing further — no new table, no migration.

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

## Switch it off

```yaml
# config.yml
weekly_combo_enabled: false
```

With this false the scan issues no weekly request, emits no weekly alert, and produces the same
alert set as before the feature. This is the direct check for **SC-007** — run the scan once with
each setting on the same date and the same assets, and diff the stored alerts.

---

## Verify the acceptance criteria

### A weekly combo is detected (US1, SC-001)

Run the scan against an asset known to form a weekly combo and confirm one `combo_weekly` alert with
a direction, a strength, a price, a four-key `details` map, and `weekly_bar_date` set to the Monday
of the current ISO week.

### Daily and weekly coexist (US1 scenario 3)

Find an asset forming both on the same day. Both alerts must be stored; neither suppresses the
other. This is what the separate `AlertType` buys.

### The setup is recorded once but surfaced all week (SC-002, SC-005, FR-014)

Run the scan on five consecutive days against an asset whose weekly combo holds:

- the `alerts` table gains **one** `combo_weekly` row, not five;
- the digest surfaces the asset on **each** of the five days.

Both are correct. The first is the de-dup signature; the second is detection re-running each scan.

### A mid-week direction flip is recorded (FR-007)

Force the forming bar's direction to flip between two runs. A second `combo_weekly` row must appear
for the same `weekly_bar_date`.

### The de-dup change is inert for other alert types (FR-013, SC-007)

```bash
poetry run pytest tests/client/test_aws_client.py -k signature
```

Every alert type other than `combo_weekly` must produce the same signature tuple as before, and an
alert stored before this feature must still de-dupe unchanged.

### The brief ranks it correctly (US2)

Submit a triage payload for an asset whose only pattern is a **Buy** `combo_weekly` — it must be
eligible for the top conviction band and the rationale must name the weekly timeframe. Repeat with
**Sell**: it must be disqualified as a long, exactly as a Sell daily combo is.

### The scan stays inside its budget (US4, SC-003)

Compare a full scan with the toggle on and off. Provider requests should grow by exactly one per
asset — if they grow by three, the forming week is being fetched separately instead of built from
the daily candles already in hand (see R1).

---

## Calibrate the thresholds (release prerequisite)

```bash
poetry run python scripts/calibrate_weekly_combo.py
```

Reports the distribution of `ma50_slope`, `bbh_slope` and `bbb_slope` over weekly bars from the
`backtest_candle_cache` table. The chosen values are committed into `COMBO_SETTINGS[UnitTime.W]`.

**Do not ship the daily values on weekly.** A slope measured over 10 bars covers ten weeks rather
than ten days, so the daily floor admits nearly everything and the daily flatness ceiling admits
almost nothing.

Also measure eligibility while you are here — the share of scanned assets returning ≥60 weekly bars
answers **SC-004** and gates release.

---

## Quality gates

```bash
poetry run black . && poetry run isort .
poetry run mypy .
poetry run flake8
poetry run pytest
cd frontend && npm run lint && npm run build
```
