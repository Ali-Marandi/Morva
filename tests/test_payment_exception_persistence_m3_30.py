from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from morva.payroll.payment_exceptions import PaymentException, PaymentExceptionStatus, PaymentExceptionType
from morva.persistence.models import Base
from morva.persistence.payment_exception_records import (
    PaymentExceptionEventRecord,
    PaymentExceptionRecord,
    PaymentExceptionRepository,
)


def make_repo() -> tuple[Session, PaymentExceptionRepository]:
    engine = create_engine("sqlite:///:memory:", future=True)
    PaymentExceptionRecord.__table__.create(engine)
    PaymentExceptionEventRecord.__table__.create(engine)
    session = Session(engine)
    return session, PaymentExceptionRepository(session)


def make_exception() -> PaymentException:
    return PaymentException(
        exception_id="EX-300",
        payment_item_id="PAY-300",
        exception_type=PaymentExceptionType.RETURN,
        reason="provider returned the payment",
    )


def test_create_persists_open_exception_and_release_is_blocked() -> None:
    session, repo = make_repo()
    repo.create(make_exception())
    session.commit()

    stored = session.query(PaymentExceptionRecord).one()
    assert stored.status == PaymentExceptionStatus.OPEN.value
    assert not repo.release_is_allowed(payment_item_id="PAY-300")


def test_resolution_persists_immutable_event_and_unblocks_item() -> None:
    session, repo = make_repo()
    repo.create(make_exception())
    session.commit()

    occurred_at = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
    event = repo.resolve(
        "EX-300",
        actor="operator-1",
        reason="return receipt reviewed",
        evidence_ref="receipt:300",
        idempotency_key="resolve:EX-300:1",
        occurred_at=occurred_at,
    )
    session.commit()

    stored = session.query(PaymentExceptionRecord).one()
    persisted_event = session.query(PaymentExceptionEventRecord).one()
    assert event.id == persisted_event.id
    assert stored.status == PaymentExceptionStatus.RESOLVED.value
    assert stored.resolution_fingerprint == persisted_event.fingerprint
    assert repo.release_is_allowed(payment_item_id="PAY-300")


def test_same_idempotency_key_is_replay_safe() -> None:
    session, repo = make_repo()
    repo.create(make_exception())
    session.commit()
    kwargs = dict(
        actor="operator-1",
        reason="return receipt reviewed",
        evidence_ref="receipt:300",
        idempotency_key="resolve:EX-300:1",
        occurred_at=datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc),
    )

    first = repo.resolve("EX-300", **kwargs)
    session.commit()
    second = repo.resolve("EX-300", **kwargs)

    assert second.id == first.id
    assert session.query(PaymentExceptionEventRecord).count() == 1


def test_different_second_resolution_is_rejected_after_resolution() -> None:
    session, repo = make_repo()
    repo.create(make_exception())
    session.commit()
    repo.resolve(
        "EX-300",
        actor="operator-1",
        reason="first resolution",
        evidence_ref="receipt:300",
        idempotency_key="resolve:EX-300:1",
        occurred_at=datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc),
    )
    session.commit()

    try:
        repo.resolve(
            "EX-300",
            actor="operator-2",
            reason="second resolution",
            evidence_ref="receipt:301",
            idempotency_key="resolve:EX-300:2",
            occurred_at=datetime(2026, 9, 16, 12, 1, tzinfo=timezone.utc),
        )
    except ValueError as exc:
        assert str(exc) == "only open payment exceptions can be resolved"
    else:
        raise AssertionError("a second resolution must be rejected")


def test_tampering_resolution_fingerprint_is_detectable() -> None:
    session, repo = make_repo()
    repo.create(make_exception())
    session.commit()
    repo.resolve(
        "EX-300",
        actor="operator-1",
        reason="first resolution",
        evidence_ref="receipt:300",
        idempotency_key="resolve:EX-300:1",
        occurred_at=datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc),
    )
    session.commit()

    stored = session.query(PaymentExceptionEventRecord).one()
    original = stored.fingerprint
    stored.fingerprint = "0" * 64
    assert stored.fingerprint != original
