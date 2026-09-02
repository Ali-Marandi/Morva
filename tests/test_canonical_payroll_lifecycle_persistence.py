from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from morva.persistence.enterprise_models import Base, LifecycleEventRecord
from morva.persistence.models import PayrollRunRecord
from morva.payroll.lifecycle import PayrollStatus, transition


def test_canonical_lifecycle_can_be_persisted_without_parallel_status_models() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    run_id = uuid4()
    with Session(engine) as session:
        run = PayrollRunRecord(
            id=run_id,
            period="1405-05",
            organization_unit_id="ORG-1",
            ruleset_version="test-pack",
            ruleset_hash="a" * 64,
            status=PayrollStatus.DRAFT.value,
            created_by="maker",
        )
        session.add(run)
        statuses = [
            PayrollStatus.DATA_RECEIVED,
            PayrollStatus.CALCULATING,
            PayrollStatus.VALIDATING,
            PayrollStatus.REVIEWED,
            PayrollStatus.APPROVED,
            PayrollStatus.FROZEN,
            PayrollStatus.EXPORTED,
            PayrollStatus.SUBMITTED,
            PayrollStatus.PAYMENT_CONFIRMED,
            PayrollStatus.RECONCILED,
        ]
        previous = PayrollStatus.DRAFT
        for sequence, target in enumerate(statuses, start=1):
            current = transition(previous, target)
            session.add(
                LifecycleEventRecord(
                    id=uuid4(),
                    payroll_run_id=run_id,
                    sequence_no=sequence,
                    previous_status=previous.value,
                    new_status=current.value,
                    actor_id=f"actor-{sequence}",
                    organization_unit_id="ORG-1",
                    reason="canonical lifecycle integration test",
                    correlation_id=f"corr-{sequence}",
                    idempotency_key=f"idem-{sequence}-123456",
                )
            )
            run.status = current.value
            previous = current
        session.commit()

        loaded = session.get(PayrollRunRecord, run_id)
        events = session.scalars(
            select(LifecycleEventRecord)
            .where(LifecycleEventRecord.payroll_run_id == run_id)
            .order_by(LifecycleEventRecord.sequence_no)
        ).all()
        assert loaded is not None
        assert loaded.status == PayrollStatus.RECONCILED.value
        assert [event.new_status for event in events] == [status.value for status in statuses]
        assert [event.sequence_no for event in events] == list(range(1, len(statuses) + 1))
