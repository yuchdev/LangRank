from __future__ import annotations

from datetime import date

import pytest

from langrank.cli import _parse_date
from langrank.errors import LangRankError


@pytest.mark.parametrize(
    ("value", "is_end", "expected"),
    [
        ("2024", False, date(2024, 1, 1)),
        ("2024", True, date(2024, 12, 31)),
        ("2025-07", False, date(2025, 7, 1)),
        ("2025-07", True, date(2025, 7, 31)),
        ("2024-02", True, date(2024, 2, 29)),
        ("2025-03-15", False, date(2025, 3, 15)),
    ],
)
def test_parse_date_accepts_year_month_and_day(value: str, is_end: bool, expected: date) -> None:
    assert _parse_date(value, is_end=is_end) == expected


def test_parse_date_none_passes_through() -> None:
    assert _parse_date(None) is None


@pytest.mark.parametrize("value", ["2025-13", "25-07", "July 2025", "2025-07-32"])
def test_parse_date_rejects_malformed(value: str) -> None:
    with pytest.raises(LangRankError, match="expected YYYY, YYYY-MM or YYYY-MM-DD"):
        _parse_date(value)
