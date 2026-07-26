"""Unit tests for the Svix (Clerk) webhook signature verification — pure
function, per the repo's no-DB-harness testing pattern (see test_billing.py)."""
import base64
import hashlib
import hmac
import time

from backend.main import _verify_svix_signature

SECRET_KEY = base64.b64encode(b"test-signing-key-32-bytes-long!!").decode()
SECRET = f"whsec_{SECRET_KEY}"
PAYLOAD = b'{"type":"user.deleted","data":{"id":"user_123"}}'
MSG_ID = "msg_abc"


def _sign(msg_id: str, ts: str, payload: bytes, secret_b64: str = SECRET_KEY) -> str:
    key = base64.b64decode(secret_b64)
    signed = f"{msg_id}.{ts}.".encode() + payload
    return base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()


def test_valid_signature_passes():
    ts = str(int(time.time()))
    sig = _sign(MSG_ID, ts, PAYLOAD)
    assert _verify_svix_signature(SECRET, MSG_ID, ts, PAYLOAD, f"v1,{sig}")


def test_secret_without_whsec_prefix_also_works():
    ts = str(int(time.time()))
    sig = _sign(MSG_ID, ts, PAYLOAD)
    assert _verify_svix_signature(SECRET_KEY, MSG_ID, ts, PAYLOAD, f"v1,{sig}")


def test_wrong_signature_fails():
    ts = str(int(time.time()))
    assert not _verify_svix_signature(SECRET, MSG_ID, ts, PAYLOAD, "v1,AAAA")


def test_tampered_payload_fails():
    ts = str(int(time.time()))
    sig = _sign(MSG_ID, ts, PAYLOAD)
    assert not _verify_svix_signature(SECRET, MSG_ID, ts, b'{"type":"user.deleted","data":{"id":"user_999"}}', f"v1,{sig}")


def test_expired_timestamp_fails():
    ts = str(int(time.time()) - 600)  # outside the 5-min replay window
    sig = _sign(MSG_ID, ts, PAYLOAD)
    assert not _verify_svix_signature(SECRET, MSG_ID, ts, PAYLOAD, f"v1,{sig}")


def test_non_numeric_timestamp_fails():
    assert not _verify_svix_signature(SECRET, MSG_ID, "not-a-number", PAYLOAD, "v1,AAAA")


def test_multiple_signatures_one_valid_passes():
    ts = str(int(time.time()))
    sig = _sign(MSG_ID, ts, PAYLOAD)
    assert _verify_svix_signature(SECRET, MSG_ID, ts, PAYLOAD, f"v1,BOGUS v1,{sig}")


def test_non_v1_version_is_ignored():
    ts = str(int(time.time()))
    sig = _sign(MSG_ID, ts, PAYLOAD)
    assert not _verify_svix_signature(SECRET, MSG_ID, ts, PAYLOAD, f"v2,{sig}")
