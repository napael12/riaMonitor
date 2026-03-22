CREATE TABLE IF NOT EXISTS advisers (
    crd VARCHAR(20) PRIMARY KEY,
    firm_name TEXT NOT NULL,
    registration_type VARCHAR(10),   -- 'SEC' or 'Exempt'
    sec_number VARCHAR(20),
    primary_state VARCHAR(2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS snapshots (
    id SERIAL PRIMARY KEY,
    adviser_crd VARCHAR(20) REFERENCES advisers(crd) ON DELETE CASCADE,
    period VARCHAR(7) NOT NULL,      -- 'YYYY-MM'
    aum NUMERIC(20,2),
    employees INTEGER,
    num_clients INTEGER,
    registration_status VARCHAR(50),
    raw JSONB,
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(adviser_crd, period)
);

CREATE INDEX IF NOT EXISTS idx_snapshots_crd ON snapshots(adviser_crd);
CREATE INDEX IF NOT EXISTS idx_snapshots_period ON snapshots(period);

CREATE TABLE IF NOT EXISTS changes (
    id SERIAL PRIMARY KEY,
    adviser_crd VARCHAR(20) REFERENCES advisers(crd) ON DELETE CASCADE,
    period_from VARCHAR(7),
    period_to VARCHAR(7),
    field VARCHAR(100),
    old_value TEXT,
    new_value TEXT,
    detected_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_changes_crd ON changes(adviser_crd);
CREATE INDEX IF NOT EXISTS idx_changes_period ON changes(period_to);
