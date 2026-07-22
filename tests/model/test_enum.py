import pytest

from model.enum import Exchange


class TestExchange:
    def test_get_value_resolves_ouinex(self):
        assert Exchange.get_value("ouinex") == Exchange.OUINEX

    def test_get_value_resolves_binance(self):
        assert Exchange.get_value("binance") == Exchange.BINANCE

    def test_get_value_resolves_saxo(self):
        assert Exchange.get_value("saxo") == Exchange.SAXO

    def test_get_value_invalid_raises(self):
        with pytest.raises(ValueError):
            Exchange.get_value("unknown")

    def test_ouinex_is_crypto(self):
        assert Exchange.OUINEX.is_crypto() is True

    def test_binance_is_crypto(self):
        assert Exchange.BINANCE.is_crypto() is True

    def test_saxo_is_not_crypto(self):
        assert Exchange.SAXO.is_crypto() is False
