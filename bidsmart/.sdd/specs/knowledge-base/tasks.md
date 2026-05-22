# knowledge-base — 实现任务

## 1. 数据库模型 + 迁移
_Status: completed_
_Boundary: src/knowledge/models.py + src/db/migrations/versions/kb_v1.py_

**Goal**: 创建 kb_documents 和 kb_chunks 表

**Acceptance Criteria:**
- [x] kb_documents: id, title, source_type, source_path, chunk_count, created_at
- [x] kb_chunks: id, doc_id(FK), chunk_index, heading, content, vector_json
- [x] Alembic 迁移脚本 kb_v1.py
- [x] `alembic upgrade head` 可正常执行

---

## 2. Embedder 单例
_Status: completed_
_Boundary: src/knowledge/embedder.py_

**Goal**: BGE 模型懒加载单例 + 文本分块器

### 2.1 chunk_text() 实现
_Status: completed_
- 500 字符/块，50 字符重叠
- 保留章节标题（正则匹配「第X条」等模式）
- 返回 `[(heading, chunk_text), ...]`

### 2.2 Embedder 单例
_Status: completed_
- `Embedder.get_instance()` 懒加载 BAAI/bge-small-zh-v1.5
- `encode(texts)` 返回 512 维 numpy 数组
- normalize_embeddings=True

---

## 3. 上传端点
_Status: completed_
_Boundary: src/knowledge/router.py — POST /admin/kb/upload_

**Goal**: 接收文件上传 → 解析 → 分块 → 向量化 → 存储

### 3.1 文件接收与解析
_Status: completed_
- 支持 .txt, .docx, .pdf
- 使用 `src/parsing/parse_document()` 提取文本
- 保存到 `storage/knowledge/{doc_id}.{ext}`

### 3.2 分块 + 向量化
_Status: completed_
- 调用 `chunk_text()` 分块
- 逐块调用 `embedder.encode()` 向量化
- 写入 kb_chunks 表（含 vector_json）

### 3.3 FAISS 索引更新
_Status: completed_
- 维护全局 FAISS 索引
- 新文档向量追加到索引

---

## 4. 检索端点
_Status: completed_
_Boundary: src/knowledge/router.py — POST /admin/kb/search_

**Goal**: 语义检索知识库内容

### 4.1 向量化查询
_Status: completed_
- 查询文本 → embedder.encode() → 512 维向量

### 4.2 FAISS 搜索
_Status: completed_
- IndexFlatIP.search(query_vector, top_k)
- 按 chunk_id 回表查询原文

### 4.3 结果组装
_Status: completed_
- 返回 chunk 原文 + 文档标题 + source_type + 相似度分数

---

## 5. 文档管理
_Status: completed_
_Boundary: src/knowledge/router.py_

### 5.1 文档列表
_Status: completed_
- `GET /admin/kb/documents` 分页列出所有文档

### 5.2 文档详情
_Status: completed_
- `GET /admin/kb/documents/{id}` 含分块列表

### 5.3 文档删除
_Status: completed_
- `DELETE /admin/kb/documents/{id}` 级联删除文件 + chunks + 索引

---

## 6. AI 集成
_Status: completed_
_Boundary: src/compliance/router.py — /ai/chat_

**Goal**: AI 对话自动检索知识库并注入上下文

- [x] 用户消息 → 自动检索 KB (top_k=3)
- [x] 检索结果注入 system prompt
- [x] 无结果时正常对话
- [x] 不暴露内部存储路径

---

## 7. 前端知识库面板
_Status: completed_
_Boundary: static/index.html_

### 7.1 三卡片布局
_Status: completed_
- 检索卡片：输入框 + 搜索按钮 + 结果展示
- 上传卡片：文件选择器 (::file-selector-button 美化) + 类型选择 + 上传按钮
- 文档列表卡片：标题 + 类型标签 + 分块数 + 时间

### 7.2 switchAdminSub() 集成
_Status: completed_
- kb 面板 toggle + loadKbDocuments() 初始化

### 7.3 CSS 类系统
_Status: completed_
- .kb-section, .kb-section-title, .kb-form-row
- .kb-form-group.flex-2, .kb-form-group.flex-1
- .kb-label, .kb-input, .kb-select
- .kb-upload-btn, .kb-file-input-native
- .kb-status (min-height 防抖动)
