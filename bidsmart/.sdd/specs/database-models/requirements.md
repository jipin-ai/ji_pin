# database-models — 需求规格 (EARS)

## 功能需求

### FR-1: 用户模型 (User) (State-driven)
**Where** 用户数据存储，**the system shall** 维护 User 表含：username, password_hash, role (admin/reviewer/viewer/bid_editor), must_change_password, created_at, updated_at。

**验收标准:**
- [x] username 唯一索引
- [x] role 枚举校验
- [x] must_change_password 默认 True

### FR-2: 项目模型 (Project) (State-driven)
**Where** 项目数据存储，**the system shall** 维护 Project 表含：name, description, department, editor, bid_time, owner_id(FK→User), created_at, updated_at。

**验收标准:**
- [x] name 非空
- [x] owner_id 外键约束
- [x] 扩展字段 (department/editor/bid_time) 可为空

### FR-3: 文档模型 (Document) (State-driven)
**Where** 文件数据存储，**the system shall** 维护 Document 表含：filename, original_name, file_path, file_size, mime_type, doc_type (tender/bid/attachment), project_id(FK), uploader_id(FK)。

**验收标准:**
- [x] 外键关联 Project 和 User
- [x] doc_type 区分招标/投标/附件
- [x] 文件路径不包含 storage root 前缀

### FR-4: 审查会话 (ReviewSession) (State-driven)
**Where** 审查结果持久化，**the system shall** 维护 ReviewSession 表含：project_id, reviewer_id, status, score, result_json, created_at。

**验收标准:**
- [x] result_json 存储完整审查结果
- [x] score 0-100 合规分数

### FR-5: 审计日志 (AuditLog) (State-driven, Append-only)
**Where** 安全审计记录，**the system shall** 维护 AuditLog 表含：user_id, action, target_type, target_id, details_json, ip_address, result, created_at。

**验收标准:**
- [x] 只追加不修改/删除
- [x] details_json 存储操作上下文
- [x] 按时间索引

### FR-6: 异步会话管理 (Ubiquitous)
**While** 所有数据库操作，**the system shall** 使用 async SQLAlchemy 会话（`get_db` 依赖注入），确保连接正确释放。

**验收标准:**
- [x] AsyncEngine 单例
- [x] async_sessionmaker 工厂
- [x] FastAPI dependency `get_db` 自动管理会话生命周期

### FR-7: 数据库迁移 (Event-driven)
**When** 模型变更，**the system shall** 通过 Alembic 生成和执行迁移脚本，保持数据库版本与代码一致。

**验收标准:**
- [x] alembic.ini 配置 script_location=src/db/migrations
- [x] 5 个迁移脚本覆盖所有版本
- [x] `alembic upgrade head` 幂等
