"""Unit tests for core/security.py — no database required."""

import os
from datetime import timedelta

import pytest

# Ensure settings can be loaded without .env
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests")

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)


# ── Password hashing ────────────────────────────────────────────────────────


class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "sichere-passwort-123"
        hashed = get_password_hash(password)
        assert hashed != password
        assert verify_password(password, hashed)

    def test_wrong_password_rejected(self):
        hashed = get_password_hash("correct-password")
        assert not verify_password("wrong-password", hashed)

    def test_different_hashes_for_same_password(self):
        pw = "same-password"
        h1 = get_password_hash(pw)
        h2 = get_password_hash(pw)
        assert h1 != h2  # bcrypt uses random salt

    def test_empty_password(self):
        hashed = get_password_hash("")
        assert verify_password("", hashed)
        assert not verify_password("not-empty", hashed)


# ── JWT tokens ───────────────────────────────────────────────────────────────


class TestJWT:
    def test_access_token_roundtrip(self):
        data = {"sub": "user-123"}
        token = create_access_token(data)
        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"

    def test_refresh_token_roundtrip(self):
        data = {"sub": "user-456"}
        token = create_refresh_token(data)
        payload = decode_token(token)
        assert payload["sub"] == "user-456"
        assert payload["type"] == "refresh"

    def test_access_token_has_expiry(self):
        token = create_access_token({"sub": "test"})
        payload = decode_token(token)
        assert "exp" in payload

    def test_custom_expiry(self):
        token = create_access_token(
            {"sub": "test"}, expires_delta=timedelta(minutes=5)
        )
        payload = decode_token(token)
        assert "exp" in payload

    def test_invalid_token_raises(self):
        from jose import JWTError

        with pytest.raises(JWTError):
            decode_token("invalid.token.here")

    def test_tampered_token_raises(self):
        from jose import JWTError

        token = create_access_token({"sub": "test"})
        # Tamper with the token
        parts = token.split(".")
        parts[1] = parts[1] + "x"
        tampered = ".".join(parts)
        with pytest.raises(JWTError):
            decode_token(tampered)

    def test_original_data_not_mutated(self):
        data = {"sub": "user-789"}
        create_access_token(data)
        assert data == {"sub": "user-789"}  # no "exp" or "type" added
