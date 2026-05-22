# admin-panel — 需求规格

## 功能需求

### FR-1: 用户创建、编辑、删除（CRUD）
**EARS: Event-driven**
> 当管理员在用户管理面板操作时，系统应提供用户的完整生命周期管理：创建新用户、查看用户列表、重置密码、删除用户。

**验收标准:**
- [x] 管理员可见用户列表（用户名、角色、创建时间）
- [x] 管理员可创建新用户（用户名≥2字符、密码≥6位、角色从 admin/reviewer/viewer/bid_editor 选择）
- [x] 创建用户时自动设置 must_change_password=True
- [x] 管理员可重置任意用户的密码
- [x] 管理员可删除非 admin 用户（admin 角色用户不可删除）
- [x] 管理员不可删除自身账号（自保护）
- [x] 用户名重复检测：重复时返回 409 错误及中文提示

### FR-2: 角色管理
**EARS: Ubiquitous**
> 系统应支持四种预定义角色，不同角色拥有不同的功能访问权限。

**验收标准:**
- [x] 四种角色：admin（管理员）、reviewer（审核员）、viewer（观察员）、bid_editor（投标书编辑）
- [x] 创建用户时可指定角色，角色值通过 UserRole 枚举校验
- [x] 用户列表显示中文角色名（管理员/审核员/观察员/投标书编辑）
- [x] 仅 admin 角色可见「管理」Tab（前端 currentUserRole === 'admin' 控制）
- [x] 后端所有管理端点通过 Depends(require_role("admin")) 保护

### FR-3: 首次登录强制改密
**EARS: State-driven**
> 当 must_change_password=True 的用户首次登录时，系统应强制跳转到改密页面，完成后才能进入主界面。

**验收标准:**
- [x] 后端登录响应包含 must_change_password 字段
- [x] 前端检测该字段后显示改密对话框（隐藏主界面 appPage）
- [x] 新密码≥6位，两次输入一致（不一致提示「两次密码不一致」）
- [x] 改密通过 POST /auth/change-password 完成
- [x] 改密成功后方可进入主界面并获取角色信息
- [x] 管理员创建的用户默认 must_change_password=True

### FR-4: 审计日志
**EARS: Ubiquitous**
> 系统应在每次管理操作时写入不可变的审计日志，记录操作人、操作类型、目标资源、IP 地址和结果。

**验收标准:**
- [x] 创建用户时写入 AuditLog(action="user_created", resource_type="user")
- [x] 重置密码时写入 AuditLog(action="password_reset", resource_type="user")
- [x] 删除用户时写入 AuditLog(action="user_deleted", resource_type="user")
- [x] details 字段为 JSON，记录目标用户名、角色等上下文
- [x] result 字段使用 AuditResult 枚举（success）
- [x] 审计日志不可修改、不可删除（append-only，无 updated_at 字段）

### FR-5: 密钥轮换
**EARS: Event-driven**
> 当管理员触发密钥轮换时，系统应生成新的 DEK 并递增版本号，旧密钥保留以便解密历史数据。

**验收标准:**
- [x] POST /admin/keys/rotate 端点仅 admin 可访问
- [x] 调用 KeyManager.rotate() 生成新 256-bit DEK
- [x] 返回 JSON: { status, message, new_version }
- [x] 旧版本 DEK 保留在 KeyManager._keys 字典中
- [x] 不返回 DEK 明文（仅返回版本号）

### FR-6: 数据导出/导入
**EARS: Event-driven**
> 当管理员触发数据导出时，系统应打包数据库、文件存储和配置为 tar.gz 下载。导入时应以合并模式恢复数据。

**验收标准:**
- [x] POST /admin/data/export 创建 tar.gz 包含：bidsmart.db、storage/、.env（API Key 脱敏）
- [x] 数据库使用 VACUUM INTO 导出干净副本
- [x] 返回 StreamingResponse（application/gzip），带 Content-Disposition 头
- [x] 导出失败时自动清理临时目录（try/finally + shutil.rmtree）
- [x] POST /admin/data/import 接受 .tar.gz 上传，验证文件扩展名
- [x] 导入验证：检查 bidsmart.db 存在于解压目录
- [x] 合并模式：INSERT OR IGNORE 各表（users, projects, documents, review_sessions, audit_logs）
- [x] 存储文件合并：仅复制目标不存在的文件（不覆盖已有文件）
- [x] 导入失败时自动清理临时目录

### FR-7: 系统配置管理
**EARS: Ubiquitous**
> 系统应提供前端配置管理界面，允许管理员查看和修改运行时配置。

**验收标准:**
- [x] 配置面板包含字段：API Base URL、API Key（password 类型）、模型名称、最大上传（MB）
- [x] 保存按钮调用 saveConfig()，写入 localStorage
- [x] 加载配置时调用 loadAdminConfig()，从 localStorage 读取并填充表单

### FR-8: 二次密码确认
**EARS: Event-driven**
> 当管理员执行敏感操作时，系统应先验证管理员密码，通过后方可执行。

**验收标准:**
- [x] 新增用户：弹出 addUserDialog 对话框，含「管理员密码」字段
- [x] 通过 POST /auth/login 验证管理员密码（用当前用户名 + 输入密码）
- [x] 验证失败则 alert「管理员密码验证失败」并中止操作
- [x] 密码验证通过后调用 POST /admin/users 执行实际创建

---

## 非功能需求

### NFR-1: 安全性
- 管理面板仅 admin 角色可见（前端 display:none + 后端 require_role("admin") 守卫）
- bcrypt 哈希存储密码（通过 passlib.hash.bcrypt）
- KEK 从环境变量 BIDSMART_KEK 加载，有开发默认值
- 导出文件中 DEEPSEEK_API_KEY 值正则替换为 ***REDACTED***
- 管理员不可删除自身账号（user_id == current_user.id → 400）
- 密钥轮换不返回 DEK 明文

### NFR-2: 可靠性
- 导入/导出使用 tempfile.mkdtemp() 临时目录，finally 块保证清理
- 数据库导出使用 VACUUM INTO 确保事务一致性
- 导入使用 INSERT OR IGNORE 避免重复数据导致失败
- 审计日志与业务操作在同一 db session 中提交

### NFR-3: 可用性
- 所有错误提示使用中文（如「用户名已存在」「无效角色」「不能删除自己的账号」）
- 角色列表显示为中文名称（管理员/审核员/观察员/投标书编辑）
- 删除操作有 confirm 确认对话框
- 导入/导出有状态反馈（exportStatus / importStatus div）

---

## 约束

- 后端：FastAPI + SQLAlchemy AsyncSession + SQLite
- 前端：纯 HTML/CSS/JS（static/index.html），无框架
- 密码哈希：passlib bcrypt
- 加密：AES-256-GCM、KEK + DEK 双层架构
- 文件存储：本地文件系统，路径 storage/
- 暗色主题保持一致性

## 边界外（Out of Scope）

- 审计日志查询前端面板（日志已写入，查询暂不在 spec 范围）
- 自动备份调度（需 cron + 额外脚本）
- 多管理员审批流程
- 用户自助注册 / 密码找回
- LDAP/OAuth 集成
- 批量用户导入（CSV/Excel）
- 角色细粒度权限（ACL）
