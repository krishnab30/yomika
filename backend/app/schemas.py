from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BookResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: str
    title: str
    original_filename: str
    status: str
    stage: str
    progress: int
    message: str
    created_at: datetime
    updated_at: datetime


class BookStatusResponse(BaseModel):
    book_id: str
    status: str
    stage: str
    progress: int
    message: str
    updated_at: str


class BookCreatedResponse(BaseModel):
    book_id: str
    title: str
    status: str