"""Unit tests for totp_service.py — no database required."""

import os
import re

import pyotp
import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests")

from app.services.totp_service import (  # noqa: E402
    generate_totp_secret,
    get_provisioning_uri,
    verify_totp_code,
)


class TestTotpSecretGeneration:
    def test_returns_valid_base32_string(self):
        """Secret must consist only of Base32 characters (A-Z, 2-7, optional = padding)."""
        secret = generate_totp_secret()
        assert re.match(r"^[A-Z2-7]+=*$", secret), f"Unexpected format: {secret!r}"

    def test_minimum_length(self):
        """TOTP spec: at least 128 bit entropy = 16 unpadded Base32 characters."""
        secret = generate_totp_secret()
        assert len(secret.rstrip("=")) >= 16

    def test_secrets_are_random(self):
        """Multiple calls must not all return the same secret."""
        secrets = {generate_totp_secret() for _ in range(10)}
        assert len(secrets) > 1, "All 10 generated secrets are identical"


class TestGetProvisioningUri:
    def test_uri_starts_with_otpauth(self):
        secret = generate_totp_secret()
        uri = get_provisioning_uri(secret, "Kind", "Familie")
        assert uri.startswith("otpauth://totp/")

    def test_uri_contains_issuer_heimdall(self):
        uri = get_provisioning_uri(generate_totp_secret(), "Kind", "TestFamilie")
        assert "Heimdall" in uri

    def test_uri_contains_child_name(self):
        uri = get_provisioning_uri(generate_totp_secret(), "MaxKind", "TestFamilie")
        assert "MaxKind" in uri

    def test_uri_is_string(self):
        secret = generate_totp_secret()
        uri = get_provisioning_uri(secret, "Kind", "Familie")
        assert isinstance(uri, str)


class TestVerifyTotpCode:
    def test_valid_current_code_passes(self):
        """A code generated right now must pass verification."""
        secret = generate_totp_secret()
        code = pyotp.TOTP(secret).now()
        assert verify_totp_code(secret, code) is True

    def test_random_code_fails(self):
        """An obviously wrong code must be rejected."""
        secret = generate_totp_secret()
        # "000000" is a valid-looking code but astronomically unlikely to match.
        # We check at least 3 different invalid codes to be safe.
        wrong_codes = ["aaaaaa", "zzzzzz", "------"]
        for code in wrong_codes:
            assert verify_totp_code(secret, code) is False

    def test_wrong_secret_fails(self):
        """A code generated with one secret must not validate against a different secret."""
        secret_a = generate_totp_secret()
        secret_b = generate_totp_secret()
        code = pyotp.TOTP(secret_a).now()
        # Only fails if secrets differ (extremely likely)
        if secret_a != secret_b:
            assert verify_totp_code(secret_b, code) is False

    def test_returns_bool(self):
        secret = generate_totp_secret()
        result = verify_totp_code(secret, "123456")
        assert isinstance(result, bool)
