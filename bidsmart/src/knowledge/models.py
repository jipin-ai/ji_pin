"""Knowledge base models."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


class KBDocument(Base):
    """A document in the knowledge base."""

    __tablename__ = "kb_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")  # manual/law/regulation/experience
    source_path: Mapped[str] = mapped_column(String(500), nullable=True)  # original file path on disk
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    chunks: Mapped[list["KBChunk"]] = relationship("KBChunk", back_populates="document", cascade="all, delete-orphan")


class KBChunk(Base):
    """A text chunk with its embedding vector."""

    __tablename__ = "kb_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("kb_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    heading: Mapped[str] = mapped_column(String(255), nullable=True)  # parent section heading
    embedding_json: Mapped[str] = mapped_column(Text, nullable=True)  # JSON-serialized embedding vector

    document: Mapped["KBDocument"] = relationship("KBDocument", back_populates="chunks")
