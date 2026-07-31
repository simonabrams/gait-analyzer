"""Unit tests for backend.claim's pure merge logic. The DB-touching orchestrator
(claim_anonymous_account) isn't covered here — see test_billing.py's docstring
for why no Postgres-backed test harness exists in this repo yet; verify that
function's behavior manually (idempotency, actual reassignment, consent
unique-constraint handling) per the plan's manual verification steps."""
from backend.claim import _merge_subscription_fields
from backend.models import Subscription


def _sub(**overrides):
    defaults = dict(
        user_id="user_test",
        tier="free",
        status=None,
        referral_code="abc1234567",
        free_scans_used=0,
        bonus_scans=0,
        referred_by_code=None,
        referral_bonus_granted=False,
    )
    defaults.update(overrides)
    return Subscription(**defaults)


def test_free_scans_used_is_additive():
    real = _sub(free_scans_used=0)
    anon_sub = _sub(free_scans_used=1)
    updates = _merge_subscription_fields(real, anon_sub)
    assert updates["free_scans_used"] == 1


def test_bonus_scans_is_additive():
    real = _sub(bonus_scans=1)
    anon_sub = _sub(bonus_scans=2)
    updates = _merge_subscription_fields(real, anon_sub)
    assert updates["bonus_scans"] == 3


def test_referred_by_code_copied_when_real_has_none():
    real = _sub(referred_by_code=None)
    anon_sub = _sub(referred_by_code="friendcode", referral_bonus_granted=True)
    updates = _merge_subscription_fields(real, anon_sub)
    assert updates["referred_by_code"] == "friendcode"
    assert updates["referral_bonus_granted"] is True


def test_referred_by_code_not_overwritten_when_real_already_has_one():
    real = _sub(referred_by_code="alreadyset")
    anon_sub = _sub(referred_by_code="friendcode", referral_bonus_granted=True)
    updates = _merge_subscription_fields(real, anon_sub)
    assert "referred_by_code" not in updates
    assert "referral_bonus_granted" not in updates


def test_tier_and_stripe_fields_never_copied():
    real = _sub(tier="free")
    anon_sub = _sub(tier="pro", status="active")
    updates = _merge_subscription_fields(real, anon_sub)
    assert "tier" not in updates
    assert "status" not in updates
    assert "stripe_customer_id" not in updates
