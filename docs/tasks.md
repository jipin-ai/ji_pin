# 通睿 AI 安全网关 — 任务规划与里程碑

> 锚定文档：[产品需求规格说明书_V4.md](./产品需求规格说明书_V4.md)  
> 状态：草稿 · 待评审  
> 更新：2026-05-23

---

## 里程碑总览

```
V1.0 「可信内核」       V1.5 「AI 就绪」        V2.0 「规模化」
2026 Q3 (8-10周)       2026 Q4 (6-8周)        2027 Q1 (8-10周)
      │                      │                      │
  M1 ██ 基础设施          M9  ██ 本地 AI 推理      M13 ██ 企业版
  M2 ██ 网关节点          M10 ██ AI 安全闸门       M14 ██ 价值交换
  M3 ██ 脱敏引擎          M11 ██ SaaS 上线         M15 ██ 规模化
  M4 ██ 脚本引擎          M12 ██ 模板市场          M16 ██ 行业方案
  M5 ██ 任务系统
  M6 ██ 审计系统
  M7 ██ 管理控制台
  M8 ██ 集成验收
```

---

## 量级规划基准（设计决策锚点）

| 参数 | V1.0 MVP (3 节点) | V1.5 商业验证 (100 节点) | V2.0 满负载 (10K+ 节点) |
|------|-------------------|-------------------------|------------------------|
| 心跳 QPS | 0.1 | 3.3 | 333+ |
| PostgreSQL 连接数 | < 20 | < 200 (PgBouncer) | < 500 (集群) |
| 审计日志日增量 | < 10MB | < 500MB | 5-10GB (分区表) |
| 心跳批量写入 | ❌ | ✅ | ✅ (UPSERT) |
| 协调节点实例数 | 1 | 1 | 2-4 (水平扩展) |
| 证书管理 | 手动 | ACME 自动化 | Vault 企业级 |

---

## Phase 1: V1.0 「可信内核」(9 周)

### M1 — 基础设施 (Week 1-2)

**目标**：协调节点核心骨架就绪，PgBouncer 前置到位，单节点注册-心跳链路通。

| ID | 任务 | 文件范围 | 依赖 | 验收 |
|----|------|----------|------|------|
| M1.1 | 项目脚手架：FastAPI 入口 + 配置管理 + Dockerfile | `coordinator/main.py`, `coordinator/config.py`, `coordinator/Dockerfile`, `docker-compose.yml` | — | `uvicorn main:app` 启动，`/health` 返回 200 |
| M1.2 | PostgreSQL schema：nodes / tasks / task_steps / audit_logs 四表 DDL + Alembic | `coordinator/db/schema.py`, `coordinator/db/migrations/` | M1.1 | `alembic upgrade head` 创建所有表 |
| M1.3 | PgBouncer 连接池：部署配置 + FastAPI 异步引擎对接 | `coordinator/db/engine.py`, `docker-compose.yml` (pgbouncer service) | M1.2 | `SELECT 1` 走 PgBouncer，SHOW POOLS 可见连接复用 |
| M1.4 | Redis 集成：任务队列 + 结果缓存 + 心跳状态暂存 | `coordinator/cache.py`, `docker-compose.yml` (redis service) | M1.1 | Redis PING/PONG，key 读写验证 |
| M1.5 | mTLS 证书体系：自签 CA 脚本 + 节点证书签发 + 吊销列表 (CRL) | `coordinator/certs/ca.py`, `coordinator/certs/issue.py`, `coordinator/certs/crl.py` | M1.1 | 签发证书 → curl --cert 调 `/health` → 200；无证书 → 403 |
| M1.6 | 节点注册 API：POST /api/v1/nodes/register → 验证证书 → 分配 node_id → 返回令牌 | `coordinator/api/nodes.py` (register) | M1.3 M1.5 | 注册成功返回 node_id + token；重复名称 → 409；无效证书 → 401 |
| M1.7 | 心跳 API：POST /api/v1/nodes/{id}/heartbeat → 写入 DB + 更新状态 | `coordinator/api/nodes.py` (heartbeat) | M1.3 | 心跳写入后查询 nodes 表 status=ONLINE |
| M1.8 | JWT 认证中间件：登录 /auth/login → JWT 签发 → 全局依赖注入 | `coordinator/auth.py`, `coordinator/api/auth.py` | M1.1 | 无 Bearer → 401；过期 Token → 401；有效 → 放行 |
| M1.9 | RBAC 四角色模型：admin / operator / auditor / viewer → 权限装饰器 | `coordinator/auth.py` (roles) | M1.8 | viewer 调 POST /tasks → 403；admin 调 → 200 |
| M1.10 | 健康检查 + Prometheus 指标端点 | `coordinator/api/health.py`, `coordinator/metrics.py` | M1.1 | `/health` 返回 DB/Redis 连通状态；`/metrics` 暴露 Prometheus 格式 |

**M1 验收**：`docker-compose up` → 注册一个模拟节点 → 心跳连续 3 轮 → 控制台可见节点 ONLINE。

---

### M2 — 网关节点 (Week 2-3)

**目标**：节点侧部署就绪，Docker 沙箱隔离验证通过。

| ID | 任务 | 文件范围 | 依赖 | 验收 |
|----|------|----------|------|------|
| M2.1 | 节点脚手架：FastAPI + 配置 + Dockerfile + docker-compose | `node/main.py`, `node/config.py`, `node/Dockerfile`, `node/docker-compose.yml` | — | 节点启动 → 向协调节点注册成功 |
| M2.2 | 节点心跳客户端：定时 30s 上报 + 拉取待执行任务 | `node/heartbeat.py` | M1.7 | 协调节点可见持续心跳，3 次断连后标记 OFFLINE |
| M2.3 | Docker 沙箱运行时：创建隔离容器 (NET=none, read-only rootfs, 2核/4GB, no-new-privileges) | `node/sandbox.py` | M2.1 | 启动沙箱容器 → 容器内 `curl google.com` 失败 → `ping 8.8.8.8` 失败 |
| M2.4 | 沙箱挂载管理：只读 /data/ + 写入拦截 /output/ | `node/sandbox.py` (mounts) | M2.3 | 容器内 `echo test > /data/file` → Permission denied；`echo test > /output/result.json` → 经过拦截层 |
| M2.5 | 节点注销流程：停止心跳 → 等待任务清空 → 撤销证书 → 清理 | `node/deregister.py` | M2.1 M1.6 | 注销后协调节点状态=SUSPENDED，已签证书加入 CRL |
| M2.6 | 节点本地 SQLite：存储脱敏规则 + 任务历史 + 本地审计 | `node/db.py` | M2.1 | SQLite 文件创建，读写验证 |
| M2.7 | 节点健康检查：磁盘/内存/CPU 指标采集 + 自检脚本 | `node/health.py` | M2.1 | 返回 JSON 含 disk_usage/load_avg/memory_free |

**M2 验收**：节点容器启动 → 自动注册 → 心跳持续 → 沙箱 NET=none 验证 → 离线标记生效。

---

### M3 — 脱敏引擎 (Week 3-4)

**目标**：6 种脱敏方法实现，规则配置化，输出白名单生效，暴露级别硬约束生效。

| ID | 任务 | 文件范围 | 依赖 | 验收 |
|----|------|----------|------|------|
| M3.1 | 脱敏方法核心实现：pseudonymize / mask / bucket / generalize / aggregate / k_anonymize | `node/sanitizer/methods.py` | M2.1 | 每个方法单元测试：输入原始 → 输出脱敏后，不可逆 |
| M3.2 | 脱敏规则引擎：字段级匹配 (精确 > 类型 > 正则) + 优先级排序 + 默认拦截 | `node/sanitizer/engine.py` | M3.1 | 配置 3 条规则 → 输入含匹配字段的 JSON → 匹配字段被脱敏，未匹配被拦截 |
| M3.3 | 规则配置 API：PUT /local/v1/rules → 写入本地 SQLite → 即时生效 | `node/api/rules.py` | M3.2 M2.6 | 修改规则后下一任务使用新规则 |
| M3.4 | 输出白名单机制：脚本声明 expected_output_fields → 仅放行白名单内字段 | `node/sanitizer/whitelist.py` | M3.2 | 脚本声明 ["score"] → 输出 {"score": 85, "revenue": 100M} → 仅 score 留，revenue 被拦截 |
| M3.5 | 暴露级别控制：L0/L1/L2 字典 + 任务校验 + 拒绝逻辑 (403) | `node/sanitizer/exposure.py` | M3.2 | 节点配 L0 → 任务要 L2 → 返回 403 + 明确差异信息 |
| M3.6 | 脱敏日志生成：sanitization_log [{field, method, original_hash, preview}] | `node/sanitizer/logger.py` | M3.2 | 每次脱敏后生成完整日志，随结果回传 |
| M3.7 | 规则配置 Web UI（控制台内嵌）：规则列表 + 添加/编辑/删除 + 预览 | 前端组件：`console/src/pages/nodes/SanitizationRules.tsx` | M3.3 | UI 增删改规则 → 节点验证生效 |

**M3 验收**：配置 `entity_name` 伪名化 + `revenue` 分档 → 输入原始数据 → 输出中名称已 Token 化、营收已分档 → 节点侧抓包验证原始值不出现。

---

### M4 — 脚本引擎 (Week 4-5)

**目标**：沙箱内脚本执行，上传签名，静态审查，恶意脚本被拦截。

| ID | 任务 | 文件范围 | 依赖 | 验收 |
|----|------|----------|------|------|
| M4.1 | 脚本规范定义：Python 3.11+ `def analyze(input_path, output_path, params) -> dict` | `node/script_engine/spec.py` | M2.3 | 规范文档，示例脚本 |
| M4.2 | 沙箱脚本执行器：Docker 容器执行 → 超时 300s → 捕获 stdout/stderr | `node/script_engine/executor.py` | M4.1 M2.3 | 合法脚本 → 正常执行返回结果；死循环 → 300s 后 kill |
| M4.3 | 脚本上传 + SHA256 签名：API POST /api/v1/scripts → 文件存储 + 哈希 | `coordinator/api/scripts.py` | M1.8 | 上传 .py → 返回 script_id + sha256 |
| M4.4 | 静态安全审查：AST 扫描 → 禁止 import subprocess/socket/os.system/eval/exec | `coordinator/scripts/auditor.py` | M4.3 | 上传含 `os.system("rm -rf /")` 的脚本 → 审查 FAILED |
| M4.5 | 预装依赖管理：pandas/numpy/scikit-learn/jieba/openpyxl + requirements.txt 白名单 | `node/script_engine/deps.py` | M4.2 | requirements.txt 含 Flask → 拒绝；含 pandas==2.0 → 允许 |
| M4.6 | 脚本版本管理：保留最近 5 版本 + 回滚 | `coordinator/scripts/versions.py` | M4.3 | 上传 6 次 → 最旧版本被归档 |

**M4 验收**：上传合法供应链评估脚本 → 静态审查通过 → 沙箱执行成功 → 上传含 `subprocess` 的恶意脚本 → 审查拦截。

---

### M5 — 任务系统 (Week 5-6)

**目标**：分析任务全链路——创建→校验→分发→执行→脱敏→结果回传→聚合。

| ID | 任务 | 文件范围 | 依赖 | 验收 |
|----|------|----------|------|------|
| M5.1 | 任务创建 API：POST /api/v1/tasks → 校验节点在线/脚本签名/暴露级别 → 生成 task_id | `coordinator/api/tasks.py` (create) | M1.9 M4.3 M3.5 | 创建成功返回 task_id；节点离线 → 拒绝；暴露级别不足 → 403 |
| M5.2 | 任务分发器：串行/并行模式 → mTLS 加密传输脚本+参数到各节点 | `coordinator/tasks/dispatcher.py` | M5.1 M2.2 | 并行任务 → 3 节点同时收到；串行 → 按序执行 |
| M5.3 | 任务状态机：PENDING→VALIDATING→DISPATCHING→RUNNING→AGGREGATING→COMPLETED | `coordinator/tasks/state.py` | M5.1 | 状态转换符合 SRS 状态图 |
| M5.4 | 沙箱任务执行对接：节点收到分发 → 启动沙箱 → 执行脚本 → 脱敏 → 回传 | `node/task_runner.py` | M5.2 M4.2 M3.2 | 端到端：创建任务 → 节点执行 → 脱敏结果回传 |
| M5.5 | 结果回传 API：POST /api/v1/nodes/{id}/tasks/{step}/result (含 sanitization_log) | `coordinator/api/tasks.py` (result) | M5.4 M3.6 | 协调节点收到脱敏结果 + 完整日志 |
| M5.6 | 聚合器：协调节点运行 aggregator.py → 输出综合评分 + completeness_score | `coordinator/tasks/aggregator.py` | M5.5 | 2 节点结果 → 聚合输出 JSON 含 per_node_details |
| M5.7 | 离线容错：节点离线 → 任务标记 PARTIAL → completeness_score = 实际/目标 | `coordinator/tasks/state.py` (partial) | M5.3 | 3 节点任务中 1 个离线 → PARTIAL，完整性 66% |
| M5.8 | 任务管理 API：列表 GET /api/v1/tasks (分页+筛选+排序) / 详情 / 取消 / 重跑 | `coordinator/api/tasks.py` (list/detail/cancel/retry) | M5.3 | 分页 20 条 → 筛选 status=RUNNING → 排序 created_at DESC |
| M5.9 | 任务管理 Web UI：甘特图 + 脱敏日志逐条展示 + 聚合预览 | 前端：`console/src/pages/tasks/` | M5.8 | UI 可见任务全链路时间线、每节点脱敏详情 |

**M5 验收**：创建含 2 个节点的并行任务 → 两节点本地沙箱执行 → 脱敏日志完整 → 聚合报告正确 → 审计日志可追溯全链路。

---

### M6 — 审计系统 (Week 6-7)

**目标**：全链路审计日志 + HMAC 防篡改 + 客户自验证工具。

| ID | 任务 | 文件范围 | 依赖 | 验收 |
|----|------|----------|------|------|
| M6.1 | 审计日志中间件：所有 API 调用自动记录 → actor/action/target/detail/ip | `coordinator/audit/middleware.py` | M5.1 | 调 POST /tasks → audit_logs 表新增 1 条 |
| M6.2 | HMAC 签名：每条审计日志 SHA256-HMAC(secret, log_content) → 存储签名 | `coordinator/audit/signer.py` | M6.1 | 日志写入后 hmac_signature 字段非空 |
| M6.3 | 审计日志查询 API：GET /api/v1/audit-logs → 时间/角色/操作/节点/任务筛选 + 分页 | `coordinator/api/audit.py` | M6.1 | 筛选 actor=admin → 返回该用户所有操作 |
| M6.4 | 审计导出：CSV + JSON 格式导出 → 含 HMAC 签名 | `coordinator/audit/exporter.py` | M6.2 M6.3 | 导出 JSON → 包含完整字段 + hmac_signature |
| M6.5 | HMAC 验证工具：独立脚本验证导出日志的完整性 | `coordinator/audit/verify.py` | M6.2 | 篡改日志 1 字节 → verify 失败 |
| M6.6 | gateway-verify CLI：一键检查沙箱隔离/网络策略/脱敏规则/审计日志 | `node/verify.py` | M2.3 M3.2 M6.2 | 运行 → 全部通过；关闭沙箱隔离 → 返回"不通过：NET 策略未生效" |
| M6.7 | 审计日志 Web UI：筛选面板 + 日志表格 + 导出按钮 + HMAC 验证按钮 | 前端：`console/src/pages/audit/` | M6.3 M6.4 | UI 筛选 → 表格更新 → 导出 CSV 可读 → HMAC 验证按钮返回"通过" |

**M6 验收**：执行 3 个任务 → 导出审计日志 → 包含完整操作链路 (创建-分发-执行-脱敏-回传-聚合) → HMAC 验证通过 → 篡改后验证失败。

---

### M7 — 管理控制台 (Week 7-8)

**目标**：五大页面全部可用，设计语言统一，dark theme 贯穿。

| ID | 任务 | 文件范围 | 依赖 | 验收 |
|----|------|----------|------|------|
| M7.1 | 前端脚手架：React + TypeScript + Vite + 路由 + 布局 + 主题 | `console/` (完整初始化) | — | `npm run dev` → dark theme 控制台首页 |
| M7.2 | 仪表盘页面：全局概览卡片 (在线节点/今日任务/成功率) + 趋势图 + 告警卡片 | `console/src/pages/dashboard/` | M7.1 M1.10 | 指标实时刷新，离线节点告警红色高亮 |
| M7.3 | 节点管理页面：列表 + 详情 (心跳时序图/资源用量/脱敏规则/任务历史) | `console/src/pages/nodes/` | M7.1 M2.7 M3.7 | 点击节点 → 展开详情面板 |
| M7.4 | 任务管理页面：列表 + 详情甘特图 + 脱敏日志展开 + 聚合预览 | `console/src/pages/tasks/` | M7.1 M5.9 | 甘特图可见每节点执行耗时柱状条 |
| M7.5 | 审计日志页面：筛选面板 + 日志表格 + 导出 + HMAC 验证 | `console/src/pages/audit/` | M7.1 M6.7 | 与 M6.7 整合 |
| M7.6 | 系统设置页面：证书管理/角色配置/全局参数/版本信息 | `console/src/pages/settings/` | M7.1 M1.5 M1.9 | 可签发新节点证书、修改角色权限 |
| M7.7 | 登录页 + 路由守卫：未登录 → 跳转登录页 | `console/src/pages/login/`, `console/src/router/` | M7.1 M1.8 | 未登录访问 /dashboard → 跳转 /login |
| M7.8 | 一键部署验证：docker-compose.yml 包含所有服务 → 30s 内控制台可访问 | `docker-compose.yml` (根目录) | M7.1-M7.7 | `docker-compose up -d` → 30s 内 `http://localhost:3000` 可访问 |

**M7 验收**：所有页面可访问，仪表盘数据实时，节点管理可操作，30s 全栈启动。

---

### M8 — 集成验收 (Week 8-9)

**目标**：13 项验收标准 (AC1-AC13) 全部通过，渗透测试，bug 清零。

| ID | 任务 | 文件范围 | 依赖 | 验收 |
|----|------|----------|------|------|
| M8.1 | AC1-AC8 自动化测试脚本：Pytest + Playwright 覆盖功能验收 | `tests/acceptance/test_ac1_8.py` | M1-M7 | 8 项全部 PASS |
| M8.2 | AC9-AC13 信任验收脚本：gateway-verify / 抓包 / 预览 / 审计 | `tests/acceptance/test_ac9_13.py` | M6.6 M7.5 | 5 项全部 PASS |
| M8.3 | 端到端集成测试：3 节点环境 → 供应链评估场景全链路 | `tests/e2e/test_supply_chain.py` | M8.1 | 3 节点 + 协调节点 → 任务创建到聚合报告完整 |
| M8.4 | 性能基准测试：M1 基础设施指标采集 | `tests/performance/` | M8.3 | 节点注册 ≤ 10s，任务分发 ≤ 5s，脱敏吞吐 ≥ 10K 字段/s |
| M8.5 | 渗透测试 (外部) | — | M8.3 | 第三方渗透测试报告 → 无高危漏洞 |
| M8.6 | 文档：部署手册 + API 文档 (OpenAPI) + 管理员手册 | `docs/` | M8.3 | 3 份文档齐全 |
| M8.7 | Bug 清零 + 代码清理 | 全项目 | M8.5 | eslint/pytest 零报错 |

**M8 验收**：AC1-AC13 全部通过，渗透测试无高危，3 份文档齐全，30s 全栈启动。

---

## Phase 2: V1.5 「AI 就绪」(7 周)

> **注：V1.5 为框架级规划，实施前需细化到文件级。**

### M9 — 本地 AI 推理 (Week 10-12)

| ID | 任务 | 关键增量 |
|----|------|----------|
| M9.1 | GGUF 模型加载：llama-cpp-python → gateway.infer(prompt, model="local") | 节点侧可加载 GGUF 文件并推理 |
| M9.2 | ONNX 模型支持：onnxruntime → 评分/分类/异常检测 | 支持 sklearn 导出 ONNX 在沙箱内运行 |
| M9.3 | 模型管理 API：上传/签名/版本/删除 | 模型绑定节点，SHA256 签名 |
| M9.4 | 模型调用审计：每次 infer() 记录 prompt/output 到本地日志 | 完整调用链可追溯 |
| M9.5 | 推理性能优化：量化 + 批处理 + 流式输出 | 单次推理 ≤ 5s（7B 模型） |
| M9.6 | 模型内存管理：LRU 缓存 + 卸载策略 | 不超过节点内存配额的 70% |

**M9 验收**：上传 Llama-3 7B GGUF → 沙箱脚本调用 gateway.infer() → 返回推理结果 → 审计日志记录完整。

### M10 — AI 安全闸门 (Week 12-13)

| ID | 任务 | 关键增量 |
|----|------|----------|
| M10.1 | 脱敏闸门：调用 infer() 前强制 apply_sanitization()，跳过直接拒绝 | 原始数据永不到达模型 |
| M10.2 | Prompt 安全扫描：检测"解密/还原/原始数据/真实姓名"等绕过语 → 拦截 | 恶意 prompt 被拒绝 |
| M10.3 | 输出二次校验：正则扫描 AI 输出中的身份证号/手机号/邮箱格式 | 模型幻觉输出含疑似原始数据 → 拦截 |
| M10.4 | 模型隔离加固：GGUF 推理在沙箱 NET=none 内 | 防止模型隐蔽通道外泄 |
| M10.5 | token 限制：单次推理 max_tokens ≤ 4096 | 防止大输出绕过校验 |

**M10 验收**：向模型传入含原始身份证号的 prompt → 预处理拦截 → 脚本收到 "sanitization required" 错误。推理输出含手机号格式 → 后处理拦截。

### M11 — SaaS 上线 (Week 13-14)

| ID | 任务 | 关键增量 |
|----|------|----------|
| M11.1 | 多租户架构：tenant_id 隔离 → 数据/节点/任务/审计按租户分 | tenant_id 贯穿所有模型 |
| M11.2 | 云部署：协调节点容器化 → Cloud Run / ECS 部署 | 公网可访问 api.tongrui.com |
| M11.3 | 计费系统：按节点数/任务量/数据量计量 → Stripe/支付宝集成 | 月底生成账单 |
| M11.4 | 注册/登录/订阅流程：自助注册 → 创建 workspace → 邀请节点 | 10 分钟内完成注册到第一个任务 |
| M11.5 | 监控告警：PagerDuty/Slack 集成 | 协调节点异常 → 运维告警 |

**M11 验收**：公网用户自助注册 → 创建 workspace → 邀请 3 个节点 → 执行首个分析任务。

### M12 — 模板市场 (Week 14-16)

| ID | 任务 | 关键增量 |
|----|------|----------|
| M12.1 | 10+ 分析模板：供应链/风控/经营分析/异常检测/相似度/趋势/聚类 | 预置模板可直接选用 |
| M12.2 | 模板审核流程：上传 → AST 扫描 → 人工审核 → 上架 | 社区贡献 → 审核通过上架 |
| M12.3 | 模板评分与评论 | 使用后可评价 |

**M12 验收**：模板市场可浏览/搜索/一键使用 → 选择供应链模板 → 自动填入默认参数 → 发起任务。

### M12.5 — 心跳批量写入 + 审计日志分区 + ACME 证书

> **从 M1 量级分析补入**

| ID | 任务 | 说明 |
|----|------|------|
| M12.5a | 心跳批量 UPSERT：替代逐条 UPDATE | 100 节点以上性能必需 |
| M12.5b | 审计日志 date 分区表 + 90 天自动清理 | 防止 TB 级审计表拖垮 DB |
| M12.5c | ACME 证书自动管理：替代手动签发 | 支持 100+ 节点规模 |

---

## Phase 3: V2.0 「规模化」(9 周)

> **注：V2.0 为框架级规划，实施前需细化到文件级。**

### M13 — 企业版 (Week 17-19)

| ID | 任务 | 关键增量 |
|----|------|----------|
| M13.1 | 私有化部署包：一键安装脚本 + 离线镜像 | 客户内网无公网环境可用 |
| M13.2 | 企业 SSO：SAML/OIDC → Okta/Azure AD/飞书 | 企业统一身份认证 |
| M13.3 | 高级 RBAC：自定义角色 + 字段级权限 | 超越四角色模型 |
| M13.4 | SIEM 集成：Splunk/ELK → syslog/CEF 格式输出 | 审计日志入企业 SIEM |
| M13.5 | 国密套件：SM2/SM4/TLS GM → 等保合规 | 政府/军工客户可用 |
| M13.6 | 第三方安全集成：360 / 奇安信 → WAF + 威胁情报 | 增强外围防御 |

### M14 — 价值交换 (Week 19-21)

| ID | 任务 | 关键增量 |
|----|------|----------|
| M14.1 | 贡献评分引擎：基于数据维度/质量/频率的加权评分 | 每次任务后更新节点贡献分 |
| M14.2 | 价值仪表盘：对比基准/盲点揭示/协同增益/贡献权重 | 每个节点看到自己的协作 ROI |
| M14.3 | 互惠计量：提供次数 vs 消费次数 → 鼓励平衡参与 | 消耗型节点限流 |
| M14.4 | 渐进信任机制：协作历史积累 → 自动协商暴露级别 | 从 L0 起步，信任积累后升级 |

### M15 — 规模化 (Week 21-24)

| ID | 任务 | 关键增量 |
|----|------|----------|
| M15.1 | 协调节点集群：2-4 实例水平扩展 + Redis 共享状态 | 支持 10K+ 节点 |
| M15.2 | Kafka 消息队列：解耦任务分发/心跳/结果回传 | 替代 Redis pub/sub |
| M15.3 | WebSocket 推送：替代节点轮询 GET /tasks/pending | 10K 节点不再空转 HTTP |
| M15.4 | 灾难恢复：主备切换 + RTO ≤ 30min | 协调节点不可用 → 自动切换 |
| M15.5 | 性能测试：10K 节点仿真 + 500 并发任务 | 全链路压力测试 |
| M15.6 | Vault 企业级证书管理：替代 ACME | 支持多级 CA 链 |

### M16 — 行业方案 (Week 24-26)

| ID | 任务 | 关键增量 |
|----|------|----------|
| M16.1 | 供应链方案包：预置评估模型 + 行业基准数据 + 报告模板 | 开箱即用 |
| M16.2 | 金融风控方案包：反欺诈/信用评估/关联交易检测 | 合规预审 |
| M16.3 | 医疗科研方案包：HIPAA 合规 + 多中心临床试验模板 | 脱敏规则符合 HIPAA |

---

## 依赖关系图 (V1.0 完整)

```
M1 (基础设施)
├─ M1.1 ──► M1.2 ──► M1.3
├─ M1.5 ──► M1.6 (证书 → 注册)
├─ M1.8 ──► M1.9 (JWT → RBAC)
└─ M1.10

M2 (网关节点)
├─ M2.1 ──► M2.3 ──► M2.4 (沙箱)
├─ M2.2 ──► 对接 M1.7 (心跳)
└─ M2.6 ──► 对接 M3.3

M3 (脱敏引擎)  ← 依赖 M2.1
M4 (脚本引擎)  ← 依赖 M2.3
M5 (任务系统)  ← 依赖 M3 + M4 + M1.9
M6 (审计系统)  ← 依赖 M5 + M2.3
M7 (管理控制台) ← 依赖 M5 + M6 + M1.10
M8 (集成验收)  ← 依赖 M1-M7 全部

M3 与 M4 可并行。
M6 与 M7 可并行（前端并行开发）。
```

---

## 风险登记

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| mTLS 1.3 证书链兼容性问题（不同 Docker 版本） | 中 | 高 | M1.5 早期验证 curl --cert，避免到最后才发现 |
| 沙箱逃逸漏洞 | 低 | 极高 | 每季度第三方渗透测试，关注 CVE |
| DeepSeek/外部 LLM API 不可用 | 低 | 中 | 降级为无 AI 模式，不影响核心脱敏功能 |
| 审计日志日增超预期 → PostgreSQL 性能下降 | 中 | 中 | M12.5b 提前到 V1.5，V1.0 设置 90 天硬删除 |
| PgBouncer 连接池配置不当导致连接泄漏 | 中 | 高 | M1.3 配连接超时 + 泄漏检测 |

---

## 工时估算 (V1.0)

| 里程碑 | 任务数 | 预估人天 | 并行策略 |
|--------|--------|----------|----------|
| M1 | 10 | 8-10 | 单线 |
| M2 | 7 | 5-7 | 可后半段与 M1 并行 |
| M3 | 7 | 5-7 | 与 M4 并行 |
| M4 | 6 | 5-7 | 与 M3 并行 |
| M5 | 9 | 7-9 | 单线（依赖 M3+M4） |
| M6 | 7 | 5-7 | 与 M7 并行 |
| M7 | 8 | 6-8 | 与 M6 并行 |
| M8 | 7 | 5-7 | 单线 |
| **合计** | **61** | **46-62 人天** | **9 周 (2 人)** |

---

## 下一步

1. 评审任务拆解粒度 → 确认或调整
2. 确定开发团队规模 → 调整工时
3. 进入 SDD 技术设计阶段 → 产出设计文档
