"""Unit tests for backend.billing gating logic. No DB/FastAPI TestClient harness
exists in this repo yet (see test_metrics.py / test_heuristics.py for the existing
pure-function testing pattern), so DB-dependent functions (get_or_create_subscription,
sync_subscription_from_stripe, handle_webhook_event) aren't covered here — only the
pure has_active_access() chokepoint and referral code generation."""
import backend.billing as billing
from backend.models import Subscription, SubscriptionTier


def _sub(tier, status):
    return Subscription(user_id="user_test", tier=tier, status=status, referral_code="abc1234567")


def test_free_tier_has_no_access(monkeypatch):
    monkeypatch.setattr(billing, "DEV_FORCE_PRO_TIER", False)
    assert not billing.has_active_access(_sub(SubscriptionTier.free.value, None))


def test_pro_trialing_has_access(monkeypatch):
    monkeypatch.setattr(billing, "DEV_FORCE_PRO_TIER", False)
    assert billing.has_active_access(_sub(SubscriptionTier.pro.value, "trialing"))


def test_pro_active_has_access(monkeypatch):
    monkeypatch.setattr(billing, "DEV_FORCE_PRO_TIER", False)
    assert billing.has_active_access(_sub(SubscriptionTier.pro.value, "active"))


def test_pro_grandfathered_has_access(monkeypatch):
    monkeypatch.setattr(billing, "DEV_FORCE_PRO_TIER", False)
    assert billing.has_active_access(_sub(SubscriptionTier.pro.value, "grandfathered"))


def test_pro_past_due_has_no_access(monkeypatch):
    monkeypatch.setattr(billing, "DEV_FORCE_PRO_TIER", False)
    assert not billing.has_active_access(_sub(SubscriptionTier.pro.value, "past_due"))


def test_pro_canceled_has_no_access(monkeypatch):
    monkeypatch.setattr(billing, "DEV_FORCE_PRO_TIER", False)
    assert not billing.has_active_access(_sub(SubscriptionTier.pro.value, "canceled"))


def test_dev_force_pro_tier_overrides_everything(monkeypatch):
    monkeypatch.setattr(billing, "DEV_FORCE_PRO_TIER", True)
    assert billing.has_active_access(_sub(SubscriptionTier.free.value, None))


def test_referral_codes_are_short_and_unique():
    codes = {billing._new_referral_code() for _ in range(1000)}
    assert len(codes) == 1000
    assert all(len(c) == 10 for c in codes)
