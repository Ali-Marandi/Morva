-- Morva production migration 002.
-- PostgreSQL 16+; run before deploying code that admits snapshots.
-- Never run against a database containing unreviewed schema drift without backup/PITR validation.

CREATE TABLE IF NOT EXISTS ruleset_approvals (
    id uuid PRIMARY KEY,
    version varchar(80) NOT NULL,
    status varchar(30) NOT NULL DEFAULT 'pending',
    legal_manifest_hash varchar(64),
    approved_by varchar(100),
    approved_at timestamp,
    population_scope varchar(80) NOT NULL DEFAULT 'global',
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_ruleset_approval_version UNIQUE (version)
);
CREATE INDEX IF NOT EXISTS ix_ruleset_approvals_version ON ruleset_approvals(version);
CREATE INDEX IF NOT EXISTS ix_ruleset_approvals_status ON ruleset_approvals(status);

CREATE TABLE IF NOT EXISTS employee_payroll_snapshots (
    id uuid PRIMARY KEY,
    payroll_run_id uuid NOT NULL,
    employee_no varchar(50) NOT NULL,
    organization_scope varchar(80) NOT NULL,
    period varchar(7) NOT NULL,
    source_manifest_hash varchar(64) NOT NULL,
    snapshot_hash varchar(64) NOT NULL,
    payload jsonb NOT NULL,
    created_by varchar(100) NOT NULL,
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_payroll_snapshot_employee UNIQUE (payroll_run_id, employee_no)
);
CREATE INDEX IF NOT EXISTS ix_employee_payroll_snapshots_run ON employee_payroll_snapshots(payroll_run_id);
CREATE INDEX IF NOT EXISTS ix_employee_payroll_snapshots_employee ON employee_payroll_snapshots(employee_no);
CREATE INDEX IF NOT EXISTS ix_employee_payroll_snapshots_hash ON employee_payroll_snapshots(snapshot_hash);

-- Snapshot rows are append-only by application contract. Production deployment must
-- also grant INSERT/SELECT to the application role and deny UPDATE/DELETE on this table.
