"""AI Compliance Review Pipeline — v1.0 six-stage architecture.

Based on: Legal-DC (2603.11772), Adaptive HR (2604.14222),
Agents-as-Judge (2506.22485), Reason and Verify (2603.10143).

Stages:
  0: Structured parsing — section numbering alignment
  1: Multi-strategy matching — 3-path fusion
  2: Dual-path verification — cross-checked LLM validation
  3: Precision excerpt — ≤500 char targeted extraction
  4: Compliance review — regulation-context-aware judgment
  5: Cross-validation — red-level dual-review consensus
  6: Aggregate — risk scoring + reporting
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field

import numpy as np
from openai import AsyncOpenAI

from src.config import Settings
from src.parsing.models import ParsedDocument


# ── Data models ────────────────────────────────────────────────────────

@dataclass
class Requirement:
    id: str
    text: str
    section_heading: str = ""
    page_number: int = 0
    weight_level: str = "amber"
    keywords: list[str] = field(default_factory=list)


@dataclass
class MatchedSection:
    requirement: Requirement
    bid_text: str
    bid_section_heading: str = ""
    bid_page_number: int = 0
    confidence: float = 0.0
    # v1.0: multi-path metadata
    agreement_score: float = 0.0
    path_votes: dict = field(default_factory=dict)
    consensus: str = "low"
    verification_result: dict | None = None
    precision_excerpt: str = ""


@dataclass
class ReviewItem:
    requirement: str
    bid_response: str
    verdict: str
    reason: str
    suggestion: str = ""
    cross_validated: bool = False


@dataclass
class ReviewReport:
    overall_score: float
    total_items: int
    compliant: int
    partial: int
    non_compliant: int
    unable_to_judge: int
    items: list[dict] = field(default_factory=list)
    risk_summary: str = ""
    suggestions: list[str] = field(default_factory=list)


# ── System prompts ──────────────────────────────────────────────────────

ITEM_REVIEW_PROMPT = """你是标书智审(BidSmart)的AI合规审查引擎。请逐项比对以下单条招标要求与投标响应。

## 判定原则
1. 宽松原则：宁可判 partial/unable_to_judge，不要轻易判 non_compliant。
2. 证据导向：判定理由必须引用投标响应中的原文或明确缺失证据。
3. partial 优先：信息不完整、表述模糊、非实质性偏离 → 判 partial。
4. 图片意识：若投标响应中包含 [图片识别] 标记，涉及图片内容的要求优先判 unable_to_judge。

## 判定标准
- ✅ compliant：投标响应完全满足或超出招标要求，有明确证据
- ⚠️ partial：基本满足，但有细微偏差或信息不完整（优先使用）
- ❌ non_compliant：投标明确不满足、缺失响应、或实质性偏离（严格把关）
- ❓ unable_to_judge：投标未提及该要求，或关键信息来自图片，或证据严重不足

## 输出格式
必须严格返回JSON：
{"verdict": "compliant|partial|non_compliant|unable_to_judge", "reason": "判定理由（引用原文证据，80字内）", "suggestion": "整改建议（如不合规或部分合规，否则空）"}"""


AGGREGATE_PROMPT = """你是标书智审的AI审查总结引擎。根据逐项审查结果，生成整体报告。

## 分析维度
1. 按权重分层统计：废标项(red) > 资质项(yellow) > 技术项(amber)
2. 区分"证据不足"(unable_to_judge) 和"证据否定"(non_compliant)
3. 关键风险点聚焦 red 级的 non_compliant 和 partial

## 输出格式
必须严格返回JSON：
{"overall_score": 85.5, "risk_summary": "按权重分层的风险概述（150字内）", "key_risks": [{"level": "red/yellow/amber", "issue": "具体风险描述", "count": 3}], "suggestions": ["整改建议1", "整改建议2", "整改建议3"], "unable_to_judge_note": "需人工复核的条款数及原因简述"}"""


# ── Stage 0: Requirement Extraction ─────────────────────────────────────


def _classify_weight(requirement_text: str, section_heading: str = "") -> str:
    text = requirement_text + " " + section_heading
    red_keywords = [
        "废标", "否决", "无效投标", "投标无效", "不接受", "不允许偏离",
        "实质性响应", "实质性要求", "参数响应", "参数不符", "参数偏离",
        "报价不统一", "分项报价", "总报价", "总价", "价格不一致", "第三方",
    ]
    for kw in red_keywords:
        if re.search(kw, text):
            return "red"
    yellow_keywords = [
        "资质", "许可证", "认证", "资格", "注册资金", "注册资本",
        "商务", "业绩", "合同", "案例", "项目经验", "原厂商", "授权", "代理",
        "付款", "质保金", "履约保证金", "发票", "交货期", "工期", "交付",
    ]
    for kw in yellow_keywords:
        if re.search(kw, text):
            return "yellow"
    return "amber"


def extract_requirements(doc: ParsedDocument) -> list[Requirement]:
    requirements: list[Requirement] = []
    numbered = doc.find_numbered_items()
    for item in numbered:
        page_num = 0
        for sec in doc.sections:
            if item["item_text"] in sec.items:
                page_num = sec.page_number
                break
        requirements.append(Requirement(
            id=f"req-{len(requirements)+1}",
            text=item["item_text"],
            section_heading=item.get("heading", ""),
            page_number=page_num,
            weight_level=_classify_weight(item["item_text"], item.get("heading", "")),
            keywords=_extract_keywords(item["item_text"]),
        ))
    if not requirements and doc.raw_text:
        pattern = re.compile(
            r'(?:^|\n)\s*((?:\(\d+\)|（\d+）|\d+[\.、．)]\s|'
            r'[一二三四五六七八九十]+[、．]\s)[^\n]+)',
            re.MULTILINE,
        )
        for match in pattern.finditer(doc.raw_text):
            text = match.group(1).strip()
            if len(text) > 5:
                requirements.append(Requirement(
                    id=f"req-{len(requirements)+1}",
                    text=text,
                    keywords=_extract_keywords(text),
                ))
    return requirements


def _extract_keywords(text: str) -> list[str]:
    cleaned = re.sub(r'[\d\.,，。；;：:（）()、\s]+', ' ', text)
    words = [w for w in cleaned.split() if len(w) >= 2]
    stop_words = {'的', '和', '与', '或', '及', '须', '应', '需', '要', '是', '在', '为', '等'}
    return [w for w in words if w not in stop_words][:10]


# ── Stage 0-5: Six-Stage Review Pipeline ────────────────────────────────


async def run_pipeline(
    tender_doc: ParsedDocument,
    bid_doc: ParsedDocument,
    settings: Settings,
) -> dict:
    """Run the complete 6-stage review pipeline (v1.0)."""
    client = AsyncOpenAI(
        api_key=settings.deepseek_api_key or "***",
        base_url=settings.deepseek_base_url or "https://api.deepseek.com",
    )

    # ── Stage 0: Requirement Extraction + Structured Parsing ──
    requirements = extract_requirements(tender_doc)
    if not requirements:
        return {"error": "未能从招标文件中提取到评审条款", "overall_score": 0, "items": []}

    # ── Stage 1: Multi-Strategy Matching ──
    from src.compliance.structured_matcher import (
        extract_numbering_tree, align_requirements,
    )
    from src.compliance.multi_matcher import (
        MatchResult, FusedMatch, fuse_matches, compute_bm25_score,
    )
    from src.knowledge.embedder import embedder as _embedder

    # Build bid section pool
    bid_sections: list[tuple[str, str, int]] = []
    for sec in bid_doc.sections:
        text = sec.heading + "\n" + sec.content
        if sec.items:
            text += "\n" + "\n".join(sec.items)
        bid_sections.append((sec.heading, text, sec.page_number))
    if not bid_sections:
        bid_sections = [("", bid_doc.text, 0)]

    # Pre-compute BGE embeddings for all bid sections
    section_texts = [t for _, t, _ in bid_sections]
    section_embeddings = _embedder.embed(section_texts)

    # Structured alignment
    tender_nodes = extract_numbering_tree(tender_doc.sections, "tender")
    bid_nodes = extract_numbering_tree(bid_doc.sections, "bid")
    alignment = align_requirements(requirements, tender_nodes, bid_nodes)

    fused_matches: list[tuple[Requirement, FusedMatch | None]] = []

    for req in requirements:
        # Path A: Structured alignment
        structured: list[MatchResult] = []
        if req.id in alignment:
            heading, score = alignment[req.id]
            # Find the corresponding bid section
            for bh, bt, bp in bid_sections:
                if bh == heading:
                    structured.append(MatchResult("structured", bh, bt, bp, score, 1))
                    break

        # Path B: Semantic matching
        req_emb = _embedder.embed_single(req.text[:2000])
        scores = np.dot(section_embeddings, req_emb)
        best_idx = int(np.argmax(scores))
        semantic = [
            MatchResult("semantic", bid_sections[best_idx][0],
                        bid_sections[best_idx][1], bid_sections[best_idx][2],
                        float(scores[best_idx]), 1)
        ]

        # Path C: Keyword/BM25 matching
        all_doc_texts = [t for _, t, _ in bid_sections]
        keyword_scores = []
        for i, (bh, bt, bp) in enumerate(bid_sections):
            score = compute_bm25_score(req.keywords, bt, all_doc_texts)
            keyword_scores.append((score, bh, bt, bp))
        keyword_scores.sort(key=lambda x: x[0], reverse=True)
        keyword = [
            MatchResult("keyword", keyword_scores[0][1],
                        keyword_scores[0][2], keyword_scores[0][3],
                        keyword_scores[0][0], 1)
        ] if keyword_scores and keyword_scores[0][0] > 0 else []

        # Fuse
        fused = fuse_matches(structured, semantic, keyword)
        fused_matches.append((req, fused))

    # ── Stage 2: Dual-Path Verification ──
    from src.compliance.dual_verifier import dual_verify

    verified_matches: list[tuple[Requirement, FusedMatch, dict]] = []

    for req, fused in fused_matches:
        if fused is None:
            continue
        verification = await dual_verify(
            req.text, fused.bid_heading, fused.bid_text, client,
            model=settings.deepseek_model or "deepseek-chat",
        )
        if verification["passed"]:
            verified_matches.append((req, fused, verification))

    if not verified_matches:
        return {
            "error": "未能匹配招标要求与投标响应内容",
            "overall_score": 0, "items": [],
            "requirement_count": len(requirements),
        }

    # ── Stage 3: Precision Excerpt Extraction ──
    from src.compliance.excerpt_extractor import extract_excerpt

    excerpted_matches: list[tuple[Requirement, FusedMatch, dict, str]] = []

    for req, fused, verification in verified_matches:
        excerpt, _ = await extract_excerpt(
            req.text, fused.bid_text, client,
            model=settings.deepseek_model or "deepseek-chat",
        )
        excerpted_matches.append((req, fused, verification, excerpt))

    # ── Check review memory ──
    memory_map: dict[str, dict] = {}
    try:
        from src.models.review_memory import ReviewMemory
        import aiosqlite
        db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
        async with aiosqlite.connect(db_path) as db:
            for req, _, _, _ in excerpted_matches:
                req_hash = ReviewMemory.hash_requirement(req.text)
                cursor = await db.execute(
                    "SELECT verdict, reason, suggestion FROM review_memory WHERE requirement_hash = ?",
                    (req_hash,))
                row = await cursor.fetchone()
                if row:
                    memory_map[req.text] = {"verdict": row[0], "reason": row[1], "suggestion": row[2] or ""}
    except Exception:
        pass

    # ── Stage 4: Compliance Review ──
    review_items: list[ReviewItem] = []

    async def _review_one(req: Requirement, fused: FusedMatch, verification: dict, excerpt: str) -> ReviewItem:
        req_text = req.text
        if req_text in memory_map:
            mem = memory_map[req_text]
            return ReviewItem(req_text, fused.bid_heading, mem["verdict"],
                              f"[记忆] {mem['reason']}", mem["suggestion"])

        reviewed = excerpt if excerpt else fused.bid_text[:3000]
        user_prompt = f"""## 招标要求
{req_text}

## 投标响应
{reviewed}

请判定合规性并返回JSON。"""

        response = await client.chat.completions.create(
            model=settings.deepseek_model or "deepseek-chat",
            messages=[
                {"role": "system", "content": ITEM_REVIEW_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=500,
        )
        content = response.choices[0].message.content or "{}"
        json_match = re.search(r'\{[^{}]*\}', content)
        if json_match:
            data = json.loads(json_match.group())
            return ReviewItem(req_text, fused.bid_heading,
                              data.get("verdict", "unable_to_judge"),
                              data.get("reason", ""), data.get("suggestion", ""))

        return ReviewItem(req_text, fused.bid_heading, "unable_to_judge", "AI响应解析失败", "")

    # Stage 4: Batch concurrent reviews
    BATCH_SIZE = 3
    for i in range(0, len(excerpted_matches), BATCH_SIZE):
        batch = excerpted_matches[i:i + BATCH_SIZE]
        tasks = [_review_one(req, fused, verif, excerpt)
                 for req, fused, verif, excerpt in batch]
        batch_results = await asyncio.gather(*tasks)
        review_items.extend(batch_results)

    # ── Stage 5: Cross-Validation (red-level items) ──
    from src.compliance.cross_validator import cross_validate_review

    for i in range(len(review_items)):
        req, fused, _, excerpt = excerpted_matches[i]
        if req.weight_level == "red":
            cv_result = await cross_validate_review(
                req.text, excerpt, client, ITEM_REVIEW_PROMPT,
                model=settings.deepseek_model or "deepseek-chat",
            )
            review_items[i] = ReviewItem(
                req.text, fused.bid_heading,
                cv_result["verdict"], cv_result["reason"],
                cv_result.get("suggestion", ""),
                cross_validated=cv_result.get("cross_validated", False),
            )

    # ── Stage 6: Aggregate ──
    matches_flat = [
        MatchedSection(req, fused.bid_text, fused.bid_heading,
                       fused.bid_page, fused.agreement_score,
                       fused.agreement_score, fused.path_votes, fused.consensus,
                       verification, excerpt)
        for (req, fused, verification, excerpt), fused in
        zip(excerpted_matches, [m[1] for m in excerpted_matches])
    ]
    report = await aggregate_results(review_items, matches_flat, settings, client)

    return {
        "overall_score": _safe_round(report.overall_score),
        "total_items": report.total_items,
        "compliant": report.compliant,
        "partial": report.partial,
        "non_compliant": report.non_compliant,
        "unable_to_judge": report.unable_to_judge,
        "items": report.items,
        "risk_summary": report.risk_summary,
        "suggestions": report.suggestions,
        "method": "pipeline-v1",
        "requirement_count": len(requirements),
        "match_count": len(review_items),
        "verified_count": len(verified_matches),
    }


# ── Stage 6: Aggregate ──────────────────────────────────────────────────


def _safe_round(value: any, fallback: float = 0.0) -> float:
    """Round to 1dp, handling LLM-generated floats and string values."""
    try:
        return round(float(value), 1)
    except (TypeError, ValueError):
        return round(fallback, 1)


async def aggregate_results(
    items: list[ReviewItem],
    matches: list[MatchedSection],
    settings: Settings,
    client: AsyncOpenAI | None = None,
) -> ReviewReport:
    if client is None:
        client = AsyncOpenAI(
            api_key=settings.deepseek_api_key or "***",
            base_url=settings.deepseek_base_url or "https://api.deepseek.com",
        )

    match_map = {m.requirement.text: m for m in matches}
    total = len(items)
    compliant = sum(1 for i in items if i.verdict == "compliant")
    partial = sum(1 for i in items if i.verdict == "partial")
    non = sum(1 for i in items if i.verdict in ("non_compliant", "noncompliant"))
    unable = sum(1 for i in items if i.verdict == "unable_to_judge")

    scored = [i for i in items if i.verdict != "unable_to_judge"]
    local_score = 0.0
    if scored:
        points = sum(100 if i.verdict == "compliant" else 60 if i.verdict == "partial" else 0 for i in scored)
        local_score = round(points / len(scored), 1)

    summary_text = "\n".join(
        f"{j+1}. [{i.verdict}] {i.requirement[:60]} → {i.reason[:60]}"
        for j, i in enumerate(items)
    )

    def _build_item(i: ReviewItem) -> dict:
        m = match_map.get(i.requirement)
        return {
            "requirement": i.requirement,
            "bid_response": i.bid_response,
            "verdict": i.verdict,
            "reason": i.reason,
            "suggestion": i.suggestion,
            "weight_level": m.requirement.weight_level if m else "amber",
            "tender_page": m.requirement.page_number if m else 0,
            "bid_page": m.bid_page_number if m else 0,
            "section_heading": m.requirement.section_heading if m else "",
            "bid_section_heading": m.bid_section_heading if m else "",
            "match_confidence": round(m.confidence, 3) if m else 0,
            "agreement_score": round(m.agreement_score, 3) if m else 0,
            "consensus": m.consensus if m else "low",
            "cross_validated": getattr(i, "cross_validated", False),
        }

    try:
        response = await client.chat.completions.create(
            model=settings.deepseek_model or "deepseek-chat",
            messages=[
                {"role": "system", "content": AGGREGATE_PROMPT},
                {"role": "user", "content": f"审查结果：\n{summary_text[:3000]}"},
            ],
            temperature=0.1,
            max_tokens=500,
        )
        content = response.choices[0].message.content or "{}"
        json_match = re.search(r'\{[^{}]*\}', content)
        if json_match:
            data = json.loads(json_match.group())
            return ReviewReport(
                overall_score=_safe_round(data.get("overall_score", local_score)),
                total_items=total, compliant=compliant, partial=partial,
                non_compliant=non, unable_to_judge=unable,
                items=[_build_item(i) for i in items],
                risk_summary=data.get("risk_summary", ""),
                suggestions=data.get("suggestions", []),
            )
    except Exception:
        pass

    return ReviewReport(
        overall_score=_safe_round(local_score), total_items=total,
        compliant=compliant, partial=partial,
        non_compliant=non, unable_to_judge=unable,
        items=[_build_item(i) for i in items],
    )


# ── Legacy: backward-compatible entry points ────────────────────────────


async def run_pipeline_stream(tender_doc, bid_doc, settings):
    """Streaming wrapper — delegates to run_pipeline with SSE yields."""
    yield {"type": "status", "message": "v1.0 六阶段审查管线启动..."}
    
    result = await run_pipeline(tender_doc, bid_doc, settings)
    
    if "error" in result:
        yield {"type": "error", "message": result["error"]}
        return

    for i, item in enumerate(result.get("items", [])):
        yield {
            "type": "item", "index": i, "total": result["total_items"],
            "requirement": item["requirement"], "verdict": item["verdict"],
            "reason": item["reason"], "suggestion": item.get("suggestion", ""),
            "weight_level": item.get("weight_level", "amber"),
            "match_confidence": item.get("match_confidence", 0),
            "agreement_score": item.get("agreement_score", 0),
            "consensus": item.get("consensus", "low"),
        }

    yield {"type": "done", "report": result}
