"""LLM Schemas.

Pydantic models for LLM-related request/response bodies.
"""

from pydantic import BaseModel


class VerifyProofRequest(BaseModel):
    quest_instance_id: str
    """The quest instance ID to verify the proof for."""


class VerifyProofResponse(BaseModel):
    approved: bool
    confidence: int
    feedback: str
    auto_approved: bool = False
    """Whether the quest was auto-approved (confidence >= threshold)."""


class ParseRuleRequest(BaseModel):
    text: str
    """Natural language rule description."""
    child_id: str | None = None
    """Optional: scope to a specific child's app groups."""


class ParseRuleResponse(BaseModel):
    success: bool
    rule: dict | None = None
    error: str | None = None


class WeeklyReportRequest(BaseModel):
    child_id: str
    """Child to generate the report for."""


class WeeklyReportResponse(BaseModel):
    child_id: str
    child_name: str
    report: str
    """Markdown-formatted weekly report."""


class ChatRequest(BaseModel):
    message: str
    """The child's message."""
    history: list[dict] | None = None
    """Previous chat messages for context."""


class ChatResponse(BaseModel):
    response: str
    """The assistant's reply."""
