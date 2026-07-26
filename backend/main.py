"""
FastAPI app: runs API, health, CORS.
"""
import base64
import hashlib
import hmac
import json
import logging
import os
import tempfile
import time
import uuid

from pathlib import Path

import jwt
import redis as redis_lib
import sentry_sdk
import stripe
from cachetools import TTLCache
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from jwt import PyJWKClient
from pythonjsonlogger import jsonlogger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from backend import billing, consent, storage
from backend.analytics import posthog_client
from backend.database import get_db
from backend.models import Run, RunStatus, Subscription, SubscriptionTier
from backend.schemas import (
    BillingStatusResponse,
    CheckoutRequest,
    CheckoutResponse,
    ConsentAcceptRequest,
    ConsentStatusResponse,
    PortalResponse,
    RunCreatedResponse,
    RunDetail,
    RunListItem,
    RunListResponse,
    RunStatusResponse,
)
from backend.storage import (
    delete_object,
    generate_presigned_url,
    raw_video_key,
    upload_file,
)

# ---------------------------------------------------------------------------
# Logging — structured JSON in production, plain text in local dev
# ---------------------------------------------------------------------------
_log_handler = logging.StreamHandler()
_log_handler.setFormatter(jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[_log_handler])
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sentry
# ---------------------------------------------------------------------------
SENTRY_DSN = os.environ.get("SENTRY_DSN", "").strip()
if SENTRY_DSN:
    sentry_sdk.init(dsn=SENTRY_DSN)
    logger.info("Sentry initialised")

if posthog_client:
    logger.info("PostHog initialised")

# ---------------------------------------------------------------------------
# Presigned URL cache — avoids an R2 round-trip on every page load.
# TTL is 30 min; presigned URLs themselves are valid for 1 hour.
# ---------------------------------------------------------------------------
_presigned_cache: TTLCache = TTLCache(maxsize=512, ttl=1800)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Runlens.io API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# JWT auth — Clerk RS256 verification via JWKS
# Set CLERK_JWKS_URL to your Clerk app's JWKS endpoint, e.g.:
#   https://<your-clerk-domain>/.well-known/jwks.json
# Leave unset to disable auth checks in local dev (all requests accepted).
# ---------------------------------------------------------------------------
CLERK_JWKS_URL = os.environ.get("CLERK_JWKS_URL", "").strip()
_jwks_client: PyJWKClient | None = None
if CLERK_JWKS_URL:
    _jwks_client = PyJWKClient(CLERK_JWKS_URL, cache_keys=True)
    logger.info("Clerk JWT auth enabled")
else:
    logger.warning("CLERK_JWKS_URL not set — JWT auth disabled (dev mode)")

_DEV_USER = "dev-user"

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")


def _verify_jwt(authorization: str) -> str:
    """Verify a Clerk Bearer JWT and return the Clerk user ID (sub claim).

    Raises HTTPException(401) on any auth failure.
    If CLERK_JWKS_URL is not configured (dev mode), returns _DEV_USER.
    """
    if not _jwks_client:
        return _DEV_USER

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization: Bearer <token>")

    token = authorization[7:]
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False},
            leeway=30,  # 30s tolerance for clock skew between browser and server
        )
        return payload["sub"]
    except jwt.ExpiredSignatureError as e:
        logger.warning("JWT expired (token issued before upload completed?): %s", e)
        raise HTTPException(status_code=401, detail="Token expired — please reload and try again")
    except Exception as e:
        logger.warning("JWT verification failed: %s: %s", type(e).__name__, e)
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_current_user(authorization: str = Header(default="")) -> str:
    return _verify_jwt(authorization)


_default_origins = "http://localhost:3000,http://127.0.0.1:3000,https://www.runlens.io,https://runlens.io"
_raw = (os.environ.get("CORS_ORIGINS") or "").strip()
origins = [o.strip() for o in (_raw or _default_origins).split(",") if o.strip()]
if not origins:
    origins = [o.strip() for o in _default_origins.split(",") if o.strip()]
logger.info("CORS allow_origins: %s", origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.exception_handler(Exception)
def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    headers = {}
    origin = request.headers.get("origin")
    if origin and origin in origins:
        headers["Access-Control-Allow-Origin"] = origin
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Check server logs."},
        headers=headers,
    )

ALLOWED_EXTENSIONS = {"mp4", "mov"}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB
_CHUNK = 65536  # 64 KB streaming chunks


def _get_run(db: Session, run_id: uuid.UUID) -> Run | None:
    return db.query(Run).filter(Run.id == run_id).first()


def _cached_presigned_url(r2_key: str) -> str:
    """Return a presigned URL, served from an in-process TTL cache."""
    if r2_key not in _presigned_cache:
        _presigned_cache[r2_key] = generate_presigned_url(r2_key)
    return _presigned_cache[r2_key]


# ---------------------------------------------------------------------------
# Health — verifies DB and Redis are reachable before returning 200
# ---------------------------------------------------------------------------
_redis_client = redis_lib.from_url(
    os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
    socket_connect_timeout=2,
)


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    failing = []

    # Database check
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("Health check: DB unreachable: %s", exc)
        failing.append("database")

    # Redis check
    try:
        _redis_client.ping()
    except Exception as exc:
        logger.error("Health check: Redis unreachable: %s", exc)
        failing.append("redis")

    if failing:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "failing": failing},
        )
    return {"status": "ok"}


@app.get("/api/local-artifacts/{run_id}/{filename}")
def serve_local_artifact(run_id: str, filename: str):
    if filename not in ("annotated.mp4", "dashboard.png") or ".." in run_id or "/" in run_id:
        raise HTTPException(404, "Not found")
    if not storage.LOCAL_STORAGE_PATH:
        raise HTTPException(404, "Not found")
    root = Path(storage.LOCAL_STORAGE_PATH).resolve()
    path = (root / "processed" / run_id / filename).resolve()
    if not path.is_file() or not str(path).startswith(str(root)):
        raise HTTPException(404, "Not found")
    return FileResponse(path, media_type="video/mp4" if filename.endswith(".mp4") else "image/png")


# ---------------------------------------------------------------------------
# POST /api/runs — create a run (requires auth; run is owned by the caller)
# ---------------------------------------------------------------------------
@app.post("/api/runs", response_model=RunCreatedResponse)
@limiter.limit("10/hour")
async def create_run(
    request: Request,
    file: UploadFile = File(...),
    height_cm: int = Form(..., ge=100, le=250),
    referral_code: str | None = Form(None),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    # Consent gate comes first: no video may be accepted (or free scan burned)
    # without a logged consent to the current policy version.
    if not consent.get_consent(db, user_id):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "consent_required",
                "message": "Please review and accept the privacy policy before uploading.",
            },
        )

    sub = billing.get_or_create_subscription(db, user_id)
    if not billing.has_active_access(sub):
        if sub.tier == SubscriptionTier.pro.value:
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "subscription_inactive",
                    "message": "Your Pro subscription is inactive. Please update your payment method.",
                },
            )
        if sub.free_scans_used >= 1 + sub.bonus_scans:
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "free_scan_used",
                    "message": "You've used your free scan. Upgrade to Pro for unlimited scans.",
                },
            )

    if referral_code and not sub.referred_by_code and referral_code != sub.referral_code:
        is_first_run = db.query(Run).filter(Run.user_id == user_id).count() == 0
        if is_first_run and db.query(Subscription).filter(Subscription.referral_code == referral_code).first():
            sub.referred_by_code = referral_code
            db.commit()

    suffix = (file.filename or "").split(".")[-1].lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Only MP4 and MOV files are allowed")

    # Validate magic bytes: all MP4/MOV containers have 'ftyp' at bytes 4–7
    header = await file.read(12)
    if header[4:8] != b"ftyp":
        raise HTTPException(400, "Invalid file: not a valid MP4 or MOV container")
    await file.seek(0)

    # Stream the upload to a temp file in 64 KB chunks instead of reading into RAM.
    run_id = uuid.uuid4()
    raw_key = raw_video_key(str(run_id))
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp_path = tmp.name
            total_bytes = 0
            while True:
                chunk = await file.read(_CHUNK)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_FILE_SIZE:
                    raise HTTPException(400, "File too large (max 500 MB)")
                tmp.write(chunk)
        upload_file(tmp_path, raw_key)
    except HTTPException:
        raise
    except RuntimeError as e:
        if "R2" in str(e) or "LOCAL_STORAGE" in str(e):
            raise HTTPException(
                503,
                "Storage not configured. Set LOCAL_STORAGE_PATH (e.g. .local_storage) or R2 credentials.",
            ) from e
        raise
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    run = Run(
        id=run_id,
        user_id=user_id,
        height_cm=height_cm,
        status=RunStatus.processing,
        progress_pct=0,
        raw_video_r2_key=raw_key,
    )
    db.add(run)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception("DB commit failed for run %s: %s", run_id, e)
        raise HTTPException(500, "Database error. Check server logs.") from e

    if sub.tier == SubscriptionTier.free.value:
        sub.free_scans_used += 1
        db.commit()

    try:
        from backend.worker import process_video
        process_video.delay(str(run_id), raw_key, height_cm)
    except Exception as e:
        logger.exception("Failed to enqueue job for run %s: %s", run_id, e)
        raise HTTPException(
            503,
            "Job queue unavailable. Is Redis running?",
        ) from e
    logger.info("Run created", extra={"run_id": str(run_id), "height_cm": height_cm, "user_id": user_id})
    if posthog_client:
        posthog_client.capture(
            user_id,
            "run_created",
            properties={"file_format": suffix},
        )
    return RunCreatedResponse(run_id=run_id, status="processing")


# ---------------------------------------------------------------------------
# GET /api/runs/{run_id}/status — public (anyone with UUID can poll status)
# ---------------------------------------------------------------------------
@app.get("/api/runs/{run_id}/status", response_model=RunStatusResponse)
@limiter.limit("120/minute")
def get_run_status(
    request: Request,
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    run = _get_run(db, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    preprocessing_warning = None
    if (run.preprocessing_meta or {}).get("was_trimmed"):
        preprocessing_warning = "Video trimmed to 3 minutes"
    return RunStatusResponse(
        status=run.status.value,
        progress=run.progress_pct or 0,
        preprocessing_warning=preprocessing_warning,
    )


# ---------------------------------------------------------------------------
# GET /api/runs/{run_id} — public (anyone with UUID can view; enables sharing)
# ---------------------------------------------------------------------------
@app.get("/api/runs/{run_id}", response_model=RunDetail)
@limiter.limit("60/minute")
def get_run(
    request: Request,
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    run = _get_run(db, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    detail = RunDetail(
        run_id=run.id,
        created_at=run.created_at,
        recorded_at=run.recorded_at,
        height_cm=run.height_cm,
        status=run.status.value,
        results=run.results_json,
        error_message=run.error_message,
    )
    if run.status == RunStatus.complete and run.results_json:
        if run.annotated_video_r2_key:
            detail.annotated_video_url = _cached_presigned_url(run.annotated_video_r2_key)
        if run.dashboard_image_r2_key:
            detail.dashboard_image_url = _cached_presigned_url(run.dashboard_image_r2_key)
    if posthog_client and run.user_id:
        posthog_client.capture(
            run.user_id,
            "run_viewed",
            properties={"run_status": run.status.value},
        )
    return detail


# ---------------------------------------------------------------------------
# GET /api/runs/{run_id}/report.pdf — auth + ownership + Pro gated (paid feature,
# unlike the public detail/share routes above)
# ---------------------------------------------------------------------------
@app.get("/api/runs/{run_id}/report.pdf")
def get_run_report_pdf(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    run = _get_run(db, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    # Return 404 (not 403) so we don't leak that the run exists — same as DELETE
    if run.user_id != user_id:
        raise HTTPException(404, "Run not found")
    if run.status != RunStatus.complete:
        raise HTTPException(400, "Run is not complete yet")

    sub = billing.get_or_create_subscription(db, user_id)
    if not billing.has_active_access(sub):
        raise HTTPException(
            status_code=402,
            detail={"code": "pro_required", "message": "PDF report export is a Pro feature."},
        )

    from backend.pdf_report import build_run_report_pdf

    fd, pdf_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    try:
        build_run_report_pdf(run, pdf_path)
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
    finally:
        try:
            os.unlink(pdf_path)
        except OSError:
            pass

    if posthog_client:
        posthog_client.capture(user_id, "pdf_report_downloaded", properties={"run_id": str(run_id)})

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="runlens-report-{run_id}.pdf"'},
    )


# ---------------------------------------------------------------------------
# GET /api/runs — list runs for the authenticated user only
# ---------------------------------------------------------------------------
@app.get("/api/runs", response_model=RunListResponse)
@limiter.limit("60/minute")
def list_runs(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    q = db.query(Run).filter(Run.user_id == user_id)
    total: int = q.with_entities(func.count(Run.id)).scalar()
    runs = q.order_by(Run.created_at.desc()).limit(limit).offset(offset).all()
    items = []
    for r in runs:
        summary = (r.results_json or {}).get("summary") or {}
        flags = (r.results_json or {}).get("flags") or []
        items.append(
            RunListItem(
                run_id=r.id,
                created_at=r.created_at,
                recorded_at=r.recorded_at,
                cadence_avg=summary.get("cadence_avg"),
                vertical_osc_avg_cm=summary.get("vertical_osc_avg_cm"),
                knee_angle_strike_avg_deg=summary.get("knee_angle_strike_avg_deg"),
                flags_count=len(flags),
            )
        )
    return RunListResponse(total=total, items=items)


# ---------------------------------------------------------------------------
# DELETE /api/runs/{run_id} — requires auth; only owner can delete
# ---------------------------------------------------------------------------
@app.delete("/api/runs/{run_id}", status_code=204)
def delete_run(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    run = _get_run(db, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    # Return 404 (not 403) so we don't leak that the run exists
    if run.user_id != user_id:
        raise HTTPException(404, "Run not found")
    # Storage deletion must succeed before the DB row goes away — otherwise we
    # tell the user their video is gone while it survives in R2 with no
    # reconciliation path. Failing here leaves the run intact so they can retry.
    try:
        for key in [run.raw_video_r2_key, run.annotated_video_r2_key, run.dashboard_image_r2_key]:
            if key:
                delete_object(key)
                _presigned_cache.pop(key, None)
    except Exception as e:
        logger.error("Storage delete failed for run %s: %s", run_id, e)
        raise HTTPException(502, "Couldn't delete the stored files. Please try again.") from e
    run_status = run.status.value
    db.delete(run)
    db.commit()
    logger.info("Run deleted", extra={"run_id": str(run_id), "user_id": user_id})
    if posthog_client:
        posthog_client.capture(
            user_id,
            "run_deleted",
            properties={"run_status": run_status},
        )
    return None


# ---------------------------------------------------------------------------
# Consent — privacy-policy consent status + acceptance (see backend/consent.py)
# ---------------------------------------------------------------------------


@app.get("/api/consent", response_model=ConsentStatusResponse)
def get_consent_status(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    record = consent.get_consent(db, user_id)
    return ConsentStatusResponse(
        policy_version=consent.PRIVACY_POLICY_VERSION,
        consented=record is not None,
        consented_at=record.created_at if record else None,
    )


@app.post("/api/consent", response_model=ConsentStatusResponse)
def accept_consent(
    body: ConsentAcceptRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    # Reject consent to any version other than the current one — a stale client
    # must reload and re-present the current policy, not log outdated consent.
    if body.policy_version != consent.PRIVACY_POLICY_VERSION:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "stale_policy_version",
                "message": "The privacy policy has been updated. Please reload and review the current version.",
            },
        )
    consented_at = consent.record_consent(db, user_id, body.policy_version)
    logger.info(
        "Consent recorded",
        extra={"user_id": user_id, "policy_version": body.policy_version},
    )
    if posthog_client:
        posthog_client.capture(
            user_id,
            "consent_accepted",
            properties={"policy_version": body.policy_version},
        )
    return ConsentStatusResponse(
        policy_version=consent.PRIVACY_POLICY_VERSION,
        consented=True,
        consented_at=consented_at,
    )


# ---------------------------------------------------------------------------
# Billing — Stripe Checkout, Customer Portal, status, and webhook
# ---------------------------------------------------------------------------
def _billing_status_response(sub: Subscription) -> BillingStatusResponse:
    return BillingStatusResponse(
        tier=sub.tier,
        status=sub.status,
        is_pro=billing.has_active_access(sub),
        trial_end=sub.trial_end,
        current_period_end=sub.current_period_end,
        cancel_at_period_end=sub.cancel_at_period_end,
        free_scans_used=sub.free_scans_used,
        bonus_scans=sub.bonus_scans,
        referral_code=sub.referral_code,
        referral_link=f"{FRONTEND_URL}/?ref={sub.referral_code}",
    )


@app.get("/api/billing/status", response_model=BillingStatusResponse)
def get_billing_status(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    sub = billing.get_or_create_subscription(db, user_id)
    return _billing_status_response(sub)


@app.post("/api/billing/checkout", response_model=CheckoutResponse)
def create_checkout(
    body: CheckoutRequest,
    email: str | None = Header(default=None, alias="X-User-Email"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    sub = billing.get_or_create_subscription(db, user_id)
    try:
        session = billing.create_checkout_session(
            sub,
            plan=body.plan,
            email=email,
            success_url=f"{FRONTEND_URL}/account/billing?checkout=success",
            cancel_url=f"{FRONTEND_URL}/pricing?checkout=canceled",
        )
    except Exception as e:
        logger.exception("Stripe checkout session creation failed for user %s: %s", user_id, e)
        raise HTTPException(502, "Could not start checkout. Please try again.") from e
    return CheckoutResponse(url=session.url)


@app.post("/api/billing/portal", response_model=PortalResponse)
def create_portal(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    sub = billing.get_or_create_subscription(db, user_id)
    if not sub.stripe_customer_id:
        raise HTTPException(404, "No billing account yet — start a Pro checkout first")
    try:
        session = billing.create_portal_session(
            sub.stripe_customer_id,
            return_url=f"{FRONTEND_URL}/account/billing",
        )
    except Exception as e:
        logger.exception("Stripe portal session creation failed for user %s: %s", user_id, e)
        raise HTTPException(502, "Could not open billing portal. Please try again.") from e
    return PortalResponse(url=session.url)


# ---------------------------------------------------------------------------
# Clerk webhook — account-deletion cascade (GDPR/CCPA deletion path).
# Configure in Clerk dashboard: endpoint /api/webhooks/clerk, event user.deleted,
# and set CLERK_WEBHOOK_SECRET to the endpoint's signing secret (whsec_...).
# ---------------------------------------------------------------------------
CLERK_WEBHOOK_SECRET = os.environ.get("CLERK_WEBHOOK_SECRET", "").strip()


def _verify_svix_signature(secret: str, msg_id: str, timestamp: str, payload: bytes, sig_header: str) -> bool:
    """Verify a Svix webhook signature (Clerk delivers via Svix).

    Scheme: base64(HMAC-SHA256(base64decode(secret), "{id}.{timestamp}.{body}")),
    sent as space-separated "v1,<sig>" entries in the svix-signature header.
    Implemented with stdlib to avoid a svix dependency.
    """
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    if abs(time.time() - ts) > 300:  # 5-min replay window, per Svix docs
        return False
    try:
        key = base64.b64decode(secret.removeprefix("whsec_"))
    except Exception:
        return False
    signed = f"{msg_id}.{timestamp}.".encode() + payload
    expected = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
    for part in sig_header.split():
        version, _, sig = part.partition(",")
        if version == "v1" and hmac.compare_digest(sig, expected):
            return True
    return False


@app.post("/api/webhooks/clerk")
async def clerk_webhook(request: Request, db: Session = Depends(get_db)):
    if not CLERK_WEBHOOK_SECRET:
        raise HTTPException(503, "Clerk webhook not configured (set CLERK_WEBHOOK_SECRET)")
    payload = await request.body()
    if not _verify_svix_signature(
        CLERK_WEBHOOK_SECRET,
        request.headers.get("svix-id", ""),
        request.headers.get("svix-timestamp", ""),
        payload,
        request.headers.get("svix-signature", ""),
    ):
        raise HTTPException(400, "Invalid webhook signature")

    event = json.loads(payload)
    if event.get("type") != "user.deleted":
        return {"received": True}
    user_id = (event.get("data") or {}).get("id")
    if not user_id:
        return {"received": True}

    # Cascade: purge the user's runs (DB rows + stored videos/images) and
    # subscription. Consent records are intentionally kept as an append-only
    # audit trail (see ConsentRecord docstring). A run's DB row is only removed
    # once its storage deletes succeed, so a failed run survives for the Svix
    # retry to re-attempt — retries are the reconciliation loop.
    runs = db.query(Run).filter(Run.user_id == user_id).all()
    deleted, failed = 0, 0
    for run in runs:
        try:
            for key in (run.raw_video_r2_key, run.annotated_video_r2_key, run.dashboard_image_r2_key):
                if key:
                    delete_object(key)
                    _presigned_cache.pop(key, None)
        except Exception as e:
            logger.error("Storage delete failed during account deletion of %s (run %s): %s", user_id, run.id, e)
            failed += 1
            continue
        db.delete(run)
        deleted += 1
    db.query(Subscription).filter(Subscription.user_id == user_id).delete()
    db.commit()
    logger.info(
        "Account deletion cascade",
        extra={"user_id": user_id, "runs_deleted": deleted, "runs_failed": failed},
    )
    if failed:
        raise HTTPException(500, f"{failed} run(s) could not be fully deleted; awaiting retry")
    if posthog_client:
        posthog_client.capture(user_id, "account_deleted", properties={"runs_deleted": deleted})
    return {"received": True}


@app.post("/api/billing/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        # .to_dict() up front: StripeObject doesn't support .get(), which billing.py relies on.
        event = stripe.Webhook.construct_event(payload, sig_header, billing.WEBHOOK_SECRET).to_dict()
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        logger.warning("Stripe webhook signature verification failed: %s", e)
        raise HTTPException(400, "Invalid webhook signature") from e
    billing.handle_webhook_event(db, event)
    return {"received": True}
