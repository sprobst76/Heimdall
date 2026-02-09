"""LLM Service.

Integration with the Anthropic Claude API for:
- Quest proof photo verification (Vision)
- Natural language rule parsing
- Weekly report generation
- Child chatbot assistant
"""

import base64
import json
import logging
from pathlib import Path

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

def _get_client() -> anthropic.Anthropic:
    """Create an Anthropic client."""
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


MODEL = "claude-sonnet-4-5-20250929"
MAX_TOKENS = 1024


# ---------------------------------------------------------------------------
# 1. Photo Verification (Vision)
# ---------------------------------------------------------------------------

async def verify_quest_proof(
    image_path: str,
    quest_name: str,
    quest_description: str | None,
    ai_prompt: str | None = None,
) -> dict:
    """Verify a quest proof photo using Claude Vision.

    Returns:
        dict with keys: approved (bool), confidence (int 0-100), feedback (str)
    """
    client = _get_client()

    # Read image and encode as base64
    full_path = Path(settings.UPLOAD_DIR) / Path(image_path).name
    if not full_path.exists():
        return {
            "approved": False,
            "confidence": 0,
            "feedback": "Bild konnte nicht gefunden werden.",
        }

    image_data = base64.standard_b64encode(full_path.read_bytes()).decode("utf-8")

    # Determine media type
    suffix = full_path.suffix.lower()
    media_type_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    media_type = media_type_map.get(suffix, "image/jpeg")

    # Build the verification prompt
    if ai_prompt:
        verification_prompt = ai_prompt
    else:
        verification_prompt = (
            f'Analysiere dieses Foto als Nachweis für die Aufgabe: "{quest_name}".'
        )
        if quest_description:
            verification_prompt += f"\nBeschreibung: {quest_description}"
        verification_prompt += (
            "\nPrüfe ob das Foto plausibel zeigt, dass die Aufgabe erledigt wurde."
        )

    system_prompt = (
        "Du bist ein Aufgaben-Verifikationssystem für eine Kindersicherungs-App. "
        "Prüfe eingereichte Fotos auf Plausibilität. Sei fair aber genau. "
        "Antworte AUSSCHLIESSLICH mit einem JSON-Objekt im folgenden Format:\n"
        '{"approved": true/false, "confidence": 0-100, "feedback": "Kurze Begründung auf Deutsch"}\n'
        "Keine weitere Erklärung, nur das JSON."
    )

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": verification_prompt,
                        },
                    ],
                }
            ],
        )

        result_text = response.content[0].text.strip()
        # Parse JSON from response
        result = json.loads(result_text)
        return {
            "approved": bool(result.get("approved", False)),
            "confidence": int(result.get("confidence", 0)),
            "feedback": str(result.get("feedback", "")),
        }

    except json.JSONDecodeError:
        logger.warning("LLM returned non-JSON response for proof verification")
        return {
            "approved": False,
            "confidence": 0,
            "feedback": "Automatische Prüfung konnte nicht durchgeführt werden.",
        }
    except Exception as e:
        logger.error("LLM proof verification failed: %s", e)
        return {
            "approved": False,
            "confidence": 0,
            "feedback": f"Fehler bei der automatischen Prüfung: {e}",
        }


# ---------------------------------------------------------------------------
# 2. Natural Language Rule Parsing
# ---------------------------------------------------------------------------

async def parse_natural_language_rule(
    text: str,
    children: list[dict],
    app_groups: list[dict],
) -> dict:
    """Parse a natural language rule description into structured rule data.

    Args:
        text: Natural language rule like "Leo darf am Wochenende eine Stunde länger spielen"
        children: List of dicts with id, name for context
        app_groups: List of dicts with id, name, category for context

    Returns:
        dict with parsed rule structure
    """
    client = _get_client()

    children_info = ", ".join(f'{c["name"]} (ID: {c["id"]})' for c in children)
    groups_info = ", ".join(
        f'{g["name"]} (ID: {g["id"]}, Kategorie: {g.get("category", "")})' for g in app_groups
    )

    system_prompt = (
        "Du bist ein Regelparser für eine Kindersicherungs-App namens HEIMDALL. "
        "Eltern geben Regeln in natürlicher Sprache ein und du wandelst sie in strukturierte Daten um.\n\n"
        f"Bekannte Kinder: {children_info}\n"
        f"Bekannte App-Gruppen: {groups_info}\n\n"
        "Antworte AUSSCHLIESSLICH mit einem JSON-Objekt im folgenden Format:\n"
        "{\n"
        '  "action": "create_rule" | "modify_rule" | "create_exception",\n'
        '  "child_id": "UUID des Kindes oder null für alle",\n'
        '  "name": "Name der Regel",\n'
        '  "day_types": ["weekday", "weekend", "holiday", "vacation"],\n'
        '  "time_windows": [{"start": "HH:MM", "end": "HH:MM"}],\n'
        '  "daily_limit_minutes": null oder Zahl,\n'
        '  "group_limits": [{"group_id": "UUID", "max_minutes": Zahl}],\n'
        '  "priority": 10,\n'
        '  "valid_from": "YYYY-MM-DD oder null",\n'
        '  "valid_until": "YYYY-MM-DD oder null",\n'
        '  "explanation": "Kurze Erklärung was die Regel bewirkt"\n'
        "}\n"
        "Keine weitere Erklärung, nur das JSON."
    )

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": text}],
        )

        result_text = response.content[0].text.strip()
        result = json.loads(result_text)
        return {"success": True, "rule": result}

    except json.JSONDecodeError:
        return {
            "success": False,
            "error": "Konnte die Eingabe nicht als Regel interpretieren. Bitte formuliere es anders.",
        }
    except Exception as e:
        logger.error("LLM rule parsing failed: %s", e)
        return {"success": False, "error": f"Fehler: {e}"}


# ---------------------------------------------------------------------------
# 3. Weekly Report Generation
# ---------------------------------------------------------------------------

async def generate_weekly_report(
    child_name: str,
    usage_data: dict,
    quest_data: dict,
    tan_data: dict,
) -> str:
    """Generate a weekly report for a child.

    Args:
        child_name: Name of the child
        usage_data: dict with usage stats (total_hours, by_group, by_day, etc.)
        quest_data: dict with quest stats (completed, total, streak, etc.)
        tan_data: dict with TAN stats (redeemed, earned, etc.)

    Returns:
        Formatted markdown report text
    """
    client = _get_client()

    system_prompt = (
        "Du bist der Berichts-Generator der Kindersicherungs-App HEIMDALL. "
        "Erstelle einen freundlichen, informativen Wochenbericht für Eltern. "
        "Verwende Emojis sparsam aber effektiv. Schreibe auf Deutsch. "
        "Der Bericht soll folgende Abschnitte haben:\n"
        "1. Zusammenfassung (2-3 Sätze)\n"
        "2. Positive Entwicklungen\n"
        "3. Auffälligkeiten (falls vorhanden)\n"
        "4. Empfehlungen\n"
        "Halte den Bericht kurz und übersichtlich (max. 200 Wörter)."
    )

    context = (
        f"Wochenbericht für {child_name}:\n\n"
        f"Nutzungsdaten: {json.dumps(usage_data, ensure_ascii=False)}\n"
        f"Quest-Daten: {json.dumps(quest_data, ensure_ascii=False)}\n"
        f"TAN-Daten: {json.dumps(tan_data, ensure_ascii=False)}"
    )

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": context}],
        )
        return response.content[0].text.strip()

    except Exception as e:
        logger.error("LLM weekly report generation failed: %s", e)
        return f"Wochenbericht konnte nicht erstellt werden: {e}"


# ---------------------------------------------------------------------------
# 4. Child Chatbot
# ---------------------------------------------------------------------------

async def child_chat(
    message: str,
    child_name: str,
    context_data: dict,
    chat_history: list[dict] | None = None,
) -> str:
    """Process a chat message from a child.

    Args:
        message: The child's message
        child_name: Name of the child
        context_data: dict with current status (remaining time, quests, rules, etc.)
        chat_history: Previous messages in the conversation

    Returns:
        The assistant's response text
    """
    client = _get_client()

    system_prompt = (
        f"Du bist HEIMDALL, ein freundlicher digitaler Assistent für {child_name}. "
        "Du hilfst Kindern, ihre Bildschirmzeit zu verstehen und motivierst sie, Quests zu erledigen. "
        "Sprich kindgerecht, freundlich und ermutigend. Verwende Du-Anrede. "
        "Beantworte nur Fragen zu Bildschirmzeit, Quests, TANs und Regeln. "
        "Bei anderen Themen sage freundlich, dass du dafür nicht zuständig bist. "
        "Halte Antworten kurz (max. 3 Sätze). Verwende gelegentlich passende Emojis.\n\n"
        f"Aktueller Status:\n{json.dumps(context_data, ensure_ascii=False, indent=2)}"
    )

    messages = []
    if chat_history:
        for msg in chat_history[-10:]:  # Keep last 10 messages for context
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })
    messages.append({"role": "user", "content": message})

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=512,
            system=system_prompt,
            messages=messages,
        )
        return response.content[0].text.strip()

    except Exception as e:
        logger.error("LLM child chat failed: %s", e)
        return "Entschuldigung, ich kann gerade nicht antworten. Versuche es gleich nochmal! 🔧"
