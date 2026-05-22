# 极品 (ji_pin) — A股「早选晚打」双引擎量化工具箱

**零成本 + 本地算力 + 云端精筛 = 每日 2.5 分钟出候选池**

## 🎯 双引擎架构

```
09:20  策略一·量价突破  → vp_breakout_scanner.py  → 3 只短线突破候选
09:25  策略二·回调强买  → a_share_scanner.py       → 5 只回调候选池
                            [用户白天做功课、盯盘]
14:30  尾盘综合分析     → closing_analysis.py        → 入场触发信号
17:00  情报融合日报      → p3_fusion_briefing.py      → 多维交叉验证
```

## 📦 核心脚本

| 脚本 | 功能 | 依赖 |
|------|------|------|
| `a_share_scanner.py` | **主力扫描器** — 五层筛选流水线 (ST过滤→趋势健康度→PSS评分→Ollama粗筛→DeepSeek精筛) | Ollama, DeepSeek API, AnySearch |
| `fetch_a_shares.py` | **数据管道** — 腾讯财经 API 全 A 股快照 (~80s, 零成本) | AKShare (仅股票清单) |
| `closing_analysis.py` | **尾盘分析** — 14:30 检查入场触发器 (缩量止跌/V反/均线企稳) | 腾讯财经 API |
| `vp_breakout_scanner.py` | **量价突破** — 策略一辅线，成交量+价格突破扫描 | 腾讯财经 API |
| `p3_fusion_briefing.py` | **情报融合** — P0资金+P1商品+P2监管→交叉验证日报 | AKShare, SQLite |
| `cfh_sentiment.py` | **社区情绪** — 东方财富财富号热门文章标记提取 | 东方财富 API |
| `watchpool.py` | **关注池监控** — 统一仪表盘 + 狙击区到价通知 | 腾讯财经 API |

## 🔧 环境要求

- Python 3.10+
- Ollama (本地推理): `deepseek-r1:14b`
- DeepSeek API (云端精筛)
- AKShare (股票代码清单)
- RTX 5080 推荐（16GB VRAM，推理 ~88.7 tok/s）

### 环境变量 (.env)

```bash
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
OLLAMA_URL=http://localhost:11434
FEISHU_APP_ID=xxx    # (P3 融合日报需要)
FEISHU_APP_SECRET=xxx
```

## 🚀 快速开始

```bash
# 完整扫描 (量化初筛 + Ollama粗筛 + DeepSeek精筛)
python a_share_scanner.py --final-n 5

# 仅量化打分 (跳过 AI)
python a_share_scanner.py --skip-coarse --skip-fine

# 尾盘分析 (14:30 检查触发器)
python closing_analysis.py

# 关注池仪表盘
python watchpool.py
```

## 🛡️ 风控体系

三层否决 + 6 条交易铁律：

1. **L1 量化否决**: 强周期 + 趋势恶化 / 下跌加速 → 一票否决
2. **L2 公告排雷**: AnySearch 批量扫描「减持/质押/监管函」
3. **L3 AI 铁律兜底**: DeepSeek 逐条检查 6 条铁律

## 📊 实测耗时

| 阶段 | 工具 | 耗时 |
|------|------|------|
| 数据获取 | 腾讯 API | ~80s |
| 量化初筛 | pandas | <1s |
| 公告排雷 | AnySearch | ~30s |
| AI 粗筛 | Ollama | ~22s |
| AI 精筛 | DeepSeek | ~19s |
| **总计** | | **~150s** |

## ⚠️ 免责声明

本工具仅供学习研究，不构成投资建议。股市有风险，投资需谨慎。

## 📄 许可证

MIT License
