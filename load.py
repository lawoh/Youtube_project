"""Chargement des données extraites dans PostgreSQL (pilote psycopg v3).

Lit les derniers fichiers JSON de ./data, applique un garde-fou qualité,
puis charge en base dans le bon ordre :
  1. dim_video        -> upsert sur video_id (rafraîchit les attributs)
  2. fact_video_stats -> insert idempotent (anti-doublon video_id + snapshot_date)
  3. video_topic      -> insert idempotent

Le tout dans UNE transaction : en cas d'erreur, rollback complet.

Usage : python load.py
"""
import glob
import json
import logging
import sys
from pathlib import Path

import psycopg

from config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER
from logging_config import setup_logging
from quality import run_all_checks

logger = logging.getLogger(__name__)


def get_connection():
    """Ouvre une connexion vers Postgres (paramètres lus dans config/.env)."""
    return psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def _load_latest(pattern: str) -> list:
    files = sorted(glob.glob(str(Path("data") / pattern)))
    if not files:
        sys.exit(f"Aucun fichier trouvé pour le motif : {pattern}")
    return json.loads(Path(files[-1]).read_text(encoding="utf-8"))


def fetch_known_video_ids(conn) -> list:
    """Renvoie tous les video_id déjà présents en base (pour le snapshot quotidien)."""
    with conn.cursor() as cur:
        cur.execute("SELECT video_id FROM dim_video;")
        return [row[0] for row in cur.fetchall()]


def upsert_dim(conn, dim_rows: list) -> None:
    """Insère ou met à jour la dimension. La clé est video_id."""
    sql = """
        INSERT INTO dim_video (
            video_id, title, channel_id, channel_title, published_at,
            category_id, duration_sec, definition, default_language, region, tags
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (video_id) DO UPDATE SET
            title            = EXCLUDED.title,
            channel_title    = EXCLUDED.channel_title,
            duration_sec     = EXCLUDED.duration_sec,
            definition       = EXCLUDED.definition,
            default_language = EXCLUDED.default_language,
            tags             = EXCLUDED.tags;
    """
    values = [
        (
            r["video_id"], r["title"], r["channel_id"], r["channel_title"],
            r["published_at"], r["category_id"], r["duration_sec"],
            r["definition"], r["default_language"], r["region"], r["tags"],
        )
        for r in dim_rows
    ]
    with conn.cursor() as cur:
        cur.executemany(sql, values)
    logger.info("dim_video : %d lignes upsert", len(values))


def insert_facts(conn, fact_rows: list) -> None:
    """Insère les métriques du jour. Les doublons (même jour) sont ignorés."""
    sql = """
        INSERT INTO fact_video_stats
            (video_id, snapshot_date, view_count, like_count, comment_count)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (video_id, snapshot_date) DO NOTHING;
    """
    values = [
        (
            r["video_id"], r["snapshot_date"],
            r["view_count"], r["like_count"], r["comment_count"],
        )
        for r in fact_rows
    ]
    with conn.cursor() as cur:
        cur.executemany(sql, values)
    logger.info("fact_video_stats : %d lignes proposées (doublons ignorés)", len(values))


def upsert_topics(conn, topic_rows: list) -> None:
    """Insère les liaisons vidéo-topic, sans doublon."""
    sql = """
        INSERT INTO video_topic (video_id, topic)
        VALUES (%s, %s)
        ON CONFLICT (video_id, topic) DO NOTHING;
    """
    values = [(r["video_id"], r["topic"]) for r in topic_rows]
    with conn.cursor() as cur:
        cur.executemany(sql, values)
    logger.info("video_topic : %d lignes proposées", len(values))


def main() -> None:
    setup_logging()
    dim_rows = _load_latest("dim_video_*.json")
    fact_rows = _load_latest("fact_stats_*.json")
    topic_rows = _load_latest("video_topic_*.json")

    # Garde-fou : on ne charge JAMAIS des données qui échouent aux contrôles.
    errors = run_all_checks(dim_rows, fact_rows, topic_rows)
    if errors:
        logger.error("Chargement annulé : %d anomalie(s) qualité.", len(errors))
        for err in errors[:10]:
            logger.error("  - %s", err)
        sys.exit(1)

    conn = get_connection()
    try:
        upsert_dim(conn, dim_rows)        # la dimension d'abord (cible des FK)
        insert_facts(conn, fact_rows)
        upsert_topics(conn, topic_rows)
        conn.commit()
        logger.info("Chargement terminé et committé.")
    except Exception:
        conn.rollback()
        logger.exception("Erreur pendant le chargement -> rollback.")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
