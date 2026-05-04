# prompt-restructure: 审查 Prompt 重构

## 问题

当前 ITEM_REVIEW_PROMPT 缺少：
1. **法规上下文**：LLM 不知道判定依据 → 靠常识判断 → 不准
2. **优先级引导**：默认倾向 non-compliant 而非 partial/unable_to_judge
3. **图片感知指令**：不知道如何处理图片相关内容

## 方案

重构三条 prompt：

### 1. ITEM_REVIEW_PROMPT（逐项审查）

新增：
- 法规引用前置：`load_skill` 加载相关法规，注入 prompt
- 判定优先级：partial > unable_to_judge > non-compliant（宽松原则）
- 图片处理指令：遇到 `[图片识别]` 标记时优先 unable_to_judge

### 2. AGGREGATE_PROMPT（汇总）

新增：
- 按权重（red/yellow/amber）分层汇总
- 明确区分"证据不足"(unable_to_judge) vs "证据否定"(non-compliant)

### 3. 新增 MATCH_VERIFY_PROMPT

用于 match-verify 阶段

## 改动范围

- `pipeline.py`: ITEM_REVIEW_PROMPT, AGGREGATE_PROMPT 重构
- 版本: 沿用 0.9.0

## 预期效果

LLM 判 non-compliant 更谨慎 → 减少 20-30 假阴性
