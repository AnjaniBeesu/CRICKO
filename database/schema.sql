-- CRICKO relational store for the scoped Cricsheet men's T20 snapshot.
-- Apply with: psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/schema.sql
CREATE TABLE IF NOT EXISTS teams (
    team_id TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    aliases JSONB NOT NULL DEFAULT '[]'::jsonb
);

CREATE TABLE IF NOT EXISTS players (
    player_id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    aliases_observed JSONB NOT NULL DEFAULT '[]'::jsonb,
    source_id_types JSONB NOT NULL DEFAULT '[]'::jsonb,
    identity_status TEXT NOT NULL DEFAULT 'SOURCE_IDENTITY_UNREVIEWED',
    bio_status TEXT NOT NULL DEFAULT 'NOT_PROVIDED_BY_THIS_COLLECTOR'
);

CREATE TABLE IF NOT EXISTS competitions (
    competition_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS matches (
    match_id TEXT PRIMARY KEY,
    source_match_id TEXT NOT NULL,
    source_archive TEXT NOT NULL,
    match_date DATE NOT NULL,
    gender TEXT NOT NULL,
    match_type TEXT NOT NULL,
    competition_id TEXT REFERENCES competitions(competition_id),
    season TEXT,
    venue TEXT,
    city TEXT,
    team1_id TEXT NOT NULL REFERENCES teams(team_id),
    team2_id TEXT NOT NULL REFERENCES teams(team_id),
    toss_winner_id TEXT REFERENCES teams(team_id),
    toss_decision TEXT,
    winner_id TEXT REFERENCES teams(team_id),
    outcome_by JSONB,
    stage TEXT,
    player_of_match_source_names JSONB NOT NULL DEFAULT '[]'::jsonb,
    officials JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_data_version TEXT,
    CHECK (team1_id <> team2_id)
);

CREATE TABLE IF NOT EXISTS innings (
    match_id TEXT NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    innings_number SMALLINT NOT NULL CHECK (innings_number > 0),
    batting_team_id TEXT NOT NULL REFERENCES teams(team_id),
    bowling_team_id TEXT NOT NULL REFERENCES teams(team_id),
    PRIMARY KEY (match_id, innings_number),
    CHECK (batting_team_id <> bowling_team_id)
);

CREATE TABLE IF NOT EXISTS player_match_map (
    player_id TEXT NOT NULL REFERENCES players(player_id),
    match_id TEXT NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    team_id TEXT NOT NULL REFERENCES teams(team_id),
    source_name TEXT NOT NULL,
    PRIMARY KEY (player_id, match_id, team_id)
);

CREATE TABLE IF NOT EXISTS deliveries (
    match_id TEXT NOT NULL,
    innings_number SMALLINT NOT NULL,
    over_number SMALLINT NOT NULL CHECK (over_number > 0),
    delivery_number SMALLINT NOT NULL CHECK (delivery_number > 0),
    actual_delivery TEXT NOT NULL,
    batting_team_id TEXT NOT NULL REFERENCES teams(team_id),
    bowling_team_id TEXT NOT NULL REFERENCES teams(team_id),
    batter_id TEXT NOT NULL REFERENCES players(player_id),
    bowler_id TEXT NOT NULL REFERENCES players(player_id),
    non_striker_id TEXT NOT NULL REFERENCES players(player_id),
    legal_delivery BOOLEAN NOT NULL,
    batter_faced BOOLEAN NOT NULL,
    batter_runs SMALLINT NOT NULL CHECK (batter_runs >= 0),
    extras_total SMALLINT NOT NULL CHECK (extras_total >= 0),
    wide_runs SMALLINT NOT NULL CHECK (wide_runs >= 0),
    noball_runs SMALLINT NOT NULL CHECK (noball_runs >= 0),
    bye_runs SMALLINT NOT NULL CHECK (bye_runs >= 0),
    legbye_runs SMALLINT NOT NULL CHECK (legbye_runs >= 0),
    penalty_runs SMALLINT NOT NULL CHECK (penalty_runs >= 0),
    total_runs SMALLINT NOT NULL CHECK (total_runs >= 0),
    bowler_runs SMALLINT NOT NULL CHECK (bowler_runs >= 0),
    dismissal_kind TEXT,
    dismissed_player_id TEXT REFERENCES players(player_id),
    bowler_credited_wicket BOOLEAN NOT NULL,
    PRIMARY KEY (match_id, innings_number, over_number, delivery_number),
    FOREIGN KEY (match_id, innings_number)
        REFERENCES innings(match_id, innings_number) ON DELETE CASCADE,
    CHECK (batting_team_id <> bowling_team_id)
);

CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(match_date);
CREATE INDEX IF NOT EXISTS idx_matches_competition_date ON matches(competition_id, match_date);
CREATE INDEX IF NOT EXISTS idx_deliveries_batter ON deliveries(batter_id, match_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_bowler ON deliveries(bowler_id, match_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_match_innings ON deliveries(match_id, innings_number);
CREATE INDEX IF NOT EXISTS idx_deliveries_batting_team ON deliveries(batting_team_id, match_id);
CREATE INDEX IF NOT EXISTS idx_player_match_team ON player_match_map(team_id, player_id);
