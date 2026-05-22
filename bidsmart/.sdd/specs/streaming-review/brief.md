# 逐条流式审查 — brief.md

## 问题
加入权重分级后，后端管线处理负载指数上升。当前模式是全部算完再返回，用户等很久才看到结果。

## 需求
- 管线处理出一条就推出一条到前端
- 主屏对照表逐条追加显示
- 每出来一条就可以立即确认/忽略，不等其他条

## 现状 (探索结果)
- `/ai/review-file/stream` 已存在，但**只发进度状态 + 最后一次性吐结果**，不是逐条推
- 前端 `startFileReview()` 用的是 `fetch` 非流式端点，没有 EventSource 代码
- pipeline.py `run_pipeline()` 批量 3 条异步 gather，最后才聚合
- `buildCompareTable()` 一次性 innerHTML 渲染全表

## 路径判定
**Path C — 新单 scope spec**: `streaming-review`
改动范围: pipeline.py（改为 async generator）、router.py（逐条 SSE emit）、index.html（EventSource + 逐行追加）

## 涉及文件
- `src/compliance/pipeline.py` — `run_pipeline()` 改 async generator
- `src/compliance/router.py` — `/review-file/stream` 逐条推送
- `static/index.html` — EventSource 监听 + 逐行追加 + 实时确认/忽略

## 明确不需要
- 不改 /ai/review-file（非流式）—— 保留向后兼容
- 不拆前端文件
- 不改数据库表结构
