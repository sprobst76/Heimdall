"""Unit tests for TAN service logic — no database required."""

import os
import re

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests")

from app.services.tan_service import WORD_LIST, _generate_code


class TestTANCodeGeneration:
    def test_code_format(self):
        """Code should match WORD-NNNN pattern."""
        code = _generate_code()
        assert re.match(r"^[A-Z]+-\d{4}$", code), f"Unexpected format: {code}"

    def test_code_word_from_list(self):
        """The word part should be from the mythological word list."""
        code = _generate_code()
        word = code.split("-")[0]
        assert word in WORD_LIST, f"{word} not in WORD_LIST"

    def test_code_digits_four_chars(self):
        """Digits should always be 4 characters (zero-padded)."""
        for _ in range(50):
            code = _generate_code()
            digits = code.split("-")[1]
            assert len(digits) == 4

    def test_codes_are_random(self):
        """Multiple generated codes should not all be identical."""
        codes = {_generate_code() for _ in range(20)}
        assert len(codes) > 1, "All 20 generated codes are identical"

    def test_word_list_not_empty(self):
        assert len(WORD_LIST) >= 10
