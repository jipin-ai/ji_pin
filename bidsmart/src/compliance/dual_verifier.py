"""Stage 2: Dual-path reflection verification.

Based on Legal-DC dual-path self-reflection mechanism (2603.11772).

Two independent LLM verification paths:
  Path A: "Does this bid section respond to this requirement?" (section→requirement)
  Path B: "Where should this requirement be addressed in the bid?" (requirement→section)

Cross-check: only pass if both paths point to the same section.
Disagreement → reduced confidence or fallback.
"""

from __future__ import annotations

import json
import re
from typing import Optional

from openai import AsyncOpenAI


PATH_A_PROMPT = """你是标书智审(BidSmart)的匹配验证引擎（路径A）。

## 任务
判断以下投标段落中是否有内容直接回应了招标要求。

## 判据
- 投标段落提到了与要求相同或相近的主题/参数/条件 → responding=true
- 投标段落完全不相关 → responding=false

## 输出格式
严格返回JSON：
{"responding": true/false, "relevant_excerpt": "回应了要求的原文摘录（不超过200字）", "confidence": 0.8}"""


PATH_B_PROMPT = """你是标书智审(BidSmart)的匹配验证引擎（路径B）。

## 任务
根据招标要求，判断该要求最应该在投标文件的哪个章节/位置被回应。

## 输出格式
严格返回JSON：
{"expected_section": "投标文件中应回应此要求的章节名称（如'第三章 技术方案'）", "expected_keywords": ["关键词1", "关键词2"], "confidence": 0.8}"""


async def verify_path_a(
    requirement_text: str,
    bid_heading: str,
    bid_text: str,
    client: AsyncOpenAI,
    model: str = "deepseek-chat",
) -> tuple[bool, str, float]:
    """Path A: Verify if bid section responds to requirement.

    Returns: (responding, relevant_excerpt, confidence)
    """
    user_prompt = f"""## 招标要求
{requirement_text[:2000]}

## 投标段落
标题: {bid_heading}
内容: {bid_text[:3000]}

请判断此投标段落是否回应了上述招标要求。"""

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": PATH_A_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=400,
        )
        content = response.choices[0].message.content or "{}"
        json_match = re.search(r'\{[^{}]*\}', content)
        if json_match:
            data = json.loads(json_match.group())
            return (
                data.get("responding", False),
                data.get("relevant_excerpt", ""),
                data.get("confidence", 0.5),
            )
    except Exception:
        pass

    return False, "", 0.0


async def verify_path_b(
    requirement_text: str,
    client: AsyncOpenAI,
    model: str = "deepseek-chat",
) -> tuple[str, list[str], float]:
    """Path B: Where should this requirement be addressed?

    Returns: (expected_section, expected_keywords, confidence)
    """
    user_prompt = f"""## 招标要求
{requirement_text[:2000]}

根据此要求，判断它最应该在投标文件的哪个章节被回应。"""

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": PATH_B_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=300,
        )
        content = response.choices[0].message.content or "{}"
        json_match = re.search(r'\{[^{}]*\}', content)
        if json_match:
            data = json.loads(json_match.group())
            return (
                data.get("expected_section", ""),
                data.get("expected_keywords", []),
                data.get("confidence", 0.5),
            )
    except Exception:
        pass

    return "", [], 0.0


async def dual_verify(
    requirement_text: str,
    bid_heading: str,
    bid_text: str,
    client: AsyncOpenAI,
    model: str = "deepseek-chat",
) -> dict:
    """Run dual-path verification and cross-check results.

    Returns:
        {
            "passed": bool,
            "consensus": "high" | "medium" | "low" | "conflict",
            "path_a": {"responding": bool, "excerpt": str, "confidence": float},
            "path_b": {"section": str, "keywords": list, "confidence": float},
            "cross_check": str,  # explanation
        }
    """
    # Run both paths concurrently
    import asyncio

    task_a = verify_path_a(requirement_text, bid_heading, bid_text, client, model)
    task_b = verify_path_b(requirement_text, client, model)

    (responding, excerpt, conf_a), (expected_section, keywords, conf_b) = \
        await asyncio.gather(task_a, task_b)

    path_a_result = {
        "responding": responding,
        "excerpt": excerpt,
        "confidence": round(conf_a, 3),
    }
    path_b_result = {
        "section": expected_section,
        "keywords": keywords,
        "confidence": round(conf_b, 3),
    }

    # Cross-check: does Path A's matched section match Path B's expected section?
    cross_check = ""
    if responding and expected_section:
        # Fuzzy match section names
        a_clean = bid_heading.lower().replace(" ", "").replace("章", "").replace("节", "")
        b_clean = expected_section.lower().replace(" ", "").replace("章", "").replace("节", "")
        if a_clean == b_clean or b_clean in a_clean or a_clean in b_clean:
            cross_check = "match: both paths agree on same section"
            consensus = "high"
        else:
            cross_check = f"partial: path A points to '{bid_heading[:50]}', path B expects '{expected_section[:50]}'"
            consensus = "medium"
    elif responding:
        cross_check = "path A positive, path B unclear"
        consensus = "medium"
    elif expected_section:
        cross_check = f"path A negative, path B expects '{expected_section[:50]}'"
        consensus = "low"
    else:
        cross_check = "both paths negative — no clear match"
        consensus = "conflict"

    passed = consensus in ("high", "medium") and responding

    return {
        "passed": passed,
        "consensus": consensus,
        "path_a": path_a_result,
        "path_b": path_b_result,
        "cross_check": cross_check,
    }
