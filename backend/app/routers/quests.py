"""Quests router.

Endpoints for managing quest templates (parent) and quest instances
(claim, submit proof, review).
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_current_user, require_parent
from app.database import get_db
from app.models.quest import QuestInstance, QuestTemplate
from app.models.user import User
from app.schemas.quest import (
    QuestInstanceResponse,
    QuestReview,
    QuestSubmitProof,
    QuestTemplateCreate,
    QuestTemplateResponse,
    QuestTemplateUpdate,
)
from app.services.quest_service import (
    claim_quest,
    create_instances_for_child,
    get_child_quest_stats,
    review_quest,
    submit_proof,
)
from app.services.rule_push_service import notify_parent_dashboard

router = APIRouter(tags=["Quests"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _verify_child_access(
    db: AsyncSession, child_id: uuid.UUID, current_user: User
) -> User:
    """Verify the current user has access to this child's data."""
    result = await db.execute(select(User).where(User.id == child_id))
    child = result.scalar_one_or_none()

    if child is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child not found",
        )

    if child.family_id != current_user.family_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this family",
        )

    return child


# ---------------------------------------------------------------------------
# Quest Templates (CRUD - Parent only)
# ---------------------------------------------------------------------------

@router.get("/families/{family_id}/quests", response_model=list[QuestTemplateResponse])
async def list_quest_templates(
    family_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user),
    active_only: bool = Query(True, description="Only return active templates"),
):
    """List all quest templates for a family."""
    if current_user.family_id != family_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this family",
        )

    query = select(QuestTemplate).where(QuestTemplate.family_id == family_id)
    if active_only:
        query = query.where(QuestTemplate.active.is_(True))
    query = query.order_by(QuestTemplate.category, QuestTemplate.name)

    result = await db.execute(query)
    return result.scalars().all()


@router.post(
    "/families/{family_id}/quests",
    response_model=QuestTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_quest_template(
    family_id: uuid.UUID,
    body: QuestTemplateCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
):
    """Create a new quest template. Requires parent role."""
    if current_user.family_id != family_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this family",
        )

    template = QuestTemplate(
        family_id=family_id,
        name=body.name,
        description=body.description,
        category=body.category,
        reward_minutes=body.reward_minutes,
        tan_groups=body.tan_groups,
        proof_type=body.proof_type,
        ai_verify=body.ai_verify,
        ai_prompt=body.ai_prompt,
        recurrence=body.recurrence,
        auto_detect_app=body.auto_detect_app,
        auto_detect_minutes=body.auto_detect_minutes,
    )
    db.add(template)
    await db.flush()
    await db.refresh(template)
    return template


@router.get("/families/{family_id}/quests/{quest_id}", response_model=QuestTemplateResponse)
async def get_quest_template(
    family_id: uuid.UUID,
    quest_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user),
):
    """Get a specific quest template."""
    if current_user.family_id != family_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this family",
        )

    result = await db.execute(
        select(QuestTemplate).where(
            QuestTemplate.id == quest_id,
            QuestTemplate.family_id == family_id,
        )
    )
    template = result.scalar_one_or_none()

    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quest template not found",
        )

    return template


@router.put("/families/{family_id}/quests/{quest_id}", response_model=QuestTemplateResponse)
async def update_quest_template(
    family_id: uuid.UUID,
    quest_id: uuid.UUID,
    body: QuestTemplateUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
):
    """Update a quest template. Requires parent role."""
    if current_user.family_id != family_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this family",
        )

    result = await db.execute(
        select(QuestTemplate).where(
            QuestTemplate.id == quest_id,
            QuestTemplate.family_id == family_id,
        )
    )
    template = result.scalar_one_or_none()

    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quest template not found",
        )

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(template, key, value)

    await db.flush()
    await db.refresh(template)
    return template


@router.delete(
    "/families/{family_id}/quests/{quest_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_quest_template(
    family_id: uuid.UUID,
    quest_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
):
    """Soft-delete a quest template by deactivating it. Requires parent role."""
    if current_user.family_id != family_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this family",
        )

    result = await db.execute(
        select(QuestTemplate).where(
            QuestTemplate.id == quest_id,
            QuestTemplate.family_id == family_id,
        )
    )
    template = result.scalar_one_or_none()

    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quest template not found",
        )

    template.active = False
    await db.flush()
    return None


# ---------------------------------------------------------------------------
# Quest Instances (Child lifecycle)
# ---------------------------------------------------------------------------

@router.get("/children/{child_id}/quests", response_model=list[QuestInstanceResponse])
async def list_child_quests(
    child_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user),
    quest_status: str | None = Query(None, alias="status", description="Filter by status"),
):
    """List quest instances for a child."""
    await _verify_child_access(db, child_id, current_user)

    query = select(QuestInstance).where(QuestInstance.child_id == child_id)

    if quest_status is not None:
        query = query.where(QuestInstance.status == quest_status)

    query = query.order_by(QuestInstance.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post(
    "/children/{child_id}/quests/assign",
    response_model=QuestInstanceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_quest(
    child_id: uuid.UUID,
    template_id: uuid.UUID = Query(..., description="Quest template ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_parent),
):
    """Assign a quest template to a child (creates instance). Parent only."""
    child = await _verify_child_access(db, child_id, current_user)

    # Verify template exists and belongs to same family
    result = await db.execute(
        select(QuestTemplate).where(
            QuestTemplate.id == template_id,
            QuestTemplate.family_id == child.family_id,
            QuestTemplate.active.is_(True),
        )
    )
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quest template not found or inactive",
        )

    instance = await create_instances_for_child(db, template, child_id)
    return instance


@router.post("/children/{child_id}/quests/{instance_id}/claim", response_model=QuestInstanceResponse)
async def claim_quest_endpoint(
    child_id: uuid.UUID,
    instance_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user),
):
    """Child claims an available quest."""
    await _verify_child_access(db, child_id, current_user)

    result = await db.execute(
        select(QuestInstance).where(
            QuestInstance.id == instance_id,
            QuestInstance.child_id == child_id,
        )
    )
    instance = result.scalar_one_or_none()

    if instance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quest instance not found",
        )

    instance = await claim_quest(db, instance)
    return instance


@router.post("/children/{child_id}/quests/{instance_id}/proof", response_model=QuestInstanceResponse)
async def submit_quest_proof(
    child_id: uuid.UUID,
    instance_id: uuid.UUID,
    body: QuestSubmitProof,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user),
):
    """Submit proof for a claimed quest."""
    child_obj = await _verify_child_access(db, child_id, current_user)

    result = await db.execute(
        select(QuestInstance).where(
            QuestInstance.id == instance_id,
            QuestInstance.child_id == child_id,
        )
    )
    instance = result.scalar_one_or_none()

    if instance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quest instance not found",
        )

    instance = await submit_proof(db, instance, body.proof_type, body.proof_url)
    await notify_parent_dashboard(child_obj.family_id, child_id, "quest_proof")
    return instance


@router.post("/children/{child_id}/quests/{instance_id}/review", response_model=QuestInstanceResponse)
async def review_quest_endpoint(
    child_id: uuid.UUID,
    instance_id: uuid.UUID,
    body: QuestReview,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
):
    """Parent reviews a submitted quest. On approval, generates a TAN."""
    child_obj = await _verify_child_access(db, child_id, current_user)

    result = await db.execute(
        select(QuestInstance).where(
            QuestInstance.id == instance_id,
            QuestInstance.child_id == child_id,
        )
    )
    instance = result.scalar_one_or_none()

    if instance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quest instance not found",
        )

    instance = await review_quest(
        db, instance, current_user.id, body.approved, body.feedback
    )
    await notify_parent_dashboard(child_obj.family_id, child_id, "quest_reviewed")
    return instance


@router.get("/children/{child_id}/quests/stats")
async def get_quest_stats(
    child_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user),
):
    """Get quest stats for a child (completed today, streak, etc.)."""
    await _verify_child_access(db, child_id, current_user)
    stats = await get_child_quest_stats(db, child_id)
    return stats
