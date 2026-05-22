# admin-panel — 设计文档

## 1. 架构概览

管理模块采用 **router → service → model** 三层架构。后端路由按职责拆分为三个文件，前端为单页 SPA 内嵌管理面板。

```
src/platform/admin/
├── router.py          # 密钥轮换端点
├── user_router.py     # 用户 CRUD + 审计日志
└── export.py          # 数据导出/导入

static/
└── index.html         # 前端管理面板（adminPanel）
```

```
┌─────────────────────────────────────────────────┐
│                   Frontend SPA                    │
│  switchPanel('admin') → switchAdminSub(name)     │
│  ┌──────────┬──────────┬──────────┬───────────┐  │
│  │ 用户管理  │ 系统配置  │ 数据迁移  │  知识库   │  │
│  └──────────┴──────────┴──────────┴───────────┘  │
│         │                                    │    │
│         ▼                                    ▼    │
│  ┌──────────────┐              ┌──────────────┐   │
│  │ 二次密码确认  │              │   localStorage │   │
│  │ POST /auth/  │              │   config 读写  │   │
│  │   login      │              └──────────────┘   │
│  └──────┬───────┘                                  │
└─────────┼────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────┐
│              Backend API (FastAPI)                │
│                                                   │
│  /admin/keys/rotate  ──► KeyManager.rotate()      │
│  /admin/users/*      ──► User CRUD + AuditLog     │
│  /admin/data/export  ──► tar.gz (DB+storage+.env) │
│  /admin/data/import  ──► Merge restore            │
│                                                   │
│  所有端点: Depends(require_role("admin"))         │
└──────────────────────────────────────────────────┘
```

## 2. UI 布局

### 2.1 管理 Tab（仅 admin 可见）

管理 Tab 通过角色判断控制显示：

```javascript
// 登录或改密后获取角色
fetch('/auth/me', {headers: {'Authorization': 'Bearer '+token}})
  .then(r => r.json())
  .then(d => {
    currentUserRole = d.role;
    if (d.role === 'admin') {
      document.getElementById('adminTabBtn').style.display = '';
    }
  });
```

Tab 按钮初始 `style="display:none"`，仅当 `currentUserRole === 'admin'` 时显示。

### 2.2 子面板切换

```javascript
function switchAdminSub(name) {
  adminSubTab = name;
  // 激活对应的子 Tab 按钮
  document.querySelectorAll('.admin-sub-tab').forEach(b =>
    b.classList.toggle('active', b.textContent.includes(
      name==='users'?'用户':name==='config'?'配置':name==='data'?'迁移':'知识'
    ))
  );
  // 显示/隐藏子面板
  document.getElementById('adminUsersPanel').classList.toggle('hidden', name!=='users');
  document.getElementById('adminConfigPanel').classList.toggle('hidden', name!=='config');
  document.getElementById('adminDataPanel').classList.toggle('hidden', name!=='data');
  document.getElementById('adminKbPanel').classList.toggle('hidden', name!=='kb');
  // 懒加载数据
  if (name==='users') loadAdminUsers();
  if (name==='config') loadAdminConfig();
  if (name==='kb') loadKbDocs();
}
```

### 2.3 子面板详情

| 子面板 | ID | 功能 |
|--------|-----|------|
| 用户管理 | adminUsersPanel | 用户表格 + 新增按钮 + 重置密码/删除操作 |
| 系统配置 | adminConfigPanel | 4 个配置字段 + 保存按钮 |
| 数据迁移 | adminDataPanel | 导出按钮 + 导入文件选择 + 状态显示 |
| 知识库 | adminKbPanel | 搜索框 + 上传表单（共享 KB 组件） |

## 3. API 设计

### 3.1 密钥轮换

```
POST /admin/keys/rotate
Auth: Bearer <token> (admin only)
Response 200:
{
  "status": "ok",
  "message": "Key rotation successful",
  "new_version": 2
}
```

实现：`router.py` — `KeyManager.rotate()` 生成新 256-bit DEK，版本递增。

### 3.2 用户管理

```
GET /admin/users
Auth: Bearer <token> (admin only)
Response 200:
{
  "users": [
    { "id": 1, "username": "admin", "role": "admin", "created_at": "2026-..." },
    ...
  ]
}

POST /admin/users
Auth: Bearer <token> (admin only)
Body: { "username": "...", "password": "...", "role": "bid_editor" }
Response 201: { "id": 3, "username": "...", "role": "bid_editor" }
Error 409: { "detail": "用户名 xxx 已存在" }
Error 400: { "detail": "无效角色: xxx。有效值: admin, reviewer, viewer, bid_editor" }

PUT /admin/users/{user_id}/password
Auth: Bearer <token> (admin only)
Body: { "password": "newpassword" }
Response 200: { "message": "已重置 xxx 的密码" }
Error 404: { "detail": "用户不存在" }

DELETE /admin/users/{user_id}
Auth: Bearer <token> (admin only)
Response 200: { "message": "已删除用户 xxx" }
Error 400: { "detail": "不能删除自己的账号" }
Error 404: { "detail": "用户不存在" }
```

### 3.3 数据导出/导入

```
POST /admin/data/export
Auth: Bearer <token> (admin only)
Response 200: Stream<application/gzip>
  Content-Disposition: attachment; filename="bidsmart_export_20260502_120000.tar.gz"
  包含: bidsmart.db (VACUUM INTO), storage/ (copytree), .env (API key redacted)
Error 500: { "detail": "数据库文件不存在" }
Error 500: { "detail": "导出失败: ..." }

POST /admin/data/import
Auth: Bearer <token> (admin only)
Body: multipart/form-data, file=<.tar.gz>
Response 200: { "storage_files": 5, "message": "导入完成（合并模式）" }
Error 400: { "detail": "仅支持 .tar.gz 文件" }
Error 400: { "detail": "无效的导出包：缺少 bidsmart.db" }
Error 500: { "detail": "导入失败: ..." }
```

## 4. 安全设计

### 4.1 二次密码确认流程

```
用户点击「新增用户」
  → showAddUserDialog() 弹出对话框
  → 用户填写用户名、密码、角色、管理员密码
  → submitAddUser() 校验表单
  → addAdminUser() 先 POST /auth/login 验证管理员密码
    → 失败: alert("管理员密码验证失败")
    → 成功: POST /admin/users 创建用户
```

### 4.2 审计日志集成

每次管理操作在同一次数据库会话中写入审计日志：

```python
# user_router.py — create_user()
db.add(AuditLog(
    user_id=current_user.id,       # 操作人
    action="user_created",         # 操作类型
    resource_type="user",          # 资源类型
    resource_id=str(user.id),      # 资源ID
    details={"username": data.username, "role": data.role},  # 上下文
    ip_address="127.0.0.1",        # 来源IP
    result=AuditResult.success     # 结果
))
await db.commit()
```

审计日志表结构（audit_logs）：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| user_id | FK → users.id | 操作人（可为 NULL） |
| action | VARCHAR(255) | 操作类型 |
| resource_type | VARCHAR(127) | 资源类型 |
| resource_id | VARCHAR(255) | 资源标识 |
| details | JSON | 结构化上下文 |
| ip_address | VARCHAR(45) | 客户端 IP |
| result | ENUM(success/failure/info) | 操作结果 |
| created_at | DATETIME | 创建时间（不可变） |

### 4.3 密钥管理架构

```
BIDSMART_KEK (env var, 32 bytes)
    │
    ▼
KeyManager
    ├── _kek: bytes                    # 密钥加密密钥
    ├── _keys: dict[int, bytes]        # 版本→DEK 映射
    ├── _current_version: int          # 当前活跃版本
    │
    ├── generate_dek() → (dek, ver)    # 生成新 DEK（不切换）
    ├── rotate() → (dek, ver)          # 生成新 DEK 并切换
    ├── get_current_dek() → (dek, ver) # 获取当前 DEK
    └── get_dek(ver) → dek             # 获取指定版本 DEK
```

## 5. 数据流

### 5.1 用户创建流程

```
管理员                    前端                     后端
  │                        │                        │
  │  点击「+ 新增用户」     │                        │
  │ ─────────────────────► │                        │
  │                        │ showAddUserDialog()    │
  │  填写表单 + 管理员密码  │                        │
  │ ─────────────────────► │                        │
  │                        │ POST /auth/login       │
  │                        │ (验证管理员密码)        │
  │                        │ ─────────────────────► │
  │                        │                        │ verify bcrypt
  │                        │ ◄───────────────────── │
  │                        │                        │
  │                        │ POST /admin/users      │
  │                        │ ─────────────────────► │
  │                        │                        │ bcrypt hash
  │                        │                        │ INSERT user
  │                        │                        │ INSERT audit_log
  │                        │                        │ COMMIT
  │                        │ ◄───────────────────── │
  │                        │ loadAdminUsers()       │
  │  表格刷新               │                        │
  │ ◄───────────────────── │                        │
```

### 5.2 数据导出流程

```
管理员                    前端                      后端
  │                        │                        │
  │  点击「导出全部数据」    │                        │
  │ ─────────────────────► │                        │
  │                        │ POST /admin/data/export│
  │                        │ ─────────────────────► │
  │                        │                        │ VACUUM INTO tmp/bidsmart.db
  │                        │                        │ copytree storage/ → tmp/
  │                        │                        │ read .env, redact API key
  │                        │                        │ tar -czf archive.tar.gz
  │                        │                        │
  │                        │ ◄─ StreamingResponse ─ │
  │                        │                        │
  │  浏览器下载 tar.gz      │                        │
  │ ◄───────────────────── │                        │
```

## 6. 设计决策

| 决策 | 方案 | 理由 |
|------|------|------|
| 管理员身份验证 | 复用 POST /auth/login | 避免重复实现密码验证逻辑 |
| 审计日志写入 | 与业务操作同一 session | 保证一致性：操作成功=日志已写入 |
| 导出 API Key 脱敏 | 正则替换 DEEPSEEK_API_KEY= | 防止密钥泄露到导出文件 |
| 导入模式 | INSERT OR IGNORE 合并 | 不覆盖已有数据，安全可重复执行 |
| 前端配置存储 | localStorage | 简单，无需后端持久化端点 |
| 用户角色约束 | 不删除 admin 用户 | 防止误删导致系统无管理员 |
| URL 前缀 | /admin/* 统一前缀 | 清晰的管理端点命名空间 |
| DB 导出方式 | VACUUM INTO | 比 .dump 更高效，生成干净副本 |
| KEK 加载 | 环境变量 BIDSMART_KEK | 12-factor 最佳实践，dev fallback 可用 |
