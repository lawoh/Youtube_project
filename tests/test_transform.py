"""Tests de la transformation (transform.build_records)."""


def test_nombre_de_lignes(good_records):
    dim_rows, fact_rows, topic_rows = good_records
    assert len(dim_rows) == 2
    assert len(fact_rows) == 2
    assert len(topic_rows) == 2


def test_dim_geomatique(good_records):
    dim_rows, _, _ = good_records
    vid = next(r for r in dim_rows if r["video_id"] == "vid001")
    assert vid["duration_sec"] == 605          # 10 min 5 s
    assert vid["definition"] == "hd"
    assert vid["default_language"] == "fr"      # vient de defaultAudioLanguage
    assert vid["tags"] == ["sig", "qgis"]


def test_dim_fallback_langue(good_records):
    dim_rows, _, _ = good_records
    vid = next(r for r in dim_rows if r["video_id"] == "vid002")
    # pas de defaultAudioLanguage -> on retombe sur defaultLanguage
    assert vid["default_language"] == "en"
    assert vid["duration_sec"] == 3720          # 1 h 2 min


def test_fact_casts_et_likes_masques(good_records):
    _, fact_rows, _ = good_records
    f1 = next(r for r in fact_rows if r["video_id"] == "vid001")
    assert f1["view_count"] == 15000            # bien casté en int
    assert f1["like_count"] == 300

    f2 = next(r for r in fact_rows if r["video_id"] == "vid002")
    assert f2["like_count"] is None             # likeCount absent -> None
    assert f2["comment_count"] == 0


def test_topics(good_records):
    _, _, topic_rows = good_records
    topics = {(r["video_id"], r["topic"]) for r in topic_rows}
    assert topics == {("vid001", "GEOMATIQUE"), ("vid002", "IA")}
