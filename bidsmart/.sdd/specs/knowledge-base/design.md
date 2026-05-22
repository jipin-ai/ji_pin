# knowledge-base — 设计文档

## 1. 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                     前端 (static/index.html)                      │
│  管理面板 → 知识库子面板                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐                   │
│  │ 检索卡片  │  │ 上传卡片  │  │ 文档列表卡片  │                   │
│  └──────────┘  └──────────┘  └──────────────┘                   │
├─────────────────────────────────────────────────────────────────┤
│                       后端路由层                                   │
│  POST /admin/kb/upload  │  GET /admin/kb/search                  │
│  GET /admin/kb/documents │ GET /admin/kb/documents/{id}          │
├──────────────┬──────────────────────┬───────────────────────────┤
│  文档解析     │      BGE 向量化        │     FAISS 索引              │
│  parse_doc() │  embedder.encode()    │  IndexFlatIP.search()     │
├──────────────┴──────────────────────┴───────────────────────────┤
│                        存储层                                      │
│  storage/knowledge/{doc_id}.ext  │  SQLite: kb_documents/chunks  │
└─────────────────────────────────────────────────────────────────┘
```

## 2. 数据流

### 上传流程
```
用户选择文件 → 前端 POST /admin/kb/upload (multipart)
  → router 接收文件 → 保存到 storage/knowledge/
  → parse_document() 提取文本
  → chunk_text() 分块 (500 char, 50 overlap)
  → 写入 kb_documents 表
  → embedder.encode(chunks) 向量化
  → 逐条写入 kb_chunks 表
  → 更新 FAISS 索引
  → 返回 { doc_id, chunk_count }
```

### 检索流程
```
用户输入查询 / AI 对话触发
  → POST /admin/kb/search { query, top_k }
  → embedder.encode(query) → query_vector (512d)
  → FAISS IndexFlatIP.search(query_vector, top_k)
  → 按 chunk_id 批量查询 kb_chunks 表
  → 组装结果（原文 + 文档标题 + source_type + score）
  → 返回 top_k 条结果
```

### AI 集成流程
```
用户发送 AI 对话 → POST /ai/chat { message }
  → router 调用 kb_search(message, top_k=3)
  → 将检索结果格式化为上下文注入 system prompt
  → 调用 DeepSeek API 生成回答
  → 返回 SSE 流式响应
```

## 3. 组件设计

### 3.1 Embedder 单例

```python
class Embedder:
    """BGE 向量化引擎 — 全应用共享单例"""
    _instance = None
    
    def __init__(self):
        self.model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
        self.dimension = 512
    
    @classmethod
    def get_instance(cls) -> "Embedder":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def encode(self, texts: list[str]) -> np.ndarray:
        """将文本列表转为 512 维向量"""
        return self.model.encode(texts, normalize_embeddings=True)
```

特点：
- 懒加载：首次调用 get_instance() 时才加载模型
- 线程安全：单例模式 + normalize_embeddings
- 内存：模型约 400MB，加载后总占用约 1GB

### 3.2 分块策略

```python
def chunk_text(text: str, chunk_size=500, overlap=50) -> list[tuple[str, str]]:
    """
    智能分块，保留章节标题。
    
    标题识别规则：
    - 以「第X条」「第X章」开头的行
    - 以数字+标点开头的行（如「1.」「1、」）
    - 以「［...］」包裹的行
    
    Returns: [(heading, chunk_text), ...]
    """
```

### 3.3 FAISS 索引

```python
# 索引类型：内积相似度（归一化向量 = 余弦相似度）
index = faiss.IndexFlatIP(512)  # 512 维

# 添加向量
index.add(embeddings)  # shape: (n_chunks, 512)

# 检索
distances, indices = index.search(query_vector.reshape(1, -1), top_k)
```

## 4. 数据库模型

### kb_documents
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| title | VARCHAR(255) | 文档标题 |
| source_type | VARCHAR(50) | manual/law/regulation/experience |
| source_path | VARCHAR(500) | 存储路径 |
| chunk_count | INTEGER | 分块数量 |
| created_at | DATETIME | 创建时间 |

### kb_chunks
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| doc_id | INTEGER FK | 关联 kb_documents.id |
| chunk_index | INTEGER | 块序号 (0-based) |
| heading | TEXT | 所属章节标题 |
| content | TEXT | 块文本内容 |
| vector_json | TEXT | JSON 序列化的 512 维向量 |

## 5. API 端点

| 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|
| POST | /admin/kb/upload | 上传文档并向量化 | admin, reviewer |
| GET | /admin/kb/documents | 列出所有文档 | admin, reviewer |
| GET | /admin/kb/documents/{id} | 获取文档详情 | admin, reviewer |
| DELETE | /admin/kb/documents/{id} | 删除文档+chunks+索引 | admin |
| POST | /admin/kb/search | 语义检索 | 所有角色 |
| GET | /admin/kb/search?q=... | GET 方式检索 | 所有角色 |

## 6. 前端设计

### 三卡片分区布局（kb-section 模式）

```
┌─────────────────────────────────────────┐
│  🔍 知识库检索                            │
│  ┌──────────────────────┬──────────────┐ │
│  │ 搜索输入框 (flex-2)    │ 搜索按钮      │ │
│  └──────────────────────┴──────────────┘ │
│  搜索结果列表...                          │
├─────────────────────────────────────────┤
│  📤 上传知识文档                           │
│  ┌──────────────────────┬──────────────┐ │
│  │ 文件选择 (flex-2)      │ 上传按钮      │ │
│  └──────────────────────┴──────────────┘ │
│  来源类型选择 + 上传状态                   │
├─────────────────────────────────────────┤
│  📚 知识库文档列表                          │
│  ┌──────────────────────────────────────┐│
│  │ 文档标题  [类型标签]  12块  2026-05-01 ││
│  │ 文档标题  [类型标签]  8块   2026-04-30 ││
│  └──────────────────────────────────────┘│
└─────────────────────────────────────────┘
```

## 7. 设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 向量模型 | BAAI/bge-small-zh-v1.5 | 中文最优，512维内存友好 |
| 索引算法 | FAISS IndexFlatIP | 精确搜索，小规模最优 |
| 分块大小 | 500 字符 | 中文语义完整性 + 检索精度平衡 |
| 重叠 | 50 字符 | 防止关键信息在边界断裂 |
| 存储 | 本地文件 + SQLite | 当前阶段无需外部向量数据库 |
| 前端布局 | 三卡片分区 | 复用 kb-section 模式，视觉统一 |
