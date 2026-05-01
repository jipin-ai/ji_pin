# streaming-review — 需求规格 (EARS)

## 功能需求

### FR1: 管线逐条产出
**While** 审查管线运行中，**the system shall** 每完成一批审查条目（≤3 条）即通过 SSE 向已连接的客户端推送单条结果，而非等待全部完成后再一次性返回。

**Acceptance**: 客户端在第一条结果出现前等待不超过第一条 AI 审查完成的时间；后续条目陆续到达，间隔≤批次审查时间。

### FR2: SSE 事件格式
**When** 管线产出一条审查结果，**the system shall** 推送 `{status: "item", data: <ReviewItem>}` 格式的 SSE 事件，包含字段：requirement, verdict, weight_level, tender_page, bid_page, reason, suggestion。

**Acceptance**: 客户端 `EventSource` 可正确解析 `data:` 行中的 JSON，每收到一条追加一行到对照表。

### FR3: 完成后推送汇总
**When** 管线所有条目审查完毕，**the system shall** 推送 `{status: "done", score: N, summary: {...}}` 事件，包含合规评分和统计。

**Acceptance**: 客户端收到 done 事件后显示总分和通过/不通过统计。

### FR4: 前端 EventSource 监听
**When** 用户点击"开始审查"，**the system shall** 将前端改为 `EventSource` 连接 `/ai/review-file/stream`，替代原有的 `fetch` 调用。

**Acceptance**: 审查过程中前端不会因为单次 HTTP 超时而中断；逐条结果实时追加。

### FR5: 对照表逐行追加
**When** 前端收到 `status: "item"` 事件，**the system shall** 将新行 `<tr>` append 到对照表 `<tbody>`，而非重建整表。

**Acceptance**: 已显示的条目不会闪烁或消失；新行自然追加在表尾。

### FR6: 逐条确认/忽略可用
**When** 新行追加到对照表，**the system shall** 该行的确认(✅)和忽略(👁️)按钮立即可点击，不依赖整表完成。

**Acceptance**: 第三条结果出来后即可对前三条进行确认/忽略操作。

### FR7: 权重排序保持
**When** 管线逐条产出结果，**the system shall** 在后端按权重排序后推送（red → yellow → amber），前端按接收顺序追加即可。

**Acceptance**: 对照表中 red 行先出现，yellow 其次，amber 最后。

### FR8: 错误处理
**If** SSE 连接中断或某条审查失败，**then the system shall** 推送 `{status: "error", message: "..."}` 事件，前端显示错误提示，不丢失已推送的条目。

**Acceptance**: 连接中断时前端显示重试按钮；已显示的条目保留在对照表中。

### FR9: 向后兼容
**Where** 非流式端点 `/ai/review-file` 被调用，**the system shall** 保持原有行为不变，一次性返回全部结果。

**Acceptance**: 原有非流式调用方不受影响。

## 非功能需求

### NFR1: 首条延迟
第一条审查结果应在用户点击"开始审查"后 15 秒内出现（正常文件大小场景）。

### NFR2: 并发连接
SSE 端点应支持至少 5 个并发连接，不互相阻塞。

## 约束
- 前端单文件 `static/index.html`，不拆文件
- 使用标准 SSE（text/event-stream），不引入 WebSocket
- 管线 batch size 保持 3
- 不动数据库表结构
- 不引入新依赖

## 非目标 (Out of Scope)
- WebSocket 方案
- 审查进度百分比精确计算
- 管线并行度调整（batch size 优化）
- 移动端适配
