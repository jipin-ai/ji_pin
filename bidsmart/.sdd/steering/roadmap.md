# BidSmart 项目路线图

> 更新于 2026-05-03

## 项目状态

- 版本: v0.8.2
- 问题: 不合规 318（目标 100），无法判断 120（目标 10）

## 已完成

| Spec | 版本 | 效果 |
|------|------|------|
| semantic-matching | v0.8.1 | BGE 语义匹配 |
| image-extraction | v0.8.2 | 图片感知（元数据注入） |

## 当前迭代（v0.9.0）

**四管齐下，所有 spec 无依赖可并行：**

```
review-accuracy/
├── confidence-filter    (A) ← 0.5天 — 低置信匹配 → auto unable_to_judge
├── match-verify         (B) ← 2-3天 — LLM 先验证匹配质量再审查
├── prompt-restructure   (C) ← 0.5天 — 审查 prompt 重构（法规+引导）
└── review-memory        (D) ← 1-2天 — 忽略按钮 → 跨项目长期记忆
```

## 目标

- 不合规: 318 → 80-120
- 无法判断: 120 → 20-40
