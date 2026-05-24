-- depends: 0002.roles_table
-- depends: 0004.tracks_table
CREATE TABLE IF NOT EXISTS
    track_roles (
        track_id UUID NOT NULL REFERENCES tracks (id) ON DELETE CASCADE,
        role_id UUID NOT NULL REFERENCES roles (id) ON DELETE RESTRICT,
        PRIMARY KEY (track_id, role_id)
    );

CREATE INDEX IF NOT EXISTS idx_track_roles_role ON track_roles (role_id);