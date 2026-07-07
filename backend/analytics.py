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
    if posthog_client:
        posthog_client.capture(user_id, event, properties=properties or {})
