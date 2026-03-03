from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.core.db import get_db
from src.api.deps.auth import get_current_user
from src.api.models.note import Tag
from src.api.models.user import User

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get(
    "",
    response_model=list[str],
    summary="List tags",
    description="List the current user's tags (names only).",
    operation_id="tags_list",
)
async def list_tags(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[str]:
    """
    Access control: returns only tags owned by the authenticated user.
    """
    res = await db.execute(
        select(Tag.name).where(Tag.user_id == user.id).order_by(func.lower(Tag.name))
    )
    return list(res.scalars().all())
