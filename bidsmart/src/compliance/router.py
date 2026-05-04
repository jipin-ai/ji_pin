"""Streaming AI compliance review endpoint — supports both legacy text and pipeline-based file review."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pathlib import Path
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_current_user
from src.db.session import get_db
from src.models.user import User
from src.models.document import Document
from src.compliance.ai_reviewer import review_compliance
from src.compliance.pipeline import run_pipeline
from src.compliance.tender_analyzer import analyze_tender, _generate_report
from src.parsing import parse_document
from src.config import Settings
from src.knowledge.embedder import embedder
import json, asyncio

router = APIRouter(prefix="/ai", tags=["AI审查"])


# ── Request Models ──────────────────────────────────────────────────────


class ReviewRequest(BaseModel):
    tender: str = ""
    bid: str = ""


class FileReviewRequest(BaseModel):
    """Review using uploaded document IDs. Supports multiple files."""
    tender_doc_ids: list[int] = []   # IDs of tender documents (can be multiple)
    bid_doc_ids: list[int] = []      # IDs of bid documents (can be multiple)
    tender_doc_id: int = 0           # Legacy single-file (kept for backward compat)
    bid_doc_id: int = 0              # Legacy single-file


# ── Legacy: Text-based review ────────────────────────────────────────────


@router.post("/review")
async def ai_review(req: ReviewRequest, user: User = Depends(get_current_user)):
    """AI逐项比对招标要求与投标响应（文本输入，向后兼容）。"""
    settings = Settings()
    result = await review_compliance(req.tender, req.bid, settings)
    return result


@router.post("/review/stream")
async def ai_review_stream(req: ReviewRequest, user: User = Depends(get_current_user)):
    """流式AI审查（文本输入）。"""
    settings = Settings()

    async def generate():
        yield f"data: {json.dumps({'status': 'analyzing', 'message': '正在解析招标要求...'}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.3)
        yield f"data: {json.dumps({'status': 'comparing', 'message': '正在逐项比对投标响应...'}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.3)
        yield f"data: {json.dumps({'status': 'reasoning', 'message': 'DeepSeek 正在推理判定...'}, ensure_ascii=False)}\n\n"

        result = await review_compliance(req.tender, req.bid, settings)
        yield f"data: {json.dumps({'status': 'done', 'result': result}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ── New: File-based pipeline review ──────────────────────────────────────


@router.post("/review-file")
async def ai_review_file(
    req: FileReviewRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """基于已上传文件的AI审查（文档解析+条款提取+段落匹配+逐项AI+聚合）。

    - 自动解析 .docx/.pdf 文件
    - 从招标文件中提取评审条款
    - 逐项匹配投标响应段落
    - 逐项AI判定
    - 聚合生成审查报告
    """
    settings = Settings()

    # Resolve IDs — support both legacy single-id and new multi-id formats
    tender_ids = req.tender_doc_ids if req.tender_doc_ids else ([req.tender_doc_id] if req.tender_doc_id else [])
    bid_ids = req.bid_doc_ids if req.bid_doc_ids else ([req.bid_doc_id] if req.bid_doc_id else [])

    if not tender_ids or not bid_ids:
        raise HTTPException(400, "请选择至少一个招标文件和一个投标文件")

    # Load and merge multiple documents
    tender_rows: list[Document] = []
    for did in tender_ids:
        r = await db.execute(select(Document).where(Document.id == did))
        row = r.scalar_one_or_none()
        if not row: raise HTTPException(404, f"Document {did} not found")
        tender_rows.append(row)

    bid_rows: list[Document] = []
    for did in bid_ids:
        r = await db.execute(select(Document).where(Document.id == did))
        row = r.scalar_one_or_none()
        if not row: raise HTTPException(404, f"Document {did} not found")
        bid_rows.append(row)

    # Parse and merge documents
    async def _parse_merge(rows: list[Document]) -> "ParsedDocument":
        from src.parsing.models import ParsedDocument, Section
        all_sections = []
        full_text = ""
        total_pages = 0
        first_title = ""
        for row in rows:
            doc = await parse_document(str(Path(settings.storage_root) / row.storage_path))
            if not first_title: first_title = doc.title
            all_sections.extend(doc.sections)
            full_text += doc.raw_text + "\n\n"
            total_pages += doc.page_count
        return ParsedDocument(
            title=first_title or "合并文档",
            sections=all_sections,
            raw_text=full_text,
            page_count=total_pages,
            file_type=rows[0].mime_type.split('/')[-1] if rows else "docx",
        )

    try:
        tender_doc = await _parse_merge(tender_rows)
        bid_doc = await _parse_merge(bid_rows)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except FileNotFoundError:
        raise HTTPException(404, "Document file not found on storage")

    # Run pipeline
    result = await run_pipeline(tender_doc, bid_doc, settings)

    # Add document metadata
    result["tender_file"] = ", ".join(r.original_name for r in tender_rows)
    result["bid_file"] = ", ".join(r.original_name for r in bid_rows)
    result["tender_title"] = tender_doc.title
    result["bid_title"] = bid_doc.title
    result["tender_pages"] = tender_doc.page_count
    result["bid_pages"] = bid_doc.page_count
    result["tender_count"] = len(tender_rows)
    result["bid_count"] = len(bid_rows)

    return result


@router.post("/review-file/stream")
async def ai_review_file_stream(
    req: FileReviewRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """流式文件审查 — 逐条推送审查结果。

    每完成一条条款审查即推送，前端逐行追加对照表。
    支持多文件合并（tender_doc_ids + bid_doc_ids）。
    """
    from src.compliance.pipeline import run_pipeline_stream

    settings = Settings()

    # Resolve IDs
    tender_ids = req.tender_doc_ids if req.tender_doc_ids else ([req.tender_doc_id] if req.tender_doc_id else [])
    bid_ids = req.bid_doc_ids if req.bid_doc_ids else ([req.bid_doc_id] if req.bid_doc_id else [])

    # ── Load documents NOW (before StreamingResponse) so DB session is valid ──
    tender_rows: list[Document] = []
    for did in tender_ids:
        r = await db.execute(select(Document).where(Document.id == did))
        row = r.scalar_one_or_none()
        if not row:
            raise HTTPException(404, f"Document {did} not found")
        tender_rows.append(row)

    bid_rows: list[Document] = []
    for did in bid_ids:
        r = await db.execute(select(Document).where(Document.id == did))
        row = r.scalar_one_or_none()
        if not row:
            raise HTTPException(404, f"Document {did} not found")
        bid_rows.append(row)

    async def generate():
        yield f"data: {json.dumps({'status': 'loading', 'message': '正在加载文件...'}, ensure_ascii=False)}\n\n"

        try:
            # Parse and merge
            from src.parsing.models import ParsedDocument, Section

            async def _parse_merge(rows):
                all_sections = []
                full_text = ""
                total_pages = 0
                first_title = ""
                for row in rows:
                    doc = await parse_document(str(Path(settings.storage_root) / row.storage_path))
                    if not first_title:
                        first_title = doc.title
                    all_sections.extend(doc.sections)
                    full_text += doc.raw_text + "\n\n"
                    total_pages += doc.page_count
                return ParsedDocument(
                    title=first_title or "合并文档",
                    sections=all_sections,
                    raw_text=full_text,
                    page_count=total_pages,
                    file_type=rows[0].mime_type.split("/")[-1] if rows else "docx",
                )

            yield f"data: {json.dumps({'status': 'parsing', 'message': '正在解析招标文件...'}, ensure_ascii=False)}\n\n"
            tender_doc = await _parse_merge(tender_rows)

            yield f"data: {json.dumps({'status': 'parsing', 'message': '正在解析投标文件...'}, ensure_ascii=False)}\n\n"
            bid_doc = await _parse_merge(bid_rows)

            yield f"data: {json.dumps({'status': 'extracting', 'message': f'招标文件 {tender_doc.page_count}页，投标文件 {bid_doc.page_count}页。开始逐条审查...'}, ensure_ascii=False)}\n\n"

            # Stream per-item review
            async for item in run_pipeline_stream(tender_doc, bid_doc, settings):
                if item.get("type") == "error":
                    yield f"data: {json.dumps({'status': 'error', 'message': item['message']}, ensure_ascii=False)}\n\n"
                    return
                elif item.get("type") == "item":
                    yield f"data: {json.dumps({'status': 'reviewing', 'item': item}, ensure_ascii=False)}\n\n"
                elif item.get("type") == "done":
                    report = item.get("report", {})
                    report["tender_file"] = ", ".join(r.original_name for r in tender_rows)
                    report["bid_file"] = ", ".join(r.original_name for r in bid_rows)
                    report["tender_title"] = tender_doc.title
                    report["bid_title"] = bid_doc.title
                    report["tender_pages"] = tender_doc.page_count
                    report["bid_pages"] = bid_doc.page_count
                    yield f"data: {json.dumps({'status': 'done', 'result': report}, ensure_ascii=False)}\n\n"

        except ValueError as e:
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
        except FileNotFoundError:
            yield f"data: {json.dumps({'status': 'error', 'message': '文件未找到'}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'message': f'审查异常: {str(e)}'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

# ── Chat / Follow-up Questions ────────────────────────────────────────────


class ChatRequest(BaseModel):
    message: str
    review_context: dict | None = None  # previous review result for context


@router.post("/chat")
async def ai_chat(req: ChatRequest, user: User = Depends(get_current_user)):
    """AI 追问 — 基于审查结果回答用户的后续问题。

    如果提供了 review_context，AI 会基于审查上下文回答。
    适用于审查完成后的风险总结、整改建议、逐项分析等追问。
    """
    from openai import AsyncOpenAI

    settings = Settings()
    if not settings.deepseek_api_key:
        raise HTTPException(500, "DeepSeek API key not configured")

    client = AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )

    # Build system prompt with review context if available
    system_prompt = (
        "你是标书智审 BidSmart 的 AI 审查助手。"
        "你只回答标书合规审查相关问题，包括：招标要求解读、投标响应合规分析、"
        "整改建议、风险点识别、条款对比等与当前审查项目直接相关的内容。"
        "遇到以下情况必须拒绝回答，统一回复「抱歉，我只回答标书合规审查相关问题。请提出与当前审查项目有关的问题。」："
        "闲聊、问候、无关技术讨论、非标书领域的任何问题。"
        "回答应简洁、专业、直接。用中文回答。"
    )

    user_message = req.message
    if req.review_context:
        ctx_summary = json.dumps({
            "overall_score": req.review_context.get("overall_score"),
            "compliant": req.review_context.get("compliant"),
            "partial": req.review_context.get("partial"),
            "non_compliant": req.review_context.get("non_compliant"),
            "items": [
                {
                    "requirement": item.get("requirement"),
                    "verdict": item.get("verdict"),
                    "reason": item.get("reason"),
                    "suggestion": item.get("suggestion"),
                }
                for item in (req.review_context.get("items") or [])
            ],
        }, ensure_ascii=False, indent=2)
        system_prompt += f"\n\n当前审查结果上下文：\n{ctx_summary}"
        user_message = f"基于以上审查结果，请回答以下问题：{req.message}"

    try:
        resp = await client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.7,
            max_tokens=2000,
        )
        reply = resp.choices[0].message.content
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(500, f"AI 响应失败: {str(e)}")


# ── Utility: preview parsed document ─────────────────────────────────────


@router.get("/preview/{document_id}")
async def preview_document(
    document_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """预览已解析的文档结构（条款、章节等）。"""
    doc_row = (await db.execute(
        select(Document).where(Document.id == document_id)
    )).scalar_one_or_none()

    if not doc_row:
        raise HTTPException(404, "Document not found")

    settings = Settings()
    try:
        full_path = Path(settings.storage_root) / doc_row.storage_path
        doc = await parse_document(str(full_path))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except FileNotFoundError:
        raise HTTPException(404, "File not found on storage")

    return {
        "id": document_id,
        "filename": doc_row.original_name,
        "title": doc.title,
        "page_count": doc.page_count,
        "char_count": doc.char_count,
        "section_count": len(doc.sections),
        "sections": [
            {
                "heading": s.heading,
                "level": s.level,
                "item_count": len(s.items),
                "char_count": len(s.content) + sum(len(i) for i in s.items),
            }
            for s in doc.sections
        ],
        "items": doc.find_numbered_items()[:20],  # first 20
    }


# ── Review Result Actions: confirm / ignore ─────────────────────────────


class ItemAction(BaseModel):
    project_id: int
    requirement: str
    bid_response: str = ""
    verdict: str
    weight_level: str = ""
    tender_page: int = 0
    bid_page: int = 0
    reason: str = ""
    suggestion: str = ""


async def _save_item(table_name: str, req: ItemAction, db: AsyncSession):
    """Insert an item into confirmed_items or ignored_items."""
    from sqlalchemy import text
    await db.execute(
        text(f"""INSERT INTO {table_name}
            (project_id, requirement, bid_response, verdict, weight_level, tender_page, bid_page, reason, suggestion)
            VALUES (:pid, :req, :bid, :verdict, :weight, :tp, :bp, :reason, :sug)"""),
        {
            "pid": req.project_id,
            "req": req.requirement,
            "bid": req.bid_response,
            "verdict": req.verdict,
            "weight": req.weight_level,
            "tp": req.tender_page,
            "bp": req.bid_page,
            "reason": req.reason,
            "sug": req.suggestion,
        },
    )


@router.post("/review/confirm")
async def confirm_item(
    req: ItemAction,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """确认已处理项，存入 confirmed_items 表。"""
    await _save_item("confirmed_items", req, db)
    await db.commit()
    return {"status": "ok", "action": "confirmed"}


@router.post("/review/ignore")
async def ignore_item(
    req: ItemAction,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """忽略项，存入 ignored_items 表。"""
    await _save_item("ignored_items", req, db)
    await db.commit()
    return {"status": "ok", "action": "ignored"}


@router.get("/projects/{project_id}/confirmed")
async def list_confirmed(
    project_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询已确认处理项。"""
    from sqlalchemy import text
    r = await db.execute(
        text("SELECT * FROM confirmed_items WHERE project_id = :pid ORDER BY handled_at DESC"),
        {"pid": project_id},
    )
    rows = r.fetchall()
    return [dict(row._mapping) for row in rows]


@router.get("/projects/{project_id}/ignored")
async def list_ignored(
    project_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询已忽略项。"""
    from sqlalchemy import text
    r = await db.execute(
        text("SELECT * FROM ignored_items WHERE project_id = :pid ORDER BY handled_at DESC"),
        {"pid": project_id},
    )
    rows = r.fetchall()
    return [dict(row._mapping) for row in rows]


# ── Review Memory (cross-project ignore/long-term memory) ──────────────


class MemoryIgnoreRequest(BaseModel):
    requirement: str
    verdict: str
    reason: str = ""
    suggestion: str = ""
    project_id: int = 0


@router.post("/memory/ignore")
async def memory_ignore(
    req: MemoryIgnoreRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save a review conclusion to cross-project memory."""
    from src.models.review_memory import ReviewMemory
    from sqlalchemy import text as sa_text

    req_hash = ReviewMemory.hash_requirement(req.requirement)
    preview = req.requirement[:200]

    await db.execute(
        sa_text("""
            INSERT INTO review_memory (requirement_hash, requirement_preview, verdict, reason, suggestion, project_id)
            VALUES (:h, :p, :v, :r, :s, :pid)
            ON CONFLICT(requirement_hash) DO UPDATE SET
                ignore_count = review_memory.ignore_count + 1,
                ignored_at = CURRENT_TIMESTAMP
        """),
        {"h": req_hash, "p": preview, "v": req.verdict, "r": req.reason, "s": req.suggestion, "pid": req.project_id or None},
    )
    await db.commit()
    return {"status": "ok", "hash": req_hash}


@router.get("/memory/list")
async def memory_list(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all cached review memory entries."""
    from sqlalchemy import text as sa_text
    r = await db.execute(
        sa_text("SELECT id, requirement_preview, verdict, reason, ignore_count, ignored_at FROM review_memory ORDER BY ignored_at DESC LIMIT 100")
    )
    return [dict(row._mapping) for row in r.fetchall()]


@router.delete("/memory/{memory_id}")
async def memory_delete(
    memory_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a review memory entry."""
    from sqlalchemy import text as sa_text
    await db.execute(sa_text("DELETE FROM review_memory WHERE id = :id"), {"id": memory_id})
    await db.commit()
    return {"status": "ok", "deleted": memory_id}


# ── Tender Analysis ────────────────────────────────────────────────────


class TenderAnalyzeRequest(BaseModel):
    """Request body for tender analysis endpoint."""
    tender_doc_id: int


@router.post("/analyze-tender")
async def analyze_tender_endpoint(
    req: TenderAnalyzeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """标前招标分析：提取所有要求并按废标/重要/一般三层分类。

    - 输入已上传的招标文件 ID
    - 返回三层分类结果 + Markdown 报告
    - 响应时间 ≤ 60 秒
    """
    settings = Settings()

    # Load document
    result = await db.execute(
        select(Document).where(Document.id == req.tender_doc_id, Document.uploaded_by == user.id)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="文档不存在或无权访问")

    # Parse
    import os
    file_path = os.path.join(settings.storage_root, doc.storage_path) if doc.storage_path else ""
    if not file_path or not os.path.exists(str(file_path)):
        raise HTTPException(status_code=400, detail="文档文件不存在")

    try:
        parsed = await parse_document(Path(file_path))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文档解析失败: {e}")

    if not parsed.text:
        raise HTTPException(status_code=400, detail="招标文件内容为空")

    # Analyze
    analysis = await analyze_tender(parsed.text, settings)

    # Generate report
    report_md = _generate_report(analysis)

    return {
        "disqualification": [
            {"text": i.text, "reason": i.reason, "section": i.section, "risk": i.risk}
            for i in analysis.disqualification
        ],
        "important": [
            {"text": i.text, "reason": i.reason, "section": i.section, "risk": i.risk}
            for i in analysis.important
        ],
        "general": [
            {"text": i.text, "reason": i.reason, "section": i.section, "risk": i.risk}
            for i in analysis.general
        ],
        "summary": analysis.summary,
        "total_count": analysis.total_count,
        "report_markdown": report_md,
    }
