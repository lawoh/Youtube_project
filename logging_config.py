"""Configuration centralisée du logging pour tout le pipeline.

Appeler setup_logging() une fois au démarrage d'un script d'entrée
(extract.py, validate_data.py...). Les modules, eux, se contentent de :

    import logging
    logger = logging.getLogger(__name__)

Le niveau se règle via la variable d'environnement LOG_LEVEL (défaut : INFO).
Sortie en double : console + fichier rotatif logs/pipeline.log.
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path("logs")
LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: str = None) -> None:
    """Configure le logger racine. Idempotent (ne double pas les handlers)."""
    level = (level or os.environ.get("LOG_LEVEL", "INFO")).upper()

    root = logging.getLogger()
    if root.handlers:  # déjà configuré (ex : relance dans le même process)
        return
    root.setLevel(level)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # Handler console
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    # Handler fichier rotatif (1 Mo x 3 sauvegardes)
    LOG_DIR.mkdir(exist_ok=True)
    file_handler = RotatingFileHandler(
        LOG_DIR / "pipeline.log",
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
