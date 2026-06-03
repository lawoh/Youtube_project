"""Applique les contrôles qualité sur les derniers fichiers JSON produits.

Usage : python validate_data.py
Sort en code 1 si des anomalies sont trouvées (utile en CI / Airflow).
"""
import glob
import json
import sys
from pathlib import Path

from quality import run_all_checks


def _load_latest(pattern: str) -> list:
    files = sorted(glob.glob(str(Path("data") / pattern)))
    if not files:
        sys.exit(f"Aucun fichier trouvé pour le motif : {pattern}")
    return json.loads(Path(files[-1]).read_text(encoding="utf-8"))


def main() -> None:
    dim_rows = _load_latest("dim_video_*.json")
    fact_rows = _load_latest("fact_stats_*.json")
    topic_rows = _load_latest("video_topic_*.json")

    print(f"dim={len(dim_rows)}  fact={len(fact_rows)}  topic={len(topic_rows)}")
    errors = run_all_checks(dim_rows, fact_rows, topic_rows)

    if errors:
        print(f"\n❌ {len(errors)} anomalie(s) détectée(s) :")
        for err in errors[:20]:
            print(f"  - {err}")
        if len(errors) > 20:
            print(f"  ... et {len(errors) - 20} autres")
        sys.exit(1)

    print("\n✅ Aucune anomalie. Données prêtes pour le chargement.")


if __name__ == "__main__":
    main()
