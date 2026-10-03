"""M4.76 verification-result persistence migration."""
from alembic import op
import sqlalchemy as sa

revision = "0055_historical_m4_75_verification_results_m4_76"
down_revision = "0054_historical_m4_74_verification_receipt_history_integrity_m4_75"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "historical_m4_72_verification_receipt_m4_75",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("verification_receipt_id", sa.Uuid(), nullable=False),
        sa.Column("persisted_fingerprint", sa.String(64), nullable=False),
        sa.Column("reconstructed_fingerprint", sa.String(64), nullable=False),
        sa.Column("persisted_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("reconstructed_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("persisted_valid", sa.Boolean(), nullable=False),
        sa.Column("reconstructed_valid", sa.Boolean(), nullable=False),
        sa.Column("valid", sa.Boolean(), nullable=False),
        sa.Column("blockers_json", sa.Text(), nullable=False),
        sa.Column("verification_fingerprint", sa.String(64), nullable=False),
        sa.Column("recorded_by", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["verification_receipt_id"], ["independent_historical_m4_72_verification_receipts_m4_74.id"]),
    )
    op.create_index("ix_m4_75_verification_receipt_id", "historical_m4_72_verification_receipt_m4_75", ["verification_receipt_id"])
    op.create_index("ix_m4_75_verification_valid", "historical_m4_72_verification_receipt_m4_75", ["valid"])
    op.create_index("ix_m4_75_verification_created_at", "historical_m4_72_verification_receipt_m4_75", ["created_at"])
    op.create_index("ix_m4_75_verification_recorded_by", "historical_m4_72_verification_receipt_m4_75", ["recorded_by"])
    op.create_index("ix_m4_75_verification_fingerprint", "historical_m4_72_verification_receipt_m4_75", ["verification_fingerprint"], unique=True)

def downgrade() -> None:
    op.drop_table("historical_m4_72_verification_receipt_m4_75")
