from utils.tradingview import (
    build_tradingview_url,
    build_tradingview_url_from_symbol,
)


def test_build_tradingview_url_maps_known_country_codes():
    assert (
        build_tradingview_url("nke", "xnys")
        == "https://www.tradingview.com/chart/?symbol=NYSE:NKE"
    )
    assert (
        build_tradingview_url("aapl", "xnas")
        == "https://www.tradingview.com/chart/?symbol=NASDAQ:AAPL"
    )
    assert (
        build_tradingview_url("mc", "xpar")
        == "https://www.tradingview.com/chart/?symbol=EURONEXT:MC"
    )


def test_build_tradingview_url_falls_back_to_euronext_for_unknown_country():
    assert (
        build_tradingview_url("foo", "xzzz")
        == "https://www.tradingview.com/chart/?symbol=EURONEXT:FOO"
    )


def test_build_tradingview_url_handles_missing_country_code():
    assert (
        build_tradingview_url("foo", None)
        == "https://www.tradingview.com/chart/?symbol=EURONEXT:FOO"
    )
    assert (
        build_tradingview_url("foo", "")
        == "https://www.tradingview.com/chart/?symbol=EURONEXT:FOO"
    )


def test_build_tradingview_url_from_symbol_parses_colon_format():
    assert (
        build_tradingview_url_from_symbol("NKE:xnys")
        == "https://www.tradingview.com/chart/?symbol=NYSE:NKE"
    )


def test_build_tradingview_url_from_symbol_handles_no_colon():
    assert (
        build_tradingview_url_from_symbol("FRA40")
        == "https://www.tradingview.com/chart/?symbol=EURONEXT:FRA40"
    )
