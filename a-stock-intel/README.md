# 🔭 A-Stock Intel

> **零成本、零海外依赖的 A 股市场情报 Agent Tool**
>
> 大盘方向判定 · 个股策略建议 · 每日情报融合

[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)

---

## 为什么你需要这个

国内做 A 股量化/AI 分析的人，每天都在跟这些事情搏斗：

- AKShare 函数名三天两头漂移
- 东方财富/新浪 API 被 DPI 拦截
- 腾讯财经只有 GBK 编码、零文档
- 深交所 JSON API 藏在网页里，没人告诉你 URL
- 数据源分散，Agent 根本没法直接调用

**这个工具把上面所有坑填了。** Agent 只需要调用一个函数，拿到的是经过验证的结论。

---

## 三个工具

| 工具 | 功能 | 输入 | 输出 |
|------|------|------|------|
| `a_stock_market_regime` | 大盘方向 | 无 | 🟢多头 / 🔴空头 / 🟡震荡 + 策略建议 |
| `a_stock_advice` | 个股策略 | 股票代码列表 | 每只：趋势跟踪/狙击等待/空仓 + MA20 价位 |
| `a_stock_daily_briefing` | 每日简报 | 无 | 完整日报（大盘+标的+交叉信号） |

### 策略自适应分层

```
大盘判定 → 策略自动切换
  🟢 多头 → 趋势跟踪（回踩 MA10/MA20 即是买点）
  🔴 空头 → 空仓等待（不做多）
  🟡 震荡 → 狙击等待（预设精确买点）
```

核心思想：**策略跟着趋势走，不在多头市场等回调，不在空头市场接飞刀。**

---

## 数据源（全部国内，零成本）

| 数据 | 来源 | 格式 |
|------|------|------|
| K线（前复权日线） | 腾讯财经 `web.ifzq.gtimg.cn` | JSON/GBK |
| 大盘指数 | 腾讯财经 | JSON/GBK |
| 商品现货/期货 | AKShare `futures_spot_price` | DataFrame |
| 龙虎榜 | AKShare `stock_lhb_jgstatistic_em` | DataFrame |
| 问询函/监管函 | 深交所 `szse.cn/api/report/ShowReport` | JSON |
| ETF 份额 | AKShare `fund_etf_fund_daily_em` | DataFrame |

**零海外 API 调用。零付费数据源。**

---

## 安装

### 方式一：Hermes Agent 用户

```bash
# 安装 skill
hermes skills install a-stock-intel

# 安装依赖
pip install numpy akshare requests

# 重启或 /reset 后生效
```

### 方式二：直接拷贝

```bash
# 拷贝工具文件到 Hermes tools 目录
cp a_stock_intel_tool.py ~/.hermes/hermes-agent/tools/

# /reset 后即可使用
```

### 方式三：独立脚本（不依赖 Hermes）

```bash
python3 -c "
from a_stock_intel_tool import _market_regime, _stock_advice

# 查大盘方向
regime = _market_regime()
print(regime['summary'])  # bull / bear / range

# 查个股策略
advice = _stock_advice('002156', regime['summary'])
print(advice['strategy'], advice['action'])
"
```

---

## 使用示例

### 在 Hermes Agent 中

```
用户: 现在大盘什么方向？通富微电和东方财富应该怎么操作？

Agent 自动调用:
  → a_stock_market_regime()  → 🟢 多头（弱势）
  → a_stock_advice(codes=['002156','300059'])
     → 通富微电 ¥62.27 MA20:55  🟢 趋势跟踪
       回踩 MA20 附近可建仓
     → 东方财富 ¥19.67  🟡 等回踩
       大盘多头但个股偏弱，等站上 MA20
```

### 在 Python 中直接调用

```python
from tools.a_stock_intel_tool import _market_regime, _stock_advice

r = _market_regime()
print(r['indices'][0]['label'])  # 🟢 多头弱势

a = _stock_advice('002156', r['summary'])
print(f"{a['strategy']}: {a['action']}")  # 🟢 趋势跟踪: 回踩 MA20(55) 附近可建仓
```

---

## 从零到一的背景

这不是调 API 的薄层封装。背后是一套完整的四层架构：

```
数据采集层 — 绕过 DPI、AKShare 漂移、GBK 编码
   ↓
状态判定层 — MA20 斜率 + 量能确认 + 多指数交叉验证
   ↓
策略适配层 — 大盘方向 → 策略自动切换
   ↓
交叉验证层 — 资金面(龙虎榜) + 产业面(商品) + 监管面(问询函)
```

全部在国内网络环境下从头搭建、验证、跑通。

---

## 许可证

MIT © 2025 [Ji Pin](https://github.com/jipin-ai)
