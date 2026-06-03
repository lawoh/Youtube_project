"""Tests unitaires des fonctions pures de parsers.py."""
import pytest

from parsers import iso8601_duration_to_seconds, to_int


@pytest.mark.parametrize(
    "duration, expected",
    [
        ("PT4M13S", 253),
        ("PT1H2M3S", 3723),
        ("PT45S", 45),
        ("PT1H", 3600),
        ("P1DT2H", 93600),   # 1 jour + 2 heures (longs lives)
        ("PT0S", 0),
    ],
)
def test_duration_valide(duration, expected):
    assert iso8601_duration_to_seconds(duration) == expected


@pytest.mark.parametrize("duration", [None, "", "abc", "12345"])
def test_duration_invalide_renvoie_none(duration):
    assert iso8601_duration_to_seconds(duration) is None


@pytest.mark.parametrize(
    "value, expected",
    [
        ("15000", 15000),
        ("0", 0),
        (42, 42),
        (None, None),
        ("abc", None),
        ("", None),
    ],
)
def test_to_int(value, expected):
    assert to_int(value) == expected
