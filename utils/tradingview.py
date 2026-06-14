from typing import Optional

EXCHANGE_MAP = {
    "xpar": "EURONEXT",
    "xnas": "NASDAQ",
    "xnys": "NYSE",
    "xlon": "LSE",
    "xfra": "FWB",
    "xetr": "XETR",
}

_DEFAULT_EXCHANGE = "EURONEXT"


def build_tradingview_url(code: str, country_code: Optional[str]) -> str:
    exchange = EXCHANGE_MAP.get(
        (country_code or "").lower(), _DEFAULT_EXCHANGE
    )
    return (
        f"https://www.tradingview.com/chart/?symbol={exchange}:{code.upper()}"
    )


def build_tradingview_url_from_symbol(symbol: str) -> str:
    if ":" in symbol:
        code, country_code = symbol.split(":", 1)
    else:
        code, country_code = symbol, None
    return build_tradingview_url(code, country_code)
