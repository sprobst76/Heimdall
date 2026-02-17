"""LLM router.

Endpoints for AI-powered features: proof verification, natural language
rule parsing, weekly reports, and child chatbot.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_child, require_parent
from app.core.rate_limit import limiter
from app.database import get_db
from app.models.quest import QuestInstance, QuestTemplate
from app.models.tan import TAN
from app.models.time_rule import TimeRule
from app.models.user import User
from app.schemas.llm import (
    ChatRequest,
    ChatResponse,
    ParseRuleRequest,
    ParseRuleResponse,
    VerifyProofRequest,
    VerifyProofResponse,
    WeeklyReportRequest,
    WeeklyReportResponse,
)
from app.services.llm_service import (
    child_chat,
    generate_weekly_report,
    parse_natural_language_rule,
    verify_quest_proof,
)
from app.services.quest_service import review_quest

router = APIRouter(prefix="/llm", tags=["LLM / AI"])

AUTO_APPROVE_THRESHOLD = 80


# ---------------------------------------------------------------------------
# 1. Proof Verification
# ---------------------------------------------------------------------------

@router.post("/verify-proof", response_model=VerifyProofResponse)
@limiter.limit("10/minute")
async def verify_proof(
    request: Request,
    body: VerifyProofRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user),
):
    """Verify a quest proof photo using AI vision.

    If the confidence is >= 80%, the quest is auto-approved and a TAN is generated.
    Otherwise, the result is stored for parent review.
    """
    # Load the quest instance
    result = await db.execute(
        select(QuestInstance).where(QuestInstance.id == body.quest_instance_id)
    )
    instance = result.scalar_one_or_none()
    if instance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quest instance not found",
        )

    # Verify the user has access
    if instance.child_id != current_user.id and current_user.family_id != (
        await _get_child_family_id(db, instance.child_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to this quest",
        )

    if instance.status != "pending_review":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quest is not in pending_review status",
        )

    if not instance.proof_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No proof uploaded for this quest",
        )

    # Load template for context
    tmpl_result = await db.execute(
        select(QuestTemplate).where(QuestTemplate.id == instance.template_id)
    )
    template = tmpl_result.scalar_one()

    # Only verify if template has ai_verify enabled
    if not template.ai_verify:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AI verification is not enabled for this quest template",
        )

    # Run AI verification
    ai_result = await verify_quest_proof(
        image_path=instance.proof_url,
        quest_name=template.name,
        quest_description=template.description,
        ai_prompt=template.ai_prompt,
    )

    # Store AI result on the instance
    instance.ai_result = ai_result
    await db.flush()

    auto_approved = False

    # Auto-approve if confidence is high enough
    if ai_result["approved"] and ai_result["confidence"] >= AUTO_APPROVE_THRESHOLD:
        # Use a system user ID for auto-review
        instance = await review_quest(
            db, instance, current_user.id, approved=True, feedback=ai_result["feedback"]
        )
        auto_approved = True

    return VerifyProofResponse(
        approved=ai_result["approved"],
        confidence=ai_result["confidence"],
        feedback=ai_result["feedback"],
        auto_approved=auto_approved,
    )


# ---------------------------------------------------------------------------
# 2. Natural Language Rule Parsing
# ---------------------------------------------------------------------------

@router.post("/parse-rule", response_model=ParseRuleResponse)
@limiter.limit("10/minute")
async def parse_rule(
    request: Request,
    body: ParseRuleRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
):
    """Parse a natural language rule description into structured data."""
    # Get children in the family
    children_result = await db.execute(
        select(User).where(
            User.family_id == current_user.family_id,
            User.role == "child",
        )
    )
    children = [
        {"id": str(c.id), "name": c.name}
        for c in children_result.scalars().all()
    ]

    # Get app groups for context
    from app.models.app_group import AppGroup

    child_ids = [c["id"] for c in children]
    if body.child_id:
        child_ids = [body.child_id]

    groups_result = await db.execute(
        select(AppGroup).where(AppGroup.child_id.in_(child_ids))
    )
    app_groups = [
        {"id": str(g.id), "name": g.name, "category": g.category}
        for g in groups_result.scalars().all()
    ]

    result = await parse_natural_language_rule(body.text, children, app_groups)

    return ParseRuleResponse(
        success=result["success"],
        rule=result.get("rule"),
        error=result.get("error"),
    )


# ---------------------------------------------------------------------------
# 3. Weekly Report
# ---------------------------------------------------------------------------

@router.post("/weekly-report", response_model=WeeklyReportResponse)
@limiter.limit("5/minute")
async def weekly_report(
    request: Request,
    body: WeeklyReportRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
):
    """Generate a weekly report for a child."""
    from datetime import datetime, time, timedelta, timezone

    # Verify child access
    child_result = await db.execute(
        select(User).where(User.id == body.child_id)
    )
    child = child_result.scalar_one_or_none()
    if child is None or child.family_id != current_user.family_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child not found",
        )

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    # Quest stats for the week
    quest_result = await db.execute(
        select(
            func.count(QuestInstance.id).label("total"),
            func.count(QuestInstance.id).filter(
                QuestInstance.status == "approved"
            ).label("completed"),
        ).where(
            QuestInstance.child_id == child.id,
            QuestInstance.created_at >= week_ago,
        )
    )
    quest_row = quest_result.one()

    # TAN stats for the week
    tan_result = await db.execute(
        select(
            func.count(TAN.id).label("total"),
            func.coalesce(func.sum(TAN.value_minutes), 0).label("total_minutes"),
        ).where(
            TAN.child_id == child.id,
            TAN.created_at >= week_ago,
            TAN.status == "redeemed",
        )
    )
    tan_row = tan_result.one()

    # Rule count
    rule_count_result = await db.execute(
        select(func.count(TimeRule.id)).where(
            TimeRule.child_id == child.id,
            TimeRule.active.is_(True),
        )
    )
    active_rules = rule_count_result.scalar() or 0

    usage_data = {
        "hinweis": "Detaillierte Nutzungsdaten werden verfügbar sobald der Geräte-Agent installiert ist",
        "aktive_regeln": active_rules,
    }

    quest_data = {
        "quests_gesamt": quest_row.total,
        "quests_erledigt": quest_row.completed,
        "erledigungs_rate": f"{(quest_row.completed / quest_row.total * 100):.0f}%" if quest_row.total > 0 else "0%",
    }

    tan_data = {
        "tans_eingeloest": tan_row.total,
        "bonus_minuten": tan_row.total_minutes,
    }

    report = await generate_weekly_report(child.name, usage_data, quest_data, tan_data)

    return WeeklyReportResponse(
        child_id=str(child.id),
        child_name=child.name,
        report=report,
    )


# ---------------------------------------------------------------------------
# 4. Child Chatbot
# ---------------------------------------------------------------------------

@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat(
    request: Request,
    body: ChatRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user),
):
    """Chat endpoint for the child assistant."""
    from datetime import datetime, time, timezone

    child = current_user
    now = datetime.now(timezone.utc)

    # Build context data
    # Quest stats today
    today_start = datetime.combine(now.date(), time(0, 0), tzinfo=timezone.utc)

    quest_count = await db.execute(
        select(func.count(QuestInstance.id)).where(
            QuestInstance.child_id == child.id,
            QuestInstance.created_at >= today_start,
        )
    )
    quest_done = await db.execute(
        select(func.count(QuestInstance.id)).where(
            QuestInstance.child_id == child.id,
            QuestInstance.status == "approved",
            QuestInstance.reviewed_at >= today_start,
        )
    )

    # Available quests
    available_quests_result = await db.execute(
        select(QuestTemplate.name).join(
            QuestInstance, QuestInstance.template_id == QuestTemplate.id
        ).where(
            QuestInstance.child_id == child.id,
            QuestInstance.status.in_(["available", "claimed"]),
        )
    )
    available_quests = [row[0] for row in available_quests_result.all()]

    # Active TANs
    active_tans = await db.execute(
        select(func.count(TAN.id)).where(
            TAN.child_id == child.id,
            TAN.status == "active",
            TAN.expires_at > now,
        )
    )

    context_data = {
        "kind_name": child.name,
        "uhrzeit": now.strftime("%H:%M"),
        "quests_heute_gesamt": quest_count.scalar() or 0,
        "quests_heute_erledigt": quest_done.scalar() or 0,
        "verfuegbare_quests": available_quests,
        "aktive_tans": active_tans.scalar() or 0,
        "hinweis": "Detaillierte Bildschirmzeit-Daten werden verfügbar sobald der Geräte-Agent installiert ist",
    }

    response_text = await child_chat(
        message=body.message,
        child_name=child.name,
        context_data=context_data,
        chat_history=body.history,
    )

    return ChatResponse(response=response_text)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def _get_child_family_id(db: AsyncSession, child_id: uuid.UUID) -> uuid.UUID | None:
    """Get the family_id for a child user."""
    result = await db.execute(select(User.family_id).where(User.id == child_id))
    row = result.one_or_none()
    return row[0] if row else None
