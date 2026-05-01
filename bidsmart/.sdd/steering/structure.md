# 标书智审 BidSmart — 架构

## 模块地图

```
┌──────────────────────────────────────────────────────────────────┐
│                    static/index.html                              │
│                   (SPA 前端, 2058行)                               │
├──────────────────────────────────────────────────────────────────┤
│                     FastAPI 路由层                                 │
│  /auth/*  │  /projects/*  │  /documents/*  │  /ai/*  │ /admin/* │
├───────────┼───────────────┼────────────────┼─────────┼──────────┤
│  auth     │  projects     │  documents     │compliance│  admin   │
│  service  │  service      │  service       │pipeline  │  router  │
│           │               │                │          │  export  │
├───────────┴───────────────┴────────────────┴─────────┼──────────┤
│                    知识库 (knowledge/)                │          │
│  embedder (BGE)  │  router (/admin/kb/*)  │  models  │          │
├──────────────────────────────────────────────────────┴──────────┤
│                    安全模块 (security/)                           │
│  encryption │ audit │ keys │ signing │ desensitize │ https       │
├──────────────────────────────────────────────────────────────────┤
│                    ORM 模型层 (SQLAlchemy)                        │
│  User │ Project │ Document │ ReviewSession │ AuditLog │         │
│  KBDocument │ KBChunk                                            │
├──────────────────────────────────────────────────────────────────┤
│             存储层 (StorageBackend 抽象)                           │
│  LocalFileStorage │ EncryptedStorageBackend (可选)                │
├──────────────────────────────────────────────────────────────────┤
│                     SQLite (bidsmart.db)                          │
└──────────────────────────────────────────────────────────────────┘
```

## 知识库管线 (BGE → FAISS)

```
文档上传 → python-docx/pymupdf 解析 → chunk_text (500字符/块, 50字符重叠)
    → BAAI/bge-small-zh-v1.5 嵌入 (sentence-transformers)
    → KBChunk 存储 (embedding_json 列)
    → 搜索: numpy dot-product 余弦相似度 → Top-K 结果
    → [P2] 计划迁移至 FAISS 索引以支持大规模检索
```

## 目录布局

```
src/
├── main.py             # App工厂: 中间件→路由→静态文件挂载
├── config.py           # pydantic-settings, 环境变量
├── dependencies.py     # get_current_user, require_role
├── db/                 # 数据库 (base, session, migrations)
├── models/             # ORM 模型 (User, Project, Document, ReviewSession, AuditLog)
├── platform/           # 业务逻辑
│   ├── auth/           # 认证服务 (register, login, refresh, me)
│   ├── projects/       # 项目管理 CRUD
│   ├── documents/      # 文档上传/下载/管理
│   ├── admin/          # 管理后台
│   │   ├── router.py       # 管理 API 端点
│   │   ├── user_router.py  # 用户管理
│   │   └── export.py       # 数据导出
│   └── middleware/     # 限流, 访问日志
├── compliance/         # AI审查管线
├── parsing/            # 文档解析 (docx, pdf)
├── knowledge/          # 智能知识库 (v0.7.1+)
│   ├── embedder.py     # 文本分块 + BGE 嵌入引擎
│   ├── models.py       # KBDocument, KBChunk ORM 模型
│   └── router.py       # 知识库 API (/admin/kb/*)
├── storage/            # 文件存储抽象 + 本地/加密实现
└── security/           # 企业级安全 (v0.7.0+)
    ├── encryption.py   # AES-256-GCM + KEK/DEK 密钥分层
    ├── audit.py        # 结构化审计日志, 异步批量写入
    ├── keys.py         # KEK/DEK 密钥管理
    ├── signing.py      # 数据签名验证
    ├── desensitize.py  # 日志/响应数据脱敏
    └── https.py        # HTTPS 强制中间件
```

## 跨模块关注点

- **认证**: `dependencies.get_current_user` 是所有 protected endpoint 的统一入口
- **RBAC**: 全局角色 (admin/reviewer/viewer) + 项目级成员 (ProjectMember, 模型已有但未接入服务 — P2)
- **审计**: AuditMiddleware 自动记录所有 HTTP 请求
- **限流**: RateLimiterMiddleware，按 IP 滑动窗口
- **脱敏**: 敏感字段 (手机号、邮箱、身份证) 在日志和低权限响应中自动脱敏

## 集成点

- **DeepSeek API**: `AsyncOpenAI` 客户端，通过 `config.deepseek_*` 配置
- **BGE 嵌入**: `sentence-transformers` 加载 `BAAI/bge-small-zh-v1.5`，首次运行自动下载
- **文件存储**: `LocalFileStorage`，路径 `{storage_root}/{project_id}/{uuid}.ext`
- **前端**: 单文件挂载在 `/`，API 调用同源
- **管理后台**: `/admin` 路由组，需 admin 角色

## 边界规则

- 路由层只做参数解析和依赖注入，业务逻辑在 service 层
- 所有 DB 操作通过 `get_db` 依赖注入 AsyncSession
- 文件上传不进入版本控制（storage/ 在 .gitignore）
- 测试文件放在 `tests/`，测试存储用 `test-storage/`
- 知识库文档存储在 `storage/knowledge/`
