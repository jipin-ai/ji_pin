"""Tender Analysis Engine — Pre-bid requirement extraction and three-tier classification.

Uses DeepSeek LLM for full-document single-pass analysis, classifying all requirements
into disqualification / important / general tiers.
"""

from dataclasses import dataclass, field
from openai import AsyncOpenAI
from src.config import Settings
import json, re


# ── Data Models ─────────────────────────────────────────────────────────


@dataclass
class TenderItem:
    text: str
    category: str          # disqualification | important | general
    reason: str
    section: str = ""
    risk: str = ""


@dataclass
class TenderAnalysis:
    disqualification: list[TenderItem] = field(default_factory=list)
    important: list[TenderItem] = field(default_factory=list)
    general: list[TenderItem] = field(default_factory=list)
    summary: str = ""
    total_count: int = 0


# ── Prompt ──────────────────────────────────────────────────────────────


TENDER_ANALYSIS_PROMPT = """你是标书智审的招标文件分析引擎。分析以下招标文件，提取所有评审要求，按三层分类。

## 分类标准

### 🔴 废标项 (disqualification)
缺失直接导致废标的条款。包括但不限于：
- 投标保证金（金额、截止日、形式）
- 资质证书（有效期、等级、专业类别）
- 投标函签字盖章要求
- 投标有效期
- 实质性响应条件（带"否则""废标""否决""无效"等后果描述的要求）

### 🟡 重要条款 (important)
评审分值占比高（≥5分）或技术/商务核心要求：
- 项目经理/技术负责人资格
- 类似项目业绩数量和规模
- 技术方案核心要求
- 工期/质量承诺
- 报价方式和高分值计分项

### 🟢 一般条款 (general)
格式、装订、基础信息类：
- 文件装订方式、份数
- 页码格式、目录要求
- 一般性承诺声明
- 基础信息填报要求

## 输出格式
严格返回 JSON，不要带 markdown 代码块标记：
{
  "disqualification": [
    {"text": "条款原文", "reason": "分类理由（1-2句）", "section": "所在章节", "risk": "具体风险描述（如：保证金到账截止时间早于投标截止时间）"}
  ],
  "important": [
    {"text": "条款原文", "reason": "分类理由（1-2句）", "section": "所在章节", "risk": "潜在风险（可选，无风险填空字符串）"}
  ],
  "general": [
    {"text": "条款原文", "reason": "分类理由（1-2句）", "section": "所在章节", "risk": ""}
  ],
  "summary": "总体分析建议（150字内，包含：总条款数、废标项数、编写建议）"
}

## 原则
1. 不漏任何条款 — 招标文件中的每一条要求都要提取
2. 分类从宽 — 不确定时降低一级（宁可重要变一般，不可一般变废标）
3. 废标项务必精确 — 必须有明确的"缺失即废标"依据
4. 条款原文保持原样 — 不要改写，直接引用招标文件原文
5. 输出纯 JSON — 不要包裹在 ```json ``` 中"""


# ── Helper Functions ────────────────────────────────────────────────────


def _estimate_tokens(text: str) -> int:
    """Rough Chinese token estimation: ~0.5 chars per token."""
    return len(text) // 2


def _safe_parse_items(data: dict, key: str) -> list[TenderItem]:
    """Parse a category list from LLM output, tolerating missing fields."""
    items = []
    for raw in data.get(key, []):
        if not isinstance(raw, dict):
            continue
        items.append(TenderItem(
            text=raw.get("text", "").strip(),
            category=key,
            reason=raw.get("reason", "").strip(),
            section=raw.get("section", "").strip(),
            risk=raw.get("risk", "").strip(),
        ))
    return items


def _extract_json(text: str) -> dict | None:
    """Robust JSON extraction from LLM output."""
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in text
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    return None


def _degraded_analysis(requirements: list[str]) -> TenderAnalysis:
    """Fallback when LLM fails: return raw requirements as general tier."""
    items = [
        TenderItem(text=r, category="general", reason="自动提取（AI分析失败）", section="", risk="")
        for r in requirements
    ]
    return TenderAnalysis(
        general=items,
        summary="⚠️ LLM 分析失败，以下为招标文件自动提取的条款列表，请人工分类。",
        total_count=len(items),
    )


def _generate_report(analysis: TenderAnalysis) -> str:
    """Generate a Markdown report from analysis results."""
    d_count = len(analysis.disqualification)
    i_count = len(analysis.important)
    g_count = len(analysis.general)

    report = f"""# 📋 招标文件分析报告

**总条款数**: {analysis.total_count}
**废标项**: {d_count} | **重要条款**: {i_count} | **一般条款**: {g_count}

---

## 🔴 废标项（{d_count}条）— 缺失即废标

"""
    for idx, item in enumerate(analysis.disqualification, 1):
        report += f"### {idx}. {item.text[:80]}\n"
        report += f"- **章节**: {item.section}\n"
        report += f"- **理由**: {item.reason}\n"
        if item.risk:
            report += f"- **⚠️ 风险**: {item.risk}\n"
        report += "\n"

    report += f"---\n\n## 🟡 重要条款（{i_count}条）— 高分值/核心要求\n\n"
    for idx, item in enumerate(analysis.important, 1):
        report += f"### {idx}. {item.text[:80]}\n"
        report += f"- **章节**: {item.section}\n"
        report += f"- **理由**: {item.reason}\n"
        if item.risk:
            report += f"- **风险**: {item.risk}\n"
        report += "\n"

    report += f"---\n\n## 🟢 一般条款（{g_count}条）— 格式/基础要求\n\n"
    for idx, item in enumerate(analysis.general, 1):
        report += f"{idx}. {item.text[:120]}\n"
        if item.section:
            report += f"   - 章节: {item.section}\n"
        report += "\n"

    report += f"---\n\n## 📝 编写建议\n\n{analysis.summary}\n"
    return report


# ── Main Analysis Function ──────────────────────────────────────────────


async def analyze_tender(
    tender_text: str,
    settings: Settings,
    client: AsyncOpenAI | None = None,
) -> TenderAnalysis:
    """Analyze tender document for three-tier requirement classification.

    Args:
        tender_text: Full text of the tender document.
        settings: Application settings (API key, base URL, model).
        client: Optional pre-configured AsyncOpenAI client.

    Returns:
        TenderAnalysis with three-tier classified requirements.
    """
    if client is None:
        client = AsyncOpenAI(
            api_key=settings.deepseek_api_key or "***",
            base_url=settings.deepseek_base_url or "https://api.deepseek.com",
        )

    # Truncate to ~8000 tokens (~16000 chars for Chinese)
    max_chars = 16000
    truncated = len(tender_text) > max_chars
    text_slice = tender_text[:max_chars]

    user_prompt = f"## 招标文件内容（{len(tender_text)}字符{f'，已截断到{max_chars}字符' if truncated else ''}）\n\n{text_slice}"

    try:
        response = await client.chat.completions.create(
            model=settings.deepseek_model or "deepseek-chat",
            messages=[
                {"role": "system", "content": TENDER_ANALYSIS_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=8000,
        )
    except Exception as e:
        return TenderAnalysis(
            summary=f"LLM 调用失败: {e}",
            total_count=0,
        )

    content = response.choices[0].message.content or ""
    finish_reason = response.choices[0].finish_reason or ""

    data = _extract_json(content)

    if data is None:
        # Check if response was truncated
        if finish_reason == "length":
            return TenderAnalysis(
                summary="⚠️ 招标文件过长，分析结果被截断。请尝试分段上传或缩短文件。",
                total_count=0,
            )
        # Fallback: extract requirements from text and degrade
        from src.compliance.pipeline import extract_requirements
        from src.parsing import ParsedDocument
        # Build a minimal ParsedDocument for extraction
        lines = tender_text.split("\n")
        numbered = []
        for line in lines:
            line = line.strip()
            if re.search(r'^\s*(\(?\d+[\)、.．]|[一二三四五六七八九十]+[、．])\s*', line) and len(line) > 5:
                numbered.append(line)
        return _degraded_analysis(numbered)

    # Parse structured output
    disqualification = _safe_parse_items(data, "disqualification")
    important = _safe_parse_items(data, "important")
    general = _safe_parse_items(data, "general")
    summary = data.get("summary", "")

    total = len(disqualification) + len(important) + len(general)

    analysis = TenderAnalysis(
        disqualification=disqualification,
        important=important,
        general=general,
        summary=summary,
        total_count=total,
    )

    return analysis
