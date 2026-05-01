# BidSmart — 测试策略

## 测试理念

- **TDD 优先**：所有新模块先写测试（RED），再实现（GREEN）
- **测试金字塔**：单元测试 > 集成测试 > 端到端测试
- **异步优先**：pytest-asyncio + httpx.AsyncClient

## 测试层次

### 1. 单元测试 (tests/)
| 文件 | 行数 | 覆盖模块 | 状态 |
|------|------|---------|------|
| test_auth.py | 209 | 认证：注册、登录、JWT、RBAC | ✅ |
| test_projects.py | 377 | 项目 CRUD、分页、权限 | ✅ |
| test_documents.py | 360 | 文件上传/下载、校验 | ✅ |
| test_security.py | 573 | 加密、审计、脱敏、密钥管理 | ✅ |
| test_middleware.py | 154 | 限流、访问日志 | ✅ |

**总计:** 1,674 行测试代码

### 2. 集成测试
- conftest.py 提供 fixtures：test app, async client, test DB
- 测试数据库使用独立文件（`test.db`），不污染生产数据
- 测试存储使用独立目录（`test-storage/`）

### 3. 端到端验证
- **手动**：浏览器访问 `8.219.137.176:39001`，执行完整工作流
- **验证项**：登录 → 创建项目 → 上传文件 → 文件审查 → AI 对话 → 知识库检索 → 管理面板操作

## 缺失测试

以下模块缺少完整测试覆盖（优先级排序）：

| 模块 | 缺失程度 | 优先级 |
|------|---------|--------|
| 知识库 | 无测试 | P1 |
| 管理后台 (用户CRUD) | 无测试 | P1 |
| 数据导出/导入 | 无测试 | P2 |
| AI 审查管线 | 无测试（依赖外部 API） | P2 |
| 文档解析 | 无测试 | P2 |
| 流式审查 (SSE) | 无测试 | P2 |

## 测试环境

### 本地
```bash
cd /root/bidsmart
/opt/hermes/.venv/bin/pytest tests/ -v
```

### 关键配置
```ini
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

## 测试数据管理

- 测试用户/项目在 fixture 中创建，teardown 中清理
- 不依赖生产数据库
- 文件测试使用小型 fixture 文件

## CI/CD 集成（待建）

理想流程：
```
git push → pytest → lint → alembic check → deploy
```
