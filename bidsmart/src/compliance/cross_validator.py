"""Stage 5: Cross-validation for critical (red-level) review items.

Based on AI Agents-as-Judge (2506.22485) multi-agent consensus approach.
For red-level (废标/否决) requirements, runs two independent LLM reviews
and compares verdicts. Disagreement → unable_to_judge, Agreement → confirmed.

This eliminates single-LLM randomness-derived false negatives.
"""

from __future__ import annotations

import asyncio
import json
import re

from openai import AsyncOpenAI


async def cross_validate_review(
    requirement_text: str,
    bid_excerpt: str,
    client: AsyncOpenAI,
    review_prompt: str,
    model: str = "deepseek-chat",
) -> dict:
    """Run two independent reviews and cross-validate.

    Returns:
        {
            "verdict": str,           # final verdict
            "reason": str,
            "suggestion": str,
            "cross_validated": bool,  # True if both reviews agree
            "review_a": dict,         # first review result
            "review_b": dict,         # second review result
        }
    """
    user_prompt = f"""## 招标要求
{requirement_text[:2000]}

## 投标响应
{bid_excerpt[:2000]}

请判定合规性并返回JSON。"""

    async def _single_review() -> dict:
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": review_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,  # Slightly higher temp for diversity
                max_tokens=500,
            )
            content = response.choices[0].message.content or "{}"
            json_match = re.search(r'\{[^{}]*\}', content)
            if json_match:
                return json.loads(json_match.group())
        except Exception:
            pass
        return {"verdict": "unable_to_judge", "reason": "审查异常", "suggestion": ""}

    # Run two independent reviews concurrently
    review_a, review_b = await asyncio.gather(
        _single_review(),
        _single_review(),
    )

    verdict_a = review_a.get("verdict", "unable_to_judge")
    verdict_b = review_b.get("verdict", "unable_to_judge")

    # Cross-validate
    if verdict_a == verdict_b:
        # Agreement → confirmed verdict
        return {
            "verdict": verdict_a,
            "reason": f"[交叉验证确认] {review_a.get('reason', '')}",
            "suggestion": review_a.get("suggestion", ""),
            "cross_validated": True,
            "review_a": review_a,
            "review_b": review_b,
        }
    else:
        # Disagreement → unable_to_judge
        return {
            "verdict": "unable_to_judge",
            "reason": f"[交叉验证冲突] 审查A判定'{verdict_a}'，审查B判定'{verdict_b}'，结论不一致",
            "suggestion": "建议人工复核此关键条款",
            "cross_validated": False,
            "review_a": review_a,
            "review_b": review_b,
        }
