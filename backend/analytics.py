"""
Shared PostHog client. Import posthog_client (or capture()) from here instead
of constructing a new client per module — avoids running multiple live
clients/background threads in the same process.
"""
import atexit
import os

from posthog import Posthog

_POSTHOG_TOKEN = os.environ.get("POSTHOG_PROJECT_TOKEN", "").strip()
_POSTHOG_HOST = os.environ.get("POSTHOG_HOST", "https://us.i.posthog.com").strip()

posthog_client: Posthog | None = None
if _POSTHOG_TOKEN:
    posthog_client = Posthog(
        project_api_key=_POSTHOG_TOKEN,
        host=_POSTHOG_HOST,
        enable_exception_autocapture=True,
    )
    atexit.register(posthog_client.shutdown)


def capture(user_id: str, event: str, properties: dict | None = None) -> None:
    # posthog>=6 moved `event` to the sole positional arg and made distinct_id/
    # properties keyword-only (capture(event, distinct_id=..., properties=...)) —
    # a breaking change from the v3.x API this call site was originally written
    # against. Route all capture() calls through this one wrapper so a future
    # SDK signature change only needs fixing here.
    if posthog_client:
        posthog_client.capture(event, distinct_id=user_id, properties=properties or {})
