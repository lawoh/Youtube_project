"""Point d'entrée de l'extraction.

Orchestration des deux flux :
  1. DÉCOUVERTE  -> ensemble {video_id: {topics}} via search.list
  2. ENRICHISSEMENT + SNAPSHOT -> détails via videos.list

Sortie pour l'instant : 3 fichiers JSON dans ./data
  - dim_video_<date>.json    (dimension : attributs stables)
  - fact_stats_<date>.json   (faits : métriques du jour)
  - video_topic_<date>.json  (liaison : un (video_id, topic) par appartenance)

Plus tard, l'écriture JSON sera remplacée par un chargement dans PostgreSQL,
et chaque fonction deviendra une tâche Airflow.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set

from config import (
    MAX_RESULTS_PER_QUERY,
    PUBLISHED_WINDOWS,
    REGION_CODE,
    RELEVANCE_LANGUAGE,
    SEARCH_QUERIES,
)
from logging_config import setup_logging
from transform import build_records
from youtube_client import fetch_video_details, get_client, search_videos

logger = logging.getLogger(__name__)
OUTPUT_DIR = Path("data")


def discover_video_ids(youtube) -> Dict[str, Set[str]]:
    """Flux DÉCOUVERTE : boucle sur (requête x fenêtre temporelle).

    Renvoie {video_id: {topics}} pour gérer le multi-appartenance
    (une vidéo peut remonter sur 'IA' et 'DATA').
    """
    video_topics: Dict[str, Set[str]] = {}

    for query, topic in SEARCH_QUERIES:
        for published_after, published_before in PUBLISHED_WINDOWS:
            ids = search_videos(
                youtube,
                query,
                max_results=MAX_RESULTS_PER_QUERY,
                region_code=REGION_CODE,
                relevance_language=RELEVANCE_LANGUAGE,
                published_after=published_after,
                published_before=published_before,
            )
            window_label = "avant-2022" if published_before else "après-2022"
            logger.info("[search] '%s' (%s, %s) -> %d vidéos", query, topic, window_label, len(ids))
            for video_id in ids:
                video_topics.setdefault(video_id, set()).add(topic)

    return video_topics


def _write_json(rows: List[dict], filename: str) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / filename
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("%d lignes écrites dans %s", len(rows), path)


def main() -> None:
    setup_logging()
    youtube = get_client()

    logger.info("=== Flux découverte ===")
    video_topics = discover_video_ids(youtube)
    logger.info("Total vidéos uniques découvertes : %d", len(video_topics))

    logger.info("=== Flux enrichissement + snapshot ===")
    items = fetch_video_details(youtube, list(video_topics.keys()))
    logger.info("Détails récupérés : %d", len(items))

    dim_rows, fact_rows, topic_rows = build_records(items, video_topics)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    logger.info("=== Écriture ===")
    _write_json(dim_rows, f"dim_video_{stamp}.json")
    _write_json(fact_rows, f"fact_stats_{stamp}.json")
    _write_json(topic_rows, f"video_topic_{stamp}.json")


if __name__ == "__main__":
    main()
