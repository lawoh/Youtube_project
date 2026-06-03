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
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List, Set, Tuple

from config import (
    MAX_RESULTS_PER_QUERY,
    PUBLISHED_WINDOWS,
    REGION_CODE,
    RELEVANCE_LANGUAGE,
    SEARCH_QUERIES,
)
from parsers import iso8601_duration_to_seconds, to_int
from youtube_client import fetch_video_details, get_client, search_videos

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
            print(f"[search] '{query}' ({topic}, {window_label}) -> {len(ids)} vidéos")
            for video_id in ids:
                video_topics.setdefault(video_id, set()).add(topic)

    return video_topics


def build_records(
    items: List[dict], video_topics: Dict[str, Set[str]]
) -> Tuple[List[dict], List[dict], List[dict]]:
    """Transforme les ressources videos.list en lignes dim / fact / liaison."""
    snapshot_day = date.today().isoformat()
    dim_rows, fact_rows, topic_rows = [], [], []

    for item in items:
        video_id = item["id"]
        snippet = item.get("snippet", {})
        content = item.get("contentDetails", {})
        stats = item.get("statistics", {})

        dim_rows.append(
            {
                "video_id": video_id,
                "title": snippet.get("title"),
                "channel_id": snippet.get("channelId"),
                "channel_title": snippet.get("channelTitle"),
                "published_at": snippet.get("publishedAt"),
                "category_id": snippet.get("categoryId"),
                "duration_sec": iso8601_duration_to_seconds(content.get("duration")),
                "definition": content.get("definition"),
                "default_language": (
                    snippet.get("defaultAudioLanguage")
                    or snippet.get("defaultLanguage")
                ),
                "region": REGION_CODE,
                "tags": snippet.get("tags", []),
            }
        )
        fact_rows.append(
            {
                "video_id": video_id,
                "snapshot_date": snapshot_day,
                "view_count": to_int(stats.get("viewCount")),
                "like_count": to_int(stats.get("likeCount")),
                "comment_count": to_int(stats.get("commentCount")),
            }
        )
        for topic in sorted(video_topics.get(video_id, [])):
            topic_rows.append({"video_id": video_id, "topic": topic})

    return dim_rows, fact_rows, topic_rows


def _write_json(rows: List[dict], filename: str) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / filename
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  -> {len(rows)} lignes écrites dans {path}")


def main() -> None:
    youtube = get_client()

    print("=== Flux découverte ===")
    video_topics = discover_video_ids(youtube)
    print(f"Total vidéos uniques découvertes : {len(video_topics)}\n")

    print("=== Flux enrichissement + snapshot ===")
    items = fetch_video_details(youtube, list(video_topics.keys()))
    print(f"Détails récupérés : {len(items)}\n")

    dim_rows, fact_rows, topic_rows = build_records(items, video_topics)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    print("=== Écriture ===")
    _write_json(dim_rows, f"dim_video_{stamp}.json")
    _write_json(fact_rows, f"fact_stats_{stamp}.json")
    _write_json(topic_rows, f"video_topic_{stamp}.json")


if __name__ == "__main__":
    main()
