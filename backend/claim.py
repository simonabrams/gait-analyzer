"""
Claim-on-signup: merges an anonymous visitor's Run(s), ConsentRecord(s), and
free-scan usage into their real Clerk account right after they sign up. See
backend/anon.py for how the anonymous id is generated/validated.
"""
from typing import NamedTuple

from sqlalchemy.orm import Session

from backend import billing, consent
from backend.models import ConsentRecord, Run, Subscription


class ClaimResult(NamedTuple):
    claimed_runs: int
    consent_claimed: bool
    free_scans_merged: int


def _merge_subscription_fields(real: Subscription, anon_sub: Subscription) -> dict:
    """Pure: compute the field updates to apply to `real` given `anon_sub`.

    Anonymous sessions can never reach Stripe checkout (that path requires a
    real Clerk user via get_current_user), so anon_sub's tier/status/stripe_*
    fields are always at their defaults — never copied onto `real`.
    """
    updates = {
        "free_scans_used": real.free_scans_used + anon_sub.free_scans_used,
        "bonus_scans": real.bonus_scans + anon_sub.bonus_scans,
    }
    if not real.referred_by_code and anon_sub.referred_by_code:
        updates["referred_by_code"] = anon_sub.referred_by_code
        updates["referral_bonus_granted"] = anon_sub.referral_bonus_granted
    return updates


def claim_anonymous_account(db: Session, anon_id: str, real_user_id: str) -> ClaimResult:
    """Reassign anon_id's runs/consent/scan-usage to real_user_id. Idempotent —
    safe to call more than once (a repeat call finds nothing left to claim)."""
    claimed_runs = (
        db.query(Run)
        .filter(Run.user_id == anon_id)
        .update({"user_id": real_user_id})
    )

    anon_sub = (
        db.query(Subscription)
        .filter(Subscription.user_id == anon_id)
        .with_for_update()
        .first()
    )
    free_scans_merged = 0
    if anon_sub:
        real_sub = billing.get_or_create_subscription(db, real_user_id)
        for key, value in _merge_subscription_fields(real_sub, anon_sub).items():
            setattr(real_sub, key, value)
        free_scans_merged = anon_sub.free_scans_used
        # Delete rather than reassign: user_id is unique, so it can't be
        # repointed onto real_user_id if a Subscription row already exists
        # there (the common case) — and deleting also frees the unique
        # referral_code so it can't be resurrected by a later claim call.
        db.delete(anon_sub)

    anon_consents = db.query(ConsentRecord).filter(ConsentRecord.user_id == anon_id).all()
    for record in anon_consents:
        if consent.get_consent(db, real_user_id, record.policy_version):
            # real_user_id already consented to this version — drop the
            # anonymous duplicate rather than violate the unique
            # (user_id, policy_version) index by reassigning it.
            db.delete(record)
        else:
            record.user_id = real_user_id

    db.commit()
    return ClaimResult(
        claimed_runs=claimed_runs,
        consent_claimed=bool(anon_consents),
        free_scans_merged=free_scans_merged,
    )
