-- depends: 0002.roles_table
CREATE TABLE IF NOT EXISTS
    members (
        id UUID PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        surname VARCHAR(255) NOT NULL,
        patronymic VARCHAR(255),
        role_id UUID NOT NULL,
        FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE RESTRICT,
        created_at TIMESTAMP NOT NULL DEFAULT NOW()
    );

CREATE INDEX IF NOT EXISTS idx_members_role ON members (role_id);