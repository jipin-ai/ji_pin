# 贡献指南 / Contributing to BidSmart

感谢你考虑为 BidSmart 做贡献！/ Thank you for considering contributing to BidSmart!

## 行为准则 / Code of Conduct

- 尊重所有贡献者 / Respect all contributors
- 建设性讨论，不人身攻击 / Constructive discussion, no personal attacks
- 中文或英文都可以 / Chinese or English are both welcome

## 如何贡献 / How to Contribute

### 报告 Bug / Reporting Bugs

在 GitHub Issues 中创建 issue，包含：
- 版本号（登录页左下角可见）
- 复现步骤
- 预期 vs 实际行为
- 截图（如有）

### 提交代码 / Submitting Code

1. **Fork** 本仓库
2. 创建 feature 分支：`git checkout -b feature/your-feature`
3. 遵循项目架构：
   - 后端：FastAPI router → service → model 分层
   - 前端：所有代码在 `static/index.html` 单文件中
   - 异步优先，所有 DB 操作用 async SQLAlchemy
4. 写测试（`tests/` 目录，pytest + httpx）
5. 确保现有测试通过：`pytest tests/ -v`
6. 提交 PR，描述变更内容和原因

### 开发环境 / Development Setup

```bash
# 克隆仓库 / Clone
git clone https://github.com/jipin-ai/bidsmart.git
cd bidsmart

# 创建虚拟环境 / Create venv
python3.11 -m venv .venv
source .venv/bin/activate

# 安装依赖 / Install dependencies
pip install -r requirements.txt

# 初始化数据库 / Initialize database
alembic upgrade head

# 创建种子用户 / Seed users
python3 -c "
import sqlite3, bcrypt
from datetime import datetime
db = sqlite3.connect('bidsmart.db')
now = datetime.utcnow().isoformat()
for u,p,r in [('admin','admin123','admin'),('reviewer','Reviewer123!','reviewer'),('viewer','Viewer123!','viewer')]:
    h = bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
    db.execute('INSERT INTO users (username,password_hash,role,created_at,updated_at) VALUES (?,?,?,?,?)', (u,h,r,now,now))
db.execute('ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT 1')
db.commit()
"

# 启动 / Start
uvicorn src.main:create_app --host 0.0.0.0 --port 39001 --factory
```

### 项目架构 / Architecture

参考 `.sdd/steering/structure.md` 和 `.sdd/steering/tech.md`

## 开发铁律 / Development Rules

1. **SDD 工作流**：所有改动走 discovery → steering → spec → impl
2. **版本号**：每次改动更新 `src/main.py` 和 `pyproject.toml`
3. **前端单文件**：SPA 在 `static/index.html`，不拆文件
4. **修改后验证 JS 语法**：提取 `<script>` 内容用 `node --check` 检查

## 许可证 / License

MIT License — 详见 LICENSE 文件
