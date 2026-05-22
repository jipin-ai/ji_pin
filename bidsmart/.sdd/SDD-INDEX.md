# BidSmart SDD 索引

## Steering 层 (方向性文档)

| 文件 | 描述 | 状态 |
|------|------|------|
| [product.md](steering/product.md) | 产品愿景、目标用户、核心功能 | ✅ |
| [tech.md](steering/tech.md) | 技术栈、依赖、部署约束 | ✅ |
| [structure.md](steering/structure.md) | 模块地图、目录布局、集成点 | ✅ |
| [roadmap.md](steering/roadmap.md) | 版本历史、P2/P3 规划 | ✅ |
| [risk-register.md](steering/risk-register.md) | 技术/安全/运维风险登记 | ✅ |
| [glossary.md](steering/glossary.md) | 28 个领域术语定义 | ✅ |

## Specs 层 (功能规格)

### 完整规格 (brief + requirements + design + tasks + spec.json)
| 目录 | 版本 | 状态 |
|------|------|------|
| [admin-panel](specs/admin-panel/) | 0.6.1 | ✅ |
| [auth-system](specs/auth-system/) | 0.1.0 | ✅ |
| [knowledge-base](specs/knowledge-base/) | 0.7.1 | ✅ |
| [project-management-ux](specs/project-management-ux/) | 0.2.0 | ✅ |
| [security-layer](specs/security-layer/) | 0.1.0 | ✅ |
| [streaming-review](specs/streaming-review/) | 0.5.0 | ⚠️ 部分未实现 |

### 基础规格 (brief + requirements only)
| 目录 | 版本 | 状态 |
|------|------|------|
| [database-models](specs/database-models/) | 0.1.0 | ✅ |
| [documents-pipeline](specs/documents-pipeline/) | 0.1.0 | ✅ |
| [middleware-layer](specs/middleware-layer/) | 0.1.0 | ✅ |
| [parsing-engine](specs/parsing-engine/) | 0.1.0 | ✅ |
| [projects-crud](specs/projects-crud/) | 0.2.0 | ✅ |
| [storage-abstraction](specs/storage-abstraction/) | 0.1.0 | ✅ |

### 元规格 (meta-specs)
| 目录 | 描述 |
|------|------|
| [bidsmart-dev-sync](specs/bidsmart-dev-sync/) | Hermes bidsmart-dev 技能同步分析 |

## 跨模块文档

| 文件 | 描述 |
|------|------|
| [CHANGELOG.md](CHANGELOG.md) | 完整版本变更历史 |
| [testing-strategy.md](testing-strategy.md) | 测试策略与覆盖分析 |
| [deployment-runbook.md](deployment-runbook.md) | 部署与运维操作手册 |

## 统计

| 指标 | 数值 |
|------|------|
| Steering 文档 | 6 |
| 完整 Specs | 6 |
| 基础 Specs | 6 |
| 跨模块文档 | 3 |
| **SDD 文档总计** | **21** |
| 代码 Python 文件 | 41 |
| 测试文件 | 6 (1,674 行) |
| 代码总行数 | ~3,200 (不含前端) |
| 前端行数 | 2,058 (static/index.html) |
