"""Transformation des ressources brutes de l'API en lignes prêtes à charger.

Ce module ne dépend NI du réseau NI de la librairie Google : il prend en entrée
des dictionnaires (la réponse videos.list) et renvoie des lignes. C'est ce qui
le rend testable avec de simples données factices.
"""
from datetime import date
from typing import Dict, List, Set, Tuple

from config import REGION_CODE
from parsers import iso8601_duration_to_seconds, to_int


def build_fact_rows(items: List[dict]) -> List[dict]:
    """Construit UNIQUEMENT les lignes de métriques (pour le snapshot quotidien).

    Pas besoin de dimension ni de topic ici : on relit des vidéos déjà connues
    et on n'enregistre que leurs compteurs du jour.
    """
    snapshot_day = date.today().isoformat()
    fact_rows = []
    for item in items:
        stats = item.get("statistics", {})
        fact_rows.append(
            {
                "video_id": item["id"],
                "snapshot_date": snapshot_day,
                "view_count": to_int(stats.get("viewCount")),
                "like_count": to_int(stats.get("likeCount")),
                "comment_count": to_int(stats.get("commentCount")),
            }
        )
    return fact_rows


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
