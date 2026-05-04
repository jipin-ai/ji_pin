# Compression Agent Integration — Requirements

## FR-1: 压缩引擎集成

### FR-1.1 Layer 1 微压缩（Ubiquitous）
系统应在 Agent 审核模式的每轮迭代中自动执行 Layer 1 微压缩，将超过100字符的旧工具结果替换为 `[cleared]`，保留最近3条工具结果不变。

**Acceptance Criteria**:
- Agent 循环每轮开始时，超过3条工具结果的消息列表自动清理
- Layer 1 执行耗时 <1ms
- 清理后消息列表格式有效，角色交替正确

### FR-1.2 Layer 2 上下文折叠（Event-driven）
当消息列表 token 估算值超过 COLLAPSE_THRESHOLD（70% × TOKEN_THRESHOLD）时，系统应对超出保留范围的长文本消息（>2400字符）执行首尾折叠，保留头部900字符和尾部500字符。

**Acceptance Criteria**:
- Token 估算 >COLLAPSE_THRESHOLD 时自动触发
- 折叠后消息首尾原始内容完整保留
- 零 API 调用，纯字符串操作

### FR-1.3 Layer 3 LLM 结构化摘要（Event-driven）
当消息列表 token 估算值超过 TOKEN_THRESHOLD 时，系统应调用 DeepSeek API 生成10章节结构化摘要（Goal/Constraints/Progress/Decisions/Resolved/Pending/Files/Remaining/Critical/Tools），并以 Token 预算方式保护尾部 ~20K tokens 的最近消息。

**Acceptance Criteria**:
- Token 超阈值时自动触发
- 摘要包含全部10个章节
- 尾部保护保留完整 tool_call/tool_result 对
- 压缩前完整转录保存为 JSONL 文件
- DeepSeek 调用超时 60s，失败不阻塞主流程

### FR-1.4 Layer 5 迭代更新（Event-driven）
当第二次及以上触发 Layer 3 时，系统应传入前次摘要 + 新增轮次，由 DeepSeek 合并更新摘要，保持相同章节结构，不丢失前次摘要中的信息。

**Acceptance Criteria**:
- 第二次触发时使用迭代更新 prompt（非首次 prompt）
- 前次摘要的所有信息保留在更新后摘要中
- Done 和 Resolved 状态正确转移

## FR-2: Agent 审核模式

### FR-2.1 Agent 模式端点（Event-driven）
系统应提供 `POST /ai/review-agent` 端点，接收 `project_id`、`user_message`，返回多轮 Agent 审核结果。Agent 应能调用工具（load_skill, read_chunk, search_kb）进行多轮推理。

**Acceptance Criteria**:
- 端点返回包含 `content`、`tool_calls`、`iterations` 的 JSON
- Agent 循环最大迭代次数 = 30
- 支持 `POST /ai/review-agent/continue` 继续会话

### FR-2.2 工具：load_skill（Event-driven）
Agent 调用 `load_skill(skill_name)` 时，系统应从 `src/skills/` 加载对应 SKILL.md 并返回完整文档内容。

**Acceptance Criteria**:
- 支持查找内置技能（src/skills/）和用户技能（~/.bidsmart/skills/）
- 返回格式：`<skill name="...">content</skill>`
- 不存在的技能名返回错误提示

### FR-2.3 工具：read_chunk（Event-driven）
Agent 调用 `read_chunk(doc_id, chunk_index)` 时，系统应从 KBChunk 表检索指定分块内容。

**Acceptance Criteria**:
- 返回 chunk 的 content + heading
- 无效 chunk_index 返回边界提示

### FR-2.4 工具：search_kb（Event-driven）
Agent 调用 `search_kb(query, top_k=5)` 时，系统应使用 BGE-M3 嵌入进行语义检索并返回最相关分块。

**Acceptance Criteria**:
- 返回 top_k 条结果，每条含 content + heading + score
- 相似度阈值 >= 0.3

### FR-2.5 旧 Pipeline 兼容（Ubiquitous）
系统应保留现有 `/ai/review-file` 和 `/ai/review-file/stream` 端点不变，Agent 模式作为额外选项。

**Acceptance Criteria**:
- 现有端点行为无变化
- 现有前端功能不受影响

## FR-3: 大文件分块（100MB+）

### FR-3.1 上传时自动分块（Event-driven）
文件上传时，系统应在解析后自动将文档分块存储到 KBChunk 表，每块 ~2000 tokens，重叠 50 tokens。

**Acceptance Criteria**:
- 100MB 文档约生成 500-800 个分块
- 分块按 heading 边界切分，不打断段落
- 分块元数据包含 section_id、page_number、chunk_index
- 分块使用 BGE-M3 生成嵌入向量

### FR-3.2 分块按需读取（Event-driven）
Agent 工具 `read_chunk` 和 `search_kb` 应从分块存储中按需读取，不一次性加载全文。

**Acceptance Criteria**:
- 单次 read_chunk 内存占用 <100KB
- search_kb 使用 FAISS 或 numpy 向量化检索，不遍历全文

### FR-3.3 文档预览优化（State-driven）
文档预览端点 `GET /ai/preview/{id}` 应支持分页参数 `?page=1&chunk_size=5`，流式返回分块内容。

**Acceptance Criteria**:
- 100MB 文档预览响应时间 <2s
- 支持 Next-Page token 翻页

## FR-4: 法规模板 SKILL.md 化

### FR-4.1 模板迁移（Event-driven）
系统应将 `storage/knowledge/` 下的4份法规文档转换为 `src/skills/` 下的 SKILL.md 格式，包含 frontmatter（name/description/category）。

**Acceptance Criteria**:
- 4份文档各生成一个 SKILL.md
- Frontmatter 字段完整：name, description, category: "regulation"
- 正文保留原始结构（章节层次）

### FR-4.2 技能加载（Event-driven）
Agent 工具 `load_skill` 应能发现并加载法规 SKILL.md。

**Acceptance Criteria**:
- `load_skill("政府采购法实施条例")` 返回对应文档
- 技能列表可通过 `/skills` 查看

## 约束

- **内存**: 单次操作内存占用不超过 500MB（1.8G ECS 约束）
- **延迟**: Agent 模式单次回复延迟不超过 60s
- **API 成本**: Layer 3 每次压缩调用的 max_tokens ≤ 2000
- **兼容性**: 不修改现有数据库 schema，不破坏现有 API 契约
- **前端**: 本次不改前端，后续迭代再加

## 参数配置（100MB+ 场景）

| 参数 | 默认值 | 100MB+ 推荐值 | 说明 |
|------|--------|--------------|------|
| TOKEN_THRESHOLD | 20000 | 40000 | 大文件语境下阈值提高 |
| TAIL_TOKEN_BUDGET | 20000 | 30000 | 保留更多尾部上下文 |
| COLLAPSE_THRESHOLD | 70% | 70% | 不变 |
| KEEP_RECENT | 3 | 5 | 大文件工具调用多，稍增加 |
| COLLAPSE_TEXT_MIN | 2400 | 5000 | 只折叠真正大的文本块 |
| COLLAPSE_HEAD | 900 | 1500 | 保留更多头部 |
| COLLAPSE_TAIL | 500 | 1000 | 保留更多尾部 |
| max_iterations | 50 | 30 | Agent 循环上限 |
| 分块大小 | — | 2000 tokens | 平衡检索精度和上下文 |

## 边界情况
- 空文档上传 → 返回 400 "Document is empty"
- 文档只有1页 → 不触发分块
- Agent 循环达到 max_iterations → 返回已有结果 + "Reached iteration limit"
- DeepSeek API 超时 → 跳过 L3 压缩，继续 L1+L2
- 法规 SKILL.md 不存在 → load_skill 返回 "Skill not found"
- 并发 Agent 请求 → 每个请求独立 session，不共享上下文

## 范围外
- 不实现 Layer 4（模型主动调用 compact 工具）
- 不修改前端 UI
- 不升级数据库（不迁移到 PostgreSQL）
- 不实现向量索引（FAISS/HNSW）— 后续迭代
- 不支持实时协同
