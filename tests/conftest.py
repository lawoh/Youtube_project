"""Fixtures partagées par les tests.

On simule ici une réponse de videos.list (deux vidéos) pour tester la chaîne
de transformation et les contrôles qualité SANS appeler l'API.
"""
import pytest

from transform import build_records


@pytest.fixture
def sample_items():
    """Deux ressources vidéo telles que renvoyées par l'API (forme brute)."""
    return [
        {
            "id": "vid001",
            "snippet": {
                "title": "Introduction aux SIG",
                "channelId": "chan_geo",
                "channelTitle": "GeoChannel",
                "publishedAt": "2019-05-01T10:00:00Z",
                "categoryId": "27",
                "defaultAudioLanguage": "fr",
                "tags": ["sig", "qgis"],
            },
            "contentDetails": {"duration": "PT10M5S", "definition": "hd"},
            "statistics": {
                "viewCount": "15000",
                "likeCount": "300",
                "commentCount": "42",
            },
        },
        {
            "id": "vid002",
            "snippet": {
                "title": "L'IA en 2023",
                "channelId": "chan_ia",
                "channelTitle": "AI Channel",
                "publishedAt": "2023-02-15T08:00:00Z",
                "categoryId": "28",
                "defaultLanguage": "en",
                "tags": [],
            },
            "contentDetails": {"duration": "PT1H2M", "definition": "hd"},
            # likeCount volontairement ABSENT (likes masqués par le créateur)
            "statistics": {"viewCount": "500000", "commentCount": "0"},
        },
    ]


@pytest.fixture
def sample_video_topics():
    return {"vid001": {"GEOMATIQUE"}, "vid002": {"IA"}}


@pytest.fixture
def good_records(sample_items, sample_video_topics):
    """Les trois jeux de lignes issus d'une transformation correcte."""
    return build_records(sample_items, sample_video_topics)
