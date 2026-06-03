"""Contrôles de qualité des données.

Chaque fonction prend des lignes et renvoie une LISTE de messages d'anomalie
(liste vide = tout va bien). Ce module est volontairement sans dépendance :
  - en test, on l'exécute sur des données factices (bonnes ET mauvaises) ;
  - dans le pipeline (Airflow), une tâche appellera run_all_checks() sur les
    vraies données et fera échouer le DAG si la liste n'est pas vide.

Règles métier retenues :
  - view_count est OBLIGATOIRE (toute vidéo publique a un nombre de vues).
  - like_count / comment_count peuvent être NULL (likes masqués, commentaires
    désactivés) -> tolérés.
  - duration_sec : None toléré (cas rares), mais jamais négatif.
"""
from typing import Dict, List, Set

ALLOWED_TOPICS = {"GEOMATIQUE", "IA", "DATA"}
COUNT_FIELDS = ("view_count", "like_count", "comment_count")


def check_required_fields(dim_rows: List[dict]) -> List[str]:
    """video_id et published_at doivent toujours être présents."""
    errors = []
    for row in dim_rows:
        if not row.get("video_id"):
            errors.append(f"video_id manquant dans une ligne dim: {row}")
        if not row.get("published_at"):
            errors.append(f"published_at manquant pour {row.get('video_id')}")
    return errors


def check_view_count_present(fact_rows: List[dict]) -> List[str]:
    """view_count ne doit jamais être NULL (sinon problème de cast en amont)."""
    return [
        f"view_count NULL pour {row['video_id']}"
        for row in fact_rows
        if row.get("view_count") is None
    ]


def check_non_negative_counts(fact_rows: List[dict]) -> List[str]:
    """Aucun compteur ne peut être négatif."""
    errors = []
    for row in fact_rows:
        for field in COUNT_FIELDS:
            value = row.get(field)
            if value is not None and value < 0:
                errors.append(f"{field} négatif ({value}) pour {row['video_id']}")
    return errors


def check_durations_non_negative(dim_rows: List[dict]) -> List[str]:
    """duration_sec, quand elle existe, ne peut pas être négative."""
    return [
        f"duration_sec négative ({row['duration_sec']}) pour {row['video_id']}"
        for row in dim_rows
        if row.get("duration_sec") is not None and row["duration_sec"] < 0
    ]


def check_no_duplicate_snapshots(fact_rows: List[dict]) -> List[str]:
    """Pas deux fois la même (video_id, snapshot_date) -> garantit l'historique propre."""
    seen: Set[tuple] = set()
    errors = []
    for row in fact_rows:
        key = (row["video_id"], row["snapshot_date"])
        if key in seen:
            errors.append(f"snapshot dupliqué: {key}")
        seen.add(key)
    return errors


def check_topics_valid(topic_rows: List[dict]) -> List[str]:
    """Tout topic doit appartenir à l'ensemble autorisé."""
    return [
        f"topic inconnu '{row['topic']}' pour {row['video_id']}"
        for row in topic_rows
        if row.get("topic") not in ALLOWED_TOPICS
    ]


def check_referential_integrity(
    dim_rows: List[dict], fact_rows: List[dict], topic_rows: List[dict]
) -> List[str]:
    """Tout video_id de fact/topic doit exister dans dim (pas d'orphelin)."""
    known_ids = {row["video_id"] for row in dim_rows}
    errors = []
    for row in fact_rows:
        if row["video_id"] not in known_ids:
            errors.append(f"fact orphelin: {row['video_id']} absent de dim_video")
    for row in topic_rows:
        if row["video_id"] not in known_ids:
            errors.append(f"topic orphelin: {row['video_id']} absent de dim_video")
    return errors


def run_all_checks(
    dim_rows: List[dict], fact_rows: List[dict], topic_rows: List[dict]
) -> List[str]:
    """Lance tous les contrôles et agrège les anomalies."""
    errors: List[str] = []
    errors += check_required_fields(dim_rows)
    errors += check_view_count_present(fact_rows)
    errors += check_non_negative_counts(fact_rows)
    errors += check_durations_non_negative(dim_rows)
    errors += check_no_duplicate_snapshots(fact_rows)
    errors += check_topics_valid(topic_rows)
    errors += check_referential_integrity(dim_rows, fact_rows, topic_rows)
    return errors
