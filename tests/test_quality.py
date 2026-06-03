"""Tests des contrôles de quality.py.

On vérifie deux choses :
  1. les données saines passent tous les contrôles (liste d'anomalies vide) ;
  2. chaque contrôle DÉTECTE bien le défaut qu'il est censé attraper.
"""
from quality import (
    check_no_duplicate_snapshots,
    check_non_negative_counts,
    check_referential_integrity,
    check_topics_valid,
    check_view_count_present,
    run_all_checks,
)


def test_donnees_saines_passent(good_records):
    dim_rows, fact_rows, topic_rows = good_records
    assert run_all_checks(dim_rows, fact_rows, topic_rows) == []


def test_detecte_view_count_manquant():
    fact_rows = [{"video_id": "v1", "snapshot_date": "2026-06-03", "view_count": None}]
    erreurs = check_view_count_present(fact_rows)
    assert len(erreurs) == 1
    assert "v1" in erreurs[0]


def test_detecte_compteur_negatif():
    fact_rows = [
        {
            "video_id": "v1",
            "snapshot_date": "2026-06-03",
            "view_count": 10,
            "like_count": -5,
            "comment_count": 0,
        }
    ]
    erreurs = check_non_negative_counts(fact_rows)
    assert len(erreurs) == 1
    assert "like_count" in erreurs[0]


def test_detecte_snapshot_duplique():
    fact_rows = [
        {"video_id": "v1", "snapshot_date": "2026-06-03", "view_count": 1},
        {"video_id": "v1", "snapshot_date": "2026-06-03", "view_count": 1},
    ]
    erreurs = check_no_duplicate_snapshots(fact_rows)
    assert len(erreurs) == 1


def test_detecte_topic_inconnu():
    topic_rows = [{"video_id": "v1", "topic": "BLOCKCHAIN"}]
    erreurs = check_topics_valid(topic_rows)
    assert len(erreurs) == 1
    assert "BLOCKCHAIN" in erreurs[0]


def test_detecte_orphelin():
    dim_rows = [{"video_id": "v1", "published_at": "2020-01-01T00:00:00Z"}]
    fact_rows = [{"video_id": "v_inconnu", "snapshot_date": "2026-06-03", "view_count": 1}]
    erreurs = check_referential_integrity(dim_rows, fact_rows, topic_rows=[])
    assert len(erreurs) == 1
    assert "v_inconnu" in erreurs[0]
