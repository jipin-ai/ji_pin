# Technology Stack

## 语言与框架

- **Backend**: Python 3.11+, FastAPI (uvicorn 服务)
- **Frontend**: 纯 HTML/CSS/JS 单文件 (`static/index.html`)
- **数据库**: SQLite (单文件 `bidsmart.db`，P0)
- **ORM**: SQLAlchemy 2.0 (async)

## AI/ML

- **LLM**: DeepSeek API (`deepseek-chat` model)
- **Embedding**: BAAI/bge-small-zh-v1.5 (512维, sentence-transformers)
- **压缩引擎**: 五层渐进式压缩 (L1-L5), token 阈值 40000

## 基础设施

- **服务器**: 阿里云 ECS 新加坡 (8.219.137.176, 4G RAM)
- **部署**: `uvicorn` 直启（不限并发，单 worker）
- **uvicorn 路径**: `/opt/hermes/.venv/bin/uvicorn`
- **消息平台**: Feishu/Lark WebSocket

## 约束

- 4G RAM 限制 — 大模型（如 BGE-M3 2GB+）需评估内存
- 新加坡 ECS 无 GFW，但 DeepSeek API 需直连
- 前端单文件 — 所有前端代码在 `static/index.html`，修改后需验证 JS 语法
- 标书=商业机密 — 不存储原始文档到外部服务，本地解析

## 约定

- 版本号: `src/main.py` + `pyproject.toml` 双写同步
- 所有改动走 SDD 工作流（discovery→steering→spec→impl）
- 布局/架构级变更 → 大版本号 (x.0)，小改/bug → 小版本号 (0.x)
- 前端 JS 陷阱: 修改后必须 `grep -n 'async async\|function function\|await await' static/index.html`
