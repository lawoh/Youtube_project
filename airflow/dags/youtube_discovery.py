"""DAG DÉCOUVERTE (hebdomadaire).

Cherche de nouvelles vidéos via search.list (coûteux en quota -> rare),
récupère leurs détails, et alimente dim_video + video_topic + un premier
snapshot de métriques.

Calendrier : tous les lundis à 03h00 UTC.
"""
import pendulum
from airflow.sdk import dag, task


@dag(
    schedule="0 3 * * 1",  # cron : minute heure jour mois jour_semaine (lundi=1)
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    tags=["youtube", "decouverte"],
)
def youtube_discovery():

    @task
    def extract() -> dict:
        from extract import discover_video_ids
        from youtube_client import get_client, fetch_video_details
        from transform import build_records

        youtube = get_client()
        video_topics = discover_video_ids(youtube)
        items = fetch_video_details(youtube, list(video_topics.keys()))
        dim_rows, fact_rows, topic_rows = build_records(items, video_topics)
        print(f"Découvert : {len(dim_rows)} vidéos")
        return {"dim": dim_rows, "fact": fact_rows, "topic": topic_rows}

    @task
    def quality_check(records: dict) -> dict:
        from quality import run_all_checks

        errors = run_all_checks(records["dim"], records["fact"], records["topic"])
        if errors:
            for err in errors[:10]:
                print("ANOMALIE:", err)
            raise ValueError(f"{len(errors)} anomalie(s) qualité — chargement bloqué")
        print("Qualité OK")
        return records

    @task
    def load(records: dict) -> None:
        from load import get_connection, insert_facts, upsert_dim, upsert_topics

        conn = get_connection()
        try:
            upsert_dim(conn, records["dim"])
            insert_facts(conn, records["fact"])
            upsert_topics(conn, records["topic"])
            conn.commit()
            print("Découverte chargée et committée.")
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    load(quality_check(extract()))


youtube_discovery()
