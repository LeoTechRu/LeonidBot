-- triggers and notifications for project alerts
CREATE TABLE IF NOT EXISTS triggers (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    channel_id UUID NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    next_fire_at TIMESTAMPTZ NOT NULL,
    alarm_id UUID NULL REFERENCES alarms(id) ON DELETE SET NULL,
    rule JSONB,
    dedupe_key TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY,
    dedupe_key TEXT NOT NULL UNIQUE,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
