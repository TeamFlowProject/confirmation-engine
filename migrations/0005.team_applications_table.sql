-- depends: 0004.tracks_table
DO $$ BEGIN CREATE TYPE team_status AS ENUM(
    'none',
    'submitted',
    'validated',
    'confirmed',
    'rejected',
    'invalid'
);

EXCEPTION WHEN duplicate_object THEN NULL;

END $$;

CREATE TABLE IF NOT EXISTS
    team_applications (
        id UUID PRIMARY KEY,
        track_id UUID NOT NULL REFERENCES tracks (id) ON DELETE RESTRICT,
        name VARCHAR(255) NOT NULL,
        status team_status NOT NULL DEFAULT 'none',
        rejection_reason TEXT,
        grace_deadline TIMESTAMPTZ
    );

CREATE INDEX IF NOT EXISTS idx_team_applications_track ON team_applications (track_id);

CREATE INDEX IF NOT EXISTS idx_team_applications_status ON team_applications (status);