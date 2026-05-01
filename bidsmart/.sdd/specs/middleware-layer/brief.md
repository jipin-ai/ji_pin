# middleware-layer — Discovery Brief

## 问题描述
生产环境需要保护 API 免受滥用（限流）和记录所有请求（审计/监控）。两个中间件在请求生命周期中的不同阶段协作：限流在最外层拦截恶意请求，日志在响应后记录结构化数据。

## 当前状态
- RateLimiterMiddleware: 基于 IP 的滑动窗口限流，可配置窗口大小和最大请求数
- AccessLogMiddleware: 结构化 JSON 日志，记录 method/path/status/duration/client_ip
- 中间件顺序: rate_limiter → audit → logging → app

## 边界
**In scope:** IP 限流、请求日志、JSON 格式输出
**Out of scope:** 用户级限流、日志聚合/可视化、分布式限流
