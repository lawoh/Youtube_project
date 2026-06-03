-- Schéma du pipeline YouTube (modèle en étoile).

-- DIMENSION : un enregistrement par vidéo (attributs stables)
CREATE TABLE IF NOT EXISTS dim_video (
    video_id          VARCHAR(20) PRIMARY KEY,  
    title             TEXT,
    channel_id        VARCHAR(30),
    channel_title     TEXT,
    published_at      TIMESTAMPTZ NOT NULL,      
    category_id       VARCHAR(5),
    duration_sec      INTEGER,
    definition        VARCHAR(2),                
    default_language  VARCHAR(10),
    region            VARCHAR(5),
    tags              TEXT[],
    first_seen_at     TIMESTAMPTZ DEFAULT now()  
);

-- FAITS : une ligne par vidéo ET par snapshot (construit l'historique)
CREATE TABLE IF NOT EXISTS fact_video_stats (
    id            BIGSERIAL PRIMARY KEY,
    video_id      VARCHAR(20) NOT NULL REFERENCES dim_video (video_id),
    snapshot_date DATE NOT NULL,
    view_count    BIGINT,
    like_count    BIGINT,
    comment_count BIGINT,
    UNIQUE (video_id, snapshot_date)   
);

-- LIAISON : multi-appartenance vidéo <-> topic
CREATE TABLE IF NOT EXISTS video_topic (
    video_id  VARCHAR(20) NOT NULL REFERENCES dim_video (video_id),
    topic     VARCHAR(20) NOT NULL,
    PRIMARY KEY (video_id, topic)
);

-- Index utiles pour les requêtes du dashboard
CREATE INDEX IF NOT EXISTS idx_dim_video_published ON dim_video (published_at);
CREATE INDEX IF NOT EXISTS idx_fact_snapshot       ON fact_video_stats (snapshot_date);
CREATE INDEX IF NOT EXISTS idx_video_topic_topic   ON video_topic (topic);
