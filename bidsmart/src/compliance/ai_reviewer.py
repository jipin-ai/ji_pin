"""AI Compliance Review Engine — DeepSeek-powered tender/bid analysis."""
from openai import AsyncOpenAI
from src.config import Settings
import json, re

SYSTEM_PROMPT = """你是标书智审(BidSmart)的AI合规审查引擎。你的任务是对比招标要求与投标响应，逐项判定合规性。

## 审查规则
1. 逐项比对：招标文件的每一条要求，在投标书中找到对应响应
2. 判定标准：
   - ✅ 合规：投标响应完全满足或超出招标要求
   - ⚠️ 部分合规：基本满足但有细微偏差或信息不完整
   - ❌ 不合规：明确不满足、缺失响应、或实质性偏离招标要求
   - ❓ 无法判断：投标书未提及该要求，或信息不足以判定
3. 每项判定必须包含：条款引用（招标文件位置）、原文摘录（关键文字）、判定理由（具体说明）
4. 最后给出：整体合规率、关键风险点、整改建议

## 输出格式
必须严格返回JSON，格式如下：
{
  "overall_score": 85.5,
  "total_items": 10,
  "compliant": 7,
  "partial": 2,
  "non_compliant": 1,
  "unable_to_judge": 0,
  "items": [
    {
      "requirement": "招标要求简述",
      "bid_response": "投标响应简述",
      "verdict": "compliant|partial|non_compliant|unable_to_judge",
      "reason": "判定理由",
      "suggestion": "整改建议（如不合规）"
    }
  ],
  "risk_summary": "关键风险概述",
  "suggestions": ["整改建议1", "整改建议2"]
}"""

async def review_compliance(
    tender_text: str,
    bid_text: str,
    settings: Settings,
) -> dict:
    """Run AI compliance review comparing tender requirements against bid response."""
    client = AsyncOpenAI(
        api_key=settings.deepseek_api_key or "sk-placeholder",
        base_url=settings.deepseek_base_url or "https://api.deepseek.com",
    )
    
    user_prompt = f"""## 招标文件要求
{tender_text[:4000]}

## 投标书响应
{bid_text[:4000]}

请逐项比对上述招标要求与投标响应，输出JSON格式的审查结果。"""

    response = await client.chat.completions.create(
        model=settings.deepseek_model or "deepseek-chat",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
        max_tokens=4000,
    )
    
    content = response.choices[0].message.content
    # Extract JSON from response
    json_match = re.search(r'\{[\s\S]*\}', content or "{}")
    if json_match:
        return json.loads(json_match.group())
    return {"error": "AI响应解析失败", "raw": content}
