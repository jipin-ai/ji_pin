# review-memory: 跨项目审查记忆

## 问题

用户希望：在对照表中点"忽略"后，记录这条（招标要求 + 投标响应 + 判定结论）到长期记忆。以后再遇到相同的对照时自动跳过，沿用之前的结论。

## 方案

### 存储层

新建 `review_memory` 表：

```sql
CREATE TABLE review_memory (
    id INTEGER PRIMARY KEY,
    requirement_hash TEXT NOT NULL,    -- SHA256(requirement_text)
    requirement_preview TEXT,          -- 前100字供审查员确认
    verdict TEXT NOT NULL,             -- compliant/partial/non_compliant/unable_to_judge
    reason TEXT,
    suggestion TEXT,
    ignored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ignore_count INTEGER DEFAULT 1,    -- 累计忽略次数，增强置信度
    project_id INTEGER                 -- 来源项目（可NULL）
);
CREATE UNIQUE INDEX idx_req_hash ON review_memory(requirement_hash);
```

### 管线集成

```
Stage 2 完成后 → 遍历 matches:
  1. 计算 requirement_hash
  2. 查 review_memory 表
  3. 命中 → 跳过 LLM 审查，直接用历史结论
  4. 未命中 → 正常送 LLM
```

### 前端

对照表操作栏已有"忽略 ⊘"按钮。点击后：
1. 调用 `POST /ai/review/ignore`（已有）
2. **新增**：同步写入 review_memory 表

### API

```
POST /ai/memory/ignore     → 写入 review_memory
GET  /ai/memory/list       → 查看已忽略列表
DELETE /ai/memory/{id}     → 删除记忆（恢复审查）
```

## 改动范围

- `src/models/`: 新增 ReviewMemory 模型
- `src/compliance/pipeline.py`: match 后查 memory，命中跳过
- `src/compliance/router.py`: 新增 /ai/memory/* 路由
- `static/index.html`: 忽略按钮调用 memory API
- 数据库: alembic migration
- 版本: 沿用 0.9.0

## 预期效果

- 重复条款自动跳过，节省 LLM tokens
- 用户训练自己的"审查规则库"，精准度随使用提升
