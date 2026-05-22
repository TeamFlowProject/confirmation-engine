-- depends: 0002.roles_table
CREATE TABLE IF NOT EXISTS
    tracks (
        id UUID PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        max_team_count INT NOT NULL,
        auto_confirm BOOL NOT NULL DEFAULT FALSE,
        grace_period_hours INT NOT NULL DEFAULT 24
    );

CREATE TABLE IF NOT EXISTS
    track_confirmation_rules (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
        track_id UUID NOT NULL REFERENCES tracks (id) ON DELETE CASCADE,
        rule_type VARCHAR(50) NOT NULL,
        params JSONB NOT NULL,
        sort_order INT NOT NULL DEFAULT 0
    );

CREATE INDEX IF NOT EXISTS idx_tracks_auto_confirm ON tracks (auto_confirm);

CREATE INDEX IF NOT EXISTS idx_track_confirmation_rules_track ON track_confirmation_rules (track_id);