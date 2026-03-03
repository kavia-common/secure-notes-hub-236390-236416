from __future__ import annotations

import uuid
from typing import Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.core.db import get_db
from src.api.deps.auth import get_current_user
from src.api.models.note import Note, NoteTag, Tag
from src.api.models.user import User
from src.api.schemas.notes import NoteCreate, NoteOut, NoteUpdate

router = APIRouter(prefix="/notes", tags=["notes"])


async def _get_or_create_tags(
    db: AsyncSession, user_id: uuid.UUID, names: Sequence[str]
) -> list[Tag]:
    cleaned = []
    seen = set()
    for n in names:
        name = (n or "").strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(name)

    if not cleaned:
        return []

    res = await db.execute(select(Tag).where(Tag.user_id == user_id, Tag.name.in_(cleaned)))
    existing = {t.name.lower(): t for t in res.scalars().all()}
    tags: list[Tag] = []
    for name in cleaned:
        t = existing.get(name.lower())
        if t is None:
            t = Tag(user_id=user_id, name=name)
            db.add(t)
        tags.append(t)

    await db.flush()
    return tags


def _note_to_out(note: Note, tags: list[str]) -> NoteOut:
    return NoteOut(
        id=str(note.id),
        title=note.title,
        content=note.content,
        tags=tags,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.get(
    "",
    response_model=list[NoteOut],
    summary="List notes",
    description="List the current user's notes. Optional search via ?q= and tag filter via ?tag=.",
    operation_id="notes_list",
)
async def list_notes(
    q: str | None = Query(default=None, description="Search query across title/content."),
    tag: str | None = Query(default=None, description="Filter notes that have this tag name."),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[NoteOut]:
    """
    Access control: returns only notes owned by the authenticated user.
    """
    stmt = (
        select(Note)
        .where(Note.user_id == user.id)
        .order_by(Note.updated_at.desc())
        .options(selectinload(Note.tags).selectinload(NoteTag.tag))
    )

    if q:
        q_like = f"%{q}%"
        stmt = stmt.where(or_(Note.title.ilike(q_like), Note.content.ilike(q_like)))

    if tag:
        stmt = stmt.join(NoteTag, NoteTag.note_id == Note.id).join(Tag, Tag.id == NoteTag.tag_id)
        stmt = stmt.where(Tag.user_id == user.id, Tag.name == tag)

    res = await db.execute(stmt)
    notes = res.scalars().unique().all()

    out: list[NoteOut] = []
    for n in notes:
        tag_names = [nt.tag.name for nt in (n.tags or []) if nt.tag is not None]
        out.append(_note_to_out(n, tag_names))
    return out


@router.get(
    "/{note_id}",
    response_model=NoteOut,
    summary="Get a note",
    description="Get a single note by id (must belong to the current user).",
    operation_id="notes_get",
)
async def get_note(
    note_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NoteOut:
    """
    Access control: note must be owned by the authenticated user.
    """
    try:
        nid = uuid.UUID(note_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid note id")

    res = await db.execute(
        select(Note)
        .where(Note.id == nid, Note.user_id == user.id)
        .options(selectinload(Note.tags).selectinload(NoteTag.tag))
    )
    note = res.scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")

    tags = [nt.tag.name for nt in (note.tags or []) if nt.tag is not None]
    return _note_to_out(note, tags)


@router.post(
    "",
    response_model=NoteOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create note",
    description="Create a new note owned by the current user.",
    operation_id="notes_create",
)
async def create_note(
    payload: NoteCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NoteOut:
    """
    Creates a note and assigns tags (creating missing tags in the user's namespace).
    """
    note = Note(user_id=user.id, title=payload.title or "", content=payload.content or "")
    db.add(note)
    await db.flush()

    tags = await _get_or_create_tags(db, user.id, payload.tags)
    for t in tags:
        db.add(NoteTag(note_id=note.id, tag_id=t.id))

    await db.commit()
    await db.refresh(note)

    # Fetch tags
    res = await db.execute(
        select(Tag.name)
        .join(NoteTag, NoteTag.tag_id == Tag.id)
        .where(NoteTag.note_id == note.id, Tag.user_id == user.id)
        .order_by(func.lower(Tag.name))
    )
    tag_names = list(res.scalars().all())
    return _note_to_out(note, tag_names)


@router.patch(
    "/{note_id}",
    response_model=NoteOut,
    summary="Update note (autosave)",
    description=(
        "Patch a note's title/content/tags. Designed for autosave: "
        "send partial updates frequently; returns updated note."
    ),
    operation_id="notes_update",
)
async def update_note(
    note_id: str,
    payload: NoteUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NoteOut:
    """
    Access control: can only update notes owned by the authenticated user.

    If tags is provided, the note's tags are replaced with the provided list.
    """
    try:
        nid = uuid.UUID(note_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid note id")

    res = await db.execute(select(Note).where(Note.id == nid, Note.user_id == user.id))
    note = res.scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")

    if payload.title is not None:
        note.title = payload.title
    if payload.content is not None:
        note.content = payload.content

    if payload.tags is not None:
        # Replace tags atomically-ish.
        await db.execute(delete(NoteTag).where(NoteTag.note_id == note.id))
        tags = await _get_or_create_tags(db, user.id, payload.tags)
        for t in tags:
            db.add(NoteTag(note_id=note.id, tag_id=t.id))

    await db.commit()

    # Re-read note and tags for response
    res2 = await db.execute(
        select(Note)
        .where(Note.id == nid, Note.user_id == user.id)
        .options(selectinload(Note.tags).selectinload(NoteTag.tag))
    )
    note2 = res2.scalar_one()
    tag_names = [nt.tag.name for nt in (note2.tags or []) if nt.tag is not None]
    return _note_to_out(note2, tag_names)


@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete note",
    description="Delete a note owned by the current user.",
    operation_id="notes_delete",
)
async def delete_note(
    note_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """
    Access control: can only delete notes owned by the authenticated user.
    """
    try:
        nid = uuid.UUID(note_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid note id")

    res = await db.execute(select(Note).where(Note.id == nid, Note.user_id == user.id))
    note = res.scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")

    await db.execute(delete(Note).where(Note.id == nid, Note.user_id == user.id))
    await db.commit()
    return None
