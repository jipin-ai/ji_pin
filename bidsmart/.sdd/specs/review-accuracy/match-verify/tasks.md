# Tasks: match-verify

新增 LLM 验证阶段。

- [ ] T1: `pipeline.py` 新增 MATCH_VERIFY_PROMPT
- [ ] T2: `pipeline.py` 新增 `verify_match(match, client, settings)` 异步函数
- [ ] T3: `pipeline.py` review_item 重构：先 verify → 通过则用 relevant_excerpt 审查 → 不通过则 unable_to_judge
- [ ] T4: `pipeline.py` run_pipeline/run_pipeline_stream 集成验证步骤
- [ ] T5: 版本沿用 0.9.0
- [ ] T6: 重启验证
