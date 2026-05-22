# Spec: 管理后台 + 知识库 + 数据迁移
Version: 0.6.0 (proposed)
Status: draft — 待审阅

---

## 一、现状分析

### 前端
- 单文件 SPA：`static/index.html`（~1370 行）
- 四个 Tab：📁项目管理 / 📄文件上传 / 📊文件审查 / 📋对照表
- 登录后不存储用户角色，前端不知道当前用户是 admin/reviewer/viewer
- 切换 Tab 通过 `switchPanel(name)` + `PANEL_NAMES` 数组控制

### 后端
- `/admin` 路由已有（密钥轮换），`require_role("admin")` 依赖已就绪
- 登录只返回 token，不返回用户角色信息
- 缺少 `/auth/me` 端点让前端获取当前用户信息

### 数据库
- `users` 表有 `role` 字段（admin/reviewer/viewer）
- `projects` 有级联删除（documents, review_sessions, project_members 等）

---

## 二、架构决策

### 管理后台不做独立系统
在现有 SPA 中新增第 5 个 Tab「⚙️ 管理」，仅 admin 用户可见。所有管理功能（知识库、配置、用户、导出）都在此 Tab 内通过子导航切换。

### 知识库嵌入管理后台
知识库的文档上传、列表、删除、索引重建等操作界面作为管理 Tab 的子页面。

### 不引入新依赖
- 前端：保持纯 HTML/CSS/JS，不引入框架
- 后端：FastAPI 路由 + SQLite，知识库向量化使用现有 DeepSeek API 或轻量方案

---

## 三、分阶段实施

### 第一阶段：管理后台骨架（v0.6.0）

#### 3.1 后端改动

| # | 端点 | 方法 | 权限 | 说明 |
|---|------|------|------|------|
| 1 | `/auth/me` | GET | 登录用户 | 返回 `{id, username, role}` |
| 2 | `/admin/users` | GET | admin | 用户列表 |
| 3 | `/admin/users` | POST | admin | 新增用户 |
| 4 | `/admin/users/{id}/password` | PUT | admin | 重置密码 |
| 5 | `/admin/users/{id}` | DELETE | admin | 删除用户 |
| 6 | `/admin/config` | GET | admin | 获取系统配置（脱敏） |
| 7 | `/admin/config` | PUT | admin | 更新系统配置 |
| 8 | `/admin/export` | POST | admin | 导出全部数据（DB + 文件 → tar.gz） |
| 9 | `/admin/import` | POST | admin | 导入数据包 |

#### 3.2 前端改动

```
面板结构新增：
├── 📁 项目管理     (现有)
├── 📄 文件上传     (现有)
├── 📊 文件审查     (现有)
├── 📋 对照表       (现有)
└── ⚙️ 管理         (新增，仅 admin 可见)
    ├── 👥 用户管理
    ├── ⚙️ 系统配置
    ├── 📚 知识库    (第二阶段启用)
    └── 📦 数据迁移
```

具体改动点：
1. `panel-tabs` 中新增第 5 个 `<button>`，`style="display:none"` 默认隐藏
2. 登录后调用 `/auth/me` 获取角色，若为 admin 则显示管理 Tab
3. 新增 `adminPanel` div，内含子导航 + 4 个子面板
4. `PANEL_NAMES` 扩展为 `['project','upload','fileReview','compare','admin']`
5. `switchPanel('admin')` 时加载对应子面板

---

### 第二阶段：知识库模块（v0.7.0）

#### 后端
- 新增 `src/knowledge/` 模块
  - `models.py`：Document 模型（title, content, source_type, vector_id, chunk_count）
  - `router.py`：上传/列表/删除/搜索 API
  - `embedder.py`：文本分块 + 向量化（调用 DeepSeek embedding 或本地方案）
  - `retriever.py`：语义检索，注入 AI 对话上下文

#### 前端（管理 Tab → 📚 知识库子面板）
- 文档上传区（支持 .txt .pdf .docx .md）
- 已上传文档列表（标题、来源、分块数、上传时间）
- 单个/批量删除按钮
- 「重建索引」按钮
- 检索测试框（输入查询 → 显示 Top-K 匹配片段 + 相似度）

#### AI 对话集成
修改 `/ai/chat` 端点：
- 接收用户消息后，先调用 `retriever.search(query, top_k=5)`
- 将检索到的知识库片段注入 system prompt
- 让 AI 基于知识库内容回答（而非仅基于审查结果）

---

### 第三阶段：数据迁移（v0.7.1）

#### 导出流程
```
POST /admin/export
→ 1. 导出 SQLite DB → /tmp/bidsmart_export/bidsmart.db
→ 2. 复制 storage/ 目录 → /tmp/bidsmart_export/storage/
→ 3. 打包 → bidsmart_export_20260501.tar.gz
→ 4. 返回下载链接 + 文件大小
```

#### 导入流程
```
POST /admin/import (multipart: tar.gz)
→ 1. 解压到 /tmp/
→ 2. 验证 DB 结构兼容
→ 3. 合并 storage 文件
→ 4. 热重启服务
→ 5. 返回导入报告
```

---

## 四、前端子面板 UI 草稿

### 用户管理子面板
```
┌─────────────────────────────────────────┐
│ 👥 用户管理                              │
│ ┌──────┬────────┬────────┬────────────┐ │
│ │ 用户名 │ 角色   │ 创建时间 │ 操作       │ │
│ ├──────┼────────┼────────┼────────────┤ │
│ │ admin │ 管理员  │ 04-30   │ —          │ │
│ │ rev01 │ 审核员  │ 05-01   │ 🔑重置 🗑  │ │
│ └──────┴────────┴────────┴────────────┘ │
│ [+ 新增用户]                              │
└─────────────────────────────────────────┘
```

### 系统配置子面板
```
┌─────────────────────────────────────────┐
│ ⚙️ 系统配置                              │
│ API Base URL: [___________________]     │
│ API Key:      [••••••••••  ] [显示]     │
│ 模型名称:      [deepseek-chat    ]       │
│ 存储路径:      [./storage        ]       │
│ 最大上传:      [250] MB                  │
│ [保存配置]                                │
└─────────────────────────────────────────┘
```

### 数据迁移子面板
```
┌─────────────────────────────────────────┐
│ 📦 数据迁移                              │
│ ┌─ 导出 ───────────────────────────────┐│
│ │ 数据库: bidsmart.db (X MB)           ││
│ │ 文件数: N 个 (Y MB)                  ││
│ │ [📥 导出全部数据]                     ││
│ └──────────────────────────────────────┘│
│ ┌─ 导入 ───────────────────────────────┐│
│ │ [选择文件] 未选择                     ││
│ │ [📤 导入数据包]                       ││
│ └──────────────────────────────────────┘│
└─────────────────────────────────────────┘
```

---

## 五、文件变更清单

### 后端新增
- `src/platform/admin/user_router.py` — 用户管理 CRUD
- `src/platform/admin/export.py` — 导出/导入逻辑

### 后端修改
- `src/platform/auth/router.py` — 新增 `/auth/me`
- `src/main.py` — 注册新路由
- `src/config.py` — 新增可配置项（通过环境变量或 DB）

### 前端修改
- `static/index.html` — 新增管理 Tab、子面板、JS 逻辑

---

## 六、待决议

1. **知识库向量化方案**：用 DeepSeek Embedding API 还是本地方案（如 sentence-transformers）？
2. **配置存储**：当前配置在 `.env` 文件，管理后台修改后是写回 `.env` 还是存数据库？
3. **导入安全性**：导入时是否清空现有数据（覆盖）还是合并？建议合并 + 冲突跳过。

---

请审阅，确认后开始第一阶段实施。

---

## 七、已确认决议

| # | 问题 | 决议 |
|---|------|------|
| 1 | 向量化方案 | DeepSeek Embedding API |
| 2 | 配置存储 | `.env` 文件，直接读写 |
| 3 | 导入策略 | 合并（追加新数据，冲突跳过） |
| 4 | 安全策略 | D：操作确认（二次弹窗+admin密码）+ audit_logs 审计 |

