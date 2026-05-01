# admin-panel — Discovery Brief

## 问题描述

BidSmart v0.7.7 已部署于 ECS，拥有完整的用户系统（admin/reviewer/viewer/bid_editor 四种角色）和数据管道。但目前缺少管理界面，所有管理操作都需要直接操作数据库或手动执行命令：

| 问题 | 现状 | 影响 |
|------|------|------|
| 无用户管理界面 | 新增用户需手动 INSERT 到 SQLite 数据库 | 操作门槛高、易出错、无法审计 |
| 角色分配困难 | 无 UI 修改用户角色 | 无法动态调整权限 |
| 无数据备份能力 | 服务器迁移需手动 scp + sqlite3 .dump | 流程脆弱、数据丢失风险 |
| 密钥轮换不可达 | KeyManager.rotate() 存在但无调用入口 | 加密密钥长期不轮换，安全合规风险 |
| 无操作审计 | 管理操作无日志留痕 | 无法追溯谁做了什么操作 |

## 期望结果

一个**仅 admin 角色可见**的管理面板，提供：

```
管理面板（仅 admin 可见）
├── 用户管理 — 用户 CRUD、角色管理、密码重置
├── 系统配置 — API Key、模型参数配置
├── 数据迁移 — 一键导出/导入（tar.gz 含 DB + 文件 + 配置）
└── 知识库 — 知识文档检索与上传
```

核心安全要求：
- **二次密码确认**：敏感操作（新增用户、重置密码、删除用户、导出数据）需验证管理员密码
- **审计日志**：所有管理操作写入 audit_logs 表（action 类型：user_created / password_reset / user_deleted）
- **自我保护**：不允许管理员删除自身账号

## 前置条件

- 用户模型（User）支持四种角色：admin, reviewer, viewer, bid_editor ✅
- passlib/bcrypt 密码哈希已集成 ✅
- AuditLog 模型和 audit_logs 表已就绪 ✅
- KeyManager（DEK 轮换）已实现 ✅
- 前端全局变量 currentUserRole 已可用于角色判断 ✅

## 依赖关系

- 依赖 steering: product.md, tech.md, structure.md ✅ 已创建
- 依赖后端 API: /auth/login, /auth/me, /auth/change-password ✅ 已实现
- 不依赖其他 spec

## 边界

**In scope:**
- 管理面板 Tab（仅 admin 可见）
- 用户 CRUD（创建、列表、删除、密码重置）
- 角色分配（admin/reviewer/viewer/bid_editor）
- 首次登录强制改密（must_change_password 字段）
- 二次密码确认（敏感操作前验证管理员密码）
- 审计日志集成（user_created / password_reset / user_deleted）
- DEK 密钥轮换 API 端点
- 数据导出（tar.gz: bidsmart.db + storage/ + .env 脱敏）
- 数据导入（合并模式，INSERT OR IGNORE）
- 系统配置读写（API Base URL、API Key、模型名、最大上传大小）
- 知识库管理子面板

**Out of scope:**
- 多管理员协作/审批流程
- LDAP / OAuth 集成
- 实时监控仪表盘
- 自动备份调度
- 审计日志查询界面（后台已写入，但暂无前端查询面板）
- 批量用户导入
- 权限细粒度 ACL（当前为角色级）

## 推荐路径

**单一 feature spec，完成后端 + 前端一体化交付。**

理由：后端 API 已部分实现（user_router.py, router.py, export.py），前端 admin panel HTML/JS 已实现。本 spec 是对已有实现的规格化归档。
