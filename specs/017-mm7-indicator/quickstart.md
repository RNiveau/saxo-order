# Quickstart: MM7 Indicator & Workflow

## What This Feature Does

Adds MM7 (7-period moving average) as a workflow trigger indicator, equivalent to the existing MM50. Traders can configure workflows that fire when price touches or approaches the MM7.

## Files to Change

| File | Change |
|------|--------|
| `model/workflow.py` | Add `MA7 = "ma7"` to `IndicatorType` enum |
| `engines/workflows.py` | Add `MA7Workflow` class |
| `engines/workflow_engine.py` | Import `MA7Workflow`; add 3 new `case` branches |
| `tests/engines/test_workflow_engine.py` | Add MM7 test cases mirroring existing MA50 tests |

## Step-by-Step

### 1. Add the enum value

In `model/workflow.py`, inside `class IndicatorType(EnumWithGetValue)`, add after `MA50`:

```python
MA7 = "ma7"
```

### 2. Add the workflow class

In `engines/workflows.py`, add after `MA50Workflow`:

```python
class MA7Workflow(AbstractWorkflow):

    logger = Logger.get_logger("ma7-workflow", logging.DEBUG)

    def init_workflow(
        self, indicator: Indicator, candles: List[Candle]
    ) -> None:
        self.indicator_value = mobile_average(candles, 7)
        super().init_workflow(indicator, candles)

    def below_condition(
        self, candle: Candle, spread: float, element: Optional[float] = None
    ) -> bool:
        if element is None:
            return self._is_within_indicator_range_minus_spread(
                candle.close, spread
            ) or self._is_within_indicator_range_minus_spread(
                candle.higher, spread
            )
        return self._is_within_indicator_range_minus_spread(element, spread)

    def above_condition(
        self, candle: Candle, spread: float, element: Optional[float] = None
    ) -> bool:
        if element is None:
            return self._is_within_indicator_range_plus_spread(
                candle.close, spread
            ) or self._is_within_indicator_range_plus_spread(
                candle.lower, spread
            )
        return self._is_within_indicator_range_plus_spread(element, spread)
```

### 3. Update the workflow engine

In `engines/workflow_engine.py`:

**Import**: Add `MA7Workflow` to the import from `engines.workflows`.

**Main dispatch** (in `run()`, inside the `match workflow.conditions[0].indicator.name` block):
```python
case IndicatorType.MA7:
    results.append(
        (
            workflow,
            self._run_workflow(
                workflow, candles, MA7Workflow()
            ),
        )
    )
```

**Weekly candle count** (in `_get_candles_from_indicator_ut`, weekly `match` block):
```python
case IndicatorType.MA7:
    nbr_weeks = 12
```

**Hourly candle count** (in `_get_candles_from_indicator_ut`, hourly `match` block):
```python
case IndicatorType.MA7:
    nbr_hour = 12 * multiplicator
```

### 4. Configure a workflow (YAML example)

```yaml
- name: buy mm7 h4 cac
  index: CAC40.I
  cfd: FRA40.I
  enable: true
  dry_run: true
  conditions:
    - indicator:
        name: ma7
        ut: h4
      close:
        direction: above
        ut: h1
        spread: 2.0
      element: close
  trigger:
    ut: h1
    signal: breakout
    location: higher
    order_direction: buy
    quantity: 1
```

### 5. Run the tests

```bash
poetry run pytest tests/engines/test_workflow_engine.py -v
poetry run mypy engines/workflows.py engines/workflow_engine.py model/workflow.py
```
