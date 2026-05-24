-- depends: 0002.roles_table
CREATE TABLE IF NOT EXISTS
    tracks (
        id UUID PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        max_team_count INT NOT NULL,
        auto_confirm BOOL NOT NULL DEFAULT FALSE,
        grace_period_hours INT NOT NULL DEFAULT 24,
        confirmation_rules JSONB NOT NULL DEFAULT '[]'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

CREATE INDEX IF NOT EXISTS idx_tracks_auto_confirm ON tracks (auto_confirm);