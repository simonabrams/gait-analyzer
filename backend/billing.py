"""
Stripe subscription service layer: checkout, portal, webhook sync, and the
single tier/access gating chokepoint (has_active_access) used everywhere else.
"""
import logging
import os
import uuid
from datetime import datetime, timezone

import stripe
from posthog import Posthog
from sqlalchemy.orm import Session

from backend.models import Subscription, SubscriptionTier

logger = logging.getLogger(__name__)

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "").strip()

PRICE_MONTHLY = os.environ.get("STRIPE_PRICE_ID_MONTHLY", "").strip()
PRICE_YEARLY = os.environ.get("STRIPE_PRICE_ID_YEARLY", "").strip()
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()

# Escape hatch for local dev: force every user to appear as Pro without running
# a real Stripe test-mode checkout. Never set this in production.
DEV_FORCE_PRO_TIER = os.environ.get("DEV_FORCE_PRO_TIER", "").strip().lower() in ("1", "true", "yes")

_ACTIVE_STATUSES = {"trialing", "active", "grandfathered"}

_POSTHOG_TOKEN = os.environ.get("POSTHOG_PROJECT_TOKEN", "").strip()
_POSTHOG_HOST = os.environ.get("POSTHOG_HOST", "https://us.i.posthog.com").strip()
posthog_client: Posthog | None = None
if _POSTHOG_TOKEN:
    posthog_client = Posthog(project_api_key=_POSTHOG_TOKEN, host=_POSTHOG_HOST)


def _capture(user_id: str, event: str, properties: dict | None = None) -> None:
    if posthog_client:
        posthog_client.capture(user_id, event, properties=properties or {})


def _new_referral_code() -> str:
    return uuid.uuid4().hex[:10]


def get_or_create_subscription(db: Session, user_id: str) -> Subscription:
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    if sub:
        return sub
    sub = Subscription(
        id=uuid.uuid4(),
        user_id=user_id,
        tier=SubscriptionTier.free.value,
        referral_code=_new_referral_code(),
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def has_active_access(sub: Subscription) -> bool:
    """Single chokepoint for 'does this user have Pro access right now.'

    All gating (current Pro tier and any future Elite tier) should read
    through this function rather than re-checking tier/status inline.
    """
    if DEV_FORCE_PRO_TIER:
        return True
    return sub.tier == SubscriptionTier.pro.value and sub.status in _ACTIVE_STATUSES


def create_checkout_session(
    sub: Subscription,
    plan: str,
    email: str | None,
    success_url: str,
    cancel_url: str,
) -> stripe.checkout.Session:
    price_id = PRICE_MONTHLY if plan == "monthly" else PRICE_YEARLY
    if not price_id:
        raise RuntimeError(f"No Stripe price configured for plan={plan!r}")

    kwargs: dict = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "subscription_data": {"trial_period_days": 7},
        "payment_method_collection": "always",
        "client_reference_id": sub.user_id,
        "metadata": {"user_id": sub.user_id},
        "success_url": success_url,
        "cancel_url": cancel_url,
    }
    if sub.stripe_customer_id:
        kwargs["customer"] = sub.stripe_customer_id
    elif email:
        kwargs["customer_email"] = email

    return stripe.checkout.Session.create(**kwargs)


def create_portal_session(customer_id: str, return_url: str) -> stripe.billing_portal.Session:
    return stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)


def sync_subscription_from_stripe(db: Session, stripe_subscription_id: str) -> Subscription | None:
    """Re-fetch the subscription from Stripe (rather than trusting webhook
    payload fields directly) and upsert its status onto our row — safe
    against out-of-order webhook delivery."""
    sub = (
        db.query(Subscription)
        .filter(Subscription.stripe_subscription_id == stripe_subscription_id)
        .first()
    )
    if not sub:
        logger.warning("No local subscription for stripe_subscription_id=%s", stripe_subscription_id)
        return None

    # stripe-python's StripeObject doesn't implement dict's .get() (only __getitem__),
    # so convert to a plain dict up front rather than mixing [] and .get() below.
    stripe_sub = stripe.Subscription.retrieve(stripe_subscription_id).to_dict()
    sub.status = stripe_sub["status"]
    item = stripe_sub["items"]["data"][0] if stripe_sub["items"]["data"] else None
    if item:
        sub.price_id = item["price"]["id"]
    if stripe_sub.get("trial_end"):
        sub.trial_end = datetime.fromtimestamp(stripe_sub["trial_end"], tz=timezone.utc)
    current_period_end = item["current_period_end"] if item else stripe_sub.get("current_period_end")
    if current_period_end:
        sub.current_period_end = datetime.fromtimestamp(current_period_end, tz=timezone.utc)
    sub.cancel_at_period_end = bool(stripe_sub.get("cancel_at_period_end"))
    db.commit()
    db.refresh(sub)
    return sub


def _handle_checkout_completed(db: Session, event_object: dict) -> None:
    user_id = event_object.get("client_reference_id") or (event_object.get("metadata") or {}).get("user_id")
    stripe_subscription_id = event_object.get("subscription")
    stripe_customer_id = event_object.get("customer")
    if not user_id or not stripe_subscription_id:
        logger.warning("checkout.session.completed missing user_id/subscription: %s", event_object.get("id"))
        return

    sub = get_or_create_subscription(db, user_id)
    sub.tier = SubscriptionTier.pro.value
    sub.stripe_customer_id = stripe_customer_id
    sub.stripe_subscription_id = stripe_subscription_id
    db.commit()

    sub = sync_subscription_from_stripe(db, stripe_subscription_id)
    if sub:
        event_name = "trial_started" if sub.status == "trialing" else "checkout_completed"
        _capture(user_id, event_name, {"plan": sub.price_id})


def _handle_subscription_updated_or_deleted(db: Session, event_object: dict, deleted: bool) -> None:
    stripe_subscription_id = event_object.get("id")
    if not stripe_subscription_id:
        return
    sub = sync_subscription_from_stripe(db, stripe_subscription_id)
    if sub and deleted:
        _capture(sub.user_id, "subscription_canceled", {})


def _handle_invoice_payment_failed(db: Session, event_object: dict) -> None:
    stripe_subscription_id = event_object.get("subscription")
    if not stripe_subscription_id:
        return
    sub = (
        db.query(Subscription)
        .filter(Subscription.stripe_subscription_id == stripe_subscription_id)
        .first()
    )
    if not sub:
        return
    # customer.subscription.updated is the authoritative status source (Stripe emits
    # both); this is a best-effort early flag so the frontend can prompt sooner.
    sub.status = "past_due"
    db.commit()
    _capture(sub.user_id, "subscription_payment_failed", {})


def handle_webhook_event(db: Session, event: dict) -> None:
    event_type = event.get("type")
    obj = (event.get("data") or {}).get("object") or {}

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(db, obj)
    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated_or_deleted(db, obj, deleted=False)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_updated_or_deleted(db, obj, deleted=True)
    elif event_type == "invoice.payment_failed":
        _handle_invoice_payment_failed(db, obj)
    else:
        logger.info("Unhandled Stripe webhook event type: %s", event_type)
