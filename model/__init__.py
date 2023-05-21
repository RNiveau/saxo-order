class Account:
    def __init__(self, key: str, fund: float, available_fund: float) -> None:
        self.key = key
        self.fund = fund
        self.available_fund = available_fund
