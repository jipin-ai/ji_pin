# 通睿 AI 安全网关 — 独立审计报告

> 日期：2026-05-23 | 审计范围：V1.0 M1 基础设施 (commit e848636)  
> 审计员：Hermes Agent (sdd-project-audit)  
> 规范依据：产品需求规格说明书_V4.md · tasks.md

---

## 1. 概览

| 指标 | 值 |
|------|-----|
| Python 源文件 | 13 |
| 总代码行数 | 891 |
| 测试文件 | **0** |
| 测试行数 | **0** |
| Ruff lint 状态 | ✅ 零错误 |
| Ruff format 状态 | ✅ 已格式化 |
| 已声明依赖 | 13 包 |
| 实际导入依赖 | 6 包 (其余为运行时/CLI 依赖) |

---

## 2. 规约对照分析

### 2.1 M1 任务完成度

| 任务 | 要求 | 实际 | 状态 |
|------|------|------|------|
| M1.1 项目脚手架 | FastAPI + config + Dockerfile | ✅ main.py, config.py, Dockerfile, docker-compose.yml | MET |
| M1.2 数据库 Schema | 4 表 (tr_nodes/tr_tasks/tr_task_steps/tr_audit_logs) | ✅ db/models.py, db/engine.py, db/init_db.py | MET |
| M1.3 PgBouncer 连接池 | 连接池配置 | ⚠️ 降级为 SQLAlchemy pool=20 (V1.0 3节点充足) | PARTIAL — 已记录 defer |
| M1.4 Redis 集成 | 任务队列 + 结果缓存 + 心跳状态 | ✅ cache.py (queue/cache/heartbeat/node_status) | MET |
| M1.5 mTLS 证书体系 | CA + 签发 + CRL | ✅ certs.py (generate_ca/issue_cert/revoke_cert/verify_cert) | MET |
| M1.6 节点注册 API | POST /api/v1/nodes/register | ✅ api/nodes.py → 返回 node_id+token | MET |
| M1.7 心跳 API | POST /api/v1/nodes/{id}/heartbeat | ✅ api/nodes.py → 写 DB+Redis | MET |
| M1.8 JWT 认证 | 登录 → JWT 签发 | ✅ api/auth.py + auth.py (create_token/decode_token) | MET |
| M1.9 RBAC 四角色 | admin/operator/auditor/viewer | ✅ auth.py require_role() 装饰器 | MET |
| M1.10 健康检查 | /health with DB+Redis status | ✅ api/health.py (DB SELECT 1 + Redis PING) | MET |

**M1 完成度：9/10 MET · 1/10 PARTIAL (PgBouncer deferred)** 

### 2.2 SRS 需求覆盖

| SRS 需求 | 覆盖状态 | 说明 |
|----------|---------|------|
| FR-1.1 节点注册 | ✅ MET | api/nodes.py register_node() |
| FR-1.2 节点心跳 | ✅ MET | api/nodes.py node_heartbeat() |
| FR-1.3 节点注销 | ✅ MET | api/nodes.py deregister_node() |
| FR-6 通信安全基础设施 | ⚠️ PARTIAL | mTLS CA 已就绪，但 HTTP 层面尚未启用 mTLS (V1.0 dev mode) |
| FR-6 JWT Token 12h | ✅ MET | jwt_expire_minutes=720 |
| FR-6 RBAC 四角色 | ✅ MET | auth.py require_role() |

---

## 3. 安全审计

### 3.1 硬编码密钥扫描

| 检查项 | 结果 |
|--------|------|
| API Key / Secret 硬编码 | ✅ 无 — JWT secret 使用占位符 `change-me-in-production`，由 `.env` 覆盖 |
| 数据库密码 | ⚠️ `.env` 含明文密码 (本地开发环境可接受) |
| `os.system` / `shell=True` | ✅ 无 — certs.py 使用 `subprocess.run()` 列表形式 (无 shell 注入) |
| `eval` / `exec` | ✅ 无 |
| `pickle` | ✅ 无 |

### 3.2 认证授权

| 检查项 | 结果 |
|--------|------|
| JWT 算法 | ✅ HS256 |
| Token 过期 | ✅ 12h (720min) |
| 登录任意密码可登录 | ⚠️ V1.0 dev mode — 接受任意非空凭据 (tasks.md 明确注明 V1.5 替换) |
| RBAC 装饰器 | ✅ 所有敏感端点已加 `require_role()` |

### 3.3 输入验证

| 检查项 | 结果 |
|--------|------|
| Pydantic 模型 | ✅ RegisterRequest, HeartbeatRequest, LoginRequest |
| SQL 注入 | ✅ SQLAlchemy ORM (参数化查询) |

### 安全评分：7/10

**扣分项**：
- Dev mode 登录弱校验 (-1)
- HTTP 无 mTLS (V1.0 dev mode 可接受, -1)
- `.env` 含明文密码 (-1)

---

## 4. 代码质量评分

| 文件 | 架构 | 命名 | DRY | 错误处理 | 类型注解 | 文档 | 总分 |
|------|------|------|-----|----------|----------|------|------|
| `main.py` | 8 | 8 | 8 | 6 | 7 | 8 | **7.5** |
| `config.py` | 9 | 9 | 9 | 7 | 9 | 8 | **8.5** |
| `db/engine.py` | 8 | 8 | 8 | 7 | 8 | 7 | **7.7** |
| `db/models.py` | 9 | 9 | 9 | 8 | 9 | 8 | **8.7** |
| `db/init_db.py` | 7 | 7 | 8 | 5 | 5 | 6 | **6.3** |
| `cache.py` | 8 | 8 | 7 | 6 | 8 | 7 | **7.3** |
| `certs.py` | 8 | 8 | 7 | 7 | 7 | 8 | **7.5** |
| `auth.py` | 8 | 8 | 8 | 8 | 8 | 8 | **8.0** |
| `api/auth.py` | 8 | 8 | 8 | 7 | 8 | 7 | **7.7** |
| `api/nodes.py` | 7 | 7 | 6 | 6 | 7 | 7 | **6.7** |
| `api/health.py` | 8 | 8 | 8 | 8 | 8 | 7 | **7.8** |
| **加权平均** | | | | | | | **7.6/10** |

### 质量亮点
- `db/models.py`：ORM 模型规范，UUID 主键 + 时间戳 + JSONB + 关系映射完整
- `config.py`：Pydantic Settings + `extra="ignore"` 防 Docker 环境变量污染
- `auth.py`：JWT + RBAC 解耦良好，依赖注入模式正确
- `certs.py`：子进程安全 (列表形式无 shell 注入)

### 质量改进点
- `api/nodes.py`：重复的 `from db.engine import AsyncSessionLocal` 在 3 个函数内联导入 → 应提到文件顶部
- `cache.py`：函数签名缺少返回值类型注解 (如 `-> None`, `-> dict | None`)
- `db/init_db.py`：无错误处理，create_all 失败静默

---

## 5. 基础设施验证

| 检查项 | 状态 |
|--------|------|
| PostgreSQL 运行 | ✅ pg_isready → accepting connections |
| Redis 运行 | ✅ redis-cli ping → PONG |
| 数据库表已创建 | ✅ 4 表 (tr_nodes/tr_tasks/tr_task_steps/tr_audit_logs) |
| Alembic 迁移 | ⚠️ 已配置但无法使用 (共享 DB 版本链冲突)，降级为 create_all |
| Docker | ⚠️ docker-compose.yml 存在但不可用 (机器无 Docker) |
| 裸机启动 | ✅ `uvicorn main:app --port 8001` 正常启动 |
| .env 配置 | ⚠️ 被 .gitignore 排除 (正确)，但 `.env.example` 存在 ✅ |

---

## 6. 测试审计

| 指标 | 值 |
|------|-----|
| 测试文件 | 0 |
| 测试函数 | 0 |
| 测试覆盖率 | 0% |

**🔴 测试维度：0/10 — 自动 FAIL**

SDD 框架要求 TDD，当前零测试不可接受。尽管 V1.0 处于开发早期且 M1 多为骨架代码，但至少需要：
- `test_config.py`：Settings 加载验证
- `test_auth.py`：JWT 签发/解码/过期
- `test_health.py`：/health 端点验证
- `test_nodes.py`：注册/心跳/注销 API 测试

---

## 7. 综合评分

| 维度 | 得分 | 权重 | 加权 |
|------|------|------|------|
| 规约覆盖 | 9/10 | 25% | 2.25 |
| 安全 | 7/10 | 20% | 1.40 |
| 代码质量 | 7.6/10 | 25% | 1.90 |
| 基础设施 | 8/10 | 15% | 1.20 |
| 测试 | **0/10** | 15% | **0.00** |
| **综合** | | | **6.75/10** |

评级：**C+ — 代码骨架质量良好，但零测试拉低了整体分数。**

---

## 8. 优先修复清单

### 🔴 Blocking (P0) — 必须在 M2 开始前修复

| # | 问题 | 文件 | 修复 |
|---|------|------|------|
| 1 | **零测试** | — | 添加 5 项最小测试套件 (config/auth/health/nodes/registration) |
| 2 | `api/nodes.py` 重复内联导入 `AsyncSessionLocal` | `api/nodes.py` | 提取到文件顶部的依赖注入或模块级 import |

### 🟡 High (P1) — 下一里程碑内修复

| # | 问题 | 文件 | 修复 |
|---|------|------|------|
| 3 | 登录弱校验 (dev mode) | `api/auth.py` | 至少添加 admin 固定密码验证 |
| 4 | `db/init_db.py` 无错误处理 | `db/init_db.py` | 添加 try/except + 日志 |
| 5 | `cache.py` 缺少部分返回值类型注解 | `cache.py` | 添加 `-> None` / `-> dict | None` |

### 🟢 Medium (P2) — V1.0 内修复

| # | 问题 | 文件 | 修复 |
|---|------|------|------|
| 6 | docker-compose.yml 不可用 | `docker-compose.yml` | 移除或标注为"参考，当前裸机运行" |
| 7 | Alembic 配置存在但无法使用 | `alembic.ini` + `db/migrations/` | 添加注释说明共享 DB 限制 |

---

## 9. 审计结论

M1 基础设施的代码骨架质量良好，架构清晰，安全基线基本到位。**最大的问题是零测试** —— 这在 SDD 框架下属于必须立即修复的 blocking 项。其余问题均为低风险改进。

**推荐下一步**：先补最小测试套件（~30 分钟），再进入 M2 网关节点开发。
