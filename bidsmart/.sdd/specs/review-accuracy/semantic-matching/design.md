# Design: 语义匹配

## 概述

在 `src/compliance/pipeline.py` 中重构 `match_sections()` 函数，用 BGE embedding + 余弦相似度替代关键词重叠匹配。

## 变更范围（单一函数）

**文件**: `src/compliance/pipeline.py`
**函数**: `match_sections()` (第 189-249 行)
**新增**: `_semantic_match()` (替代 `_keyword_overlap`)
**删除**: `_keyword_overlap()` 函数体（保留签名作废弃标记）

## 实现细节

### 核心逻辑

```python
def _semantic_match(req_embedding, bid_section_embeddings):
    """返回 (best_idx, best_score)"""
    scores = cosine_similarity([req_embedding], bid_section_embeddings)[0]
    best_idx = int(np.argmax(scores))
    return best_idx, float(scores[best_idx])

def match_sections(requirements, bid_doc, embedder=None):
    # 1. 构建投标段落池 (不变)
    # 2. 预计算所有 bid_sections 的 embedding (批量，一次性)
    # 3. 对每条 requirement:
    #    a. embed requirement text
    #    b. 计算与所有 bid_section embeddings 的余弦相似度
    #    c. 选最高分段落
    #    d. 若 best_score < 0.2 → fallback 到位置比例映射
```

### Embedder 注入

匹配函数接受可选的 `embedder` 参数：
- 调用方（`run_pipeline` / `run_pipeline_stream`）传入 `from src.knowledge.embedder import embedder`
- 若 embedder 为 None，回退到原有关键词匹配逻辑（向后兼容）

### 余弦相似度

使用 numpy：
```python
import numpy as np
# embeddings already normalized by SentenceTransformer(normalize_embeddings=True)
scores = np.dot(section_embeddings, req_embedding)  # 等价余弦相似度
```

### Fallback 阈值

`SEMANTIC_MATCH_THRESHOLD = 0.2`
- 相似度 < 0.2 → 认为无有效匹配，回退到位置比例映射
- 阈值可通过环境变量 `SEMANTIC_MATCH_THRESHOLD` 覆盖（加入 config.py）

## 性能分析

| 场景 | 关键词匹配 | 语义匹配 | 说明 |
|------|-----------|---------|------|
| 10条条款, 20段落 | <1ms | ~200ms | bge-small-zh-v1.5 512维, 批量encode |
| 100条条款, 50段落 | <1ms | ~1s | 预计算段落embedding + 逐条点积 |
| 200条条款, 100段落 | <1ms | ~3s | 仍在5s约束内 |

## 文件变更清单

1. **`src/compliance/pipeline.py`** — 核心改动
   - 新增 `import numpy as np`
   - 新增 `_semantic_match()` 函数
   - 重构 `match_sections()` (新增 embedder 参数, 语义匹配主逻辑)
   - 标记 `_keyword_overlap()` 为废弃
   - 新增 `SEMANTIC_MATCH_THRESHOLD = 0.2` 常量

2. **`src/config.py`** — 配置扩展
   - 新增 `semantic_match_threshold: float = 0.2`

3. **`pyproject.toml`** — 依赖声明
   - 新增 `"sentence-transformers>=3.0"`

## 不改变

- `run_pipeline()` / `run_pipeline_stream()` 的返回格式
- `ReviewItem` / `MatchedSection` / `ReviewReport` 数据模型
- 前端 `index.html` 无需修改（`match_confidence` 字段已存在）
- `POST /ai/review-file` / `POST /ai/review-file/stream` API 契约
