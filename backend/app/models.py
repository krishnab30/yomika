from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class Book(Base):
    __tablename__ = "books"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    original_filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    original_path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    audiobook_path: Mapped[str | None] = (
        mapped_column(
            String(1000),
            nullable=True,
        )
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="queued",
    )

    stage: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="queued",
    )

    progress: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    message: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        default="",
    )

    chapter_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    book_id: Mapped[str] = mapped_column(
        ForeignKey("books.id"),
        nullable=False,
        index=True,
    )

    chapter_number: Mapped[int | None] = (
        mapped_column(
            Integer,
            nullable=True,
        )
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    filename: Mapped[str | None] = (
        mapped_column(
            String(1000),
            nullable=True,
        )
    )

    audio_path: Mapped[str | None] = (
        mapped_column(
            String(1000),
            nullable=True,
        )
    )

    duration_seconds: Mapped[float | None] = (
        mapped_column(
            Float,
            nullable=True,
        )
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
    )