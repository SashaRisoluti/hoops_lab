-- 001_initial_schema.sql — structural tables created empty at migration time.
--
-- The data-bearing tables are NOT defined here:
--   * wide stat tables (box scores, season stats, shots, play-by-play,
--     lineups) are created by the seeder directly from Parquet, preserving
--     every source column (see hoops_lab/storage/seed.py and the registry in
--     hoops_lab/storage/models.py);
--   * teams / players / seasons / games are derived by the seeder.

CREATE TABLE IF NOT EXISTS possessions (
    game_id            VARCHAR NOT NULL,
    possession_number  INTEGER NOT NULL,
    season             VARCHAR,
    offense_team_id    BIGINT,
    defense_team_id    BIGINT,
    period             INTEGER,
    start_game_clock   VARCHAR,
    end_game_clock     VARCHAR,
    points             INTEGER,
    outcome            VARCHAR,
    PRIMARY KEY (game_id, possession_number)
);

CREATE TABLE IF NOT EXISTS player_percentiles (
    player_id               BIGINT NOT NULL,
    stat_name               VARCHAR NOT NULL,
    stat_value              DOUBLE,
    percentile              DOUBLE,
    rank                    INTEGER,
    population_filter_hash  VARCHAR NOT NULL,
    sample_size             INTEGER,
    date_computed           TIMESTAMP,
    PRIMARY KEY (player_id, stat_name, population_filter_hash)
);

CREATE TABLE IF NOT EXISTS live_game_events (
    game_id        VARCHAR NOT NULL,
    action_number  INTEGER NOT NULL,
    received_at    TIMESTAMP,
    period         INTEGER,
    game_clock     VARCHAR,
    team_id        BIGINT,
    player_id      BIGINT,
    action_type    VARCHAR,
    description    VARCHAR,
    score_home     INTEGER,
    score_away     INTEGER,
    PRIMARY KEY (game_id, action_number)
);

CREATE SEQUENCE IF NOT EXISTS alerts_seq;

CREATE TABLE IF NOT EXISTS alerts (
    alert_id    BIGINT PRIMARY KEY DEFAULT nextval('alerts_seq'),
    game_id     VARCHAR,
    created_at  TIMESTAMP DEFAULT current_timestamp,
    rule        VARCHAR NOT NULL,
    severity    VARCHAR DEFAULT 'info',
    message     VARCHAR NOT NULL,
    payload     VARCHAR
);
