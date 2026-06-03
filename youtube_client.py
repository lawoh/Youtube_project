"""Wrapper minimal autour de l'API YouTube Data v3.

Deux opérations seulement :
  - search_videos    : DÉCOUVERTE, trouve des IDs par mot-clé (coûteux : 100 unités/appel)
  - fetch_video_details : ENRICHISSEMENT + SNAPSHOT, détails par lot de 50 IDs (1 unité/appel)
"""
from typing import List, Optional

from googleapiclient.discovery import build

from config import API_KEY


def get_client():
    """Construit le client YouTube. Lève une erreur claire si la clé manque."""
    if not API_KEY:
        raise RuntimeError(
            "YOUTUBE_API_KEY absente. Définis-la avant de lancer le script."
        )
    return build("youtube", "v3", developerKey=API_KEY)


def search_videos(
    youtube,
    query: str,
    max_results: int = 100,
    region_code: Optional[str] = None,
    relevance_language: Optional[str] = None,
    published_after: Optional[str] = None,
    published_before: Optional[str] = None,
) -> List[str]:
    """Renvoie une liste d'IDs de vidéos correspondant à la requête.

    Pagine via nextPageToken jusqu'à max_results (l'API plafonne vers ~500).
    """
    video_ids: List[str] = []
    page_token = None

    while len(video_ids) < max_results:
        params = {
            "part": "id",
            "q": query,
            "type": "video",
            "maxResults": min(50, max_results - len(video_ids)),
            "order": "relevance",
        }
        # On n'ajoute les paramètres optionnels que s'ils sont définis,
        # sinon le client envoie "None" et l'API renvoie une erreur.
        if region_code:
            params["regionCode"] = region_code
        if relevance_language:
            params["relevanceLanguage"] = relevance_language
        if published_after:
            params["publishedAfter"] = published_after
        if published_before:
            params["publishedBefore"] = published_before
        if page_token:
            params["pageToken"] = page_token

        response = youtube.search().list(**params).execute()

        for item in response.get("items", []):
            video_id = item.get("id", {}).get("videoId")
            if video_id:
                video_ids.append(video_id)

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return video_ids


def fetch_video_details(youtube, video_ids: List[str]) -> List[dict]:
    """Renvoie les ressources complètes (snippet + contentDetails + statistics).

    videos.list accepte jusqu'à 50 IDs par appel -> on découpe en lots.
    """
    results: List[dict] = []
    for start in range(0, len(video_ids), 50):
        batch = video_ids[start : start + 50]
        response = (
            youtube.videos()
            .list(part="snippet,contentDetails,statistics", id=",".join(batch))
            .execute()
        )
        results.extend(response.get("items", []))
    return results
