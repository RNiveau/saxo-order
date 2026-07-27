import datetime

from fastapi import HTTPException


def parse_iso_date(value: str) -> datetime.date:
    """Parse a YYYY-MM-DD query parameter into a date.

    Raises a 400 HTTPException on an invalid format, so router handlers
    can call this directly without wrapping it themselves.
    """
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date, expected YYYY-MM-DD",
        )
