"""The regeneration gate.

Regenerating the golden snapshot makes it pass by construction, so the
gate is the only thing between "I regenerated it" and a behavior change
nobody reviewed. It therefore needs testing itself - an unguarded
regenerate looks identical to a guarded one right up until it silently
rewrites a shipped definition's numbers.
"""

import json
from unittest.mock import patch

import pytest

from tests.api.services.backtest import test_backtest_golden as golden


def entry(trades, result, exits=("stop_loss",)):
    return {
        "run": {
            "summary": {
                "number_of_days": 42,
                "number_of_trades": trades,
                "number_of_winning_positions": trades,
                "number_of_losing_positions": 0,
                "number_of_be": 0,
                "final_result": result,
            }
        },
        "exit_reasons": {name: {"count": 1} for name in exits},
    }


@pytest.fixture
def golden_file(tmp_path):
    path = tmp_path / "backtest_golden.json"
    with patch.object(golden, "GOLDEN_FILE", path):
        yield path


def regenerate(built, accepted=frozenset()):
    async def _build():
        return built

    with patch.object(golden, "_build_snapshot", _build):
        return golden._regenerate(set(accepted))


class TestUnchangedAndNew:
    def test_an_identical_rebuild_writes_and_succeeds(self, golden_file):
        snapshot = {"B9H": entry(10, 100.0)}
        golden_file.write_text(json.dumps(snapshot))
        assert regenerate(snapshot) == 0

    def test_a_new_definition_needs_no_permission(self, golden_file):
        """Adding a backtest is the common case and must stay one
        command - it changes nothing that already existed."""
        golden_file.write_text(json.dumps({"B9H": entry(10, 100.0)}))
        built = {"B9H": entry(10, 100.0), "C5M": entry(5, 50.0)}
        assert regenerate(built) == 0
        assert set(json.loads(golden_file.read_text())) == {"B9H", "C5M"}

    def test_a_missing_file_is_written_from_scratch(self, golden_file):
        assert regenerate({"B9H": entry(10, 100.0)}) == 0
        assert golden_file.exists()


class TestChangedDefinitions:
    def test_a_changed_definition_is_refused(self, golden_file):
        golden_file.write_text(json.dumps({"B9H": entry(10, 100.0)}))
        assert regenerate({"B9H": entry(11, 250.0)}) == 1

    def test_the_file_is_left_untouched_when_refused(self, golden_file):
        """The refusal has to be total: a half-written file would be
        worse than either outcome."""
        before = json.dumps({"B9H": entry(10, 100.0)})
        golden_file.write_text(before)
        regenerate({"B9H": entry(11, 250.0)})
        assert golden_file.read_text() == before

    def test_naming_it_allows_the_change(self, golden_file):
        golden_file.write_text(json.dumps({"B9H": entry(10, 100.0)}))
        assert regenerate({"B9H": entry(11, 250.0)}, {"B9H"}) == 0
        assert (
            json.loads(golden_file.read_text())["B9H"]["run"]["summary"][
                "final_result"
            ]
            == 250.0
        )

    def test_naming_a_different_one_does_not_help(self, golden_file):
        golden_file.write_text(
            json.dumps({"B9H": entry(10, 100.0), "G9H": entry(8, 80.0)})
        )
        built = {"B9H": entry(11, 250.0), "G9H": entry(8, 80.0)}
        assert regenerate(built, {"G9H"}) == 1

    def test_all_accepts_everything(self, golden_file):
        golden_file.write_text(
            json.dumps({"B9H": entry(10, 100.0), "G9H": entry(8, 80.0)})
        )
        built = {"B9H": entry(11, 250.0), "G9H": entry(9, 90.0)}
        assert regenerate(built, {"all"}) == 0

    def test_a_change_outside_the_summary_is_still_caught(self, golden_file):
        """Two runs can agree on every summary figure and still differ in
        the per-day rows or a trade's exit price - the snapshot compares
        the whole entry, so the gate must too."""
        before = entry(10, 100.0)
        after = entry(10, 100.0)
        after["run"]["days"] = [{"date": "2026-03-02"}]
        golden_file.write_text(json.dumps({"B9H": before}))
        assert regenerate({"B9H": after}) == 1


class TestRefusalMessage:
    def test_it_names_the_definition_and_what_moved(self, golden_file, capsys):
        golden_file.write_text(json.dumps({"B9H": entry(10, 100.0)}))
        regenerate({"B9H": entry(11, 250.0)})
        out = capsys.readouterr().out
        assert "B9H" in out
        assert "number_of_trades: 10 -> 11" in out
        assert "final_result: 100.0 -> 250.0" in out

    def test_it_prints_the_command_that_would_accept_it(
        self, golden_file, capsys
    ):
        golden_file.write_text(json.dumps({"B9H": entry(10, 100.0)}))
        regenerate({"B9H": entry(11, 250.0)})
        assert "--accept B9H" in capsys.readouterr().out

    def test_it_reports_an_exit_mix_change(self, golden_file, capsys):
        golden_file.write_text(
            json.dumps({"B9H": entry(10, 100.0, ("stop_loss",))})
        )
        regenerate({"B9H": entry(10, 100.0, ("take_profit",))})
        assert "exits:" in capsys.readouterr().out

    def test_it_says_so_when_only_the_detail_moved(self, golden_file, capsys):
        before = entry(10, 100.0)
        after = entry(10, 100.0)
        after["run"]["days"] = [{"date": "2026-03-02"}]
        golden_file.write_text(json.dumps({"B9H": before}))
        regenerate({"B9H": after})
        assert "summary identical" in capsys.readouterr().out
