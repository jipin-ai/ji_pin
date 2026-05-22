# admin-panel — 实现任务

## 1. Admin 路由设置
_Status: completed_
_Boundary: src/platform/admin/router.py_
_Depends: 无_

**Goal**: 建立管理端 API 路由基础结构，实现密钥轮换端点。

**Acceptance Criteria:**
- [x] 创建 APIRouter(prefix="/admin", tags=["admin"])
- [x] POST /admin/keys/rotate 端点：生成新 DEK，返回版本号
- [x] 通过 Depends(require_role("admin")) 保护
- [x] _get_key_manager() 依赖注入从 app.state 或 fallback 获取 KeyManager
- [x] 不返回 DEK 明文

### 1.1 创建 router.py
_Status: completed_
_文件: src/platform/admin/router.py_
_实现: KeyManager 依赖注入 + rotate_keys() 端点_

---

## 2. 用户 CRUD 端点
_Status: completed_
_Boundary: src/platform/admin/user_router.py_
_Depends: 1_

**Goal**: 实现完整的用户管理 API（列表、创建、重置密码、删除）并集成审计日志。

**Acceptance Criteria:**
- [x] GET /admin/users — 列出所有用户（id, username, role, created_at）
- [x] POST /admin/users — 创建用户（bcrypt 哈希、角色校验、must_change_password=True）
- [x] PUT /admin/users/{user_id}/password — 重置密码
- [x] DELETE /admin/users/{user_id} — 删除用户（不能删除自身、不能删除 admin）
- [x] 重复用户名检测（409 错误）
- [x] 无效角色检测（400 错误，提示有效值）
- [x] 审计日志写入（user_created / password_reset / user_deleted）
- [x] Pydantic 请求模型：CreateUserRequest、ResetPasswordRequest

### 2.1 创建 user_router.py
_Status: completed_
_文件: src/platform/admin/user_router.py_
_模型: CreateUserRequest (username:2-64, password:6-128, role:str)_
_模型: ResetPasswordRequest (password:6-128)_
_实现: list_users(), create_user(), reset_password(), delete_user()_

### 2.2 审计日志集成
_Status: completed_
_实现: 每个 CRUD 操作后 db.add(AuditLog(...)) + db.commit()_
_详情: action=user_created|password_reset|user_deleted, result=AuditResult.success_

---

## 3. 前端管理面板 + switchAdminSub()
_Status: completed_
_Boundary: static/index.html — adminPanel 区域_
_Depends: 2_

**Goal**: 在 SPA 中实现 admin 专属管理面板，含子面板切换和所有管理 UI。

**Acceptance Criteria:**
- [x] adminTabBtn 初始隐藏，登录后角色为 admin 时显示
- [x] switchPanel('admin') 显示 adminPanel，隐藏其他面板
- [x] switchAdminSub(name) 切换四个子面板：users/config/data/kb
- [x] 用户管理子面板：表格展示用户列表，含操作按钮
- [x] 新增用户对话框：含管理员密码验证字段
- [x] 重置密码：prompt 输入新密码
- [x] 删除用户：confirm 确认，admin 角色不可删除
- [x] 系统配置子面板：4 个字段 + 保存/加载 localStorage
- [x] 数据迁移子面板：导出按钮 + 导入文件选择 + 状态反馈
- [x] 知识库子面板：搜索 + 上传（复用 KB 组件）

### 3.1 Admin Panel HTML 结构
_Status: completed_
_位置: static/index.html line 718-790_
_结构: adminPanel div → 4 个 admin-sub-tab 按钮 → 4 个子 panel div_

### 3.2 switchAdminSub() 实现
_Status: completed_
_位置: static/index.html line 1813-1825_
_逻辑: 切换 .active 类 + 显示/隐藏子 panel + 懒加载数据_

### 3.3 loadAdminUsers() + 用户操作
_Status: completed_
_位置: static/index.html_
_函数: loadAdminUsers() — 渲染用户表格_
_函数: showAddUserDialog() / closeAddUserDialog() — 新增用户对话框_
_函数: submitAddUser() / addAdminUser() — 二次密码确认 + 创建_
_函数: showResetPwdDialog() — prompt 重置密码_

### 3.4 系统配置面板
_Status: completed_
_函数: loadAdminConfig() — 从 localStorage 读取配置填充表单_
_函数: saveConfig() — 从表单读取配置写入 localStorage_

---

## 4. 数据导出/导入功能
_Status: completed_
_Boundary: src/platform/admin/export.py_
_Depends: 2, 3_

**Goal**: 实现一键数据导出（tar.gz）和合并导入，支持服务器迁移。

**Acceptance Criteria:**
- [x] POST /admin/data/export — 创建 tar.gz，流式返回
- [x] 导出内容：bidsmart.db（VACUUM INTO）、storage/（copytree）、.env（脱敏）
- [x] POST /admin/data/import — 接收 .tar.gz，合并导入
- [x] 导入验证：bidsmart.db 存在检查
- [x] 合并策略：INSERT OR IGNORE 各表
- [x] 文件合并：仅复制目标不存在的文件
- [x] 临时目录清理：try/finally shutil.rmtree
- [x] 前端 exportData() / importData() 函数

### 4.1 创建 export.py
_Status: completed_
_文件: src/platform/admin/export.py_
_实现: export_data() — VACUUM INTO + copytree + tar + StreamingResponse_
_实现: import_data() — 解压 + ATTACH DATABASE + INSERT OR IGNORE_

### 4.2 前端导出/导入函数
_Status: completed_
_位置: static/index.html_
_函数: exportData() — POST /admin/data/export，触发浏览器下载_
_函数: importData() — 读取文件 input，POST /admin/data/import_

---

## 5. 审计集成验证
_Status: completed_
_Boundary: 全模块_
_Depends: 2_

**Goal**: 确保所有管理操作正确写入审计日志，满足合规要求。

**Acceptance Criteria:**
- [x] user_created 日志：记录创建人、目标用户名、角色
- [x] password_reset 日志：记录操作人、目标用户名
- [x] user_deleted 日志：记录操作人、被删除用户名
- [x] AuditLog 使用 AuditResult.success
- [x] ip_address 来源（当前写死 127.0.0.1，生产需从 request 获取）
- [x] created_at 自动填充（server_default=func.now()）

### 5.1 审计日志代码审查
_Status: completed_
_验证: user_router.py 中每个端点都有 AuditLog 写入_
_验证: AuditLog 模型定义（audit_log.py）正确：不可变、无 updated_at_

---

## 6. 端到端验证
_Status: pending_
_Depends: 5_

**Goal**: 走完整管理流程，确认无断裂。

**验证步骤:**
- [ ] 以 admin 登录 → 看到「管理」Tab
- [ ] 用户管理：创建新用户 → 列表中显示 → 重置密码 → 删除
- [ ] 二次密码确认：错误密码被拒绝，正确密码允许操作
- [ ] 系统配置：修改 API Key → 保存 → 刷新后仍存在
- [ ] 数据迁移：导出 → 下载 tar.gz → 解压验证内容 → 导入
- [ ] 密钥轮换：POST /admin/keys/rotate → 返回新版本号
- [ ] 审计日志：检查 audit_logs 表有对应记录
