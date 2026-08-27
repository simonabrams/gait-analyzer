"""Privacy-policy consent: current version + record/query helpers.

Consent is per policy version: bumping PRIVACY_POLICY_VERSION (env var) makes
every user's existing consent stale, which forces the frontend to re-prompt
before the next upload (the re-consent-on-material-change flow). Old rows are
kept as an audit trail.
"""
import os
from datetime import datetime

from sqlalchemy.orm import Session

from backend.models import ConsentRecord

# Bump only when the published policy text materially changes — every bump
# forces all users through the consent prompt again.
PRIVACY_POLICY_VERSION = os.environ.get("PRIVACY_POLICY_VERSION", "2026-08-27-draft").strip()


def get_consent(db: Session, user_id: str, policy_version: str | None = None) -> ConsentRecord | None:
    """Return the user's consent record for the given (default: current) policy version."""
    return (
        db.query(ConsentRecord)
        .filter(
            ConsentRecord.user_id == user_id,
            ConsentRecord.policy_version == (policy_version or PRIVACY_POLICY_VERSION),
        )
        .first()
    )


def record_consent(
    db: Session, user_id: str, policy_version: str, age_confirmed: bool | None = None
) -> datetime:
    """Record consent for a policy version, idempotently. Returns the consent timestamp.

    `age_confirmed` is the "I'm 18 or older" checkbox — required of every user
    (signed in or not) as of PRIVACY_POLICY_VERSION 2026-08-27-draft; see
    backend/main.py's accept_consent for the server-side enforcement. Older
    rows recorded before this requirement have it as None.
    """
    existing = get_consent(db, user_id, policy_version)
    if existing:
        return existing.created_at
    record = ConsentRecord(user_id=user_id, policy_version=policy_version, age_confirmed=age_confirmed)
    db.add(record)
    db.commit()
    return record.created_at
