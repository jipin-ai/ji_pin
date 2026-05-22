# middleware-layer — 需求规格 (EARS)

## 功能需求

### FR-1: IP 滑动窗口限流 (Ubiquitous)
**While** 系统运行，**the system shall** 对每个 IP 地址维护独立的滑动窗口计数器 → 超过阈值时返回 429 Too Many Requests。

**验收标准:**
- [x] 可配置窗口大小和最大请求数
- [x] 429 响应含 Retry-After 头
- [x] 内存计数器，重启后重置

### FR-2: 结构化访问日志 (Ubiquitous)
**While** 每个请求完成，**the system shall** 以 JSON 格式记录：method, path, status_code, duration_ms, client_ip。

**验收标准:**
- [x] 日志输出到 stdout（systemd journal 收集）
- [x] JSON 单行格式，可被 grep/jq 解析
- [x] 不影响响应延迟（异步写入）

### FR-3: 中间件优先级 (Ubiquitous)
**Where** 请求经过中间件链，**the system shall** 按 rate_limiter → audit → logging → app 顺序执行。

**验收标准:**
- [x] 限流先于业务逻辑
- [x] 审计在日志之前（确保被拒绝的请求也被审计）
