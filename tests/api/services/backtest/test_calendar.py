import datetime
from zoneinfo import ZoneInfo

from api.services.backtest import (
    is_future_paris_date,
    is_today_not_yet_closed,
    paris_reference_window_utc,
    paris_session_end_utc,
    session_key,
)
from model import EuCfdMarket, EUMarket

PARIS_TZ = ZoneInfo("Europe/Paris")


class TestReferenceWindow:
    def test_reference_window_cest_summer(self):
        start, end = paris_reference_window_utc(
            datetime.date(2026, 6, 2), EUMarket()
        )
        assert start == datetime.datetime(2026, 6, 2, 7, 0)
        assert end == datetime.datetime(2026, 6, 2, 8, 0)

    def test_reference_window_cet_winter(self):
        start, end = paris_reference_window_utc(
            datetime.date(2026, 1, 15), EUMarket()
        )
        assert start == datetime.datetime(2026, 1, 15, 8, 0)
        assert end == datetime.datetime(2026, 1, 15, 9, 0)


class TestSessionEnd:
    def test_session_end_cest_summer(self):
        assert paris_session_end_utc(
            datetime.date(2026, 6, 2), EUMarket()
        ) == datetime.datetime(2026, 6, 2, 15, 30)

    def test_session_end_cet_winter(self):
        assert paris_session_end_utc(
            datetime.date(2026, 1, 15), EUMarket()
        ) == datetime.datetime(2026, 1, 15, 16, 30)


class TestTradableDateGuards:
    def test_is_future_paris_date(self):
        now = datetime.datetime(2026, 6, 2, 10, 0, tzinfo=PARIS_TZ)
        assert is_future_paris_date(datetime.date(2026, 6, 3), now=now)
        assert not is_future_paris_date(datetime.date(2026, 6, 2), now=now)
        assert not is_future_paris_date(datetime.date(2026, 6, 1), now=now)

    def test_today_before_session_close_is_not_yet_closed(self):
        now = datetime.datetime(2026, 6, 2, 10, 0, tzinfo=PARIS_TZ)
        assert is_today_not_yet_closed(
            datetime.date(2026, 6, 2), EUMarket(), now=now
        )

    def test_today_after_session_close_is_closed(self):
        now = datetime.datetime(2026, 6, 2, 18, 0, tzinfo=PARIS_TZ)
        assert not is_today_not_yet_closed(
            datetime.date(2026, 6, 2), EUMarket(), now=now
        )

    def test_other_day_is_never_not_yet_closed(self):
        now = datetime.datetime(2026, 6, 2, 10, 0, tzinfo=PARIS_TZ)
        assert not is_today_not_yet_closed(
            datetime.date(2026, 6, 1), EUMarket(), now=now
        )
        assert not is_today_not_yet_closed(
            datetime.date(2026, 6, 3), EUMarket(), now=now
        )


class TestEuCfdMarketSession:
    """The impulsive-candle variant trades the 9:00-22:00 CFD session
    (FR-G12), so only the session end moves - the 9h reference window is
    identical because EuCfdMarket also opens at 9:00."""

    def test_reference_window_is_unchanged_summer(self):
        start, end = paris_reference_window_utc(
            datetime.date(2026, 6, 2), EuCfdMarket()
        )
        assert start == datetime.datetime(2026, 6, 2, 7, 0)
        assert end == datetime.datetime(2026, 6, 2, 8, 0)

    def test_reference_window_is_unchanged_winter(self):
        start, end = paris_reference_window_utc(
            datetime.date(2026, 1, 15), EuCfdMarket()
        )
        assert start == datetime.datetime(2026, 1, 15, 8, 0)
        assert end == datetime.datetime(2026, 1, 15, 9, 0)

    def test_session_ends_at_22h_paris_summer(self):
        assert paris_session_end_utc(
            datetime.date(2026, 6, 2), EuCfdMarket()
        ) == datetime.datetime(2026, 6, 2, 20, 0)

    def test_session_ends_at_22h_paris_winter(self):
        assert paris_session_end_utc(
            datetime.date(2026, 1, 15), EuCfdMarket()
        ) == datetime.datetime(2026, 1, 15, 21, 0)

    def test_today_is_still_open_after_the_cash_close(self):
        """18:00 Paris: the Euronext session has ended but the CFD session
        has not, so a CFD-market day is not yet queryable."""
        now = datetime.datetime(2026, 6, 2, 18, 0, tzinfo=PARIS_TZ)
        day = datetime.date(2026, 6, 2)
        assert not is_today_not_yet_closed(day, EUMarket(), now=now)
        assert is_today_not_yet_closed(day, EuCfdMarket(), now=now)

    def test_today_is_closed_after_22h(self):
        now = datetime.datetime(2026, 6, 2, 22, 30, tzinfo=PARIS_TZ)
        assert not is_today_not_yet_closed(
            datetime.date(2026, 6, 2), EuCfdMarket(), now=now
        )


class TestSessionKey:
    """session_key identifies the window a day's candles are fetched over
    - the part of the raw-candle cache key that is not the instrument."""

    def test_cash_session(self):
        assert session_key(EUMarket()) == "0900-1730"

    def test_cfd_session(self):
        assert session_key(EuCfdMarket()) == "0900-2200"

    def test_sessions_with_different_ends_do_not_collide(self):
        assert session_key(EUMarket()) != session_key(EuCfdMarket())
