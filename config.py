"""Configuration centrale du pipeline d'extraction YouTube."""
import os

from dotenv import load_dotenv

# Charge les variables définies dans le fichier .env (à la racine du projet).
# Ne fait rien si le fichier est absent : on retombe sur l'environnement système.
load_dotenv()

# Clé API lue depuis l'environnement (ne JAMAIS la mettre en dur dans le code).
API_KEY = os.environ.get("YOUTUBE_API_KEY")

# Requêtes de découverte : (terme recherché, topic attribué).
# Plusieurs termes peuvent pointer vers le même topic (FR + EN pour couvrir le monde).
SEARCH_QUERIES = [
    ("SIG système information géographique", "GEOMATIQUE"),
    ("GIS geographic information system",    "GEOMATIQUE"),
    ("géomatique",                            "GEOMATIQUE"),
    ("intelligence artificielle",             "IA"),
    ("artificial intelligence",               "IA"),
    ("machine learning",                      "IA"),
    ("data engineering",                      "DATA"),
    ("data science",                          "DATA"),
]

# Fenêtres de publication (RFC 3339, UTC) pour équilibrer avant/après ChatGPT.
# Une recherche par fenêtre force l'API à exposer aussi les vieilles vidéos.
# Format : (published_after, published_before). None = pas de borne.
PUBLISHED_WINDOWS = [
    ("2015-01-01T00:00:00Z", "2022-11-29T23:59:59Z"),  # avant le lancement de ChatGPT
    ("2022-11-30T00:00:00Z", None),                    # après
]

# Portée géographique : None = monde entier (ton objectif).
REGION_CODE = None
RELEVANCE_LANGUAGE = None

# Nombre max de vidéos par (requête x fenêtre). L'API plafonne de toute façon ~500.
# Attention au quota : chaque page de 50 = 1 appel search = 100 unités.
MAX_RESULTS_PER_QUERY = 100