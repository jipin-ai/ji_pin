# database-models — Discovery Brief

## 问题描述
BidSmart 的数据持久化层需要定义核心业务实体（用户、项目、文档、审查记录、审计日志）及其关系。SQLAlchemy async ORM + Alembic 迁移提供类型安全和版本化数据库演进。

## 当前状态
### 模型 (6 个)
- **User**: 用户认证与角色 (admin/reviewer/viewer/bid_editor)
- **Project**: 投标项目（含 department/editor/bid_time）
- **Document**: 上传文件（关联项目 + 用户）
- **ReviewSession**: 审查会话记录
- **AuditLog**: 审计日志（append-only）
- **ProjectMember**: 项目级 RBAC（模型已有，P2 接入）

### 基础设施
- `src/db/base.py`: SQLAlchemy Base
- `src/db/session.py`: AsyncEngine + async_sessionmaker
- `src/db/migrations/`: 5 个 Alembic 迁移脚本

## 边界
**In scope:** ORM 模型、异步会话管理、数据库迁移、SQLite 支持
**Out of scope:** PostgreSQL 迁移（P2）、读写分离、连接池监控
