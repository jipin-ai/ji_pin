# Spec: 知识库模块（精准轻量 RAG）

> **版本:** 0.7.0 (proposed)
> **状态:** draft — 待审阅
> **参照:** AnythingLLM 简化版 — 文档工作空间模式

---

## 一、目标

标书审查人员在 AI 对话框追问不合规条款时，AI 能**检索知识库中的法律法规、公司制度、历史经验**，给出有依据的专业回答，而非仅基于标书文本本身。

**核心指标：精准定位、精准回复。**

---

## 二、不做的事

| 不做 | 原因 |
|------|------|
| 多轮对话记忆 | 场景固定，不需上下文接力 |
| 复杂工作流编排 | 太重，背离精准原则 |
| 用户权限细分 | 管理员统一管理知识库 |
| 向量数据库（Chroma/Milvus） | SQLite 足够，减少依赖 |
| 全站搜索引擎 | 只在 AI 追问时触发检索 |

---

## 三、技术选型

| 层 | 选择 | 理由 |
|----|------|------|
| 向量模型 | `BAAI/bge-small-zh-v1.5` | 中文 SOTA 小模型，100MB，CPU 友好 |
| 分块策略 | 500 字/块 + 50 字重叠 | 标书条款粒度，重叠防截断 |
| 向量存储 | SQLite TEXT 列（JSON 序列化） | 零依赖，数据量小时性能足够 |
| 相似度 | 余弦相似度（numpy 点积） | 简单、可解释 |
| 检索 Top-K | 5，阈值 0.3 | 太少缺上下文，太多稀释精度 |
| 前端框架 | 纯 HTML/CSS/JS | 与现有 SPA 一致 |

---

## 四、数据流

```
┌──────────────────────────────────────────────────────────┐
│  录入阶段                                                  │
│                                                          │
│  上传文件 ──→ 文本解析(docx/pdf/txt/md) ──→ 分块(500字)   │
│                                                  │       │
│                                          BGE 向量化       │
│                                                  │       │
│                              kb_documents ←── kb_chunks   │
│                              (元信息)        (文本+向量)   │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  查询阶段（AI 追问时触发）                                  │
│                                                          │
│  用户追问 ──→ BGE 向量化 ──→ 余弦相似度 Top-5              │
│                                      │                   │
│                              拼入 system prompt           │
│                                      │                   │
│                              DeepSeek 生成回答             │
└──────────────────────────────────────────────────────────┘
```

---

## 五、数据库表

### kb_documents
| 列 | 类型 | 说明 |
|----|------|------|
| id | INTEGER PK | |
| title | VARCHAR(255) | 文档标题 |
| source_type | VARCHAR(50) | manual / law / regulation / experience |
| source_path | VARCHAR(500) | 原始文件存储路径 |
| chunk_count | INTEGER | 分块数量 |
| created_at | DATETIME | |

### kb_chunks
| 列 | 类型 | 说明 |
|----|------|------|
| id | INTEGER PK | |
| document_id | FK → kb_documents | 级联删除 |
| chunk_index | INTEGER | 文档内序号 |
| content | TEXT | 原始文本 |
| heading | VARCHAR(255) | 所属章节标题 |
| embedding_json | TEXT | JSON 序列化的 512 维向量 |

---

## 六、API 端点

全部挂载在 `/admin/kb`，需要 admin 权限。

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/admin/kb/upload` | 上传文档（multipart: file + title + source_type） |
| GET | `/admin/kb/documents` | 文档列表 |
| DELETE | `/admin/kb/documents/{id}` | 删除文档（级联删 chunks + 文件） |
| POST | `/admin/kb/search` | 检索测试（query → top-5 chunks + scores） |

---

## 七、AI 对话改造

修改 `POST /ai/chat`：

```
现有流程：用户消息 → DeepSeek 直接回答

改造后：  用户消息
              │
              ├──→ 知识库检索（query → Top-5 chunks）
              │
              └──→ system prompt 追加：
                   「以下是知识库中的相关内容，请基于这些内容回答：
                     [CHUNK 1] (来源: xxx法 第X条)
                     [CHUNK 2] ...
                     如果知识库内容不足以回答，请明确告知。」
              │
              └──→ DeepSeek 生成回答
```

---

## 八、文件清单

### 新增文件
| 文件 | 说明 |
|------|------|
| `src/knowledge/__init__.py` | 模块入口 |
| `src/knowledge/models.py` | KBDocument + KBChunk 模型 |
| `src/knowledge/embedder.py` | 分块器 + BGE 向量化（单例） |
| `src/knowledge/router.py` | 上传/列表/删除/搜索 API |
| `src/db/migrations/versions/kb_v1.py` | 数据库迁移 |

### 修改文件
| 文件 | 改动 |
|------|------|
| `src/main.py` | 注册 knowledge 路由 + 导入模型 |
| `src/compliance/router.py` | `/ai/chat` 注入知识库检索 |
| `static/index.html` | 📚知识库子面板 + 上传/列表/检索 UI |

### 外部依赖
| 包 | 用途 |
|----|------|
| `sentence-transformers` | BGE 模型推理 |
| `numpy` | 向量计算（已有） |

---

## 九、风险与缓解

| 风险 | 缓解 |
|------|------|
| BGE 模型首次加载慢（~5s） | 单例懒加载，服务启动后预热 |
| 大文档分块多，检索慢 | Top-K 限制 + numpy 批量矩阵运算 |
| JSON 存向量膨胀（~2KB/块） | 512 维 × 4 bytes ≈ 2KB，一万块仅 ~20MB，可接受 |
| sentence-transformers 安装失败 | 服务器已有 numpy，pip install 即可 |

---

## 十、实施计划

| 步骤 | 内容 | 预计改动量 |
|------|------|-----------|
| 1 | 安装 sentence-transformers | 一条命令 |
| 2 | 创建 models.py + DB 迁移 | ~30 行 |
| 3 | 创建 embedder.py | ~80 行 |
| 4 | 创建 router.py | ~120 行 |
| 5 | 修改 main.py 注册路由 | ~5 行 |
| 6 | 修改 /ai/chat 注入检索 | ~20 行 |
| 7 | 前端知识库子面板 | ~100 行 |
| 8 | 测试端到端流程 | |

---

**请审阅，确认后立即实施。**
