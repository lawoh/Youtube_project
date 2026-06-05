"""DAG SNAPSHOT (quotidien).

Ne cherche RIEN de nouveau : il relit les vidéos déjà connues en base
et enregistre leurs métriques du jour. Quasi gratuit en quota
(videos.list = 1 unité pour 50 vidéos). C'est lui qui construit l'historique.

Calendrier : tous les jours à 06h00 UTC.
"""
import pendulum
from airflow.sdk import dag, task


@dag(
    schedule="0 6 * * *",  # tous les jours à 06h00
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    tags=["youtube", "snapshot"],
)
def youtube_snapshot():

    @task
    def get_known_ids() -> list:
        from load import get_connection, fetch_known_video_ids

        conn = get_connection()
        try:
            ids = fetch_known_video_ids(conn)
        finally:
            conn.close()
        print(f"{len(ids)} vidéos connues à re-mesurer")
        return ids

    @task
    def snapshot(video_ids: list) -> list:
        from youtube_client import get_client, fetch_video_details
        from transform import build_fact_rows

        youtube = get_client()
        items = fetch_video_details(youtube, video_ids)
        fact_rows = build_fact_rows(items)
        print(f"{len(fact_rows)} mesures collectées")
        return fact_rows

    @task
    def quality_check(fact_rows: list) -> list:
        # On réutilise les contrôles ciblés adaptés aux métriques seules
        from quality import (
            check_no_duplicate_snapshots,
            check_non_negative_counts,
            check_view_count_present,
        )

        errors = (
            check_view_count_present(fact_rows)
            + check_non_negative_counts(fact_rows)
            + check_no_duplicate_snapshots(fact_rows)
        )
        if errors:
            for err in errors[:10]:
                print("ANOMALIE:", err)
            raise ValueError(f"{len(errors)} anomalie(s) — snapshot bloqué")
        print("Qualité OK")
        return fact_rows

    @task
    def load(fact_rows: list) -> None:
        from load import get_connection, insert_facts

        conn = get_connection()
        try:
            insert_facts(conn, fact_rows)
            conn.commit()
            print("Snapshot du jour chargé.")
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    load(quality_check(snapshot(get_known_ids())))


youtube_snapshot()
