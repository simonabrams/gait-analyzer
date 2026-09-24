"""
Anonymous-visitor identity: validates client-generated anon IDs and resolves
the effective user_id (real Clerk user or anonymous) for endpoints that must
work both signed-in and signed-out (see main.py's create_run/consent routes).
"""
import re

from fastapi import HTTPException

ANON_ID_RE = re.compile(
    r"^anon:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def validate_anon_id(anon_id: str | None) -> str | None:
    """Return the anon_id unchanged if it matches the expected `anon:<uuid>`
    shape, None if input is None, or raise 400 if it's present but malformed."""
    if anon_id is None:
        return None
    if not ANON_ID_RE.match(anon_id):
        raise HTTPException(status_code=400, detail="Invalid anonymous ID")
    return anon_id


def resolve_user_id(auth_user_id: str | None, x_anon_id: str | None) -> str:
    """Prefer a real authenticated user_id; fall back to a validated anon id.
    Raises 400 if neither is present."""
    if auth_user_id:
        return auth_user_id
    resolved = validate_anon_id(x_anon_id)
    if resolved is None:
        raise HTTPException(status_code=400, detail="Missing anonymous ID (X-Anon-Id header)")
    return resolved


def resolve_user_id_optional(auth_user_id: str | None, x_anon_id: str | None) -> str | None:
    """Like resolve_user_id, but tolerates having neither credential instead of
    raising — for endpoints that must stay fully public (e.g. a run's public
    status/detail, viewable by anyone with the link) but still want to know
    "is the caller the owner" when identity happens to be available. A
    malformed (present but invalid) x_anon_id still yields None rather than
    a 400 here, since an ownership check is best-effort on these endpoints,
    not a hard requirement to see the response at all."""
    if auth_user_id:
        return auth_user_id
    try:
        return validate_anon_id(x_anon_id)
    except HTTPException:
        return None
