# Tasks: confidence-filter

全部在 pipeline.py 中实现，无前端改动。

- [ ] T1: `config.py` 新增 LOW_CONFIDENCE_THRESHOLD=0.25, MEDIUM_CONFIDENCE_THRESHOLD=0.4
- [ ] T2: `pipeline.py` run_pipeline(): match 后过滤低置信 → auto unable_to_judge
- [ ] T3: `pipeline.py` run_pipeline_stream(): 同样逻辑
- [ ] T4: `pipeline.py` review_item prompt: 低置信匹配时标注 "⚠️ 低匹配置信度"
- [ ] T5: 版本 0.9.0 (pyproject + main.py)
- [ ] T6: 重启验证
