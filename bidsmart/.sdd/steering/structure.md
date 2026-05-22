# Architecture

## 模块地图

```
src/
├── main.py              # FastAPI app 工厂, 路由注册, 版本号
├── config.py            # pydantic-settings (DeepSeek/DB/存储/压缩)
├── db/                  # 数据库 session + 模型
├── models/              # SQLAlchemy 模型 (User/Document/Project)
├── compliance/
│   ├── pipeline.py      # 🔴 核心: 4-stage 审查管线 (extract→match→review→aggregate)
│   ├── ai_reviewer.py   # 旧版: 单次 LLM 审查 (向后兼容)
│   ├── agent_loop.py    # Agent ReAct 循环 (工具调用+压缩)
│   ├── agent_router.py  # Agent 模式路由
│   ├── agent_tools.py   # Agent 工具 (load_skill/read_chunk/search_kb)
│   ├── compression_engine.py  # 五层压缩引擎
│   └── router.py        # /ai/* 路由 (review/review-file/review-agent)
├── parsing/
│   ├── chunker.py       # 文档分块器 (100MB→6K chunks)
│   ├── pdf_parser.py    # PDF 解析
│   ├── docx_parser.py   # DOCX 解析
│   └── models.py        # ParsedDocument/Section 数据模型
├── knowledge/
│   ├── embedder.py      # BGE Embedder (bge-small-zh-v1.5, 512维)
│   └── router.py        # /kb/* 路由 (知识库管理)
├── skills/              # 法规 SKILL.md (招投标法/政府采购法 ×4)
└── static/
    └── index.html       # 单文件前端 SPA
```

## 目录布局

```
/root/bidsmart/
├── src/                 # 源码
├── static/              # 前端
├── storage/             # 上传文件 + 知识库文档
├── .sdd/                # SDD 工作流
├── bidsmart.db          # SQLite 数据库
├── pyproject.toml       # 依赖 + 版本
└── .env                 # DeepSeek API key
```

## 数据流（审查管线）

```
POST /ai/review-file/stream
  → 加载文档 (DB → parse_document)
  → Stage 1: extract_requirements (招标文件 → 条款列表)
  → Stage 2: match_sections (条款 → 投标段落匹配) 🔴 当前瓶颈
  → Stage 3: review_item (逐条 LLM 审查，batch=3)
  → Stage 4: aggregate (汇总报告)
  → SSE push 到前端逐条渲染
```

## 集成点

- `src/compliance/pipeline.match_sections()` — 待改造的核心集成点
- `src/knowledge/embedder.Embedder` — 已可用，未接入 pipeline
- 前端 `buildCompareTable()` → SSE `appendCompareRow()` → `finalizeCompareTable()`
