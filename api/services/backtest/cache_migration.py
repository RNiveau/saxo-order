"""One-off migration of the raw-candle cache from the v1 per-definition
key to the v2 (instrument, session) key.

v1 keyed every entry on `{code}:{instrument}:v1`, so the six definitions
stored six copies of the very same Saxo candles - `B9H`, `B9HTC` and
`B9HWS` each held their own FRA40.I series. v2 keys on what the fetch
actually depends on, which collapses those copies into one entry per
(instrument, session, day).

The planning half here is pure: it turns the table's items into a list of
writes and deletes, so what the migration would do can be shown (and
tested) without touching DynamoDB.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from api.services.backtest.candle_source import (
    CACHE_SCHEMA_VERSION,
    cache_key,
)
from api.services.backtest.definitions import get_definition
from client.aws_client import DynamoDBClient, DynamoDBOperationError

# v1 keys, e.g. "B9HWS:FRA40.I:v1". The version is matched explicitly so a
# re-run over an already-migrated table finds nothing to do rather than
# re-processing current-schema keys.
V1_KEY_PATTERN = re.compile(r"^(?P<code>[^:]+):(?P<instrument>[^:]+):v1$")

CURRENT_KEY_SUFFIX = f":v{CACHE_SCHEMA_VERSION}"


@dataclass
class _Candidate:
    """One contender for a target (new key, trading date) slot: either a
    v1 row to be rewritten, or the current-schema row already sitting
    there."""

    item: Dict[str, Any]
    m5_fetched: bool
    # False for a row already stored under the current key - it is a
    # contender so a v1 row cannot silently replace something better,
    # but nothing needs writing if it wins.
    needs_write: bool


@dataclass
class MigrationPlan:
    """What the migration would write and delete, plus what it could not
    account for."""

    # (item to write under its new key, m5_fetched) pairs.
    writes: List[Tuple[Dict[str, Any], bool]] = field(default_factory=list)
    # (old key, trading_date) pairs to remove once the writes land.
    deletes: List[Tuple[str, str]] = field(default_factory=list)
    # Target slots a current-schema row already covers at least as well as
    # anything v1 holds. Nothing is written for them, but the v1 rows
    # feeding them are still safe to delete.
    already_present: List[Tuple[str, str]] = field(default_factory=list)
    # Old keys whose definition code is no longer in the registry: they
    # can't be mapped to an instrument/session, so they are reported and
    # left in place rather than guessed at or dropped.
    orphans: List[str] = field(default_factory=list)
    # Rows left untouched: already on the current key, or a key shape this
    # migration doesn't recognise.
    skipped: int = 0
    # Distinct target slots the v1 rows map onto, for duplicates_removed.
    target_slots: int = 0

    @property
    def v1_entries(self) -> int:
        """Every v1 row found, mappable or not."""
        return len(self.deletes) + len(self.orphans)

    @property
    def duplicates_removed(self) -> int:
        """Entries the migration collapses: every v1 row that doesn't
        survive as a distinct entry of its own."""
        return len(self.deletes) - self.target_slots


@dataclass
class MigrationResult:
    written: int = 0
    deleted: int = 0
    # Kept apart because the consequences differ: a failed write means a
    # day was not migrated (its v1 row is deliberately left in place), a
    # failed delete means a migrated day left a duplicate v1 row behind.
    write_failures: int = 0
    delete_failures: int = 0

    @property
    def failed(self) -> int:
        return self.write_failures + self.delete_failures


def _entry_rank(
    item: Dict[str, Any], m5_fetched: bool, needs_write: bool = True
) -> Tuple:
    """How useful an item is, for picking a winner when several entries
    contend for the same target slot. Real data beats a no-data marker, a
    complete 5-minute series beats a partial one, and a longer series
    beats a shorter one (two entries for the same day should hold the
    same candles, but if they don't, keep the fuller one). On a tie a row
    already stored under the current key wins, so an equally-good v1 row
    doesn't cause a pointless rewrite."""
    return (
        bool(item.get("has_data")),
        m5_fetched,
        len(item.get("m5_candles") or []),
        not needs_write,
    )


def _was_m5_fetched(item: Dict[str, Any], definition_code: str) -> bool:
    """Whether the writing definition actually fetched the day's 5-minute
    candles, or short-circuited on its minimum H1 range (FR-033).

    v1 items carry no such flag, so it is reconstructed: only a definition
    with a minimum range could skip the fetch, and only on a day whose
    cached H1 range fails that threshold. Everything else was a genuine
    fetch, empty result included."""
    if not item.get("has_data"):
        return True
    definition = get_definition(definition_code)
    if definition is None or definition.min_h1_range_points is None:
        return True
    h1_candle = item.get("h1_candle") or {}
    try:
        h1_range = float(h1_candle["higher"]) - float(h1_candle["lower"])
    except (KeyError, TypeError, ValueError):
        # A malformed H1 candle is unusable either way; call it fetched so
        # the entry is migrated as-is and the reader's own malformed-item
        # handling treats it as a miss.
        return True
    return h1_range > definition.min_h1_range_points


def build_plan(items: List[Dict[str, Any]]) -> MigrationPlan:
    """Turn the table's current contents into the writes and deletes that
    move it onto the current key. Pure - no I/O.

    Rows already stored under the current key are contenders rather than
    noise: a v1 row only overwrites one if it is strictly better. Without
    that, a partially-completed run followed by a second one (exactly the
    documented recovery path) could push a stale v1 copy over an entry
    the running application had since improved."""
    plan = MigrationPlan()
    best: Dict[Tuple[str, str], _Candidate] = {}
    v1_targets: set = set()

    def offer(slot: Tuple[str, str], candidate: _Candidate) -> None:
        current = best.get(slot)
        if current is None or _entry_rank(
            candidate.item, candidate.m5_fetched, candidate.needs_write
        ) > _entry_rank(current.item, current.m5_fetched, current.needs_write):
            best[slot] = candidate

    for item in items:
        old_key = item.get("definition_code")
        trading_date = item.get("trading_date")
        if not isinstance(old_key, str) or not isinstance(trading_date, str):
            plan.skipped += 1
            continue

        match = V1_KEY_PATTERN.match(old_key)
        if match is None:
            plan.skipped += 1
            if old_key.endswith(CURRENT_KEY_SUFFIX):
                offer(
                    (old_key, trading_date),
                    _Candidate(
                        item=item,
                        m5_fetched=bool(item.get("m5_fetched", True)),
                        needs_write=False,
                    ),
                )
            continue

        code = match.group("code")
        definition = get_definition(code)
        if definition is None:
            plan.orphans.append(old_key)
            continue

        plan.deletes.append((old_key, trading_date))
        new_key = cache_key(definition)
        migrated = dict(item)
        migrated["definition_code"] = new_key
        v1_targets.add((new_key, trading_date))
        offer(
            (new_key, trading_date),
            _Candidate(
                item=migrated,
                m5_fetched=_was_m5_fetched(item, code),
                needs_write=True,
            ),
        )

    plan.target_slots = len(v1_targets)
    plan.writes = [
        (c.item, c.m5_fetched) for c in best.values() if c.needs_write
    ]
    plan.already_present = [
        slot for slot, c in best.items() if not c.needs_write
    ]
    return plan


class CacheMigration:
    """Applies a MigrationPlan against DynamoDB."""

    def __init__(
        self,
        dynamodb_client: DynamoDBClient,
        logger: Optional[logging.Logger] = None,
    ):
        self.dynamodb_client = dynamodb_client
        self.logger = logger or logging.getLogger(__name__)

    async def build_plan(self) -> MigrationPlan:
        items = await self.dynamodb_client.scan_backtest_candles()
        return build_plan(items)

    async def apply(self, plan: MigrationPlan) -> MigrationResult:
        """Write every new entry, then delete the old ones - in that
        order, so an interrupted run leaves duplicated data rather than
        deleted data. A failed write cancels the deletes that would have
        removed its source rows, so nothing is lost; the migration is
        idempotent, so the fix is to run it again."""
        result = MigrationResult()
        # A slot a current-schema row already covers needs no write, but
        # the v1 rows feeding it are just as safe to delete as if one had
        # been made.
        written_keys = set(plan.already_present)

        for item, m5_fetched in plan.writes:
            key = (item["definition_code"], item["trading_date"])
            try:
                await self.dynamodb_client.store_backtest_candles(
                    item["definition_code"],
                    item["trading_date"],
                    bool(item.get("has_data")),
                    item.get("h1_candle"),
                    item.get("m5_candles"),
                    m5_fetched,
                )
            except (DynamoDBOperationError, RuntimeError) as e:
                self.logger.error(f"Failed to migrate {key}: {e}")
                result.write_failures += 1
                continue
            written_keys.add(key)
            result.written += 1

        for old_key, trading_date in plan.deletes:
            if not self._is_covered(old_key, trading_date, written_keys):
                continue
            try:
                await self.dynamodb_client.delete_backtest_candles(
                    old_key, trading_date
                )
            except (DynamoDBOperationError, RuntimeError) as e:
                self.logger.error(
                    f"Failed to delete {old_key}/{trading_date}: {e}"
                )
                result.delete_failures += 1
                continue
            result.deleted += 1

        return result

    @staticmethod
    def _is_covered(
        old_key: str, trading_date: str, written_keys: set
    ) -> bool:
        """Whether the new entry replacing this old row was written. An
        old row whose replacement failed is kept."""
        match = V1_KEY_PATTERN.match(old_key)
        if match is None:
            return False
        definition = get_definition(match.group("code"))
        if definition is None:
            return False
        return (cache_key(definition), trading_date) in written_keys
