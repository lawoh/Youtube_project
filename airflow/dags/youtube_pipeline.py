"""DAG du pipeline YouTube : extraction -> contrôle qualité -> chargement.

Réutilise tes modules existants sans les modifier :
  - extract.discover_video_ids        (découverte des IDs)
  - youtube_client.fetch_video_details (détails des vidéos)
  - transform.build_records            (mise en forme dim / fact / topic)
  - quality.run_all_checks             (garde-fou qualité)
  - load.*                             (chargement Postgres)

Les données passent d'une tâche à l'autre via XCom (pas de fichiers intermédiaires).
Déclenchement manuel pour l'instant : un run consomme du quota API.
"""
import pendulum
from airflow.sdk import dag, task


@dag(
    schedule=None,  # manuel : on passera à un calendrier ensuite
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    tags=["youtube"],
)
def youtube_pipeline():

    @task
    def extract() -> dict:
        # Imports dans la tâche : la lecture du DAG reste légère et rapide
        from extract import discover_video_ids
        from youtube_client import get_client, fetch_video_details
        from transform import build_records

        youtube = get_client()
        video_topics = discover_video_ids(youtube)
        items = fetch_video_details(youtube, list(video_topics.keys()))
        dim_rows, fact_rows, topic_rows = build_records(items, video_topics)
        print(f"Extrait : {len(dim_rows)} vidéos")
        return {"dim": dim_rows, "fact": fact_rows, "topic": topic_rows}

    @task
    def quality_check(records: dict) -> dict:
        from quality import run_all_checks

        errors = run_all_checks(records["dim"], records["fact"], records["topic"])
        if errors:
            for err in errors[:10]:
                print("ANOMALIE:", err)
            # Lever une exception fait ÉCHOUER la tâche -> le chargement ne démarre pas
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
            print("Chargement terminé et committé.")
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # Le chaînage des appels crée automatiquement les dépendances :
    # extract -> quality_check -> load
    load(quality_check(extract()))


youtube_pipeline()
