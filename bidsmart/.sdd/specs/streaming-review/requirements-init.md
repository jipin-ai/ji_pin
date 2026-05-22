# streaming-review — 需求初始化

## 项目描述
BidSmart 标书智审系统当前的文件审查模式是：上传招标+投标文件 → 管线完整计算所有审查条目 → 一次性返回全部结果。加入权重分级后计算负载加大，用户等待时间长。

需要改为**流式逐条推送**：管线处理出一条审查结果，立即推送到前端对照表显示，用户无需等待全部完成即可逐条进行确认/忽略操作。

## 谁有这个问题
投标审核人员 — 上传文件后等待时间过长，且必须等全部结果出来才能开始逐条确认/忽略。

## 当前状态
- 后端 `/ai/review-file/stream` 端点存在但只发送进度状态 (loading/parsing/extracting)，管线走完后一次性发 `{status: 'done', result: <全部结果>}`
- 前端 `startFileReview()` 使用 `fetch` 调用非流式端点 `/ai/review-file`，无 EventSource 代码
- `run_pipeline()` 批量 3 条异步 gather，全部完成后才聚合返回
- `buildCompareTable()` 一次性 innerHTML 渲染全表

## 期望变更
- 管线改为 async generator，每完成一批（3条）即产出
- 后端 `/ai/review-file/stream` 改造成逐条 SSE 推送 `{status: 'item', data: review_item}`
- 前端改用 EventSource 监听，每收到一条就 `appendChild <tr>` 追加到对照表
- 每条追加的行立即带确认/忽略按钮，可实时操作
- 所有项目推送完毕后发 `{status: 'done', ...}` 显示总分和统计
