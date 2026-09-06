"""The bundled state snapshot: what an instrument looks like right now."""

import asyncio
from typing import List, Optional

from mcp.server.mcpserver.exceptions import ToolError

from mcp_server.dependencies import resolve_market
from mcp_server.errors import current_market_client
from mcp_server.models import IndicatorSnapshot, IndicatorValue, ResponseMeta
from model import (
    AssetType,
    IndicatorName,
    MarketName,
    Provenance,
    UnitTime,
)
from model.enum import Exchange
from services import candle_source, indicator_bundle_service
from utils.logger import Logger

logger = Logger.get_logger("mcp_tools_indicators")

SUPPORTED_UNIT_TIMES = (UnitTime.D, UnitTime.W)

# Enough completed days to cover the week now forming; the weekly series
# only reads the current ISO week out of them, so fetching the indicators'
# full daily depth here would buy history nothing looks at.
DAYS_FOR_FORMING_WEEK = 10


def _variation_pct(closes: List[float]) -> Optional[float]:
    if len(closes) < 2 or closes[1] == 0:
        return None
    return round((closes[0] - closes[1]) / closes[1] * 100, 4)


async def build_snapshot(
    instrument_id: int,
    asset_type: AssetType,
    unit_time: UnitTime,
    include: Optional[List[IndicatorName]],
    exchange: Exchange,
    market: Optional[MarketName],
) -> IndicatorSnapshot:
    """Fetch once, then compute. Kept apart from the tool for testability."""
    if unit_time not in SUPPORTED_UNIT_TIMES:
        raise ToolError(
            f"{unit_time.value} is not supported; this server reads "
            + " and ".join(u.value for u in SUPPORTED_UNIT_TIMES)
        )
    if include is not None and len(include) == 0:
        raise ToolError(
            "include was empty; omit it for the full set, or name the "
            "indicators you want"
        )

    if exchange is not Exchange.SAXO:
        raise ToolError(
            f"{exchange.value} is not supported yet; this server reads "
            "market data from saxo only. Labelling a saxo answer with "
            "another venue would be worse than refusing - an instrument id "
            "means something different on each."
        )
    if unit_time is UnitTime.W and market is None:
        raise ToolError(
            "The weekly timeframe needs a market: the week now forming is "
            "assembled from the days elapsed in it, and without session "
            "hours those days are incomplete, which would understate the "
            "bar's close, high and low with no way to tell. Pass market, "
            "or ask for the daily timeframe."
        )

    requested = include or indicator_bundle_service.DEFAULT_INDICATORS
    # Exactly what the requested indicators need - not the scan's 250, which
    # is deeper than even macd0lag and would make every shallow request pay
    # the full cost.
    needed = indicator_bundle_service.required_bars(requested)
    client, provenance = current_market_client()
    resolved_market = resolve_market(market)

    # On the weekly path the daily leg only supplies the forming week, so
    # the indicators' depth applies to the weekly series instead.
    daily = await asyncio.to_thread(
        candle_source.build_daily_series,
        client,
        instrument_id,
        resolved_market,
        asset_type,
        DAYS_FOR_FORMING_WEEK if unit_time is UnitTime.W else needed,
    )
    if unit_time is UnitTime.W:
        candles = await asyncio.to_thread(
            candle_source.build_weekly_series,
            client,
            instrument_id,
            daily,
            asset_type,
            needed,
        )
    else:
        candles = daily

    if not candles:
        raise ToolError(
            "The simulated client returns no candles, so there is nothing "
            "to analyse. Opting in to simulated data does not make this "
            "tool work - refresh the Saxo access token."
            if provenance is Provenance.SIMULATED
            else f"No history returned for instrument {instrument_id}"
        )

    outcomes = indicator_bundle_service.compute_bundle(candles, requested)
    closes = [c.close for c in candles]

    return IndicatorSnapshot(
        meta=ResponseMeta(
            provenance=provenance,
            exchange=exchange,
            unit_time=unit_time,
            last_bar_date=candles[0].date if candles else None,
            forming_period_included=resolved_market is not None,
        ),
        instrument_id=instrument_id,
        asset_type=asset_type,
        current_price=round(closes[0], 4) if closes else None,
        variation_pct=_variation_pct(closes),
        indicators=[
            IndicatorValue(
                name=o.name,
                value=o.value,
                unavailable_reason=o.unavailable_reason,
            )
            for o in outcomes
        ],
        bars_fetched=len(candles),
    )
