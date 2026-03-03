from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class NoteOut(BaseModel):
    id: str = Field(..., description="Note UUID.")
    title: str = Field(..., description="Note title.")
    content: str = Field(..., description="Note content.")
    tags: List[str] = Field(default_factory=list, description="Tag names assigned to the note.")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp.")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp.")


class NoteCreate(BaseModel):
    title: str = Field(default="", description="Note title.")
    content: str = Field(default="", description="Note content.")
    tags: List[str] = Field(default_factory=list, description="Tag names to assign.")


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Updated title (optional).")
    content: Optional[str] = Field(None, description="Updated content (optional).")
    tags: Optional[List[str]] = Field(None, description="Replace tags with this list (optional).")
