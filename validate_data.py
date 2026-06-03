"""Applique les contrôles qualité sur les derniers fichiers JSON produits.

Usage : python validate_data.py
Sort en code 1 si des anomalies sont trouvées (utile en CI / Airflow).
"""
import glob
import json
import logging
import sys
from pathlib import Path

from logging_config import setup_logging
from quality import run_all_checks

logger = logging.getLogger(__name__)


def _load_latest(pattern: str) -> list:
    files = sorted(glob.glob(str(Path("data") / pattern)))
    if not files:
        sys.exit(f"Aucun fichier trouvé pour le motif : {pattern}")
    return json.loads(Path(files[-1]).read_text(encoding="utf-8"))


def main() -> None:
    setup_logging()
    dim_rows = _load_latest("dim_video_*.json")
    fact_rows = _load_latest("fact_stats_*.json")
    topic_rows = _load_latest("video_topic_*.json")

    logger.info("dim=%d  fact=%d  topic=%d", len(dim_rows), len(fact_rows), len(topic_rows))
    errors = run_all_checks(dim_rows, fact_rows, topic_rows)

    if errors:
        logger.error("%d anomalie(s) détectée(s) :", len(errors))
        for err in errors[:20]:
            logger.error("  - %s", err)
        if len(errors) > 20:
            logger.error("  ... et %d autres", len(errors) - 20)
        sys.exit(1)

    logger.info("Aucune anomalie. Données prêtes pour le chargement.")


if __name__ == "__main__":
    main()
