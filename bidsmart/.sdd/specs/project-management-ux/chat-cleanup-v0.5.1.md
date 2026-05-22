# Spec: AI Chat Enhancement + Auto Cleanup
Version: 0.5.1
Status: done

## Task 1: AI Chat 工作范围收紧
**文件:** `src/compliance/router.py`
- 修改 `/ai/chat` 的 system prompt
- 增加话题检测：非标书审查相关问题 → 拒绝回答
- 拒绝话术：「抱歉，我只回答标书合规审查相关问题。」

## Task 2: AI 会话框动态显示
**文件:** `static/index.html`
- 新增收起/展开按钮（header 右侧）
- 空闲 60 秒后自动收起
- 收起后会话历史不丢失
- 保持左右面板 1.618:1 比例
- 输入框获得焦点或收到新消息时自动展开

## Task 3: 过期项目定期清理
**文件:** 新增 `scripts/cleanup_expired.py` + cron
- bid_time < now 的项目自动删除（含关联数据）
- 每次清理最多 50 个
- cron 每天凌晨 3 点执行
