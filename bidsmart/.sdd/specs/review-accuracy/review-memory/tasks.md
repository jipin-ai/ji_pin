# Tasks: review-memory

跨项目审查记忆系统。

## 后端

- [ ] T1: `pyproject.toml` 版本 0.9.0
- [ ] T2: `src/models/` 新增 ReviewMemory 模型 (SQLAlchemy)
- [ ] T3: `src/main.py` 版本 0.9.0 + 导入新模型
- [ ] T4: `src/compliance/router.py` 新增 `POST /ai/memory/ignore` + `GET /ai/memory/list` + `DELETE /ai/memory/{id}`
- [ ] T5: `src/compliance/pipeline.py` match 后查 review_memory 表，命中跳过 LLM

## 前端

- [ ] T6: `static/index.html` 忽略按钮 POST /ai/memory/ignore
- [ ] T7: 前端 JS 验证

## 数据库

- [ ] T8: 手动创建 review_memory 表（或通过 SQLAlchemy metadata.create_all）
- [ ] T9: 重启 + 验证
