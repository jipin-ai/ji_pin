# match-verify: LLM 匹配验证

## 问题

BGE 语义匹配选出的"最相似"段落中，3000 字符只有一小部分跟招标要求相关。LLM 看到大量不相关内容 → 判"没有响应" → false non-compliant。

## 方案

三阶段验证链（arXiv:2603.10143 "Reason and Verify" 框架落地）：

```
Stage 2a: 语义匹配 → 候选段落
Stage 2b: LLM 验证 → "这段投标内容是否在回应这条招标要求？"
          返回: yes/no + 相关子段落（精确到句）+ 置信度
Stage 2c: 合规审查 → 基于验证通过的精确定位进行判定
```

验证 prompt：
> "招标要求：{requirement}
> 投标段落：{bid_text[:3000]}
> 请判断：这段投标文字中是否有内容直接回应了上述招标要求？
> 返回 JSON: {"responding": true/false, "relevant_excerpt": "摘录相关原文", "confidence": 0.8}"

验证通过（responding=true）→ 用 relevant_excerpt 替换完整段落 → 精确定位审查
验证不通过（responding=false）→ 直接 unable_to_judge

## 改动范围

- `pipeline.py`: 新增 `verify_match()` 函数，重构 review_item 流程
- 版本: 沿用 0.9.0

## 预期效果

不合规再减 30-50（消除匹配漂移导致的假阴性）
