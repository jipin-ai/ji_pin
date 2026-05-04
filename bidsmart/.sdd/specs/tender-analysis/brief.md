# Pre-bid Tender Analysis (标前招标分析)

## Motivation
实测发现招标文件 514 条条款中仅 53 条在投标书中有对应响应（覆盖率 10%）。根因不是匹配引擎问题，而是投标书编写人未系统性拆解招标要求，遗漏大量条款。

## Goal
新增标前分析功能：输入招标文件 → AI 自动提取并三层分类所有要求 → 输出结构化分析报告，辅助投标书编写。

## Three-Tier Classification
1. **废标项 (Disqualification)**: 缺失直接导致废标（资质、保证金、投标有效期、实质性响应条件）
2. **重要条款 (Important)**: 评分权重高或技术核心要求
3. **一般条款 (General)**: 格式、装订、基础信息类要求

## Scope
- 1 个新端点: `POST /ai/analyze-tender`
- 1 个 LLM prompt（全文一次性分析，非逐条）
- 输出 JSON + 可选 Word 报告
- 复用现有文档解析管线

## Non-Goals
- 不修改现有 review 管线
- 不新建数据库表（纯计算型端点）
- 不输出到前端（MVP阶段仅 API）

## Success Criteria
- 招标文件分析 ≤ 60 秒
- 废标项召回率 ≥ 90%（人工验证）
- 生成可打印的 Markdown 报告
