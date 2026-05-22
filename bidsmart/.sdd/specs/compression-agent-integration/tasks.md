# Compression Agent Integration — Tasks

## 1. 基础设施搭建
_Status: pending_
_Depends: none_

### 1.1 复制压缩引擎 (P)
_Status: pending_
_Boundary: src/compliance/compression_engine.py_
_Depends: none_

- [ ] 复制 `/root/compression_engine/compression_engine.py` 到 `src/compliance/compression_engine.py`
- [ ] 调整 import 路径适配 BidSmart 项目结构
- [ ] 验证 `python3 -c "from src.compliance.compression_engine import CompressionEngine"` 无错误

### 1.2 添加文档分块器 (P)
_Status: pending_
_Boundary: src/parsing/chunker.py_
_Depends: none_

- [ ] 实现 `chunk_document(parsed: ParsedDocument, chunk_size=2000, overlap=50) -> list[dict]`
- [ ] 按 heading 边界切分，不打断段落
- [ ] 调用 BGE-M3 embedder 生成嵌入向量
- [ ] 返回 `[{content, heading, section_id, page_number, chunk_index, embedding}]`

### 1.3 法规模板 SKILL.md 化 (P)
_Status: pending_
_Boundary: src/skills/_
_Depends: none_

- [ ] 读取 `storage/knowledge/*.md` 4份文件
- [ ] 转换为 SKILL.md 格式（frontmatter: name, description, category: "regulation"）
- [ ] 保存到 `src/skills/<法规名>/SKILL.md`
- [ ] 提供 `skills/list` 功能

## 2. Agent 核心
_Status: pending_
_Depends: 1.1, 1.2, 1.3_

### 2.1 Agent 工具实现
_Status: pending_
_Boundary: src/compliance/agent_tools.py_
_Depends: 1.1, 1.3_

- [ ] ToolBase 抽象基类（name, description, parameters, execute）
- [ ] LoadSkillTool — 从 `src/skills/` 加载 SKILL.md
- [ ] ReadChunkTool — 从 KBChunk 表读取指定分块
- [ ] SearchKBTool — BGE-M3 语义检索知识库
- [ ] 每个工具验证 JSON Schema 格式的输出

### 2.2 AgentLoop 实现
_Status: pending_
_Boundary: src/compliance/agent_loop.py_
_Depends: 1.1, 2.1_

- [ ] AgentReviewLoop 类：初始化（settings, project_id, chunks, engine）
- [ ] `run(user_message)` — ReAct 循环，max 30 iterations
- [ ] 每轮调用 `compression.manage(messages)` → Layer 1 自动执行
- [ ] LLM stream_chat + 工具执行
- [ ] Layer 3 阈值触发自动压缩
- [ ] `continue_session(user_message)` — 保持上下文
- [ ] 返回 `{content, tool_calls, iterations, session_id, compression_stats}`

### 2.3 Agent 路由
_Status: pending_
_Boundary: src/compliance/agent_router.py_
_Depends: 2.2_

- [ ] `POST /ai/review-agent` — 新建 Agent 审核会话
- [ ] `POST /ai/review-agent/continue` — 继续会话
- [ ] Request schema: `{project_id, message, session_id?}`
- [ ] Response schema: `{content, tool_calls, iterations, session_id, compression_stats}`
- [ ] 会话管理：in-memory dict，key = session_id

## 3. 集成
_Status: pending_
_Depends: 2.3_

### 3.1 配置 + 主应用
_Status: pending_
_Boundary: src/config.py, src/main.py_
_Depends: 2.3_

- [ ] `src/config.py` 添加压缩参数（COMPRESSION_TOKEN_THRESHOLD 等 7 项）
- [ ] `src/main.py` 注册 agent_router
- [ ] 版本号: 0.7.8 → 0.8.0（架构级变更）
- [ ] `pyproject.toml` 同步版本号

### 3.2 兼容性验证
_Status: pending_
_Boundary: 全项目_
_Depends: 3.1_

- [ ] 现有 API 端点行为无变化（curl 测试 /ai/review-file, /health, /auth/login）
- [ ] 服务启动无 import 错误
- [ ] 前端 index.html 无 JS 语法错误

## 4. 测试
_Status: pending_
_Depends: 3.2_

### 4.1 Layer 1 测试
_Status: pending_
_Boundary: 无（集成测试）_
_Depends: 3.1_

- [ ] 用模拟标书（50轮对话）测试 L1 效果
- [ ] 验证 token 削减率 ≥ 50%
- [ ] 验证压缩后消息格式有效
- [ ] 验证工具结果保留最近 KEEP_RECENT 条

### 4.2 Layer 3 测试
_Status: pending_
_Boundary: 无（集成测试）_
_Depends: 4.1_

- [ ] 用模拟标书（50轮）触压后验证 DeepSeek 摘要生成
- [ ] 验证 10 章节结构完整
- [ ] 验证转录文件保存
- [ ] 验证压缩后 Agent 可继续正常工作

### 4.3 SKILL.md 加载测试
_Status: pending_
_Boundary: src/skills/_
_Depends: 4.1_

- [ ] `load_skill("政府采购法实施条例")` 返回正确内容
- [ ] 不存在的技能名返回 "Skill not found"
- [ ] 技能列表可用
