# 标前招标分析 — 任务分解

## 1. 核心分析模块
_Status: completed_
_Boundary: src/compliance/tender_analyzer.py_
_Depends: none_

**Goal**: 新建 `tender_analyzer.py`，实现 `analyze_tender()` 和降级逻辑。

### 1.1 创建模块 + 数据模型 (P)
_Status: completed_
_Boundary: src/compliance/tender_analyzer.py_
_Depends: none_

- 定义 `TenderItem` / `TenderAnalysis` dataclass
- 定义 `TENDER_ANALYSIS_PROMPT` 常量
- 实现 `_safe_parse_analysis()` JSON 解析
- 实现 `_degraded_analysis()` 降级函数

### 1.2 实现 analyze_tender() 主函数 (P)
_Status: completed_
_Boundary: src/compliance/tender_analyzer.py_
_Depends: 1.1_

- 截断文本到 8000 tokens（按字符估算：~16000 chars）
- 调用 DeepSeek API（复用 Settings 配置）
- 解析 JSON 响应，构造 TenderAnalysis
- JSON 解析失败时调用降级函数
- 生成 Markdown 报告字符串（`_generate_report()`）

## 2. API 端点
_Status: completed_
_Boundary: src/compliance/router.py_
_Depends: 1_

**Goal**: 在 compliance router 中新增 `/ai/analyze-tender` 端点。

### 2.1 新增 AnalyzeRequest schema + 端点函数
_Status: completed_
_Boundary: src/compliance/router.py_
_Depends: 1.2_

- 定义 `AnalyzeRequest(BaseModel)` — 接受 `tender_doc_id: int`
- 实现 `ai_analyze_tender()` 端点函数
- auth: `Depends(get_current_user)`
- 流程：文档查询 → parse_document → analyze_tender → 返回 JSON
- 错误处理：文档不存在 → 404，解析失败 → 400

### 2.2 计算 total_count 和统计
_Status: completed_
_Boundary: src/compliance/router.py_
_Depends: 2.1_

- 确保返回的 `total_count` 等于三层 items 数量之和
- 添加 `report_markdown` 到响应（始终生成）

## 3. 版本号 + 重启
_Status: completed_
_Boundary: src/main.py_
_Depends: 2_

**Goal**: 版本号 → 1.1.0，重启服务。

### 3.1 Bump version + restart
_Status: completed_
_Boundary: src/main.py_
_Depends: 2.2_

- `main.py` 版本号改为 `1.1.0`
- kill 39001 端口，重启 uvicorn
- health check 返回新版本号

## 4. 实测验证
_Status: completed_
_Boundary: none (manual)_
_Depends: 3_

**Goal**: 用已有招标文件跑一次分析，验证三层分类正确性。

### 4.1 调用 analyze-tender 验证
_Status: completed_
_Boundary: none_
_Depends: 3.1_

- 用 三院三部弱电分包 招标文件调用端点
- 验证返回的 disqualification 包含已知废标项（如保证金、资质等）
- 验证 total_count 匹配文档条款数
- 验证 Markdown 报告格式正确

---

## 依赖关系图

```
1.1 (P) ──┐
           ├── 1.2 ── 2.1 ── 2.2 ── 3.1 ── 4.1
1.2 (P) ──┘
```

(P) = 可并行，但 sdd-impl 按顺序执行以避免冲突。
