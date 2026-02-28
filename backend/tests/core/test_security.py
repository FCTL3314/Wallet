from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def test_hash_and_verify_password():
    hashed = hash_password("Secret123")
    assert verify_password("Secret123", hashed)


def test_wrong_password():
    hashed = hash_password("Secret123")
    assert not verify_password("Wrong456", hashed)


def test_access_token_roundtrip():
    token = create_access_token(42)
    assert decode_access_token(token) == 42


def test_invalid_token_returns_none():
    assert decode_access_token("not.a.token") is None


def test_expired_token_returns_none():
    from datetime import datetime, timedelta, timezone

    from jose import jwt

    from app.core.config import settings

    expired_payload = {
        "sub": "1",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    assert decode_access_token(token) is None


def test_refresh_token_pair():
    raw, hashed = create_refresh_token()
    assert len(raw) > 20
    assert len(hashed) == 64  # sha256 hex digest


def test_hash_refresh_token_deterministic():
    raw, hashed = create_refresh_token()
    assert hash_refresh_token(raw) == hashed
