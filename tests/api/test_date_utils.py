import datetime

import pytest
from fastapi import HTTPException

from api.date_utils import parse_iso_date


class TestParseIsoDate:
    def test_valid_date_is_parsed(self):
        assert parse_iso_date("2026-06-02") == datetime.date(2026, 6, 2)

    def test_invalid_format_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            parse_iso_date("02/06/2026")
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Invalid date, expected YYYY-MM-DD"

    def test_empty_string_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            parse_iso_date("")
        assert exc_info.value.status_code == 400
