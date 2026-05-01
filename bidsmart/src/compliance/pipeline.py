"""AI Compliance Review Pipeline — multi-stage: extract → match → review → aggregate.

Replaces the old single-call approach. Handles large documents by:
1. Extracting numbered requirements from tender
2. Matching each requirement to relevant bid sections (keyword overlap)
3. Sending per-item prompts to AI (small context, fits easily)
4. Aggregating all results
"""

import asyncio
import json
import re
from dataclasses import dataclass, field

from openai import AsyncOpenAI

from src.config import Settings
from src.parsing.models import ParsedDocument


# ── Data models ────────────────────────────────────────────────────────


@dataclass
class Requirement:
    """An extracted requirement from the tender document."""
    id: str                          # e.g. "req-3"
    text: str                        # full requirement text
    section_heading: str = ""        # parent section heading
    page_number: int = 0             # page in tender document
    weight_level: str = "amber"      # red / yellow / amber
    keywords: list[str] = field(default_factory=list)


@dataclass
class MatchedSection:
    """A bid section matched to a requirement."""
    requirement: Requirement
    bid_text: str                    # matched bid content
    bid_section_heading: str = ""
    bid_page_number: int = 0         # page in bid document
    confidence: float = 0.0          # 0-1 match score


@dataclass
class ReviewItem:
    """Single-item review result from AI."""
    requirement: str
    bid_response: str
    verdict: str                     # compliant|partial|non_compliant|unable_to_judge
    reason: str
    suggestion: str = ""


@dataclass
class ReviewReport:
    """Aggregated review results."""
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

## 判定标准
- ✅ compliant（合规）：投标响应完全满足或超出招标要求
- ⚠️ partial（部分合规）：基本满足但有细微偏差或信息不完整
- ❌ non_compliant（不合规）：明确不满足、缺失响应、或实质性偏离
- ❓ unable_to_judge（无法判断）：信息不足以判定

## 输出格式
必须严格返回JSON：
{"verdict": "compliant|partial|non_compliant|unable_to_judge", "reason": "判定理由（50字内）", "suggestion": "整改建议（如不合规，否则空）"}"""


AGGREGATE_PROMPT = """你是标书智审的AI审查总结引擎。根据逐项审查结果，生成整体报告。

## 输出格式
必须严格返回JSON：
{"overall_score": 85.5, "risk_summary": "关键风险概述（100字内）", "suggestions": ["整改建议1", "整改建议2", "整改建议3"]}"""


# ── Stage 1: Requirement Extraction ─────────────────────────────────────


def _classify_weight(requirement_text: str, section_heading: str = "") -> str:
    """Classify requirement into weight tiers based on keywords.

    Returns 'red' (废标/关键), 'yellow' (资质/商务), 'amber' (技术/其他).
    """
    text = requirement_text + " " + section_heading

    # Red: disqualifying items
    red_keywords = [
        "废标", "否决", "无效投标", "投标无效", "取消投标资格",
        "不接受", "不允许偏离", "实质性响应", "实质性要求",
        "参数响应", "参数不符", "参数偏离",
        "报价不统一", "分项报价", "总报价", "总价", "价格不一致",
        "第三方", "除.*外.*单位", "非投标人",
    ]
    import re
    for kw in red_keywords:
        if re.search(kw, text):
            return "red"

    # Yellow: qualifications and commercial
    yellow_keywords = [
        "资质", "许可证", "认证", "资格", "注册资金", "注册资本",
        "商务", "业绩", "合同", "案例", "项目经验",
        "原厂商", "授权", "代理",
        "付款", "质保金", "履约保证金", "发票",
        "交货期", "工期", "交付",
    ]
    for kw in yellow_keywords:
        if re.search(kw, text):
            return "yellow"

    # Amber: technical and others (default)
    return "amber"


def extract_requirements(doc: ParsedDocument) -> list[Requirement]:
    """Extract numbered requirements from the tender document.

    Leverages the parser's find_numbered_items() for structured items,
    and falls back to regex on raw text for unstructured documents.
    """
    requirements: list[Requirement] = []

    # Try structured items first
    numbered = doc.find_numbered_items()
    for item in numbered:
        # Find which section this item belongs to (for page number)
        page_num = 0
        for sec in doc.sections:
            if item["item_text"] in sec.items:
                page_num = sec.page_number
                break
        req = Requirement(
            id=f"req-{len(requirements)+1}",
            text=item["item_text"],
            section_heading=item.get("heading", ""),
            page_number=page_num,
            weight_level=_classify_weight(item["item_text"], item.get("heading", "")),
            keywords=_extract_keywords(item["item_text"]),
        )
        requirements.append(req)

    # Fallback: if no structured items found, regex on raw text
    if not requirements and doc.raw_text:
        pattern = re.compile(
            r'(?:^|\n)\s*((?:\(\d+\)|（\d+）|\d+[\.、．)]\s|'
            r'[一二三四五六七八九十]+[、．]\s)[^\n]+)',
            re.MULTILINE,
        )
        for match in pattern.finditer(doc.raw_text):
            text = match.group(1).strip()
            if len(text) > 5:  # filter noise
                requirements.append(Requirement(
                    id=f"req-{len(requirements)+1}",
                    text=text,
                    keywords=_extract_keywords(text),
                ))

    return requirements


def _extract_keywords(text: str) -> list[str]:
    """Extract key terms for matching."""
    # Remove numbers and punctuation, keep meaningful Chinese/English words
    cleaned = re.sub(r'[\d\.\,，。；;：:（）()、\s]+', ' ', text)
    words = [w for w in cleaned.split() if len(w) >= 2]
    # Add common bid-domain stop words to filter
    stop_words = {'的', '和', '与', '或', '及', '须', '应', '需', '要', '是', '在', '为', '等'}
    return [w for w in words if w not in stop_words][:10]


# ── Stage 2: Section Matching ───────────────────────────────────────────


def match_sections(
    requirements: list[Requirement],
    bid_doc: ParsedDocument,
) -> list[MatchedSection]:
    """Match each requirement to the most relevant bid document sections.

    Uses keyword overlap scoring. Returns sorted by confidence.
    """
    matches: list[MatchedSection] = []

    # Build bid section pool
    bid_sections: list[tuple[str, str, int]] = []  # (heading, content, page_number)
    for sec in bid_doc.sections:
        section_text = sec.heading + "\n" + sec.content
        if sec.items:
            section_text += "\n" + "\n".join(sec.items)
        bid_sections.append((sec.heading, section_text, sec.page_number))

    # If no sections, use full text as one section
    if not bid_sections:
        bid_sections = [("", bid_doc.text, 0)]

    for req in requirements:
        best_score = 0.0
        best_text = ""
        best_heading = ""
        best_page = 0

        for heading, content, page_num in bid_sections:
            score = _keyword_overlap(req.keywords, content)
            if score > best_score:
                best_score = score
                best_text = content
                best_heading = heading
                best_page = page_num

        # If no keyword match, fallback to section-position matching:
        # requirements in tender section N → bid section N (or nearest)
        if best_score == 0:
            req_idx = 0
            for i, r in enumerate(requirements):
                if r.id == req.id:
                    req_idx = i
                    break
            # Map requirement index to bid section index proportionally
            bid_idx = min(int(req_idx / len(requirements) * len(bid_sections)), len(bid_sections) - 1)
            if bid_idx < len(bid_sections):
                best_heading, best_text, best_page = bid_sections[bid_idx]
                best_score = 0.01  # mark as fallback

        matches.append(MatchedSection(
            requirement=req,
            bid_text=best_text[:3000],
            bid_section_heading=best_heading,
            bid_page_number=best_page,
            confidence=best_score,
        ))

    # Sort by confidence descending
    matches.sort(key=lambda m: m.confidence, reverse=True)
    return matches


def _keyword_overlap(keywords: list[str], text: str) -> float:
    """Calculate keyword overlap score (0-1)."""
    if not keywords:
        return 0.0
    hits = sum(1 for kw in keywords if kw in text)
    return hits / len(keywords)


# ── Stage 3: Per-Item AI Review ─────────────────────────────────────────


async def review_item(
    match: MatchedSection,
    settings: Settings,
    client: AsyncOpenAI | None = None,
) -> ReviewItem:
    """Send a single requirement + matched bid text to AI for review."""
    if client is None:
        client = AsyncOpenAI(
            api_key=settings.deepseek_api_key or "***",
            base_url=settings.deepseek_base_url or "https://api.deepseek.com",
        )

    user_prompt = f"""## 招标要求
{match.requirement.text}

## 投标响应
{match.bid_text[:3000]}

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
        return ReviewItem(
            requirement=match.requirement.text,
            bid_response=match.bid_section_heading or "(投标响应)",
            verdict=data.get("verdict", "unable_to_judge"),
            reason=data.get("reason", ""),
            suggestion=data.get("suggestion", ""),
        )

    return ReviewItem(
        requirement=match.requirement.text,
        bid_response="",
        verdict="unable_to_judge",
        reason="AI响应解析失败",
    )


# ── Stage 4: Aggregate ──────────────────────────────────────────────────


async def aggregate_results(
    items: list[ReviewItem],
    matches: list[MatchedSection],
    settings: Settings,
    client: AsyncOpenAI | None = None,
) -> ReviewReport:
    """Aggregate all per-item results into a final report."""
    if client is None:
        client = AsyncOpenAI(
            api_key=settings.deepseek_api_key or "***",
            base_url=settings.deepseek_base_url or "https://api.deepseek.com",
        )

    # Build a map from requirement text → match (for page numbers)
    match_map = {m.requirement.text: m for m in matches}

    # Quick local aggregation for counts
    total = len(items)
    compliant = sum(1 for i in items if i.verdict == "compliant")
    partial = sum(1 for i in items if i.verdict == "partial")
    non = sum(1 for i in items if i.verdict in ("non_compliant", "noncompliant"))
    unable = sum(1 for i in items if i.verdict == "unable_to_judge")

    # Calculate score: compliant=100, partial=60, non=0, unable excluded
    scored = [i for i in items if i.verdict != "unable_to_judge"]
    if scored:
        points = sum(
            100 if i.verdict == "compliant" else
            60 if i.verdict == "partial" else 0
            for i in scored
        )
        local_score = points / len(scored)
    else:
        local_score = 0.0

    # Use AI for risk summary and suggestions
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
                overall_score=data.get("overall_score", local_score),
                total_items=total,
                compliant=compliant,
                partial=partial,
                non_compliant=non,
                unable_to_judge=unable,
                items=[_build_item(i) for i in items],
                risk_summary=data.get("risk_summary", ""),
                suggestions=data.get("suggestions", []),
            )
    except Exception:
        pass

    # Fallback: local-only aggregation
    return ReviewReport(
        overall_score=local_score,
        total_items=total,
        compliant=compliant,
        partial=partial,
        non_compliant=non,
        unable_to_judge=unable,
        items=[_build_item(i) for i in items],
        risk_summary="",
        suggestions=[],
    )


# ── Full Pipeline ───────────────────────────────────────────────────────


async def run_pipeline(
    tender_doc: ParsedDocument,
    bid_doc: ParsedDocument,
    settings: Settings,
) -> dict:
    """Run the complete 4-stage review pipeline.

    Returns the same dict format as the legacy ai_reviewer for backwards compatibility.
    """
    # Stage 1: Extract requirements
    requirements = extract_requirements(tender_doc)

    if not requirements:
        return {
            "error": "未能从招标文件中提取到评审条款",
            "overall_score": 0,
            "items": [],
        }

    # Stage 2: Match to bid sections
    matches = match_sections(requirements, bid_doc)

    if not matches:
        return {
            "error": "未能匹配招标要求与投标响应内容",
            "overall_score": 0,
            "items": [],
            "requirement_count": len(requirements),
        }

    # Stage 3: Per-item AI review (concurrent for speed)
    client = AsyncOpenAI(
        api_key=settings.deepseek_api_key or "***",
        base_url=settings.deepseek_base_url or "https://api.deepseek.com",
    )

    # Process in batches to avoid rate limits
    BATCH_SIZE = 3
    review_items: list[ReviewItem] = []

    for i in range(0, len(matches), BATCH_SIZE):
        batch = matches[i:i + BATCH_SIZE]
        tasks = [review_item(m, settings, client) for m in batch]
        batch_results = await asyncio.gather(*tasks)
        review_items.extend(batch_results)

    # Stage 4: Aggregate
    report = await aggregate_results(review_items, matches, settings, client)

    return {
        "overall_score": report.overall_score,
        "total_items": report.total_items,
        "compliant": report.compliant,
        "partial": report.partial,
        "non_compliant": report.non_compliant,
        "unable_to_judge": report.unable_to_judge,
        "items": report.items,
        "risk_summary": report.risk_summary,
        "suggestions": report.suggestions,
        "method": "pipeline",       # indicates new pipeline was used
        "requirement_count": len(requirements),
        "match_count": len(matches),
    }

# ── Streaming Pipeline ───────────────────────────────────────────────────


async def run_pipeline_stream(
    tender_doc,
    bid_doc,
    settings,
):
    """Streaming pipeline — yields each review item as it completes.

    Yields dicts: {"type": "item", "index": N, "total": M, ...} per review,
    then {"type": "done", "report": {...}} at the end.
    """
    # Stage 1: Extract requirements
    requirements = extract_requirements(tender_doc)
    if not requirements:
        yield {"type": "error", "message": "未能从招标文件中提取到评审条款"}
        return

    # Stage 2: Match
    matches = match_sections(requirements, bid_doc)
    if not matches:
        yield {"type": "error", "message": "未能匹配招标要求与投标响应内容"}
        return

    # Stage 3: Stream per-item review
    client = AsyncOpenAI(
        api_key=settings.deepseek_api_key or "***",
        base_url=settings.deepseek_base_url or "https://api.deepseek.com",
    )

    total = len(matches)
    review_items: list = []
    for i, match in enumerate(matches):
        item = await review_item(match, settings, client)
        review_items.append(item)
        yield {
            "type": "item",
            "index": i,
            "total": total,
            "requirement": match.requirement.text,
            "verdict": item.verdict,
            "reason": item.reason,
            "suggestion": item.suggestion,
            "weight_level": match.requirement.weight_level,
            "tender_page": match.requirement.page_number,
            "bid_page": match.bid_page_number,
            "bid_section_heading": match.bid_section_heading,
            "section_heading": match.requirement.section_heading,
            "match_confidence": round(match.confidence, 3),
        }

    # Stage 4: Aggregate
    report = await aggregate_results(review_items, matches, settings, client)

    yield {
        "type": "done",
        "report": {
            "overall_score": report.overall_score,
            "total_items": report.total_items,
            "compliant": report.compliant,
            "partial": report.partial,
            "non_compliant": report.non_compliant,
            "unable_to_judge": report.unable_to_judge,
            "items": report.items,
            "risk_summary": report.risk_summary,
            "suggestions": report.suggestions,
            "method": "pipeline-stream",
            "requirement_count": len(requirements),
            "match_count": len(matches),
        },
    }
