"""Dashboard Streamlit du projet YouTube — charte blanc / vert / bleu.

Trois onglets : vue d'ensemble, analyse par chaîne, analyse par vidéo.

Lancement (depuis la RACINE du projet, environnement activé) :
    pip install streamlit pandas plotly
    streamlit run dashboard.py
"""
import pandas as pd
import plotly.express as px
import streamlit as st

from load import get_connection

CHATGPT = pd.Timestamp("2022-11-30", tz="UTC")
ORDRE_PERIODE = ["Avant ChatGPT", "Après ChatGPT"]

# Charte YouTube : rouge, anthracite, gris (sur fond blanc)
RED = "#FF0000"
CHARCOAL = "#212121"
GRAY = "#909090"

TOPIC_COLORS = {"GEOMATIQUE": RED, "IA": CHARCOAL, "DATA": GRAY}
PERIODE_COLORS = {"Avant ChatGPT": GRAY, "Après ChatGPT": RED}

px.defaults.template = "plotly_white"
px.defaults.color_discrete_sequence = [RED, CHARCOAL, GRAY]

# Libellés français des colonnes pour les tableaux
COLS_VIDEO = {
    "title": st.column_config.TextColumn("Titre"),
    "topic": st.column_config.TextColumn("Thème"),
    "published_at": st.column_config.DatetimeColumn("Publiée le", format="DD/MM/YYYY"),
    "view_count": st.column_config.NumberColumn("Vues", format="%d"),
    "like_count": st.column_config.NumberColumn("Likes", format="%d"),
    "comment_count": st.column_config.NumberColumn("Commentaires", format="%d"),
}

st.set_page_config(page_title="YouTube — SIG / IA / DATA", page_icon=":bar_chart:", layout="wide")
st.markdown(
    """<style>
    .block-container {padding-top: 2.5rem; max-width: 1300px;}
    [data-testid="stMetricValue"] {font-size: 1.7rem; color: #212121;}
    </style>""",
    unsafe_allow_html=True,
)


def fmt(n) -> str:
    try:
        return f"{int(n):,}".replace(",", " ")
    except (TypeError, ValueError):
        return "—"


def _query(sql: str, params=None) -> pd.DataFrame:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [c.name for c in cur.description]
            rows = cur.fetchall()
    finally:
        conn.close()
    return pd.DataFrame(rows, columns=cols)


@st.cache_data(ttl=600)
def load_videos() -> pd.DataFrame:
    df = _query(
        """
        SELECT d.video_id, d.title, d.channel_title, d.published_at,
               d.duration_sec, t.topic,
               f.view_count, f.like_count, f.comment_count
        FROM dim_video d
        JOIN video_topic t USING (video_id)
        JOIN (
            SELECT DISTINCT ON (video_id)
                   video_id, view_count, like_count, comment_count
            FROM fact_video_stats
            ORDER BY video_id, snapshot_date DESC
        ) f USING (video_id);
        """
    )
    df["published_at"] = pd.to_datetime(df["published_at"], utc=True)
    df["annee"] = df["published_at"].dt.year
    df["periode"] = df["published_at"].apply(
        lambda d: "Avant ChatGPT" if d < CHATGPT else "Après ChatGPT"
    )
    df["duree_min"] = (df["duration_sec"] / 60).round(1)
    return df


@st.cache_data(ttl=600)
def load_total_snapshots() -> pd.DataFrame:
    return _query(
        """SELECT snapshot_date, sum(view_count) AS vues_totales
           FROM fact_video_stats GROUP BY snapshot_date ORDER BY snapshot_date;"""
    )


@st.cache_data(ttl=600)
def load_video_history(video_id: str) -> pd.DataFrame:
    return _query(
        """SELECT snapshot_date, view_count, like_count, comment_count
           FROM fact_video_stats WHERE video_id = %s ORDER BY snapshot_date;""",
        (video_id,),
    )


# ------------------------------------------------------------ chargement + filtre
st.title(":bar_chart: Vidéos YouTube : SIG, géomatique, IA & data")
st.caption("Production mondiale de contenu, avant et après le lancement de ChatGPT (30 nov. 2022).")

df_all = load_videos()

st.sidebar.header("Filtres")
themes = sorted(df_all["topic"].unique())
choisis = st.sidebar.multiselect("Thèmes", themes, default=themes)
df = df_all[df_all["topic"].isin(choisis)]
if df.empty:
    st.warning("Aucune donnée pour ce filtre.")
    st.stop()

tab_apercu, tab_chaines, tab_videos = st.tabs(["Vue d'ensemble", "Par chaîne", "Par vidéo"])

# =============================================================== VUE D'ENSEMBLE
with tab_apercu:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Vidéos", fmt(df["video_id"].nunique()))
    k2.metric("Chaînes", fmt(df["channel_title"].nunique()))
    k3.metric("Avant ChatGPT", fmt((df["periode"] == "Avant ChatGPT").sum()))
    k4.metric("Après ChatGPT", fmt((df["periode"] == "Après ChatGPT").sum()))
    st.divider()

    st.subheader("Production par thème, avant vs après ChatGPT")
    ap = df.groupby(["topic", "periode"]).size().reset_index(name="nb")
    fig = px.bar(
        ap, x="topic", y="nb", color="periode", barmode="group",
        category_orders={"periode": ORDRE_PERIODE}, color_discrete_map=PERIODE_COLORS,
        labels={"topic": "Thème", "nb": "Nombre de vidéos", "periode": "Période"},
    )
    st.plotly_chart(fig, width="stretch")

    st.subheader("Vidéos publiées par année")
    par_an = df.groupby(["annee", "topic"]).size().reset_index(name="nb")
    fig2 = px.line(
        par_an, x="annee", y="nb", color="topic", markers=True,
        color_discrete_map=TOPIC_COLORS,
        labels={"annee": "Année", "nb": "Nombre de vidéos", "topic": "Thème"},
    )
    fig2.add_vline(x=2022, line_dash="dash", annotation_text="ChatGPT")
    st.plotly_chart(fig2, width="stretch")

    cga, cgb = st.columns(2)
    with cga:
        st.subheader("Répartition par thème")
        rep = df.groupby("topic").size().reset_index(name="nb")
        figp = px.pie(rep, names="topic", values="nb", color="topic",
                      color_discrete_map=TOPIC_COLORS, hole=0.45)
        st.plotly_chart(figp, width="stretch")
    with cgb:
        st.subheader("Vues médianes par thème")
        med = df.groupby(["topic", "periode"])["view_count"].median().reset_index()
        figm = px.bar(
            med, x="topic", y="view_count", color="periode", barmode="group",
            category_orders={"periode": ORDRE_PERIODE}, color_discrete_map=PERIODE_COLORS,
            labels={"topic": "Thème", "view_count": "Vues (médiane)", "periode": "Période"},
        )
        st.plotly_chart(figm, width="stretch")

    st.info(
        "Note méthodologique : les vues sont celles d'aujourd'hui, pas de l'époque de "
        "publication. Une vidéo ancienne a eu plus de temps pour les accumuler — interprète "
        "les médianes avec prudence. Le volume de production reste l'indicateur le plus fiable."
    )

    st.subheader("Évolution du total des vues (snapshots quotidiens)")
    snap = load_total_snapshots()
    if len(snap) < 2:
        st.write("L'historique commence : il faut au moins deux jours de snapshots pour voir une tendance.")
    else:
        snap["snapshot_date"] = pd.to_datetime(snap["snapshot_date"])
        st.plotly_chart(
            px.line(snap, x="snapshot_date", y="vues_totales", markers=True,
                    color_discrete_sequence=[RED],
                    labels={"snapshot_date": "Date", "vues_totales": "Vues cumulées"}),
            width="stretch",
        )

# =================================================================== PAR CHAÎNE
with tab_chaines:
    par_chaine = (
        df.groupby("channel_title")
        .agg(videos=("video_id", "nunique"),
             vues_totales=("view_count", "sum"),
             vues_medianes=("view_count", "median"))
        .reset_index()
        .sort_values("videos", ascending=False)
    )

    st.subheader("Top 15 chaînes (par nombre de vidéos)")
    top_ch = par_chaine.head(15)
    figc = px.bar(top_ch, x="videos", y="channel_title", orientation="h",
                  color_discrete_sequence=[RED],
                  labels={"videos": "Nombre de vidéos", "channel_title": "Chaîne"})
    figc.update_yaxes(categoryorder="total ascending")
    st.plotly_chart(figc, width="stretch")

    st.divider()
    st.subheader("Détail d'une chaîne")
    chaine = st.selectbox("Choisir une chaîne", par_chaine["channel_title"])
    sub = df[df["channel_title"] == chaine]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Vidéos", fmt(sub["video_id"].nunique()))
    c2.metric("Vues totales", fmt(sub["view_count"].sum()))
    c3.metric("Vues médianes", fmt(sub["view_count"].median()))
    duree_med = sub["duree_min"].median()
    c4.metric("Durée médiane", f"{duree_med:.1f} min" if pd.notna(duree_med) else "—")

    colx, coly = st.columns(2)
    with colx:
        repc = sub.groupby("topic").size().reset_index(name="nb")
        st.plotly_chart(
            px.pie(repc, names="topic", values="nb", color="topic",
                   color_discrete_map=TOPIC_COLORS, hole=0.45, title="Thèmes de la chaîne"),
            width="stretch",
        )
    with coly:
        anc = sub.groupby("annee").size().reset_index(name="nb")
        st.plotly_chart(
            px.bar(anc, x="annee", y="nb", title="Publications par année",
                   color_discrete_sequence=[CHARCOAL],
                   labels={"annee": "Année", "nb": "Vidéos"}),
            width="stretch",
        )

    st.dataframe(
        sub.sort_values("view_count", ascending=False)[
            ["title", "topic", "published_at", "view_count", "like_count", "comment_count"]
        ].head(20),
        width="stretch", hide_index=True, column_config=COLS_VIDEO,
    )

# =================================================================== PAR VIDÉO
with tab_videos:
    st.subheader("Statistiques d'une vidéo")
    chaines = ["Toutes"] + sorted(df["channel_title"].unique())
    f_ch = st.selectbox("Filtrer par chaîne (optionnel)", chaines)
    pool = df if f_ch == "Toutes" else df[df["channel_title"] == f_ch]
    titre = st.selectbox(
        "Choisir une vidéo",
        pool.sort_values("view_count", ascending=False)["title"].tolist(),
    )
    v = pool[pool["title"] == titre].iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Vues", fmt(v["view_count"]))
    c2.metric("Likes", fmt(v["like_count"]))
    c3.metric("Commentaires", fmt(v["comment_count"]))
    c4.metric("Durée", f"{v['duree_min']:.1f} min" if pd.notna(v["duree_min"]) else "—")

    st.markdown(
        f"**Chaîne :** {v['channel_title']}  |  **Thème :** {v['topic']}  "
        f"|  **Publiée le :** {v['published_at'].date()}"
    )

    st.subheader("Évolution des métriques (snapshots)")
    hist = load_video_history(v["video_id"])
    if len(hist) < 2:
        st.write(
            "Pas encore assez de snapshots pour cette vidéo — la courbe se remplira "
            "au fil des exécutions quotidiennes du DAG."
        )
    else:
        hist["snapshot_date"] = pd.to_datetime(hist["snapshot_date"])
        hist = hist.rename(columns={
            "view_count": "Vues", "like_count": "Likes", "comment_count": "Commentaires",
        })
        figh = px.line(
            hist, x="snapshot_date", y=["Vues", "Likes", "Commentaires"],
            markers=True, color_discrete_sequence=[RED, CHARCOAL, GRAY],
            labels={"snapshot_date": "Date", "value": "Valeur", "variable": "Métrique"},
        )
        st.plotly_chart(figh, width="stretch")
