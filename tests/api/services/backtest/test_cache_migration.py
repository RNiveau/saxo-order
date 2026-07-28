"""Migration of the raw-candle cache from the v1 per-definition key onto
the v2 (instrument, session) key."""

from unittest.mock import AsyncMock, MagicMock

from api.services.backtest.cache_migration import (
    CacheMigration,
    build_plan,
)
from client.aws_client import DynamoDBClient, DynamoDBOperationError
from tests.api.services.backtest.helpers import h1_candle, m5_candle

TRADING_DATE = "2026-06-02"
FRA40_KEY = "FRA40.I:0900-1730@Europe/Paris:v2"
GER40_CFD_KEY = "GER40.I:0900-2200@Europe/Paris:v2"


def item(old_key, trading_date=TRADING_DATE, has_data=True, m5_count=1):
    entry = {
        "definition_code": old_key,
        "trading_date": trading_date,
        "has_data": has_data,
    }
    if has_data:
        entry["h1_candle"] = h1_candle().to_dict()
        entry["m5_candles"] = [
            m5_candle(i, 8005, 8010, 7995, 8000).to_dict()
            for i in range(m5_count)
        ]
    return entry


class TestBuildPlan:
    def test_collapses_definitions_sharing_an_instrument_and_session(self):
        plan = build_plan(
            [
                item("B9H:FRA40.I:v1"),
                item("B9HTC:FRA40.I:v1"),
                item("B9HWS:FRA40.I:v1"),
            ]
        )

        assert len(plan.writes) == 1
        assert len(plan.deletes) == 3
        assert plan.duplicates_removed == 2
        migrated, m5_fetched = plan.writes[0]
        assert migrated["definition_code"] == FRA40_KEY
        assert migrated["trading_date"] == TRADING_DATE
        assert m5_fetched is True

    def test_keeps_separate_entries_per_day_and_session(self):
        plan = build_plan(
            [
                item("B9H:FRA40.I:v1", trading_date="2026-06-02"),
                item("B9H:FRA40.I:v1", trading_date="2026-06-03"),
                item("G9HIC:GER40.I:v1"),
            ]
        )

        keys = {
            (i["definition_code"], i["trading_date"]) for i, _ in plan.writes
        }
        assert keys == {
            (FRA40_KEY, "2026-06-02"),
            (FRA40_KEY, "2026-06-03"),
            (GER40_CFD_KEY, TRADING_DATE),
        }

    def test_partial_entry_from_a_min_range_definition_is_flagged(self):
        """B9HWS skipped the 5-minute fetch on a day below its 40-point
        minimum, so its empty m5_candles is "not fetched", not "no data"
        - the flag has to be reconstructed from the cached H1 range."""
        narrow = item("B9HWS:FRA40.I:v1", m5_count=0)
        narrow["h1_candle"] = h1_candle(higher=8020.0, lower=8000.0).to_dict()

        plan = build_plan([narrow])

        assert plan.writes[0][1] is False

    def test_wide_day_from_a_min_range_definition_is_complete(self):
        """Same definition, a day whose range clears the threshold: the
        5-minute fetch did happen, so the entry migrates as complete."""
        plan = build_plan([item("B9HWS:FRA40.I:v1")])

        assert plan.writes[0][1] is True

    def test_complete_entry_wins_over_a_partial_one(self):
        narrow = item("B9HWS:FRA40.I:v1", m5_count=0)
        narrow["h1_candle"] = h1_candle(higher=8020.0, lower=8000.0).to_dict()
        full = item("B9H:FRA40.I:v1", m5_count=3)
        full["h1_candle"] = narrow["h1_candle"]

        plan = build_plan([narrow, full])

        migrated, m5_fetched = plan.writes[0]
        assert m5_fetched is True
        assert len(migrated["m5_candles"]) == 3

    def test_data_wins_over_a_no_data_marker(self):
        plan = build_plan(
            [
                item("B9H:FRA40.I:v1", has_data=False),
                item("B9HTC:FRA40.I:v1"),
            ]
        )

        assert len(plan.writes) == 1
        assert plan.writes[0][0]["has_data"] is True

    def test_already_migrated_keys_are_left_alone(self):
        plan = build_plan(
            [item(FRA40_KEY), {"definition_code": "junk", "trading_date": "x"}]
        )

        assert plan.writes == []
        assert plan.deletes == []
        assert plan.skipped == 2

    def test_unknown_definition_is_reported_not_dropped(self):
        plan = build_plan([item("GONE:FRA40.I:v1")])

        assert plan.orphans == ["GONE:FRA40.I:v1"]
        assert plan.deletes == []
        assert plan.writes == []


class TestApply:
    def _client(self):
        client = MagicMock(spec=DynamoDBClient)
        client.store_backtest_candles = AsyncMock()
        client.delete_backtest_candles = AsyncMock()
        return client

    async def test_writes_new_entries_then_deletes_old_ones(self):
        client = self._client()
        plan = build_plan([item("B9H:FRA40.I:v1"), item("B9HTC:FRA40.I:v1")])

        result = await CacheMigration(client).apply(plan)

        assert result.written == 1
        assert result.deleted == 2
        assert result.failed == 0
        store_args = client.store_backtest_candles.call_args[0]
        assert store_args[0] == FRA40_KEY
        assert store_args[5] is True
        deleted = {
            c[0][0] for c in client.delete_backtest_candles.call_args_list
        }
        assert deleted == {"B9H:FRA40.I:v1", "B9HTC:FRA40.I:v1"}

    async def test_a_failed_write_keeps_its_old_entries(self):
        """Old rows are only removed once their replacement landed, so an
        interrupted migration leaves duplicated data, never lost data."""
        client = self._client()
        client.store_backtest_candles = AsyncMock(
            side_effect=DynamoDBOperationError("put_item", "boom")
        )
        plan = build_plan([item("B9H:FRA40.I:v1"), item("B9HTC:FRA40.I:v1")])

        result = await CacheMigration(client).apply(plan)

        assert result.written == 0
        assert result.failed == 1
        client.delete_backtest_candles.assert_not_called()

    async def test_second_run_finds_nothing_to_do(self):
        client = self._client()
        client.scan_backtest_candles = AsyncMock(
            return_value=[item(FRA40_KEY)]
        )

        plan = await CacheMigration(client).build_plan()

        assert plan.writes == []
        assert plan.deletes == []
