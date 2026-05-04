"""Stage 3: Precision excerpt extraction.

Based on Reason and Verify framework (2603.10143).
Extracts only the relevant portion of a matched bid section,
reducing input from 3000 chars to ≤500 chars of targeted content.
"""

from __future__ import annotations

import json
import re

from openai import AsyncOpenAI


EXCERPT_PROMPT = """你是标书智审(BidSmart)的原文摘录引擎。

## 任务
从投标段落中摘录与招标要求直接相关的内容（原文照抄，不总结）。

## 规则
1. 只摘录直接回应了招标要求的句子
2. 保持原文措辞，不要改写
3. 如果段落中多处相关，摘录最核心的1-3句
4. 如果整个段落都不相关，返回空字符串
5. 总摘录不超过500字

## 输出格式
严格返回JSON：
{"excerpt": "摘录的原文", "relevance": "high|medium|low"}"""


async def extract_excerpt(
    requirement_text: str,
    bid_text: str,
    client: AsyncOpenAI,
    model: str = "deepseek-chat",
    max_chars: int = 500,
) -> tuple[str, str]:
    """Extract the most relevant excerpt from bid text for a given requirement.

    Returns:
        (excerpt_text, relevance_level)
    """
    if len(bid_text) <= max_chars:
        # Bid text is already short enough
        return bid_text, "high"

    user_prompt = f"""## 招标要求
{requirement_text[:2000]}

## 投标段落
{bid_text[:3000]}

请摘录与上述招标要求直接相关的原文。"""

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": EXCERPT_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=300,
        )
        content = response.choices[0].message.content or "{}"
        json_match = re.search(r'\{[^{}]*\}', content)
        if json_match:
            data = json.loads(json_match.group())
            excerpt = data.get("excerpt", "")
            relevance = data.get("relevance", "low")
            # Truncate to max_chars
            if len(excerpt) > max_chars:
                excerpt = excerpt[:max_chars]
            return excerpt, relevance
    except Exception:
        pass

    # Fallback: return first max_chars of bid text
    return bid_text[:max_chars], "low"
