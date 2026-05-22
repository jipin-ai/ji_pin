# Tasks: 语义匹配

## 任务列表（依赖顺序）

### T1: 添加 sentence-transformers 依赖
- [ ] `pyproject.toml`: `dependencies` 新增 `"sentence-transformers>=3.0"`
- [ ] `pyproject.toml`: version 更新为 `0.8.1`
- [ ] 验证: `pip install -e .` 不报错

### T2: 添加语义匹配阈值配置
- [ ] `src/config.py`: 新增 `semantic_match_threshold: float = 0.2`
- [ ] `src/main.py`: version 更新为 `0.8.1`

### T3: 实现语义匹配函数
- [ ] `src/compliance/pipeline.py`: 添加 `import numpy as np`
- [ ] `src/compliance/pipeline.py`: 新增 `_semantic_match(req_emb, sec_embs) → (idx, score)`
- [ ] `src/compliance/pipeline.py`: 新增 `SEMANTIC_MATCH_THRESHOLD = 0.2`

### T4: 重构 match_sections 主函数
- [ ] `src/compliance/pipeline.py`: `match_sections()` 新增 `embedder=None` 参数
- [ ] 批量预计算所有 bid_sections 的 embedding（一次性 encode）
- [ ] 循环中：embed requirement → cosine sim → 选最高分
- [ ] best_score < threshold → 回退到位置比例 fallback
- [ ] embedder=None → 回退到原有关键词匹配（向后兼容）

### T5: 更新调用方传入 embedder
- [ ] `src/compliance/pipeline.py`: `run_pipeline()` 中 `match_sections(requirements, bid_doc, embedder)`
- [ ] `src/compliance/pipeline.py`: `run_pipeline_stream()` 中同上
- [ ] embedder 实例来自 `from src.knowledge.embedder import embedder`

### T6: 标记废弃函数
- [ ] `_keyword_overlap()` 保留签名，添加 `# DEPRECATED: replaced by _semantic_match` 注释

### T7: 重启服务 + 验证
- [ ] `fuser -k 39001/tcp; sleep 1`
- [ ] 启动 uvicorn 确认无 import 错误
- [ ] `curl -s http://localhost:39001/health` 返回 200
- [ ] 版本检查: `/openapi.json` 返回 `0.8.1`

### T8: 前端 JS 语法验证
- [ ] `grep -n 'async async\|function function\|await await' static/index.html` 返回空

## 版本

`0.8.0` → `0.8.1`（小版本号，bug fix 级别改动）
