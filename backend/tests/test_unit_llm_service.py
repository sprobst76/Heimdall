"""Tests for LLM service with mocked Anthropic client."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.llm_service import (
    child_chat,
    generate_weekly_report,
    parse_natural_language_rule,
    verify_quest_proof,
)


def _mock_response(text: str) -> MagicMock:
    """Create a mock Anthropic API response with given text content."""
    content_block = MagicMock()
    content_block.text = text
    response = MagicMock()
    response.content = [content_block]
    return response


class TestVerifyQuestProof:
    @patch("app.services.llm_service._get_client")
    @patch("app.services.llm_service.settings")
    async def test_approved(self, mock_settings, mock_get_client):
        """High-confidence approval returns correct result."""
        # Create a temp image file
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"\xff\xd8\xff\xe0fake-jpeg-data")
            temp_path = f.name

        mock_settings.UPLOAD_DIR = str(Path(temp_path).parent)
        mock_settings.ANTHROPIC_API_KEY = "test-key"

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response(
            json.dumps({"approved": True, "confidence": 95, "feedback": "Aufgabe erledigt"})
        )
        mock_get_client.return_value = mock_client

        result = await verify_quest_proof(
            image_path=Path(temp_path).name,
            quest_name="Zimmer aufräumen",
            quest_description="Zimmer soll ordentlich sein",
        )

        assert result["approved"] is True
        assert result["confidence"] == 95
        assert result["feedback"] == "Aufgabe erledigt"
        mock_client.messages.create.assert_called_once()

        Path(temp_path).unlink(missing_ok=True)

    @patch("app.services.llm_service._get_client")
    @patch("app.services.llm_service.settings")
    async def test_rejected(self, mock_settings, mock_get_client):
        """Low-confidence rejection returns correct result."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"\x89PNGfake-png-data")
            temp_path = f.name

        mock_settings.UPLOAD_DIR = str(Path(temp_path).parent)
        mock_settings.ANTHROPIC_API_KEY = "test-key"

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response(
            json.dumps({"approved": False, "confidence": 20, "feedback": "Nicht erkennbar"})
        )
        mock_get_client.return_value = mock_client

        result = await verify_quest_proof(
            image_path=Path(temp_path).name,
            quest_name="Abspülen",
            quest_description=None,
        )

        assert result["approved"] is False
        assert result["confidence"] == 20

        Path(temp_path).unlink(missing_ok=True)

    @patch("app.services.llm_service._get_client")
    @patch("app.services.llm_service.settings")
    async def test_invalid_json_fallback(self, mock_settings, mock_get_client):
        """Non-JSON response gracefully falls back."""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"\xff\xd8\xff\xe0fake")
            temp_path = f.name

        mock_settings.UPLOAD_DIR = str(Path(temp_path).parent)
        mock_settings.ANTHROPIC_API_KEY = "test-key"

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response(
            "Sorry, I cannot verify this image properly."
        )
        mock_get_client.return_value = mock_client

        result = await verify_quest_proof(
            image_path=Path(temp_path).name,
            quest_name="Test",
            quest_description=None,
        )

        assert result["approved"] is False
        assert result["confidence"] == 0
        assert "nicht durchgeführt" in result["feedback"]

        Path(temp_path).unlink(missing_ok=True)

    @patch("app.services.llm_service.settings")
    async def test_missing_image(self, mock_settings):
        """Missing image file returns error result."""
        mock_settings.UPLOAD_DIR = "/tmp/nonexistent_dir_12345"

        result = await verify_quest_proof(
            image_path="nonexistent.jpg",
            quest_name="Test",
            quest_description=None,
        )

        assert result["approved"] is False
        assert result["confidence"] == 0
        assert "nicht gefunden" in result["feedback"]


class TestParseNaturalLanguageRule:
    @patch("app.services.llm_service._get_client")
    async def test_success(self, mock_get_client):
        """Successful rule parsing returns structured data."""
        rule_json = {
            "action": "create_rule",
            "child_id": "abc-123",
            "name": "Wochenend-Bonus",
            "day_types": ["weekend"],
            "time_windows": [{"start": "08:00", "end": "20:00"}],
            "daily_limit_minutes": 180,
            "group_limits": [],
            "priority": 10,
            "valid_from": None,
            "valid_until": None,
            "explanation": "Am Wochenende 3 Stunden erlaubt",
        }

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response(json.dumps(rule_json))
        mock_get_client.return_value = mock_client

        result = await parse_natural_language_rule(
            text="Leo darf am Wochenende 3 Stunden spielen",
            children=[{"id": "abc-123", "name": "Leo"}],
            app_groups=[{"id": "grp-1", "name": "Spiele", "category": "gaming"}],
        )

        assert result["success"] is True
        assert result["rule"]["action"] == "create_rule"
        assert result["rule"]["daily_limit_minutes"] == 180

    @patch("app.services.llm_service._get_client")
    async def test_unparseable_input(self, mock_get_client):
        """Non-JSON LLM response returns error."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response(
            "Ich verstehe die Regel nicht ganz."
        )
        mock_get_client.return_value = mock_client

        result = await parse_natural_language_rule(
            text="???",
            children=[],
            app_groups=[],
        )

        assert result["success"] is False
        assert "error" in result


class TestGenerateWeeklyReport:
    @patch("app.services.llm_service._get_client")
    async def test_report_generated(self, mock_get_client):
        """Weekly report returns markdown text."""
        report_text = "## Wochenbericht für Leo\n\nLeo hat diese Woche 5 Quests erledigt!"

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response(report_text)
        mock_get_client.return_value = mock_client

        result = await generate_weekly_report(
            child_name="Leo",
            usage_data={"total_hours": 14},
            quest_data={"completed": 5, "total": 7},
            tan_data={"redeemed": 3},
        )

        assert "Leo" in result
        assert "Quests" in result


class TestChildChat:
    @patch("app.services.llm_service._get_client")
    async def test_chat_response(self, mock_get_client):
        """Chat returns assistant response."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response(
            "Du hast noch 45 Minuten übrig! 🎮"
        )
        mock_get_client.return_value = mock_client

        result = await child_chat(
            message="Wie viel Zeit hab ich noch?",
            child_name="Leo",
            context_data={"remaining_minutes": 45, "quests_today": 2},
        )

        assert "45 Minuten" in result

    @patch("app.services.llm_service._get_client")
    async def test_chat_with_history(self, mock_get_client):
        """Chat history is included in API call."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response("Ja, du hast 2 Quests offen!")
        mock_get_client.return_value = mock_client

        history = [
            {"role": "user", "content": "Hallo!"},
            {"role": "assistant", "content": "Hallo Leo! 👋"},
        ]

        result = await child_chat(
            message="Habe ich noch Quests?",
            child_name="Leo",
            context_data={"quests_open": 2},
            chat_history=history,
        )

        # Verify history + new message are passed
        call_args = mock_client.messages.create.call_args
        messages = call_args.kwargs["messages"]
        assert len(messages) == 3  # 2 history + 1 new
        assert messages[0]["content"] == "Hallo!"
        assert messages[2]["content"] == "Habe ich noch Quests?"
