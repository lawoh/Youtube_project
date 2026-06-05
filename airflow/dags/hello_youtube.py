"""DAG de test : sert uniquement à vérifier qu'Airflow détecte et exécute
les DAG déposés dans le dossier dags/. On le supprimera ensuite.

Syntaxe Airflow 3 (Task SDK) : imports depuis airflow.sdk.
"""
import pendulum
from airflow.sdk import dag, task


@dag(
    schedule=None,  # pas de calendrier : déclenchement manuel pour ce test
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    tags=["test"],
)
def hello_youtube():
    @task
    def say_hello():
        print("Airflow détecte et exécute bien mon DAG !")
        return "ok"

    say_hello()


hello_youtube()