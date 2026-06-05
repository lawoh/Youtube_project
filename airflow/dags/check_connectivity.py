"""DAG de test de connectivité.

Valide deux choses avant de déployer le vrai pipeline :
  1. Airflow peut importer tes modules (dépendances installées + PYTHONPATH).
  2. Airflow peut se connecter à ton youtube_db via host.docker.internal:5433.

À supprimer une fois le vrai pipeline en place.
"""
import pendulum
from airflow.sdk import dag, task


@dag(
    schedule=None,  # déclenchement manuel
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    tags=["test"],
)
def check_connectivity():
    @task
    def check_imports():
        # Imports faits DANS la tâche : la lecture du DAG reste légère
        import config

        print("Clé API présente :", bool(config.API_KEY))
        print("DB_HOST :", config.DB_HOST, "| DB_PORT :", config.DB_PORT)
        return "imports ok"

    @task
    def check_db():
        from load import get_connection

        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM dim_video;")
                count = cur.fetchone()[0]
        finally:
            conn.close()
        print(f"Connexion réussie — dim_video contient {count} lignes")
        return count

    check_imports() >> check_db()


check_connectivity()
