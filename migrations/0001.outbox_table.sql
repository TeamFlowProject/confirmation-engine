DO $$ BEGIN CREATE TYPE event_status AS ENUM('SENT', 'PENDING', 'FAILED');

EXCEPTION WHEN duplicate_object THEN NULL;

END $$;

CREATE TABLE IF NOT EXISTS
    outbox_events (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
        aggregate_type VARCHAR(100) NOT NULL,
        aggregate_id UUID NOT NULL,
        event_type VARCHAR(200) NOT NULL,
        payload JSONB NOT NULL,
        status event_status NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        processed_at TIMESTAMPTZ,
        retry_count INT NOT NULL DEFAULT 0,
        error_message TEXT,
        idempotency_key VARCHAR(255) UNIQUE
    );

CREATE INDEX IF NOT EXISTS idx_outbox_relay ON outbox_events (status, created_at)
WHERE
    status = 'PENDING';

CREATE INDEX IF NOT EXISTS idx_outbox_aggregate ON outbox_events (aggregate_type, aggregate_id);