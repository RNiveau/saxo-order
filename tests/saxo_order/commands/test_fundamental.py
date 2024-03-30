import pytest
from click.testing import CliRunner

import saxo_order.commands.fundamental as command
from client.saxo_client import SaxoClient
from model import ZoneBourseScore, ZoneBourseScrap


class TestFundamental:

    def test_calculate_score(
        self,
    ):
        zb = ZoneBourseScrap()
        zb.init_data([2018, 2019, 2020, 2021, 2022])
        for category in ZoneBourseScrap.WANTED_CATEGORIES:
            zb.create_category(category)
        # data come from total energies (TTE)
        zb.data[2022]["Capitalisation"] = "155896"
        zb.data[2022]["Free Cash Flow"] = "31677"
        zb.data[2022]["Capex"] = "15690"
        zb.data[2022]["ROE"] = "32,4%"
        zb.data[2022]["Dette Nette"] = "18994"
        zb.data[2018]["Résultat net"] = "11446"
        zb.data[2019]["Résultat net"] = "11267"
        zb.data[2020]["Résultat net"] = "-7242"
        zb.data[2021]["Résultat net"] = "16032"
        zb.data[2022]["Résultat net"] = "20526"
        zb.data[2018]["Marge nette"] = "6,22%"
        zb.data[2019]["Marge nette"] = "6,39%"
        zb.data[2020]["Marge nette"] = "-6,05%"
        zb.data[2021]["Marge nette"] = "8,68%"
        zb.data[2022]["Marge nette"] = "7,8%"
        zb.data[2018]["Marge d'exploitation"] = "10,23%"
        zb.data[2019]["Marge d'exploitation"] = "9,86%"
        zb.data[2020]["Marge d'exploitation"] = "4,28%"
        zb.data[2021]["Marge d'exploitation"] = "13,21%"
        zb.data[2022]["Marge d'exploitation"] = "19,19%"

        zb_score = ZoneBourseScore()
        score_lines = command.calculate_score(zb_score, zb, 2022)
        assert zb.data[2018]["Croissance résultat"] == "-"
        assert zb.data[2019]["Croissance résultat"] == "-1.56%"
        assert zb.data[2020]["Croissance résultat"] == "-"
        assert zb.data[2021]["Croissance résultat"] == "42.29%"
        assert zb.data[2022]["Croissance résultat"] == "28.03%"
        assert zb_score.capitalisation == 155896
        assert zb_score.capex == 15690
        assert zb_score.free_cash_flow == 31677
        assert f"{zb_score.croissance:.3f}" == "0.229"
        assert f"{zb_score.marge_nette:.4f}" == "7.2725"
        assert f"{zb_score.marge_exploitation:.4f}" == "13.1225"
        assert zb_score.nb_years == 4
        assert zb_score.score == 7
        assert zb_score.weighted_score == 9

        assert score_lines[0].endswith("2 1 2")
        assert score_lines[1].endswith("1 1 1")
        assert score_lines[2].endswith("2 0 0")
        assert score_lines[3].endswith("2 0 0")
        assert score_lines[4].endswith("1 0 0")
        assert score_lines[5].endswith("1 1 1")
        assert score_lines[6].endswith("2 1 2")
        assert score_lines[7].endswith("1 0 0")
        assert score_lines[8].endswith("1 0 0")
        assert score_lines[9].endswith("1 1 1")
        assert score_lines[10].endswith("1 1 1")
        assert score_lines[11].endswith("1 1 1")
