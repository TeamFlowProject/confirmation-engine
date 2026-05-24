CREATE TABLE IF NOT EXISTS
    roles (
        id UUID PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        count INT NOT NULL DEFAULT 0,
        created_at TIMESTAMP NOT NULL DEFAULT NOW()
    );