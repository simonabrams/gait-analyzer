"""Integration tests for the confidence gate's DB/HTTP-facing effects:
free-scan refund (backend/worker.py) and the PDF endpoint's refusal to
generate a report from ungated-out data (backend/main.py).

Requires a real Postgres reachable via DATABASE_URL (or backend.database's
localhost default). This repo has no DB/FastAPI-TestClient test harness
(see test_billing.py's docstring) and CI doesn't run a Postgres service, so
these are skipped rather than failed when one isn't reachable — run them
locally against a real Postgres (e.g. `DATABASE_URL=... pytest
backend/tests/test_confidence_gate_integration.py`) to exercise this
coverage. The rest of the confidence-gate behavior (the gate decision
itself, aggregation, and how a hard fail reshapes results_json) is covered
by pure unit tests in test_confidence_gate.py, test_metrics.py, and
test_job_runner.py, which always run.
"""
import uuid

import pytest
from sqlalchemy import text

from backend.confidence_gate import GateResult
from backend.database import SessionLocal, engine
from backend.models import Run, RunStatus, Subscription, SubscriptionTier


def _db_available() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _db_available(),
    reason="No reachable Postgres (DATABASE_URL) — skipped, see module docstring.",
)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _hard_fail_gate() -> GateResult:
    return GateResult(
        hard_fail=True,
        low_confidence=False,
        reason="insufficient_strides",
        reason_metric=None,
        detected_stride_count=4,
        usable_stride_count=4,
        computed_cadence=91.4,
        user_message="We only detected 4 usable strides in this clip.",
    )


def _ok_gate() -> GateResult:
    return GateResult(
        hard_fail=False,
        low_confidence=False,
        reason=None,
        reason_metric=None,
        detected_stride_count=20,
        usable_stride_count=20,
        computed_cadence=179.7,
    )


def _free_user_with_run(db, scans_used: int = 1) -> tuple[str, Run]:
    user_id = f"user_test_{uuid.uuid4().hex[:10]}"
    sub = Subscription(
        id=uuid.uuid4(),
        user_id=user_id,
        tier=SubscriptionTier.free.value,
        referral_code=uuid.uuid4().hex[:10],
        free_scans_used=scans_used,
    )
    db.add(sub)
    run = Run(id=uuid.uuid4(), user_id=user_id, height_cm=175, status=RunStatus.processing)
    db.add(run)
    db.commit()
    return user_id, run


# ---- Entitlement: acceptance criterion "does not consume a free analysis" ----
def test_hard_fail_refunds_the_free_scan(db):
    from backend.worker import _finalize_run

    user_id, run = _free_user_with_run(db, scans_used=1)
    out = {"results": {"summary": {}, "flags": [], "meta": {}}, "gate": _hard_fail_gate()}
    _finalize_run(db, run, out)

    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    assert sub.free_scans_used == 0
    # Complete, not failed — routes to the existing empty-summary "couldn't
    # measure your gait" screen, not the generic pipeline-error screen.
    assert run.status == RunStatus.complete


def test_normal_result_does_not_refund_the_free_scan(db):
    from backend.worker import _finalize_run

    user_id, run = _free_user_with_run(db, scans_used=1)
    out = {
        "results": {"summary": {"cadence_avg": 179.7}, "flags": [], "meta": {}},
        "gate": _ok_gate(),
    }
    _finalize_run(db, run, out)

    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    assert sub.free_scans_used == 1
    assert run.status == RunStatus.complete


def test_refund_never_goes_negative(db):
    from backend.worker import _refund_free_scan

    user_id, run = _free_user_with_run(db, scans_used=0)
    _refund_free_scan(db, run)
    db.commit()
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    assert sub.free_scans_used == 0


# ---- PDF endpoint: acceptance criterion "no PDF" for a hard-failed run ----
def test_pdf_endpoint_refuses_a_hard_failed_run(db, monkeypatch):
    import backend.main as m
    from fastapi.testclient import TestClient

    monkeypatch.setattr(m.billing, "DEV_FORCE_PRO_TIER", False)
    client = TestClient(m.app)

    # Dev mode (no CLERK_JWKS_URL) maps any bearer token to this fixed user id.
    run = Run(
        id=uuid.uuid4(),
        user_id=m._DEV_USER,
        height_cm=175,
        status=RunStatus.complete,
        results_json={"summary": {}, "flags": [], "meta": {"confidence_gate": {"hard_fail": True}}},
    )
    db.add(run)
    db.commit()

    r = client.get(f"/api/runs/{run.id}/report.pdf", headers={"Authorization": "Bearer fake"})
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["code"] == "insufficient_data"


def test_pdf_endpoint_succeeds_for_a_normal_run(db, monkeypatch):
    import backend.main as m
    from fastapi.testclient import TestClient

    monkeypatch.setattr(m.billing, "DEV_FORCE_PRO_TIER", True)  # bypass the separate Pro-tier gate
    client = TestClient(m.app)

    run = Run(
        id=uuid.uuid4(),
        user_id=m._DEV_USER,
        height_cm=175,
        status=RunStatus.complete,
        results_json={
            "summary": {"cadence_avg": 179, "vertical_osc_avg_cm": 8},
            "flags": [],
            "meta": {},
        },
    )
    db.add(run)
    db.commit()

    r = client.get(f"/api/runs/{run.id}/report.pdf", headers={"Authorization": "Bearer fake"})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
