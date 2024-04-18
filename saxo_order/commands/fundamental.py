from typing import List

import click

from client.zone_bourse_client import ZoneBourseClient
from model import ZoneBourseScore, ZoneBourseScrap
from saxo_order.commands import catch_exception
from utils.exception import SaxoException


@click.command
@click.option(
    "--url",
    type=str,
    required=True,
    prompt="What is the zone bourse url ?",
)
@catch_exception(handle=SaxoException)
def get_score(url: str):
    referential_year = click.prompt(
        "What year has to be used as the main one ?", type=int, default=2023
    )
    zb_client = ZoneBourseClient()
    zb_score = ZoneBourseScore()
    zb_score.is_ath = (
        click.prompt(
            "Do we have new ATH in the last 3 months ?", type=click.Choice(["y", "n"])
        )
        == "y"
    )
    zb_score.is_outperformance = (
        click.prompt(
            "Do we have a outperformance compared to the indexe ?",
            type=click.Choice(["y", "n"]),
        )
        == "y"
    )
    zb_score.is_bullish = (
        click.prompt("Do we have a bullish trend ?", type=click.Choice(["y", "n"]))
        == "y"
    )
    zb_score.is_dividend_increase = (
        click.prompt("Does dividend rate increase ?", type=click.Choice(["y", "n"]))
        == "y"
    )

    zb = zb_client.parse_fundamental(url)

    score_lines = calculate_score(zb_score, zb, referential_year)

    print(f"{' ':<20}", end=" ")
    for year in zb.data:
        print(f"{year:<10}", end="")
    print("")
    for category in ZoneBourseScrap.WANTED_CATEGORIES:
        print(f"{category:<20}", end=" ")
        for year in zb.data:
            print(f"{zb.data[year][category]:<10}", end="")
        print("")
    print()

    for line in score_lines:
        print(line)
    print(f"{'Total':<45} - {zb_score.score} {zb_score.weighted_score}")


def calculate_score(
    zb_score: ZoneBourseScore, zb_data: ZoneBourseScrap, referential_year: int
) -> List[str]:
    zb_score.capitalisation = zb_data_to_float(
        zb_data.data[referential_year]["Capitalisation"]
    )
    zb_score.free_cash_flow = zb_data_to_float(
        zb_data.data[referential_year]["Free Cash Flow"]
    )
    zb_score.capex = zb_data_to_float(zb_data.data[referential_year]["Capex"])

    label_croissance = "Croissance résultat"
    for year in zb_data.data:
        if year > referential_year:
            break
        if year == 2020:
            # we exclude 2020 due to the covid crisis
            zb_data.add_data(
                year,
                label_croissance,
                "-",
            )
            continue
        if zb_score.resultat_net == 0:
            zb_score.resultat_net = zb_data_to_float(zb_data.data[year]["Résultat net"])
            zb_data.add_data(
                year,
                label_croissance,
                "-",
            )
        else:
            diff = zb_score.resultat_net - zb_data_to_float(
                zb_data.data[year]["Résultat net"]
            )
            year_croissance = abs(diff) / abs(zb_score.resultat_net)
            if diff > 0:
                year_croissance *= -1
            zb_score.croissance += year_croissance
            zb_score.resultat_net = zb_data_to_float(zb_data.data[year]["Résultat net"])
            zb_data.add_data(
                year,
                label_croissance,
                f"{year_croissance * 100:.2f}%",
            )
        zb_score.marge_nette += zb_data_to_float(zb_data.data[year]["Marge nette"])
        zb_score.marge_exploitation += zb_data_to_float(
            zb_data.data[year]["Marge d'exploitation"]
        )
        zb_score.nb_years += 1

    zb_score.croissance /= zb_score.nb_years - 1
    zb_score.marge_exploitation /= zb_score.nb_years
    zb_score.marge_nette /= zb_score.nb_years

    score_lines = []
    score_lines.append(
        build_line_score(
            "Croissance Résultat net > 10% /an", zb_score.croissance > 0.1, 2, zb_score
        )
    )
    score_lines.append(
        build_line_score(
            "Croissance Résultat net > 15% /an", zb_score.croissance > 0.15, 1, zb_score
        )
    )
    score_lines.append(
        build_line_score(
            "Marge nette > 10% /an",
            zb_score.marge_nette >= 10,
            2,
            zb_score,
        )
    )
    score_lines.append(
        build_line_score(
            "Marge d'exploitation > 20%/an",
            zb_score.marge_exploitation >= 20,
            2,
            zb_score,
        )
    )
    score_lines.append(
        build_line_score(
            "Marge d'exploitation > 40%/an",
            zb_score.marge_exploitation >= 40,
            1,
            zb_score,
        )
    )
    score_lines.append(
        build_line_score(
            "Taux de croissance des dividendes stable",
            not zb_score.is_dividend_increase,
            1,
            zb_score,
        )
    )
    score_lines.append(
        build_line_score(
            "ROE > 10%",
            zb_data_to_float(zb_data.data[referential_year]["ROE"]) >= 10,
            2,
            zb_score,
        )
    )
    score_lines.append(
        build_line_score(
            "Capex/Résultat net < 25%",
            zb_score.capex < zb_score.resultat_net * 0.25,
            1,
            zb_score,
        )
    )
    score_lines.append(
        build_line_score(
            "Capex/Résultat net < 50%",
            zb_score.capex < zb_score.resultat_net * 0.50,
            1,
            zb_score,
        )
    )
    free_cash_flow = zb_score.free_cash_flow if zb_score.free_cash_flow > 0 else 1
    score_lines.append(
        build_line_score(
            "Capitalisation / Free cash flow < 8",
            zb_score.capitalisation / free_cash_flow <= 8,
            1,
            zb_score,
        )
    )
    score_lines.append(
        build_line_score(
            "Capitalisation / Free cash flow < 20",
            zb_score.capitalisation / free_cash_flow <= 20,
            1,
            zb_score,
        )
    )
    score_lines.append(
        build_line_score(
            "Niveau d'endettement < 4 * le résultat net",
            zb_data_to_float(zb_data.data[referential_year]["Dette Nette"])
            < zb_score.resultat_net * 4,
            1,
            zb_score,
        )
    )
    score_lines.append(
        build_line_score("Nouveau plus haut < 3 mois", zb_score.is_ath, 1, zb_score)
    )
    score_lines.append(
        build_line_score(
            "Superforme son benchmark (indice)", zb_score.is_outperformance, 1, zb_score
        )
    )
    score_lines.append(
        build_line_score(
            "Tendance haussière sur les 5 dernières années",
            zb_score.is_bullish,
            2,
            zb_score,
        )
    )

    return score_lines


def build_line_score(
    title: str, condition: bool, coefficient: int, zb_score: ZoneBourseScore
) -> str:
    line = f"{title:<45} {coefficient} "
    if condition:
        line = f"{line}1 {coefficient}"
        zb_score.score += 1
        zb_score.weighted_score += coefficient
    else:
        line = f"{line}0 0"
    return line


def zb_data_to_float(nbr: str) -> float:
    return float(nbr.replace(",", ".").replace("%", "").replace("-", "0"))
