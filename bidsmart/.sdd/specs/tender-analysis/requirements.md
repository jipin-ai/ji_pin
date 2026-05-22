# 标前招标分析 — 需求规格

## 功能需求

### R1: 招标文件分析端点
**When** 用户提交招标文件（上传文件或文档ID），**the system shall** 解析文件内容、调用 LLM 一次性分析所有条款、按三层分类返回结构化结果。

**Acceptance Criteria:**
- `POST /ai/analyze-tender` 接收 `tender_doc_id` 或直接文件上传
- 返回 JSON，含 `disqualification`/`important`/`general` 三个列表
- 每项含：条款原文、分类理由、所属章节、风险提示
- 响应时间 ≤ 60 秒（含 LLM 调用）

### R2: 三层分类逻辑
**The system shall** 按以下定义对招标条款分类：

| 层级 | 标签 | 定义 | 示例 |
|------|------|------|------|
| 🔴 废标项 | disqualification | 缺失直接废标 | 保证金金额/截止日、资质证书有效期、投标函签字盖章 |
| 🟡 重要条款 | important | 评审分值占比高或核心技术要求 | 项目经理经验年数、技术方案BIM要求、类似业绩数量 |
| 🟢 一般条款 | general | 格式/装订/基础信息 | 页码格式、装订方式、目录要求 |

**Acceptance Criteria:**
- 废标项召回率 ≥ 90%（对已知废标条款的文件人工验证）
- 分类附带理由（1-2句说明为什么归入该层级）
- 无条款被遗漏（total = disqualification + important + general = 提取条款总数）

### R3: LLM Prompt 设计
**The system shall** 使用全文一次性分析策略，将招标文件全文（≤6000 tokens）送入 DeepSeek，要求其输出结构化 JSON。

**Acceptance Criteria:**
- Prompt 包含三层定义和输出格式指令
- 温度参数 ≤ 0.1（高确定性分类）
- 输出格式：`{"analysis": {"disqualification": [...], "important": [...], "general": [...]}, "summary": "..."}`
- max_tokens ≥ 4000（确保长文件完整输出）

### R4: 报告生成
**Where** 用户请求报告格式，**the system shall** 生成 Markdown 格式的可打印分析报告。

**Acceptance Criteria:**
- 报告含：标题、文件信息、三层统计、逐层详细列表、编写建议
- 废标项以红色高亮标记
- 输出为纯文本 Markdown，可直接复制到飞书文档/Word

### R5: 与现有管线集成
**The system shall** 复用现有文档解析管线（`parse_document`），不使用新的文档处理逻辑。

**Acceptance Criteria:**
- 使用 `src.parsing.parse_document` 解析输入文件
- 复用 `Settings` 配置（API key、base URL、model）
- 认证使用现有 `get_current_user` 依赖

## 非功能需求

### N1: 性能
- 首次分析（含文档解析+LLM）≤ 60 秒
- 后续分析（已解析文档）≤ 30 秒

### N2: 可靠性
- LLM 输出解析失败时返回降级结果（仅条款列表，无分类）
- API 超时默认 120 秒

### N3: 安全
- 遵循现有认证体系（`get_current_user`）
- 不记录招标原文到日志（商业机密保护）

## 边界条件

| 场景 | 处理方式 |
|------|---------|
| 招标文件为空 | 返回 400 + error message |
| LLM 返回格式错误 | 降级：返回原始提取条款 + warning |
| 招标文件 > 10000 tokens | 截断到前 8000 tokens + 尾部告警 |
| 招标文件无编号条款 | 降级：按段落提取，不做三层分类 |
| 并发请求 | 无特殊处理，每个请求独立调用 |

## 出界 (Out of Scope)

- 不对比投标文件（那是 review 管线的职责）
- 不生成 Word/PDF（MVP 仅 JSON + Markdown）
- 不存储分析结果到数据库
- 不修改前端 UI
- 不使用 stream 模式
