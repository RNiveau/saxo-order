import pytest

from mcp_server import models
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
