# 标书智审 BidSmart — 技术栈

## 语言和框架
- **语言**: Python 3.11+
- **Web框架**: FastAPI 0.115+ (async)
- **ASGI服务器**: Uvicorn 0.34+
- **ORM**: SQLAlchemy 2.0+ (async, aiosqlite)
- **数据库**: SQLite (开发阶段，P2 迁移到 PostgreSQL)
- **迁移**: Alembic 1.14+

## AI/ML
- **核心引擎**: DeepSeek API (`deepseek-chat` 模型)
- **SDK**: `openai` Python SDK (AsyncOpenAI, 兼容 DeepSeek API)
- **文档解析**: python-docx (.docx), pymupdf/fitz (.pdf)
- **知识库嵌入**: sentence-transformers (BAAI/bge-small-zh-v1.5), numpy
- **向量检索**: numpy dot-product 余弦相似度 (计划迁移 FAISS)

## 安全
- **认证**: JWT (HS256), python-jose 3.3+
- **密码哈希**: bcrypt 4.2+, passlib 1.7+
- **加密**: AES-256-GCM (cryptography), KEK/DEK 分层密钥管理
- **审计**: 结构化JSON审计日志，异步批量写入
- **数据脱敏**: 日志/响应自动脱敏 (desensitize)
- **传输安全**: HTTPS 强制 (https 中间件)

## 前端
- **技术**: 纯 HTML/CSS/JS（单文件 SPA, 2058 行）
- **UI风格**: Anthropic 暖色羊皮纸风格 (#f5f4ed 主背景 + #c96442 accent)
- **通信**: Fetch API + Bearer Token

## 部署
- **服务器**: 阿里云 ECS (Alibaba Cloud Linux)
- **进程管理**: systemd (`bidsmart.service`), Restart=always
- **端口**: 39001（安全组放行范围 39000-40000）
- **启动命令**: `uvicorn src.main:create_app --host 0.0.0.0 --port 39001 --factory`
- **存储**: 本地文件系统 (`./storage/{project_id}/`)
- **Python 环境**: `/opt/hermes/.venv`

## 依赖补充 (requirements.txt 未显式列出但生产依赖)
| 包名 | 用途 |
|------|------|
| `sentence-transformers` | BGE 模型加载与嵌入生成 |
| `aiosqlite` | SQLAlchemy 异步 SQLite 驱动 |
| `passlib` | 密码哈希抽象层 (bcrypt 后端) |
| `numpy` | 嵌入向量计算与相似度搜索 |
| `BAAI/bge-small-zh-v1.5` | 中文嵌入模型 (HuggingFace, 首次运行时自动下载) |

## 约束
- 国产化优先：DeepSeek 替代 OpenAI，BGE 替代 OpenAI Embeddings，本地存储替代云存储
- 不支持 WebSocket，优先 SSE/轮询 (P2 计划引入 WebSocket)
- 单进程部署，无容器化（当前阶段）
- 配置文件通过 `.env` 管理，不硬编码密钥

## 约定
- 所有 API 返回 JSON，文件下载除外
- 认证统一走 Bearer Token（Authorization header）
- 数据库操作全部异步（async SQLAlchemy + aiosqlite）
- 文件上传不分块（当前），通过配置 `max_upload_size_mb` 控制
- 测试: pytest + httpx，测试存储目录独立于生产
