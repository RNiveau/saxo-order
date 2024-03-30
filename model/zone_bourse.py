class ZoneBourseScore:

    def __init__(self) -> None:
        self.marge_nette = 0.0
        self.marge_exploitation = 0.0
        self.capitalisation = 0.0
        self.free_cash_flow = 0.0
        self.score = 0
        self.weighted_score = 0
        self.croissance = 0.0
        self.resultat_net = 0.0
        self.capex = 0.0
        self.nb_years = 0
        self.is_ath = False
        self.is_outperformance = False
        self.is_bullish = False
        self.is_dividend_increase = False


class ZoneBourseScrap:

    WANTED_CATEGORIES = [
        "Capitalisation",
        "Résultat net",
        "Croissance résultat",
        "ROE",
        "Marge nette",
        "Marge d'exploitation",
        "Capex",
        "Free Cash Flow",
        "Dette Nette",
    ]

    def __init__(self) -> None:
        self.data: dict[int, dict] = {}

    def init_data(self, years: list[int]) -> None:
        for year in years:
            if year > 0:
                self.data[year] = {}

    def create_category(self, category: str) -> None:
        for year in self.data:
            self.data[year][category] = 0

    def add_data(self, year: int, category: str, data: str):
        self.data[year][category] = data
