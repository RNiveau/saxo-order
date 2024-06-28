import typing

import requests
from bs4 import BeautifulSoup

from model import ZoneBourseScrap


class ZoneBourseClient:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
                " AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            }
        )

    @typing.no_type_check
    def parse_fundamental(self, url: str) -> ZoneBourseScrap:
        s = self.session.get(url).text
        soup = BeautifulSoup(s, "html.parser")
        table = soup.find("table", id="valuationTable")
        ths = table.find_all("th")
        years = [0] * len(ths)
        for index, th in enumerate(ths):
            try:
                years[index] = int(th.text.strip())
            except Exception:
                pass
        zb = ZoneBourseScrap()
        zb.init_data(years)

        for row in (
            table.find_all("tr")
            + soup.find("table", id="iseTableA").find_all("tr")
            + soup.find("table", id="bsTable").find_all("tr")
        ):
            category = ""
            for index, cell in enumerate(row.find_all("td")):
                if index == 0:
                    category = cell.text.strip().split("\n")[0]
                    if category == "ROE (RN / Capitaux Propres)":
                        category = "ROE"
                    zb.create_category(category)
                else:
                    zb.add_data(
                        years[index],
                        category,
                        cell.text.strip()
                        .replace("\u202f", "")
                        .replace("\n", "")
                        .replace("\xa0", ""),
                    )
        zb.create_category("Croissance résultat")
        return zb
