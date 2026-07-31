"""Unit tests for backend.anon — anonymous-id validation and user resolution."""
import pytest
from fastapi import HTTPException

import backend.anon as anon

VALID = "anon:12345678-1234-5678-1234-567812345678"


def test_validate_anon_id_accepts_valid_shape():
    assert anon.validate_anon_id(VALID) == VALID


def test_validate_anon_id_accepts_uppercase_hex():
    upper = VALID.upper()
    assert anon.validate_anon_id(upper) == upper


def test_validate_anon_id_returns_none_for_none():
    assert anon.validate_anon_id(None) is None


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "12345678-1234-5678-1234-567812345678",  # missing anon: prefix
        "anon:not-a-uuid",
        "anon:12345678-1234-5678-1234-56781234567",  # one char short
        "anon:12345678-1234-5678-1234-5678123456789",  # one char long
        "user_2abcDEF",  # real Clerk id shape
        "anon:12345678-1234-5678-1234-567812345678; DROP TABLE runs;--",
    ],
)
def test_validate_anon_id_rejects_malformed(bad):
    with pytest.raises(HTTPException) as exc_info:
        anon.validate_anon_id(bad)
    assert exc_info.value.status_code == 400


def test_resolve_user_id_prefers_auth_over_anon():
    assert anon.resolve_user_id("user_real", VALID) == "user_real"


def test_resolve_user_id_falls_back_to_anon():
    assert anon.resolve_user_id(None, VALID) == VALID


def test_resolve_user_id_raises_when_both_absent():
    with pytest.raises(HTTPException) as exc_info:
        anon.resolve_user_id(None, None)
    assert exc_info.value.status_code == 400


def test_resolve_user_id_raises_on_malformed_anon_id_even_without_auth():
    with pytest.raises(HTTPException) as exc_info:
        anon.resolve_user_id(None, "not-a-valid-anon-id")
    assert exc_info.value.status_code == 400
