import datetime

import pytest

from mcp_server import models
from model import Provenance, UnitTime
from model.enum import Exchange

ASSET_BEARING_MODELS = [
    models.InstrumentRef,
    models.StoredAlert,
    models.DigestEntry,
    models.AssetContext,
]


@pytest.mark.parametrize(
    "model", ASSET_BEARING_MODELS, ids=lambda m: m.__name__
)
def test_an_asset_bearing_model_names_its_exchange(model):
    """Venue is stated, never inferred.

    CLAUDE.md is explicit that a Saxo asset can have no country code, so
    nothing may deduce the venue from the rest of the payload. The watchlist
    holds Saxo, Binance and Ouinex assets side by side and the digest item
    already stores the exchange, so a model that drops it is asking the
    reader to guess between venues whose codes collide.
    """
    assert "exchange" in model.model_fields
    assert model.model_fields["exchange"].annotation is Exchange


def test_the_bar_series_names_its_exchange_through_its_meta():
    assert "exchange" in models.ResponseMeta.model_fields
    assert models.BarSeries.model_fields["meta"].annotation is (
        models.ResponseMeta
    )


def _meta(last_bar_date):
    return models.ResponseMeta(
        provenance=Provenance.LIVE,
        exchange=Exchange.SAXO,
        unit_time=UnitTime.D,
        last_bar_date=last_bar_date,
    )


def test_a_naive_bar_date_is_serialised_with_an_offset():
    """The tool schema says date-time, which means RFC 3339.

    Saxo bar times arrive naive, and a naive datetime serialises without an
    offset - the client then rejects the whole answer over a field nothing
    was asking about.
    """
    dumped = _meta(datetime.datetime(2026, 9, 5, 17, 30))
    assert dumped.model_dump(mode="json")["last_bar_date"] == (
        "2026-09-05T17:30:00+00:00"
    )


def test_an_aware_bar_date_keeps_its_own_offset():
    aware = datetime.datetime(
        2026,
        9,
        5,
        17,
        30,
        tzinfo=datetime.timezone(datetime.timedelta(hours=2)),
    )
    assert _meta(aware).model_dump(mode="json")["last_bar_date"] == (
        "2026-09-05T17:30:00+02:00"
    )


def test_an_absent_bar_date_stays_null():
    assert _meta(None).model_dump(mode="json")["last_bar_date"] is None
