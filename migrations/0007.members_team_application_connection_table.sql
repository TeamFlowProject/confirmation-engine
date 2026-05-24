-- depends: 0003.members_table
-- depends: 0004.tracks_table
CREATE TABLE IF NOT EXISTS
    team_application_members (
        application_id UUID NOT NULL REFERENCES team_applications (id) ON DELETE CASCADE,
        member_id UUID NOT NULL REFERENCES members (id) ON DELETE RESTRICT,
        PRIMARY KEY (application_id, member_id)
    );

CREATE INDEX IF NOT EXISTS idx_team_application_members_member ON team_application_members (member_id);