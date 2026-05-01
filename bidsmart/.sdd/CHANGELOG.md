# BidSmart — 变更日志 (CHANGELOG)

## v0.7.7 (2026-05-01) — 里程碑发布

### 新增
- SDD 框架全面梳理：从 3 个 spec 扩展到 13 个 spec 目录
- Steering 层：新增 roadmap.md、risk-register.md、glossary.md
- Spec: admin-panel、knowledge-base、security-layer、auth-system、documents-pipeline、projects-crud、middleware-layer、parsing-engine、storage-abstraction、database-models
- 跨模块文档：testing-strategy.md、deployment-runbook.md、SDD-INDEX.md

### 修复
- 数据库恢复流程文档化（alembic + seed + must_change_password 补列）
- passlib/bcrypt 版本兼容方案
- systemd 服务管理迁移（fuser -k → systemctl restart）
- 备份排除路径陷阱文档化

### 运维
- systemd bidsmart.service 管理（Restart=always）
- 双备份策略（ECS + 本地 Mac）

## v0.7.6 (2026-04-30)

### 变更
- 知识库面板重设计：三卡片分区布局（检索/上传/列表）
- 统一 input/select 尺寸
- 自定义下拉箭头
- 全宽上传按钮
- 补全 .kb-* CSS 类系统
- 修复 adminDataPanel 缺闭合导致 KB 面板隐藏
- 登录页回溯至原版

## v0.7.5 (2026-04-30)

### 变更
- 知识库 CSS 补充：kb-upload-zone 虚线框、kb-search-input/btn、kb-info-box
- 文件选取器美化 (::file-selector-button)

## v0.7.3 (2026-04-29)

### 变更
- Anthropic 暖羊皮纸 UI 重设计
- 底色 #f5f4ed + accent #c96442
- 按钮 hover/active 反馈

## v0.7.2 (2026-04-29)

### 新增
- 新增用户角色下拉框（含投标书编辑 bid_editor）
- 首次登录强制修改密码
- 补装 passlib 依赖

## v0.7.1 (2026-04-28)

### 新增
- 知识库模块：BGE 向量化 + FAISS 本地检索
- AI 对话自动注入知识库上下文
- 管理面板知识库子面板

## v0.6.1 (2026-04-27)

### 新增
- 管理后台骨架：⚙️管理 Tab（仅 admin 可见）
- 用户 CRUD（二次密码确认 + 审计）
- 数据导出/导入 + 系统配置面板

## v0.5.3 (2026-04-26)

### 新增
- 对照表 💬追问按钮（点击条款自动填入 AI 对话框）

## v0.5.2 (2026-04-25)

### 新增
- 对照表 💬追问按钮

## v0.5.1 (2026-04-24)

### 新增
- AI 对话收窄（非标书问题拒绝回答）
- 会话框动态收起/展开（60s 自动收起）
- 过期项目自动清理（cron 每天凌晨 3 点）

## v0.5.0 (2026-04-23)

### 新增
- 逐条流式审查（SSE + 前端逐行追加 + 确认/忽略）

## v0.4.0 (2026-04-22)

### 新增
- 多文件合并审查 + 权重三级分类

## v0.3.0 (2026-04-21)

### 新增
- 黄金比例布局 + 对照表

## v0.2.0 (2026-04-20)

### 变更
- 项目管理 UX 重构

## v0.1.0 (2026-04-19)

### 新增
- 初始版本：基础标书审查功能
