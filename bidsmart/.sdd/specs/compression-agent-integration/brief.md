# Compression Agent Integration — Brief

**Feature**: 压缩引擎集成到 BidSmart + 大文件分块 + 法规模板化  
**Created**: 2026-05-02  
**SDD Path**: Path C — New single-scope feature  
**Status**: discovery-done → ready for spec-init

## Problem

BidSmart v0.7.8 无法处理 100MB+ 标书文档。核心问题：
1. **全量内存加载** — PDF/DOCX 解析器一次性读入全部内容
2. **上下文截断** — 每条 AI 审查只取前 3000-4000 字符
3. **无 Agent 模式** — pipeline 是单向流水线，无法多轮追问/修正
4. **无法规知识库集成** — 4份法规文档存在 DB 但审查时未被引用
5. **无上下文管理** — 多轮对话无压缩机制

## Goals

1. **压缩引擎集成**: 将已验证的五层压缩引擎集成到 BidSmart 的 Agent 审核模式
2. **大文件分块**: 100MB+ 文档自动分块，按需检索相关片段
3. **Agent 审核模式**: 新建支持工具调用的多轮 Agent 审核模式（保留旧 pipeline 兼容）
4. **法规模板**: 4份法规知识库文档迁移为 SKILL.md 格式
5. **参数配置**: 针对 100MB+ 场景调优压缩参数

## Approach: B — Standard Integration

- **新增 Agent 审核模式** (`/ai/review-agent`) — LLM 拥有工具访问权限（load_skill, read_chunk, search_kb），五层压缩管理上下文
- **保留旧 Pipeline 兼容** — `/ai/review-file` 和 `/ai/review-file/stream` 不变
- **文档分块存储** — 上传时自动分块（每块 ~2000 tokens），存入 KBChunk 表，支持语义检索
- **知识库 SKILL.md 化** — 4份法规模板转为 `src/skills/` 下的 SKILL.md 格式
- **渐进启用**: L1 默认开启（零成本），L3 在 Agent 模式中按阈值触发

## Non-Goals

- 不替换现有 pipeline 架构
- 不修改前端 UI（仅后端）
- 不改数据库 schema（复用 KBChunk 表）
- L4（模型主动压缩）本次不实现

## Depends On

- `/root/compression_engine/compression_engine.py` — 已验证的五层压缩引擎
- BidSmart v0.7.8 现有 pipeline 和知识库基础设施
- DeepSeek API — 已配置，延迟 ~10-20s

## Related Specs

- 无（新功能）
