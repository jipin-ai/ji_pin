# streaming-review — 实现任务

## 1. Pipeline 异步生成器
_Status: pending_
_Boundary: src/compliance/pipeline.py_
_Depends: none_

**Goal**: 新增 `run_pipeline_stream()` async generator，每批次完成后 yield 单条结果。

**Acceptance Criteria**:
- [ ] `run_pipeline_stream()` 与 `run_pipeline()` 共享解析/匹配/审查逻辑
- [ ] 批次完成时 yield `{"status":"item", "data":<ReviewItem>}`
- [ ] 全部完成后 yield `{"status":"done", "score":<float>, "summary":{...}}`
- [ ] 异常时 yield `{"status":"error", "message":<str>}`

### 1.1 抽取共享管线逻辑 (P)
_Status: pending_
_Boundary: src/compliance/pipeline.py_
_Depends: none_

从 `run_pipeline()` 中提取 `_parse_and_match()` 辅助函数（解析+提取+匹配），使两个管道函数复用。

### 1.2 实现 run_pipeline_stream() generator
_Status: pending_
_Boundary: src/compliance/pipeline.py_
_Depends: 1.1_

在 `aggregate_results()` 阶段改为逐条 yield，保持权重排序。最后 yield done 事件。

### 1.3 错误处理
_Status: pending_
_Boundary: src/compliance/pipeline.py_
_Depends: 1.2_

单条审查失败不中断整个流，yield error 事件继续下一条。

---

## 2. SSE 端点改造
_Status: pending_
_Boundary: src/compliance/router.py_
_Depends: 1.2_

**Goal**: `/review-file/stream` 使用 ReadableStream + POST 模式，消费 generator。

**Acceptance Criteria**:
- [ ] 端点返回 `StreamingResponse(media_type="text/event-stream")`
- [ ] 使用 `tender_doc_ids` / `bid_doc_ids` 数组（修复旧格式兼容）
- [ ] 消费 `run_pipeline_stream()` 逐条 SSE 推送

### 2.1 改写 review-file-stream 端点
_Status: pending_
_Boundary: src/compliance/router.py_
_Depends: 1.2_

```python
@router.post("/review-file/stream")
async def ai_review_file_stream(req, user, db):
    async def generate():
        docs = await _load_docs(req.tender_doc_ids, req.bid_doc_ids, db)
        yield f"data: {json.dumps({'status':'parsing'})}\n\n"
        async for event in run_pipeline_stream(docs['tender'], docs['bid'], db, settings):
            yield f"data: {json.dumps(event)}\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")
```

### 2.2 修复多文件 ID 兼容
_Status: pending_
_Boundary: src/compliance/router.py_
_Depends: 2.1_

将端点中的 `req.tender_doc_id`/`req.bid_doc_id` 改为 `req.tender_doc_ids`/`req.bid_doc_ids`，同时兼容旧格式。

---

## 3. 前端流式渲染
_Status: pending_
_Boundary: static/index.html_
_Depends: 2.1_

**Goal**: 前端用 `fetch + ReadableStream` 替代 EventSource，逐条追加对照表行。

**Acceptance Criteria**:
- [ ] 点击"开始审查"后对照表 tbody 清空
- [ ] 每收到 item SSE 事件即追加一行
- [ ] 每行按钮立即可点（确认/忽略）
- [ ] 收到 done 事件后显示总分
- [ ] 连接中断显示错误提示

### 3.1 实现 fetch + ReadableStream 读取
_Status: pending_
_Boundary: static/index.html (startFileReview 函数)
_Depends: 2.1_

替换 `fetch + await r.json()` 为 `fetch + response.body.getReader()` 循环读取 SSE 行。

### 3.2 实现 appendCompareRow() 逐行追加
_Status: pending_
_Boundary: static/index.html (buildCompareTable 附近)
_Depends: 3.1_

从 `buildCompareTable()` 中提取行模板逻辑为 `createCompareRow(item)`，`appendCompareRow()` 调用它后 `tbody.appendChild(tr)`。

### 3.3 确保按钮实时可用
_Status: pending_
_Boundary: static/index.html
_Depends: 3.2_

`confirmItem()` / `ignoreItem()` 依赖 `event.target.closest('tr')` 找到行并删除。逐行模式下每行独立 DOM 元素，确认逻辑不变。

### 3.4 done/error 事件处理
_Status: pending_
_Boundary: static/index.html
_Depends: 3.1_

收到 `status:"done"` → 显示总分弹窗。收到 `status:"error"` → 对照表保留已有行，顶部显示错误横幅。

---

## 4. 收尾：版本号 + 重启 + 验证
_Status: pending_
_Boundary: 全局
_Depends: 1.3, 2.2, 3.4_

**Goal**: 升级版本号，重启服务，完成功能验证。

**Acceptance Criteria**:
- [ ] `src/main.py` 和 `pyproject.toml` 版本号 → `0.5.0`
- [ ] 服务重启后健康检查通过
- [ ] 浏览器端多文件审查逐条出结果

### 4.1 版本号升级 (P)
_Status: pending_
_Boundary: src/main.py + pyproject.toml
_Depends: none_

### 4.2 重启 + 验证 (P)
_Status: pending_
_Boundary: 服务
_Depends: 4.1_
