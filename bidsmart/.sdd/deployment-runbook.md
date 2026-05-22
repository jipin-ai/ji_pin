# BidSmart — 部署运行手册

## 服务器信息

| 项 | 值 |
|------|-----|
| 实例 | 阿里云 ECS |
| IP | 8.219.137.176 |
| 系统 | Alibaba Cloud Linux |
| 端口 | 39001 (安全组 39000-40000) |
| Python | /opt/hermes/.venv/bin/python3.11 |
| uvicorn | /opt/hermes/.venv/bin/uvicorn |

## 服务管理 (systemd)

### 启停控制
```bash
# 启动
systemctl start bidsmart

# 停止
systemctl stop bidsmart

# 重启
systemctl restart bidsmart

# 查看状态
systemctl status bidsmart --no-pager
```

### 查看日志
```bash
# 最近 50 行
journalctl -u bidsmart -n 50 --no-pager

# 实时跟踪
journalctl -u bidsmart -f

# 今天的日志
journalctl -u bidsmart --since today --no-pager
```

### systemd 配置文件
位置: `/etc/systemd/system/bidsmart.service`
```
[Service]
Type=simple
User=root
WorkingDirectory=/root/bidsmart
ExecStart=/opt/hermes/.venv/bin/uvicorn src.main:create_app --host 0.0.0.0 --port 39001 --factory
Restart=always
RestartSec=5
```

## 验证部署

```bash
# 健康检查
curl -s http://localhost:39001/health
# → {"status":"ok","version":"0.7.7"}

# 版本检查
curl -s http://localhost:39001/openapi.json | python3 -c "import sys,json;print(json.load(sys.stdin)['info']['version'])"
```

## 数据库恢复

如果 bidsmart.db 丢失/损坏（0 字节）：

```bash
cd /root/bidsmart
# 1. 运行迁移建表
/opt/hermes/.venv/bin/alembic upgrade head

# 2. 种子用户
/opt/hermes/.venv/bin/python3 -c "
import sqlite3, bcrypt
from datetime import datetime
db = sqlite3.connect('bidsmart.db')
now = datetime.utcnow().isoformat()
users = [('admin','admin123','admin'),('reviewer','Reviewer123!','reviewer'),('viewer','Viewer123!','viewer')]
for u,p,r in users:
    h = bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
    db.execute('INSERT INTO users (username,password_hash,role,created_at,updated_at) VALUES (?,?,?,?,?)', (u,h,r,now,now))
db.commit()
print('Done')
"

# 3. 补 must_change_password 列
/opt/hermes/.venv/bin/python3 -c "
import sqlite3
c = sqlite3.connect('bidsmart.db')
c.execute('ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT 1')
c.commit()
print('Column added')
"

# 4. 重启
systemctl restart bidsmart
```

## 备份策略

### 备份命令
```bash
cd /root
tar czf /root/bidsmart-backups/bidsmart-$(date +%Y%m%d_%H%M%S).tar.gz \
  --exclude=bidsmart/storage bidsmart/
```

⚠️ 不要用 `--exclude=storage`（会误删 src/storage/ 源码）

### 恢复
```bash
cd /root
tar xzf /root/bidsmart-backups/BACKUP_FILE.tar.gz
systemctl restart bidsmart
```

## 故障排查

### 服务启动失败
```bash
# 1. 查看错误
journalctl -u bidsmart -n 50 --no-pager

# 2. 手动启动调试
cd /root/bidsmart
/opt/hermes/.venv/bin/uvicorn src.main:create_app --host 0.0.0.0 --port 39001 --factory 2>&1 | head -30
```

常见原因：
- `ModuleNotFoundError: No module named 'src.storage'` → 备份排除路径错误，重建 src/storage/
- `no such table: users` → 数据库为空，运行 alembic upgrade head
- `address already in use` → systemd 已自动重启，等待 5 秒

### 端口占用
```bash
ss -tlnp | grep 39001
# systemd 会自动重启，无需手动处理
```
