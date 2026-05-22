# bidsmart-dev 技能同步更新

## 来源
用户要求"按照sdd开发框架更新升级" bidsmart-dev 技能，使其与当前代码仓库 (v0.4.0) 保持一致。

## 发现路径
Path B — 文档修复，无需创建完整 spec。直接修技能。

## 对比分析：技能 vs 实际代码

### 1. API 端点表 — 缺少路由
技能列出 16 个端点，实际注册 22 个。缺失：
- POST /auth/register (用户注册)
- POST /auth/refresh (令牌刷新)
- GET /users/me (当前用户)
- GET /users/me/admin (管理员视图)
- POST /admin/keys/rotate (密钥轮换)
- GET /admin/keys/status (密钥状态)

### 2. API 路径参数名不一致
- 技能: `{id}` → 实际: `{project_id}` 或 `{document_id}`
- 实际更精确，技能应修正

### 3. API 表格式问题
- 路径列出现 `\*\*/auth/login\*\*` — Markdown 加粗被错误转义

### 4. FAQ "审查接口多文件支持" 描述错误
- 当前: "旧文件重新审查即可获得页码"
- 应: "接受 tender_doc_ids + bid_doc_ids 数组，后端合并多文件后统一审查"

### 5. 文件路径错误
- 技能: `src/routers/` → 实际: `src/platform/*/router.py` + `src/compliance/router.py`

## 建议
直接修复以上 5 处，技能版本号不变 (bidsmart-dev 版本 = BidSmart 版本 = 0.4.0)。
