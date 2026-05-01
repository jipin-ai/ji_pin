"""Knowledge base API router."""

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.dependencies import get_current_user, require_role
from src.knowledge.embedder import chunk_text, embedder
from src.knowledge.models import KBChunk, KBDocument
from src.models.user import User
from src.parsing import parse_document

router = APIRouter(prefix="/admin/kb", tags=["admin-kb"])
KB_STORAGE = Path("storage/knowledge")


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


@router.post("/upload")
async def upload_kb_document(
    file: UploadFile,
    title: str = "",
    source_type: str = "manual",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Upload a document to the knowledge base."""
    if not file.filename:
        raise HTTPException(400, "文件名不能为空")

    # Parse document
    KB_STORAGE.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename).suffix.lower()
    file_id = uuid.uuid4().hex[:12]
    save_path = KB_STORAGE / f"{file_id}{ext}"

    content_bytes = await file.read()
    save_path.write_bytes(content_bytes)

    try:
        parsed = await parse_document(str(save_path))
        text_content = parsed.raw_text if hasattr(parsed, "raw_text") else ""
        if hasattr(parsed, "sections"):
            text_content = "\n\n".join(
                s.heading + "\n" + s.content if s.heading else s.content
                for s in parsed.sections
            )
    except Exception:
        # Fallback: read as plain text
        text_content = content_bytes.decode("utf-8", errors="replace")

    if not text_content.strip():
        save_path.unlink()
        raise HTTPException(400, "文档内容为空，无法解析")

    # Chunk and embed
    chunks = chunk_text(text_content)
    if not chunks:
        save_path.unlink()
        raise HTTPException(400, "文档分块失败")

    # Create document record
    doc = KBDocument(
        title=title or file.filename,
        source_type=source_type,
        source_path=str(save_path),
        chunk_count=len(chunks),
    )
    db.add(doc)
    await db.flush()

    # Embed all chunks
    chunk_texts = [f"{h}\n{c}" if h else c for h, c in chunks]
    embeddings = embedder.embed(chunk_texts)

    import json
    for i, ((heading, content), emb) in enumerate(zip(chunks, embeddings)):
        chunk = KBChunk(
            document_id=doc.id,
            chunk_index=i,
            content=content,
            heading=heading,
            embedding_json=json.dumps(emb.tolist()),
        )
        db.add(chunk)

    await db.commit()
    await db.refresh(doc)

    return {"id": doc.id, "title": doc.title, "chunk_count": doc.chunk_count}


@router.get("/documents")
async def list_kb_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """List all knowledge base documents."""
    result = await db.execute(
        select(KBDocument).order_by(KBDocument.created_at.desc())
    )
    docs = result.scalars().all()
    return {
        "documents": [
            {
                "id": d.id,
                "title": d.title,
                "source_type": d.source_type,
                "chunk_count": d.chunk_count,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in docs
        ]
    }


@router.delete("/documents/{doc_id}")
async def delete_kb_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Delete a knowledge base document and its chunks."""
    result = await db.execute(select(KBDocument).where(KBDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "文档不存在")

    # Delete file from disk
    if doc.source_path:
        try:
            Path(doc.source_path).unlink(missing_ok=True)
        except Exception:
            pass

    # Delete from DB (cascades to chunks)
    await db.delete(doc)
    await db.commit()

    return {"message": f"已删除「{doc.title}」"}

@router.post("/search")
async def search_knowledge(
    req: SearchRequest,
    db = Depends(get_db),
    current_user = Depends(require_role("admin")),
):
    """Test search in knowledge base."""
    import json
    import numpy as np
    from sqlalchemy import select
    from src.knowledge.models import KBChunk, KBDocument

    chunk_result = await db.execute(
        select(KBChunk).where(KBChunk.embedding_json.isnot(None))
    )
    all_chunks = chunk_result.scalars().all()
    if not all_chunks:
        return {"results": []}

    chunk_embeddings = [np.array(json.loads(c.embedding_json)) for c in all_chunks]
    matches = embedder.search(req.query, chunk_embeddings, top_k=req.top_k)

    results = []
    for idx, score in matches:
        chunk = all_chunks[idx]
        doc_result = await db.execute(
            select(KBDocument).where(KBDocument.id == chunk.document_id)
        )
        doc = doc_result.scalar_one_or_none()
        results.append({
            "title": doc.title if doc else "未知",
            "heading": chunk.heading,
            "content": chunk.content,
            "score": score,
        })

    return {"results": results}
