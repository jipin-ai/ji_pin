"""Seed default users for development. / 初始化默认用户（开发环境）"""
import sqlite3
import bcrypt
from datetime import datetime

db = sqlite3.connect('bidsmart.db')
now = datetime.utcnow().isoformat()

users = [
    ('admin', 'admin123', 'admin'),
    ('reviewer', 'Reviewer123!', 'reviewer'),
    ('viewer', 'Viewer123!', 'viewer'),
]

for username, password, role in users:
    pwhash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    db.execute(
        'INSERT OR IGNORE INTO users (username, password_hash, role, created_at, updated_at) '
        'VALUES (?, ?, ?, ?, ?)',
        (username, pwhash, role, now, now)
    )

# Ensure must_change_password column exists
try:
    db.execute('ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT 1')
except sqlite3.OperationalError:
    pass  # Column already exists

db.commit()
for row in db.execute('SELECT username, role FROM users'):
    print(f'  {row[0]:12} ({row[1]})')
db.close()
print('\nDefault users seeded. Login at http://localhost:39001')
print('  admin    / admin123      (管理员)')
print('  reviewer / Reviewer123!  (审核员)')
print('  viewer   / Viewer123!    (观察员)')
