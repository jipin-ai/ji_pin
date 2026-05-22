# review-accuracy: 对照评审精准度提升

## 问题

用户实测反馈：BidSmart 标书智审的对照评审精准度仅 10-15%，几乎等于随机猜测水平。

## 根因

`src/compliance/pipeline.py` 的 Stage 2（匹配阶段 `match_sections`）使用纯关键词重叠匹配，关键词提取逻辑简陋（9个停用词），无关键词命中时回退到「按位置比例盲猜映射」。导致每条招标条款匹配到的投标文本基本是随机段落，LLM 拿到错误输入自然无法做出正确判定。

**不是 LLM 审不准，是匹配阶段把输入给错了。**

## 关键发现

1. **BGE embedder 已存在但未被 pipeline 使用**：`src/knowledge/embedder.py` 使用 `BAAI/bge-small-zh-v1.5`（512维），仅用于知识库搜索和 Agent 模式的 `search_kb`，pipeline 的 `match_sections` 完全未使用
2. **pyproject.toml 缺少 sentence-transformers 依赖**：运行时通过 Hermes 全局 venv 可用，但不正式
3. **论文支持**：多篇 arXiv 论文（2025-2026）验证了三阶段匹配→LLM验证→逐项审查的架构可达到 90%+ 精准度

## 方案路线图（4 阶段）

| 阶段 | 方案 | 预期精准度 | 改动范围 |
|------|------|-----------|---------|
| P0 | 语义匹配（BGE embedding→cosine sim） | 10%→50%+ | pipeline.py match_sections |
| P1 | 混合检索（BM25 + Dense + Reranker） | 50%→75% | 新增 matcher 模块 |
| P2 | Match-Verify-Review 三阶段验证链 | 75%→88% | pipeline 重构为三阶段 |
| P3 | Multi-Agent 专项审查 | 88%→93% | 扩展 agent_loop |

## 论文依据

- **arXiv:2506.22485** "AI Agents-as-Judge" (Dasgupta 2025): Multi-agent 企业文档审查，95% 人机一致率
- **arXiv:2604.14222** "Adaptive Hybrid Retrieval" (Hashmi 2026): Tree Reasoning 0.938 vs Vector RAG 0.821，覆盖法律/金融/医疗
- **arXiv:2603.10143** "Reason and Verify" (Khan 2026): Canadian AI 2026 收录，三阶段验证框架

## 依赖

- `sentence-transformers` (需加入 pyproject.toml)
- `BAAI/bge-small-zh-v1.5` (已下载缓存)
- `pip install rank-bm25` (P1 阶段)
- `BAAI/bge-reranker-v2-m3` (P1 阶段)

## 当前版本

v0.8.0
