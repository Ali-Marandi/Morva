-- Morva P0 audit-chain migration for PostgreSQL.
-- Run before deploying application code that writes AuditChainHeadRecord.

CREATE TABLE IF NOT EXISTS audit_chain_heads (
    id INTEGER PRIMARY KEY,
    last_sequence_no INTEGER NOT NULL DEFAULT 0,
    last_hash VARCHAR(64) NOT NULL DEFAULT '',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM audit_events
        GROUP BY sequence_no
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'audit_events contains duplicate sequence_no values; repair before enabling unique sequence enforcement';
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_audit_event_sequence ON audit_events(sequence_no);

INSERT INTO audit_chain_heads(id, last_sequence_no, last_hash)
SELECT 1, COALESCE(MAX(sequence_no), 0), COALESCE(
    (SELECT current_hash FROM audit_events ORDER BY sequence_no DESC LIMIT 1), ''
)
FROM audit_events
ON CONFLICT (id) DO UPDATE
SET last_sequence_no = EXCLUDED.last_sequence_no,
    last_hash = EXCLUDED.last_hash,
    updated_at = CURRENT_TIMESTAMP;
