# 标书智审 BidSmart — 术语表

## 业务领域术语

| 术语 | 英文/缩写 | 定义 |
|------|-----------|------|
| **招标文件** | Tender Document / Bidding Document | 招标方发布的采购需求文件，包含技术规格、商务条款、评分标准等。在 BidSmart 中作为审查基准 ("标尺")。 |
| **投标文件** | Bid Document / Proposal | 投标方编制的响应文件，需逐条响应招标要求。在 BidSmart 中作为被审查对象。 |
| **合规审查** | Compliance Review | AI 驱动的自动化审查流程：提取招标条款 → 逐条比对投标响应 → 判定合规/不合规/部分合规 → 生成整改建议。 |
| **对照表** | Compliance Table / Mapping Table | 审查输出的核心数据结构：{招标条款, 投标响应, 合规判定, 置信度, 建议} 的逐条映射表。 |
| **审查会话** | ReviewSession | 一次合规审查的完整记录，包含上传文件、AI 审查结果、人工复核标注、最终评分。 |
| **项目** | Project | 围绕一个投标机会组织的顶层容器，包含招标文件、投标文件、审查会话、项目成员。 |
| **条款提取** | Clause Extraction | 从 PDF/DOCX 招标文件中自动识别和提取结构化条款（第X条、技术要求、评分项等）。 |
| **整改建议** | Remediation Suggestion | AI 针对不合规条款生成的修改建议，帮助投标团队快速修正投标文件。 |

## 安全术语

| 术语 | 英文/缩写 | 定义 |
|------|-----------|------|
| **KEK** | Key Encryption Key | 密钥加密密钥 — 用于加密/解密 DEK 的主密钥，不直接加密业务数据。离线安全存储，定期轮换。 |
| **DEK** | Data Encryption Key | 数据加密密钥 — 每个文件独立的加密密钥，用于 AES-256-GCM 加密。DEK 本身用 KEK 加密后存储。 |
| **KEK/DEK 分层** | Envelope Encryption | 双层密钥管理架构：KEK 加密 DEK，DEK 加密数据。实现密钥轮换时无需重新加密所有文件。 |
| **RBAC** | Role-Based Access Control | 基于角色的访问控制。BidSmart 全局三级角色：admin (管理员)、reviewer (审核员)、viewer (查看者)。P2 扩展项目级 RBAC。 |
| **脱敏** | Desensitization | 自动识别并遮蔽敏感信息（手机号、邮箱、身份证号），在审计日志和低权限 API 响应中执行。 |
| **审计日志** | Audit Log | 结构化 JSON 格式的操作记录，包含操作人、时间、动作、资源、结果。异步批量写入，不可篡改。 |

## AI/技术术语

| 术语 | 英文/缩写 | 定义 |
|------|-----------|------|
| **BGE** | BAAI General Embedding | 智源研究院 (BAAI) 发布的中文嵌入模型系列。BidSmart 使用 `bge-small-zh-v1.5`，384 维向量，擅长中文语义理解。 |
| **FAISS** | Facebook AI Similarity Search | Meta 开源的高性能向量相似度搜索库。BidSmart 当前使用 numpy dot-product，P2 计划迁移 FAISS 以支持大规模 (10万+) 向量检索。 |
| **SSE** | Server-Sent Events | 服务器推送事件 — 单向实时通信协议。BidSmart 用于 AI 审查进度推送（流式输出审查结果）。 |
| **分块** | Chunking | 文本预处理步骤：将长文档切分为固定大小 (500字符) 的文本块，50字符重叠，保留章节标题上下文。用于知识库嵌入。 |
| **向量化** | Embedding / Vectorization | 将文本块转换为固定维度 (384) 的浮点数向量。BGE 模型生成归一化向量，余弦相似度 = 向量点积。 |
| **余弦相似度** | Cosine Similarity | 衡量两个向量方向相似度的指标，范围 [-1, 1]。BidSmart 用于知识库语义检索排序，阈值 > 0.3。 |
| **DeepSeek** | DeepSeek API | 深度求索公司的大语言模型 API，BidSmart 的核心 AI 引擎，通过 OpenAI 兼容接口调用 `deepseek-chat` 模型。 |
| **FastAPI** | FastAPI | Python 现代异步 Web 框架，BidSmart 的基础框架，支持自动 OpenAPI 文档生成。 |

## 系统术语

| 术语 | 英文/缩写 | 定义 |
|------|-----------|------|
| **SPA** | Single Page Application | 单页应用 — BidSmart 前端为单个 `index.html` 文件 (2058行)，通过 Fetch API 与后端通信，无页面刷新。 |
| **ECS** | Elastic Compute Service | 阿里云弹性计算服务 — BidSmart 当前部署在单台 ECS 实例上，Alibaba Cloud Linux 系统。 |
| **systemd** | System Daemon | Linux 系统和服务管理器。BidSmart 通过 `bidsmart.service` unit 管理进程生命周期，Restart=always。 |
| **ORM** | Object-Relational Mapping | 对象关系映射 — SQLAlchemy 2.0 async 模式，Python 对象与 SQLite 表之间自动映射。 |
| **Alembic** | Alembic | SQLAlchemy 官方数据库迁移工具，管理 BidSmart 数据库 schema 版本演进。 |

---

最后更新: 2026-05-01 | 版本: v0.7.7
