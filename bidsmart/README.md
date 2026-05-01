<p align="center">
  <img src="https://img.shields.io/badge/version-0.7.8-c96442" alt="version">
  <img src="https://img.shields.io/badge/python-3.11+-blue" alt="python">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="license">
  <img src="https://img.shields.io/badge/status-active-success" alt="status">
</p>

<h1 align="center">🏛️ 标书智审 BidSmart</h1>
<p align="center"><strong>AI-Powered Bid Document Compliance Review System</strong></p>
<p align="center">中文 · <a href="#english">English ↓</a></p>

---

> 上传招标文件 + 投标文件 → AI 自动逐条比对 → 逐项合规判定 + 整改建议 + 合规评分

---

## ✨ 功能

| 模块 | 说明 |
|------|------|
| 📊 **智能合规审查** | DeepSeek AI 逐条比对招标/投标文件，输出合规评分 + 逐项判定 |
| 📁 **项目管理** | 以项目为单位组织文件，支持部门/编辑人/投标时间等元信息 |
| 📚 **知识库 (RAG)** | BGE 向量化 + FAISS 本地检索，AI 对话自动引用法规/制度/历史经验 |
| ⚙️ **管理后台** | 用户 CRUD、角色管理 (admin/reviewer/viewer)、数据导出/导入 |
| 🔐 **企业级安全** | AES-256-GCM 加密存储、JWT 认证、RBAC 权限控制、审计日志 |
| 🎨 **暖色 UI** | Anthropic 风格羊皮纸主题，中文企业用户友好 |

## 🚀 快速开始

```bash
# 1. 克隆
git clone https://github.com/jipin-ai/bidsmart.git
cd bidsmart

# 2. 安装依赖 (Python 3.11+)
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 4. 初始化数据库
alembic upgrade head
python3 scripts/seed_users.py

# 5. 启动
uvicorn src.main:create_app --host 0.0.0.0 --port 39001 --factory

# 6. 访问
open http://localhost:39001
```

**测试账号：** `admin` / `admin123`

## 🏗️ 技术栈

| 层 | 技术 |
|----|------|
| 框架 | FastAPI (async) |
| 数据库 | SQLite + SQLAlchemy 2.0 (async) + Alembic |
| AI | DeepSeek API (deepseek-chat) |
| 向量化 | BAAI/bge-small-zh-v1.5 + FAISS |
| 前端 | 纯 HTML/CSS/JS 单文件 SPA (2058 行) |
| 安全 | JWT (HS256) + bcrypt + AES-256-GCM |
| 部署 | Uvicorn + systemd (阿里云 ECS) |

## 📁 项目结构

```
bidsmart/
├── src/
│   ├── main.py              # FastAPI 应用工厂
│   ├── config.py             # 配置管理 (pydantic-settings)
│   ├── compliance/           # AI 审查管线 (pipeline + SSE 流式)
│   ├── knowledge/            # 知识库 (BGE + FAISS + RAG)
│   ├── platform/             # 业务模块 (auth/projects/documents/admin)
│   ├── models/               # ORM 模型 (6 张表)
│   ├── parsing/              # 文档解析 (.docx/.pdf)
│   ├── storage/              # 文件存储抽象层
│   ├── security/             # 加密/审计/脱敏/密钥管理
│   └── db/                   # 数据库会话 + 迁移
├── static/index.html         # 前端 SPA
├── tests/                    # 测试套件 (1674 行)
├── scripts/                  # 运维脚本
└── .sdd/                     # SDD 设计文档 (21 份)
```

## 📖 文档

- [产品愿景](.sdd/steering/product.md)
- [技术栈](.sdd/steering/tech.md)
- [架构设计](.sdd/steering/structure.md)
- [路线图](.sdd/steering/roadmap.md)
- [变更日志](.sdd/CHANGELOG.md)
- [部署手册](.sdd/deployment-runbook.md)
- [测试策略](.sdd/testing-strategy.md)
- [贡献指南](CONTRIBUTING.md)

## 🤝 贡献

欢迎 Issue 和 PR！详见 [CONTRIBUTING.md](CONTRIBUTING.md)

## 📄 许可证

MIT License © 2026 [集品 AI (jipin-ai)](https://github.com/jipin-ai)

---

<h1 id="english">🏛️ BidSmart</h1>

> Upload tender + bid documents → AI line-by-line compliance review → verdicts + fix suggestions + score

## ✨ Features

| Module | Description |
|--------|-------------|
| 📊 **AI Compliance Review** | DeepSeek-powered line-by-line comparison of tender vs bid documents with compliance scoring |
| 📁 **Project Management** | Organize documents by project with metadata (department, editor, bid deadline) |
| 📚 **Knowledge Base (RAG)** | BGE embedding + FAISS local vector search; AI chat auto-injects relevant regulations |
| ⚙️ **Admin Panel** | User CRUD, role management (admin/reviewer/viewer), data export/import |
| 🔐 **Enterprise Security** | AES-256-GCM encrypted storage, JWT auth, RBAC, audit logging |
| 🎨 **Warm UI** | Anthropic-inspired parchment theme, optimized for Chinese enterprise users |

## 🚀 Quick Start

```bash
git clone https://github.com/jipin-ai/bidsmart.git
cd bidsmart
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Edit and add your DEEPSEEK_API_KEY
alembic upgrade head
python3 scripts/seed_users.py
uvicorn src.main:create_app --host 0.0.0.0 --port 39001 --factory
# Open http://localhost:39001
```

**Test account:** `admin` / `admin123`

## 🏗️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI (async) |
| Database | SQLite + SQLAlchemy 2.0 (async) + Alembic |
| AI Engine | DeepSeek API (deepseek-chat) |
| Embeddings | BAAI/bge-small-zh-v1.5 + FAISS |
| Frontend | Vanilla HTML/CSS/JS SPA (2058 lines) |
| Security | JWT (HS256) + bcrypt + AES-256-GCM |
| Deployment | Uvicorn + systemd (Alibaba Cloud ECS) |

---

<p align="center">
  <sub>Built with ❤️ by <a href="https://github.com/jipin-ai">集品 AI (jipin-ai)</a> · 标书合规，智能把关</sub>
</p>
