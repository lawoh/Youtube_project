"""Fonctions de transformation des champs bruts renvoyés par l'API."""
import re
from typing import Optional

# Les durées YouTube sont au format ISO 8601, ex : "PT4M13S", "PT1H2M", "P1DT2H".
_DURATION_RE = re.compile(
    r"P(?:(?P<days>\d+)D)?T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?"
)


def iso8601_duration_to_seconds(duration: Optional[str]) -> Optional[int]:
    """Convertit une durée ISO 8601 en secondes. None si non parsable."""
    if not duration:
        return None
    match = _DURATION_RE.fullmatch(duration)
    if not match:
        return None
    parts = {key: int(value) for key, value in match.groupdict(default="0").items()}
    return (
        parts["days"] * 86400
        + parts["hours"] * 3600
        + parts["minutes"] * 60
        + parts["seconds"]
    )


def to_int(value) -> Optional[int]:
    """Cast une valeur (souvent une string renvoyée par l'API) en int. None si impossible.

    L'API renvoie viewCount, likeCount, etc. en STRING -> il faut les caster.
    likeCount peut être absent si le créateur masque les likes -> None.
    """
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
