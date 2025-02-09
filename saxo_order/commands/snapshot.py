from typing import List
import click
from click.core import Context
from prettytable import PrettyTable
from slack_sdk import WebClient

from client.saxo_client import SaxoClient
from model import EUMarket
from model.workflow import UnitTime
from saxo_order.commands import catch_exception
from services.candles_service import CandlesService
from services.indicator_service import bollinger_bands, mobile_average
from utils.configuration import Configuration
from utils.exception import SaxoException
from utils.helper import get_date_utc0
from utils.logger import Logger

logger = Logger.get_logger("snapshot")


@click.command()
@click.pass_context
@catch_exception(handle=SaxoException)
def snapshot(ctx: Context):
    execute_snapshot(ctx.obj["config"])


def execute_snapshot(config: str):
    configuration = Configuration(config)
    saxo_client = SaxoClient(configuration=configuration)
    candles_service = CandlesService(saxo_client=saxo_client)
    slack_client = WebClient(token=configuration.slack_token)
    indexes = [
        "FRA40.I",
        "GER40.I",
    ]  # "US500.I"]
    eu_market = EUMarket()

    # Define columns
    for index in indexes:
        # asset = saxo_client.get_asset(code=index)
        candles_h1 = candles_service.build_hour_candles(
            code=index,
            cfd_code=index,
            ut=UnitTime.H1,
            open_hour_utc0=eu_market.open_hour,
            close_hour_utc0=eu_market.close_hour,
            nbr_hours=160 * 3,
            open_minutes=eu_market.open_minutes,
            date=get_date_utc0(),
        )
        candles_h4 = candles_service.build_hour_candles(
            code=index,
            cfd_code=index,
            ut=UnitTime.H4,
            open_hour_utc0=eu_market.open_hour,
            close_hour_utc0=eu_market.close_hour,
            nbr_hours=160 * 3 * 4,
            open_minutes=eu_market.open_minutes,
            date=get_date_utc0(),
        )
        candles_daily = candles_service.build_hour_candles(
            code=index,
            cfd_code=index,
            ut=UnitTime.D,
            open_hour_utc0=eu_market.open_hour,
            close_hour_utc0=eu_market.close_hour,
            nbr_hours=160 * 3 * 8,
            open_minutes=eu_market.open_minutes,
            date=get_date_utc0(),
        )
        table = PrettyTable()
        bb_h1_2 = bollinger_bands(candles_h1)
        bb_h4_2 = bollinger_bands(candles_h4)
        bb_daily_2 = bollinger_bands(candles_daily)
        bb_h1_25 = bollinger_bands(candles_h1, 2.5)
        bb_h4_25 = bollinger_bands(candles_h4, 2.5)
        bb_daily_25 = bollinger_bands(candles_daily, 2.5)
        am50_h1 = mobile_average(candles=candles_h1, period=50)
        am50_h4 = mobile_average(candles=candles_h4, period=50)
        am50_daily = mobile_average(candles=candles_daily, period=50)
        table.field_names = ["Indicator", "H1", "H4", "Daily"]
        zones = find_zones([am50_h1, am50_h4, am50_daily, bb_h1_2.bottom, bb_h4_2.bottom, bb_daily_2.bottom, bb_h1_25.bottom, bb_h4_25.bottom, bb_daily_25.bottom, bb_h1_2.up, bb_h4_2.up, bb_daily_2.up, bb_h1_25.up, bb_h4_25.up, bb_daily_25.up])
        # next step: deflatten the zones to show a different symbol.
        # create a method to show the value
        table.add_row(
            [
                "MM 50",
                f"{am50_h1:.2f} {'*' if am50_h1 in zones else ''}",
                f"{am50_h4:.2f} {'*' if am50_h4 in zones else ''}",
                f"{am50_daily:.2f} {'*' if am50_daily in zones else ''}",
            ]
        )
        table.add_row(
            [
                "BBH 2.0",
                f"{bb_h1_2.up:.2f} {'*' if bb_h1_2.up in zones else ''}",
                f"{bb_h4_2.up:.2f} {'*' if bb_h4_2.up in zones else ''}",
                f"{bb_daily_2.up:.2f} {'*' if bb_daily_2.up in zones else ''}"
            ]
        )
        table.add_row(
            [
                "BBH 2.5",
                f"{bb_h1_25.up:.2f} {'*' if bb_h1_25.up in zones else ''}",
                f"{bb_h4_25.up:.2f} {'*' if bb_h4_25.up in zones else ''}",
                f"{bb_daily_25.up:.2f} {'*' if bb_daily_25.up in zones else ''}",
            ]
        )
        table.add_row(
            [
                "BBL 2.0",
                f"{bb_h1_2.bottom:.2f} {'*' if bb_h1_2.bottom in zones else ''}",
                f"{bb_h4_2.bottom:.2f} {'*' if bb_h4_2.bottom in zones else ''}",
                f"{bb_daily_2.bottom:.2f} {'*' if bb_daily_2.bottom in zones else ''}",
            ]
        )
        table.add_row(
            [
                "BBL 2.5",
                f"{bb_h1_25.bottom:.2f} {'*' if bb_h1_25.bottom in zones else ''}",
                f"{bb_h4_25.bottom:.2f} {'*' if bb_h4_25.bottom in zones else ''}",
                f"{bb_daily_25.bottom:.2f} {'*' if bb_daily_25.bottom in zones else ''}",
            ]
        )
        slack_client.chat_postMessage(
            channel="#snapshots",
            text=f"{index} ({candles_h1[0].close}) ```{table}```",
        )
        print(table)

def find_zones(numbers: List[float]) -> List[List[float]]:
    sorted_numbers = sorted(numbers)
    zones = []
    current_zone = [sorted_numbers[0]]

    for i in range(1, len(sorted_numbers)):
        if sorted_numbers[i] - current_zone[-1] <= 10:
            current_zone.append(sorted_numbers[i])
        else:
            zones.append(current_zone)
            current_zone = [sorted_numbers[i]]
    
    if current_zone:
        zones.append(current_zone)
    
    return list(filter(lambda x: len(x) > 1, zones))
