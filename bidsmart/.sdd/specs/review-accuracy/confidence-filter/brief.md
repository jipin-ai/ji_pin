# confidence-filter: 匹配置信度过滤

## 问题

当前所有匹配结果无论置信度高低都送 LLM 审查。低置信匹配（<0.2）本质是随机段落 → LLM 判 non-compliant → 产生大量假阴性（318 个不合规中估计 200+ 是匹配错误导致）。

## 方案

在 pipeline Stage 2 和 Stage 3 之间插入置信度过滤：

- match_confidence < LOW_THRESHOLD（默认 0.25）→ 自动 unable_to_judge，不送 LLM
- match_confidence < MEDIUM_THRESHOLD（默认 0.4）→ 送 LLM 但标注"低置信匹配"
- match_confidence >= MEDIUM_THRESHOLD → 正常审查

## 改动范围

- `pipeline.py`: run_pipeline / run_pipeline_stream 中新增过滤逻辑
- `config.py`: 新增两个阈值配置
- 版本: 0.8.2 → 0.9.0

## 预期效果

不合规 318 → ~120（减少 ~200 假阴性转为 unable_to_judge）
