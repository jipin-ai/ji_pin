#!/usr/bin/env python3
"""
A-Share Sniper Scanner -- 狙击埋伏策略（v2.0）
============================================
策略核心：不等目标进入瞄准镜绝不开枪。
  选股方向：股价回落到 MA20 支撑位附近的股票（不是追涨）
  买入逻辑：预设精确买点 = MA20 x 0.95 ~ 0.97，等市场自己送上门
  非击球区就等着，不硬推。

三层架构:
  1. 狙击初筛: 腾讯API全市场快照 -> 距狙击区间排序 -> Top 50
  2. Ollama粗筛: deepseek-r1:14b 技术面/基本面验证 -> Top 15
  3. DeepSeek细筛: V4 Pro 深度分析 -> Top 3-5 推荐

数据源: 腾讯 qt.gtimg.cn（不受DPI拦截，52周高低+20日涨跌全有）
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from typing import Dict, List

import numpy as np
import pandas as pd
import requests

# 加载 .env
try:
    from dotenv import load_dotenv

    load_dotenv(os.path.expanduser("~/.hermes/.env"), override=True)
except ImportError:
    pass

# -- 配置 -----------------------------------------------------------
OLLAMA_URL = "http://localhost:11434/api/generate"
COARSE_MODEL = "deepseek-r1:14b"
COARSE_OPTIONS = {"num_ctx": 4096, "temperature": 0.05, "top_p": 0.85}

FINE_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
FINE_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
FINE_TEMPERATURE = 0.05  # 同 Ollama 粗筛温度，确保细筛输出稳定可复现
FINE_MAX_TOKENS = 4096

# ── 狙击参数 -------------------------------------------------------
PRICE_MIN, PRICE_MAX = 3.0, 80.0
MCAP_MIN = 50.0
PE_MIN, PE_MAX = 0.1, 50.0
AMOUNT_MIN = 5e7
HOT_THRESHOLD = 20.0
SNIPER_LOW, SNIPER_HIGH = 0.95, 0.97
MAX_DISTANCE = 8.0
COARSE_N, FINE_N, FINAL_N = 50, 15, 5
PRINCIPAL = 10000  # 本金（元）- 测试阶段
STOP_LOSS_PCT = -0.02   # 止损旧语义（保留给compare_yesterday兼容）
TAKE_PROFIT_PCT = 0.10  # 止盈旧语义（保留兼容）
STOP_MA20_MARGIN = -0.02   # 策略二止损：MA20 下方 2%
TAKE_PROFIT_PCT_NEW = 0.08  # 策略二止盈：入场价 +8%（取min(+8%, 前高)）
CANDIDATES_FILE = os.path.expanduser("~/.hermes/data/sniper_candidates.json")
YESTERDAY_FILE = os.path.expanduser("~/.hermes/data/sniper_yesterday.json")

# ── 强周期行业关键词（PE 低 ≠ 低估，需降权）──
CYCLICAL_KEYWORDS = [
    "铝", "钢", "铁", "煤", "炭", "化工", "有色", "水泥", "玻璃",
    "铜", "锌", "镍", "锂", "钴", "稀土", "石化", "原油", "天然气",
    "航运", "港口", "造船", "造纸", "化纤", "化肥", "农药",
]

# ── 一票否决关键词（公告/股东行为红线）──
VETO_KEYWORDS = {
    "减持": "大股东减持",
    "质押": "高比例质押",
    "监管函": "监管处罚",
    "问询函": "交易所问询",
    "立案": "证监会立案",
    "不分红": "不分红",
    "ST": "风险警示",
}

# ── 路径 -----------------------------------------------------------
SKILL_DIR = os.path.expanduser("~/.hermes/skills/finance/vt-weekly-scanner")
FETCH_SCRIPT = os.path.join(SKILL_DIR, "scripts", "fetch_a_shares.py")
VENV_PYTHON = os.path.expanduser("~/.hermes/hermes-agent/venv/bin/python")
ANYSEARCH_CLI = os.path.expanduser(
    "~/.hermes/skills/anysearch/scripts/anysearch_cli.py"
)
ANYSEARCH_PYTHON = "python3"  # 系统 Python，非 venv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ============================================================
#  数据层 -- 腾讯API
# ============================================================


def fetch_snapshot(max_retries: int = 3) -> List[Dict]:
    """调用 fetch_a_shares.py 通过腾讯API获取全市场快照（含重试）"""
    for attempt in range(1, max_retries + 1):
        logger.info(f"📡 获取全A股快照（腾讯API）... 第{attempt}次")
        try:
            r = subprocess.run(
                [VENV_PYTHON, FETCH_SCRIPT],
                capture_output=True,
                text=True,
                timeout=600,
            )
            if r.returncode != 0:
                err = r.stderr[-300:] if r.stderr else "无错误输出"
                logger.warning(f"fetch_a_shares.py 失败 (exit={r.returncode}): {err}")
                if attempt < max_retries:
                    wait = attempt * 30
                    logger.info(f"  等待 {wait}s 后重试...")
                    time.sleep(wait)
                    continue
                raise RuntimeError(f"fetch_a_shares.py 连续失败 {max_retries} 次")

            # stdout 是 JSON，可能格式化有换行
            # 找 "timestamp" 然后向前找最近的 {
            ts_pos = r.stdout.rfind('"timestamp"')
            if ts_pos == -1:
                logger.warning(f"stdout 中未找到 timestamp，长度: {len(r.stdout)}")
                if attempt < max_retries:
                    time.sleep(attempt * 30)
                    continue
                raise RuntimeError("无法从输出中提取JSON")
            # 向前搜索最近的 {
            json_start = r.stdout.rfind("{", 0, ts_pos)
            if json_start == -1:
                json_start = 0

            data = json.loads(r.stdout[json_start:])
            stocks = data.get("stocks", [])
            logger.info(f"✅ 获取 {len(stocks)} 只股票快照")
            return stocks
        except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
            logger.warning(f"获取快照失败 ({type(e).__name__}): {e}")
            if attempt < max_retries:
                time.sleep(attempt * 30)
                continue
            raise
    raise RuntimeError("获取快照失败：已达最大重试次数")


def snapshot_to_df(stocks: List[Dict]) -> pd.DataFrame:
    df = pd.DataFrame(stocks)
    for c in [
        "price",
        "change_pct",
        "volume",
        "amount",
        "pe",
        "market_cap",
        "ret_5d",
        "ret_10d",
        "ret_20d",
        "high_52w",
        "low_52w",
    ]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[df["price"] > 0].copy()
    df["symbol_clean"] = df["code"].astype(str).str.zfill(6)
    return df


# ============================================================
#  狙击初筛
# ============================================================


def sniper_filter(df: pd.DataFrame) -> pd.DataFrame:
    total = len(df)
    logger.info(f"🔫 狙击初筛（共 {total} 只）...")

    # ST 排除
    if "name" in df.columns:
        df = df[
            ~df["name"].astype(str).str.contains(r"ST|\*ST|退", na=True, regex=True)
        ]
    # 京交所排除
    bj = df["symbol_clean"].str.len().eq(6) & df["symbol_clean"].str.match(r"^[489]")
    df = df[~bj]
    logger.info(f"  ST/京交所: {len(df)} 只")

    df = df[(df["price"] >= PRICE_MIN) & (df["price"] <= PRICE_MAX)]
    logger.info(f"  价格[{PRICE_MIN}-{PRICE_MAX}]: {len(df)} 只")

    if "market_cap" in df.columns:
        df = df[df["market_cap"] >= MCAP_MIN]
        logger.info(f"  市值>{MCAP_MIN}亿: {len(df)} 只")

    if "pe" in df.columns:
        df = df[(df["pe"] >= PE_MIN) & (df["pe"] <= PE_MAX)]
        logger.info(f"  PE[{PE_MIN}-{PE_MAX}]: {len(df)} 只")

    if "low_52w" in df.columns and "price" in df.columns:
        df = df[df["price"] > df["low_52w"]]
        logger.info(f"  股价>52周低: {len(df)} 只")

    if "ret_5d" in df.columns:
        df = df[df["ret_5d"] < HOT_THRESHOLD]
        logger.info(f"  5日涨<{HOT_THRESHOLD}%: {len(df)} 只")

    if "amount" in df.columns and (df["amount"] > 0).sum() > len(df) * 0.3:
        df = df[df["amount"] >= AMOUNT_MIN]
        logger.info(f"  成交额>{AMOUNT_MIN / 1e8:.1f}亿: {len(df)} 只")

    # 可买性：entry_price × 100 ≤ principal/2（至少买1手）
    max_unit_price = PRINCIPAL / 2 / 100
    df = df[df["price"] <= max_unit_price]
    logger.info(f"  可买性(≤¥{max_unit_price:.0f}/股): {len(df)} 只")

    logger.info(f"🔫 结果: {len(df)}/{total} ({len(df) / total * 100:.1f}%)")
    return df.copy()


def calc_sniper_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """计算狙击指标 + 趋势健康度：MA20反推 -> 狙击区间 -> 距击球点 -> 趋势评分"""
    df = df.copy()

    # MA 反推
    df["ma5"] = df["price"] / (1 + df["ret_5d"] / 100)
    if "ret_10d" in df.columns:
        df["ma10"] = df["price"] / (1 + df["ret_10d"] / 100)
    else:
        df["ma10"] = (df["ma5"] + df["ma20"]) / 2  # fallback

    df["ma20"] = df["price"] / (1 + df["ret_20d"] / 100)
    df["sniper_low"] = df["ma20"] * SNIPER_LOW
    df["sniper_high"] = df["ma20"] * SNIPER_HIGH
    df["dist_to_sniper_pct"] = (
        (df["price"] - df["sniper_high"]) / df["sniper_high"] * 100
    )

    # ── 趋势健康度（4分制，≥3分才算合格狙击候选）──
    # 1. 均线多头排列: MA5 > MA10 > MA20
    df["trend_align"] = ((df["ma5"] > df["ma10"]) & (df["ma10"] > df["ma20"])).astype(
        int
    )
    # 2. 趋势未破: 股价 > MA20
    df["trend_intact"] = (df["price"] > df["ma20"]).astype(int)
    # 3. 非急速下跌: 20日涨跌 > -10%
    df["trend_notcrash"] = (df["ret_20d"] > -10).astype(int)
    # 4. 安全垫: 股价 > 52周低 × 1.05
    if "low_52w" in df.columns:
        df["trend_safe"] = (df["price"] > df["low_52w"] * 1.05).astype(int)
    else:
        df["trend_safe"] = 0

    # 5. 下跌加速检测: 5日跌幅超过20日跌幅一半 → 危险加速
    if "ret_5d" in df.columns and "ret_20d" in df.columns:
        df["trend_accel"] = (
            ((df["ret_5d"] < 0) & (df["ret_20d"] < 0))
            & (df["ret_5d"] < df["ret_20d"] * 0.5)
        ).astype(int)
    else:
        df["trend_accel"] = 0

    df["trend_health"] = (
        df["trend_align"]
        + df["trend_intact"]
        + df["trend_notcrash"]
        + df["trend_safe"]
        - df["trend_accel"]  # 下跌加速扣1分
    ).clip(0, 4)

    # ── 强周期行业标记（PE 低 ≠ 低估）──
    if "name" in df.columns:
        pattern = "|".join(CYCLICAL_KEYWORDS)
        df["is_cyclical"] = (
            df["name"].astype(str).str.contains(pattern, na=False, regex=True).astype(int)
        )
    else:
        df["is_cyclical"] = 0

    def status(row):
        if row["price"] < row.get("low_52w", 0):
            return "broken"
        if row["price"] < row["sniper_low"]:
            return "oversold"
        if row["price"] <= row["sniper_high"]:
            return "in_zone"
        if row["dist_to_sniper_pct"] <= MAX_DISTANCE:
            return "approaching"
        return "far"

    df["sniper_status"] = df.apply(status, axis=1)

    def score(row):
        s = row["sniper_status"]
        if s == "in_zone":
            base = 0
        elif s == "approaching":
            base = abs(row["dist_to_sniper_pct"]) * 10
        elif s == "oversold":
            od = (row["price"] - row["sniper_low"]) / row["sniper_low"] * 100
            base = 30 + abs(od) * 5
        elif s == "broken":
            return 500
        else:
            return 999
        # 趋势健康度惩罚：每缺1分 +15
        base += (4 - row["trend_health"]) * 15
        return base

    df["sniper_score"] = df.apply(score, axis=1)
    # PE 加分（低PE加更多分）
    if "pe" in df.columns:
        df["sniper_score"] -= (
            df["pe"].clip(1, 50).apply(lambda x: max(0, 20 - x * 0.4)).fillna(0)
        )

    return df.sort_values("sniper_score").reset_index(drop=True)


def pick_top(df: pd.DataFrame, n: int = COARSE_N) -> pd.DataFrame:
    """优先择 in_zone 和 approaching，且趋势健康度 ≥ 3"""
    # 趋势健康度过滤
    qualified = df[df["trend_health"] >= 3]
    dropped = len(df) - len(qualified)
    if dropped > 0:
        logger.info(f"🔧 趋势过滤: 淘汰 {dropped} 只（趋势健康度 < 3/4）")

    pri = qualified[qualified["sniper_status"].isin(["in_zone", "approaching"])].head(n)
    if len(pri) < n:
        ov = qualified[qualified["sniper_status"] == "oversold"].head(n - len(pri))
        pri = pd.concat([pri, ov])

    logger.info(f"🎯 狙击候选 Top {len(pri)} (趋势合格 ≥3/4):")
    for i, (_, r) in enumerate(pri.head(15).iterrows(), 1):
        e = {"in_zone": "🟢", "approaching": "🟡", "oversold": "🔵"}.get(
            r["sniper_status"], "⚪"
        )
        bars = "▮" * int(r["trend_health"]) + "▯" * (4 - int(r["trend_health"]))
        logger.info(
            f"  {i:2d}. {e} {r['code']} {r['name']:6s} ¥{r['price']:.2f} | "
            f"狙击区 ¥{r['sniper_low']:.2f}-{r['sniper_high']:.2f} | "
            f"距击球点 {r['dist_to_sniper_pct']:+.1f}% | "
            f"趋势 {bars} | PE:{r.get('pe', '?')}"
        )
    return pri.reset_index(drop=True)


# ============================================================
#  AI -- Ollama 粗筛 + DeepSeek 细筛
# ============================================================


def strip_think(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def build_coarse_prompt(candidates: pd.DataFrame) -> str:
    """粗筛 Prompt：仪器角色 — 验证 PSS，辨别金子 vs 石块，不重新排名"""
    lines = []
    for _, r in candidates.iterrows():
        th = int(r.get("trend_health", 0))
        pss = r.get("pss", 0)
        risk_tags = []
        if r.get("is_cyclical"):
            risk_tags.append("🔶周期")
        if r.get("trend_accel", 0) == 1:
            risk_tags.append("⚠️加速跌")
        tag_str = " " + " ".join(risk_tags) if risk_tags else ""
        lines.append(
            f"{'🥇' if pss >= 60 else '⚠️'} {r['code']} {r['name']} | "
            f"PSS:{pss:.1f} | ¥{r['price']:.2f} | "
            f"狙击区 ¥{r['sniper_low']:.2f}-{r['sniper_high']:.2f} | "
            f"距击球点 {r['dist_to_sniper_pct']:+.1f}% | "
            f"风报比:{r.get('rr_ratio', 0):.2f} | 趋势{th}/4 | "
            f"5日:{r.get('ret_5d', 0):+.1f}% | 20日:{r.get('ret_20d', 0):+.1f}% | "
            f"PE:{r.get('pe', '?')} | 市值:{r.get('market_cap', '?')}亿{tag_str}"
        )

    prompt = f"""你是一台精密仪器，负责辨别金子与石块。PSS量化模型已经从50只候选股中选出以下{len(candidates)}只高分标的，你的工作是：

🔍 验证而非重排：
1. 检查每只的PSS五维评分是否合理（入场/风报/趋势/基本面/催化剂）
2. 标记「⚠️ 石块」：有任何致命缺陷的（趋势破坏、风报比<1.5、PE虚高、行业衰退）
3. 确认「🥇 金子」：PSS合理 + 无致命缺陷

🚨 特别注意以下风险标记：
- 🔶周期: 强周期行业（铝/钢/煤/化工等），PE低≠低估，必须结合行业周期判断
- ⚠️加速跌: 5日跌幅超过20日跌幅一半 → 下跌在加速，可能接飞刀

❌ 不要做的事：
- 不要重新排名（PSS已经排好）
- 不要编造新的股票
- 不要修改PSS分数

候选股票（PSS已排序）：
{"=" * 80}
{chr(10).join(lines)}
{"=" * 80}

输出JSON，对每只标注判断：
{{"verified": [
  {{"code":"000001","name":"平安银行","verdict":"gold","pss_ok":true,"fatal_flaw":null,"note":"风报比合理，趋势健康"}},
  {{"code":"000002","name":"XX股票","verdict":"rock","pss_ok":false,"fatal_flaw":"风报比仅0.8，止损位不明确","note":"不适合狙击"}}
],
"gold_count": N,
"rock_count": M
}}

只输出JSON，不要其他文字。"""
    return prompt


def build_fine_prompt(candidates: pd.DataFrame, final_n: int = FINAL_N) -> str:
    """细筛 Prompt：深度狙击分析 + PSS 量化评分"""
    lines = []
    for _, r in candidates.iterrows():
        ma20 = r.get("ma20", 0)
        trigger_price = round(r["price"], 2)  # 当前价即入场参考价
        stop_price = round(ma20 * (1 + STOP_MA20_MARGIN), 2) if ma20 > 0 else trigger_price
        target_price = round(trigger_price * (1 + TAKE_PROFIT_PCT_NEW), 2)
        pss = r.get("pss", 0)
        rr = r.get("rr_ratio", 0)
        risk_tags = []
        if r.get("is_cyclical"):
            risk_tags.append("🔶强周期(PE低≠低估)")
        if r.get("trend_accel", 0) == 1:
            risk_tags.append("⚠️下跌加速")
        tag_str = " | " + " | ".join(risk_tags) if risk_tags else ""
        lines.append(
            f"【{r['code']} {r['name']}】\n"
            f"  当前价: ¥{r['price']:.2f} | MA20: ¥{ma20:.2f} | 距MA20: {r['dist_to_sniper_pct']:+.1f}%\n"
            f"  PSS:{pss:.1f} | 入场{r.get('entry_score', 0):.0f} | 风报{r.get('rr_score', 0):.0f} | 趋势{r.get('trend_score', 0):.0f} | 基本{r.get('fundamental_score', 0):.0f}\n"
            f"  5日涨跌: {r.get('ret_5d', 0):+.1f}% | 20日涨跌: {r.get('ret_20d', 0):+.1f}% | 52周低: ¥{r.get('low_52w', '?'):.2f} | 52周高: ¥{r.get('high_52w', '?'):.2f}\n"
            f"  PE:{r.get('pe', '?')} | 市值:{r.get('market_cap', '?')}亿\n"
            f"  入场参考: ¥{trigger_price} | 止损(MA20-2%): ¥{stop_price} | 止盈(+8%): ¥{target_price} | 风报比: {rr:.2f}{tag_str}"
        )

    prompt = f"""你是一位回调强买策略分析师。以下 {len(candidates)} 只股票已通过量化初筛+Ollama粗筛+PSS精准评分，均在 MA20 支撑位附近。

⚠️ 关键：每只股票已附带 PSS (Precision Sniper Score) 精准狙击评分（100分制），这是量化模型对五维度的加权打分：
  入场精度(30%) + 风报比(25%) + 趋势质量(20%) + 基本面(15%) + 催化剂(10%)

策略定位：回调强买（Pullback Strength）—— 不等股价跌到狙击区，看到「止跌信号」就主动入场。
三个入场触发器（满足任一即可）：
  🔫 缩量止跌：当日量 < 前日量×0.7 且收阳
  🔫 V反信号：盘中低点距 MA20 ≤ 1%
  🔫 均线企稳：盘中触及 MA20 后反弹企稳

你的任务：
1. 审核 PSS 评分是否合理（特别是催化剂维度——结合行业景气度/政策面调整）
2. 从中选出 {final_n} 只回调强买候选（按调整后 PSS 排）
3. PSS Top 2 优先，除非有明确的否定理由
4. 给出每只候选的入场建议（止损=MA20下方2%，止盈=min(+8%, 前高)）

分析维度：
1. 催化剂调整：结合行业政策、板块轮动、事件驱动，调整催化剂评分（±20分）
2. 技术形态确认：PSS中的趋势分是否合理？有无遗漏的风险信号？
3. 入场触发器评估：哪个触发器最可能先触发？为什么？

━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 铁律速查（每只候选必须逐条过）:
━━━━━━━━━━━━━━━━━━━━━━━━━━

① 公告排雷: AnySearch 已对 Top 15 自动预扫（减持/质押/监管函/问询函），你收到的候选已通过此关。如仍有疑虑请标注。
   → 大股东近30天减持 ≥1% → 一票否决
   → 控股股东质押 >80% → 一票否决
   → 近90天有监管函/问询函 → 一票否决
   → 不分红 + 大股东减持 → 一票否决

② 强周期行业 (🔶标记): PE低≠低估，必须结合商品价格/行业供需判断
   → 铝/钢/煤/化工/有色/水泥等 — 周期底部PE可以极低却是陷阱

③ 下跌加速 (⚠️标记): 5日跌幅远超20日跌幅 → 别接飞刀
   → 等止跌信号(缩量/下影线/均线走平)再入场

④ 单票仓位 ≤ 10%: 小户单只不超过1.5万

⑤ 目标价 > 成本价: 不合理目标直接驳回

⑥ 止损同步给出: MA20 下方 2%

━━━━━━━━━━━━━━━━━━━━━━━━━━

候选股票（含PSS评分）:
{"=" * 80}
{chr(10).join(lines)}
{"=" * 80}

输出格式（每只候选）：
## 🥇 #N 代码 名称 — 调整后PSS: XX.X | 入场: ¥X.XX
**距MA20**: ±X.X% | **MA20**: ¥X.XX
**止损位**: ¥X.XX（MA20下方2%） | **止盈位**: ¥X.XX（min(+8%, 前高¥X.XX)）
**风报比**: X.XX
**最可能触发**: [缩量止跌/V反/均线企稳 — 说明原因]
**铁律检查**: 
  ① 公告排雷: [结果]
  ② 强周期判断: [是/否]
  ③ 下跌加速: [是/否]
**催化剂评估**: [行业/政策/情绪]
**置信度**: X/10
**核心理由**: ...
**风险提示**: 1... 2... 3...

## 📋 候选池汇总（最终{final_n}只）
| 代码 | 名称 | 入场价 | 止损(MA20-2%) | 止盈(min+8%/前高) | MA20 | 距均线% |
|------|------|--------|--------------|-------------------|------|---------|
| XXXXXX | XXXX | ¥X.XX | ¥X.XX | ¥X.XX | ¥X.XX | X.X% |

⚠️ 操作提示: 以上为「候选池」，非「挂单指令」。实际入场需满足三个触发器之一。
14:30 尾盘分析会检查触发器状态并给出最终入场建议。"""

    return prompt


def call_ollama(
    prompt: str, model: str = COARSE_MODEL, temperature: float = None
) -> str:
    logger.info(f"[粗筛] 调用 Ollama ({model})，{len(prompt)} 字符...")

    options = COARSE_OPTIONS.copy()
    if temperature is not None:
        options["temperature"] = temperature

    # JSON Schema 约束输出（防治幻觉+确保合法JSON）
    # ⚠️ "verified" 字段名必须与 parse_coarse() 的 data.get("verified") 一致
    json_schema = {
        "type": "object",
        "properties": {
            "verified": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "name": {"type": "string"},
                        "verdict": {"type": "string", "enum": ["gold", "rock"]},
                        "pss_ok": {"type": "boolean"},
                        "fatal_flaw": {"type": "string"},
                        "note": {"type": "string"},
                    },
                    "required": [
                        "code",
                        "name",
                        "verdict",
                        "pss_ok",
                        "fatal_flaw",
                        "note",
                    ],
                },
            },
            "gold_count": {"type": "integer"},
            "rock_count": {"type": "integer"},
        },
        "required": ["verified", "gold_count", "rock_count"],
    }

    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                "model": model,
                "prompt": prompt,
                "format": json_schema,
                "stream": False,
                "options": options,
            },
            timeout=300,
        )
        r.raise_for_status()
        raw = r.json().get("response", "")
        cleaned = strip_think(raw)
        logger.info(
            f"[粗筛] Ollama 返回 {len(cleaned)} 字符 (temp={options.get('temperature', 'default')})"
        )
        return cleaned
    except requests.exceptions.ConnectionError:
        logger.error("无法连接 Ollama (localhost:11434)，降级跳过粗筛")
        return ""
    except Exception as e:
        logger.error(f"Ollama 调用失败: {e}")
        raise


def parse_coarse(text: str, fallback: pd.DataFrame, n: int) -> pd.DataFrame:
    """解析 Ollama 验证输出，提取金子（gold），过滤石块（rock）。含名称校正。"""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
        verified = data.get("verified", [])

        # 提取 gold 标的
        gold_codes = set()
        rocks = []
        for v in verified:
            code_clean = "".join(filter(str.isdigit, str(v.get("code", ""))))
            if v.get("verdict") == "gold":
                gold_codes.add(code_clean)
            else:
                rocks.append(
                    f"{code_clean} {v.get('name', '')}: {v.get('fatal_flaw', '未知')}"
                )

        if rocks:
            logger.info(f"🪨 Ollama 标记石块 {len(rocks)} 只:")
            for r in rocks[:5]:
                logger.info(f"   ❌ {r}")

        if gold_codes:
            result = fallback[fallback["symbol_clean"].isin(gold_codes)]
            if len(result) >= n // 2:
                logger.info(f"🥇 Ollama 确认金子: {len(result)} 只")
                return result.head(n)
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(f"[粗筛] Ollama 输出解析异常 ({type(e).__name__}): {e}")

    logger.warning("[粗筛] Ollama 验证失败，回退到 PSS Top N")
    return fallback.head(n)


# ============================================================
#  PSS 精准狙击评分
# ============================================================


def veto_check(df: pd.DataFrame) -> tuple:
    """一票否决检查：强周期 + 趋势恶化 = 降级；下跌加速 = 警告

    返回 (cleaned_df, veto_log) — cleaned_df 已移除一票否决标的。
    减持/质押/监管函属外部公告数据，在细筛阶段由 AI 搜索确认。
    """
    veto_log = []
    mask = pd.Series(True, index=df.index)

    for idx, row in df.iterrows():
        code = row.get("code", "?")
        name = row.get("name", "?")
        reasons = []

        # ① 强周期 + 趋势恶化（trend_health < 2）→ 一票否决
        if row.get("is_cyclical") and row.get("trend_health", 0) < 2:
            reasons.append("强周期行业+趋势恶化(trend_health<2)")

        # ② 强周期 + PE < 5（估值陷阱）→ 降级警告（不否决，但标记）
        # (仅标记，不排斥)

        # ③ 下跌加速 + 趋势健康度=0 → 一票否决
        if row.get("trend_accel", 0) == 1 and row.get("trend_health", 0) <= 1:
            reasons.append("下跌加速+趋势崩溃")

        if reasons:
            mask[idx] = False
            veto_log.append(f"  ❌ {code} {name}: {'; '.join(reasons)}")

    n_vetoed = (~mask).sum()
    if veto_log:
        logger.warning(f"🛑 一票否决 {n_vetoed} 只:")
        for line in veto_log:
            logger.warning(line)

    return df[mask].copy(), veto_log


def calc_pss_scores(candidates: pd.DataFrame) -> pd.DataFrame:
    """计算精准狙击评分 PSS (Precision Sniper Score)

    五维加权：
      入场精度 30% + 风报比 25% + 趋势质量 20% + 基本面 15% + 催化剂 10%
    """
    df = candidates.copy()

    # 1. 入场精度 (30%): 距击球点越近越好
    df["entry_score"] = (
        (1 - df["dist_to_sniper_pct"].abs().clip(0, MAX_DISTANCE) / MAX_DISTANCE) * 100
    ).clip(0, 100)

    # 2. 风报比 (25%): (目标-入场) / (入场-止损)
    entry = df["sniper_high"]
    # 止损：入场价 × (1 - 2%)；止盈：入场价 × (1 + 10%)
    stop = entry * (1 + STOP_LOSS_PCT)  # * 0.98
    target = entry * (1 + TAKE_PROFIT_PCT)  # * 1.10
    df["rr_ratio"] = ((target - entry) / (entry - stop)).clip(0, 20)
    # 风报比 ≥ 2.0 满分，1.0-2.0 线性，<1.0 低分
    df["rr_score"] = (df["rr_ratio"].clip(0, 3) / 3 * 100).clip(0, 100)

    # 3. 趋势质量 (20%): trend_health / 4 * 100
    df["trend_score"] = (df["trend_health"] / 4 * 100).clip(0, 100)

    # 4. 基本面安全 (15%): PE越低越好，强周期股 PE 权重减半
    if "pe" in df.columns:
        df["fundamental_score"] = (
            df["pe"].clip(1, 50).apply(lambda x: max(0, min(100, (20 - x) * 5)))
        ).fillna(50)
        # 强周期行业: PE 低 ≠ 低估，权重减半
        if "is_cyclical" in df.columns:
            cyclical_mask = df["is_cyclical"] == 1
            df.loc[cyclical_mask, "fundamental_score"] *= 0.5
            n_cyclical = cyclical_mask.sum()
            if n_cyclical > 0:
                logger.info(f"  ⚠️ 强周期行业 {n_cyclical} 只: PE 权重减半")
    else:
        df["fundamental_score"] = 50

    # 5. 催化剂 (10%): 默认50，DeepSeek可覆盖
    df["catalyst_score"] = 50

    # PSS 加权总分
    df["pss"] = (
        df["entry_score"] * 0.30
        + df["rr_score"] * 0.25
        + df["trend_score"] * 0.20
        + df["fundamental_score"] * 0.15
        + df["catalyst_score"] * 0.10
    )

    # Top 2 = 挂单候选
    top2 = df.head(2)
    logger.info("🎯 PSS 精准狙击评分 — Top 2 挂单候选:")
    for i, (_, r) in enumerate(top2.iterrows(), 1):
        logger.info(
            f"  #{i} {r['code']} {r['name']} | PSS:{r['pss']:.1f} | "
            f"入场:{r['entry_score']:.0f} 风报:{r['rr_score']:.0f} "
            f"趋势:{r['trend_score']:.0f} 基本:{r['fundamental_score']:.0f}"
        )

    return df.sort_values("pss", ascending=False).reset_index(drop=True)


def anysearch_veto_scan(df: pd.DataFrame, max_stocks: int = 15) -> tuple:
    """AnySearch 公告排雷：对 Top N 候选批量搜索减持/质押/监管函/问询函

    返回 (cleaned_df, veto_log) — 命中的直接一票否决。
    匿名 API 按 IP 限流，建议只对 Top 15 执行。
    """
    if not os.path.exists(ANYSEARCH_CLI):
        logger.warning("AnySearch CLI 未安装，跳过公告扫描。")
        return df.copy(), []

    top_n = min(len(df), max_stocks)
    if top_n == 0:
        return df.copy(), []

    logger.info(f"🔍 AnySearch 公告排雷: 扫描 Top {top_n} 只...")
    candidates = df.head(top_n)

    # 构建批量查询
    queries = []
    for _, r in candidates.iterrows():
        code = r["code"]
        name = r.get("name", "")
        queries.append({
            "query": f"{name} {code} 公告 新闻",
            "zone": "cn",
            "max_results": 5,
            "freshness": "month",
        })

    try:
        # 分块查询（API 限制每批最多 5 个 query）
        CHUNK_SIZE = 5
        all_raw = []
        for i in range(0, len(queries), CHUNK_SIZE):
            chunk = queries[i : i + CHUNK_SIZE]
            chunk_json = json.dumps(chunk, ensure_ascii=False)
            r = subprocess.run(
                [ANYSEARCH_PYTHON, ANYSEARCH_CLI, "batch_search", chunk_json],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if r.returncode != 0:
                logger.warning(
                    f"AnySearch chunk {i // CHUNK_SIZE + 1} 失败 "
                    f"(exit={r.returncode}): {r.stderr[-200:]}"
                )
                continue
            all_raw.append(r.stdout)

        if not all_raw:
            logger.warning("所有 AnySearch 分块均失败，跳过公告扫描。")
            return df.copy(), []

        raw_output = "\n".join(all_raw)
    except subprocess.TimeoutExpired:
        logger.warning("AnySearch 超时，跳过公告扫描。")
        return df.copy(), []
    except Exception as e:
        logger.warning(f"AnySearch 异常: {e}")
        return df.copy(), []

    # 按股票解析结果，检查关键词命中
    veto_codes = set()
    veto_log = []

    # 拆分每个查询的输出块
    blocks = re.split(r"\n## 查询 \d+: ", raw_output)
    for block in blocks[1:]:  # 第一个是空的
        if not block.strip():
            continue

        # 从候选池中匹配股票
        matched_stock = None
        for _, candidate in candidates.iterrows():
            code = str(candidate["code"])
            name = str(candidate.get("name", ""))
            if code in block or name in block:
                matched_stock = candidate
                break

        if matched_stock is None:
            continue

        # 按单条结果分割 (### N. ...)
        result_items = re.split(r"\n### \d+\. ", block)
        hit_keywords = set()
        for item in result_items:
            if not item.strip():
                continue
            # 关键：在单条结果中同时出现股票代码/名称 + 关键词才判命中
            has_stock = (
                str(matched_stock["code"]) in item
                or str(matched_stock.get("name", "")) in item
            )
            if not has_stock:
                continue
            for kw, label in VETO_KEYWORDS.items():
                if kw in item:
                    hit_keywords.add(label)

        if hit_keywords:
            code = str(matched_stock["code"])
            name = str(matched_stock.get("name", ""))
            veto_codes.add(code)
            veto_log.append(
                f"  🛑 {code} {name}: AnySearch命中 → "
                f"{', '.join(hit_keywords)}"
            )

    if veto_codes:
        logger.warning(f"🛑 AnySearch 公告排雷: 否决 {len(veto_codes)} 只！")
        for line in veto_log:
            logger.warning(line)
        # 从候选池中移除
        cleaned = df[~df["code"].astype(str).isin(veto_codes)].copy()
        return cleaned, veto_log
    else:
        logger.info("✅ AnySearch 公告排雷: 全部通过")
        return df.copy(), veto_log


def call_fine(prompt: str, api_key: str, base_url: str, model: str) -> str:
    logger.info(f"[细筛] 调用 {model}，{len(prompt)} 字符...")
    url = base_url.rstrip("/") + "/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": FINE_TEMPERATURE,
        "max_tokens": FINE_MAX_TOKENS,
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=300)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        logger.info(f"[细筛] 返回 {len(content)} 字符")
        return content
    except Exception as e:
        logger.error(f"[细筛] API 失败: {e}")
        raise


# ============================================================
#  昨日对比 + 仓位计算
# ============================================================


def _parse_fine_recommendations(fine_report: str) -> list[str]:
    """从 DeepSeek 细筛报告的 📋 挂单指令 表格中提取推荐代码列表"""
    codes = []
    # 匹配表格行: | 002668 | TCL智家 | ¥9.39 | 1 | ...
    # 第一列是6位数字代码
    pattern = re.compile(r"^\|\s*(\d{6})\s*\|", re.MULTILINE)
    # 只在「挂单指令」小节内匹配
    # 找到 📋 挂单指令 小节
    section_start = fine_report.find("📋 挂单指令")
    if section_start == -1:
        # 也尝试 ## 📋 格式
        section_start = fine_report.find("挂单指令")
    if section_start == -1:
        return codes

    # 取该小节到下一个 ## 或文件尾
    section = fine_report[section_start:]
    next_section = re.search(r"\n## ", section)
    if next_section:
        section = section[: next_section.start()]

    for m in pattern.finditer(section):
        code = m.group(1)
        if code not in codes:
            codes.append(code)
    return codes


def compare_yesterday(
    fine_candidates: pd.DataFrame,
    fine_report: str = "",
    fine_skipped: bool = False,
    principal: float = PRINCIPAL,
    yesterday_file: str = YESTERDAY_FILE,
):
    """对比昨日 DeepSeek 推荐与今日推荐，输出持续/退出/新入选。

    v2.2 修复：不再基于 PSS 排名自己生成挂单表。
    挂单指令由 DeepSeek 细筛报告输出（唯一权威来源）。
    compare_yesterday 仅从报告中解析推荐代码做对比 + 保存供明日使用。
    """
    os.makedirs(os.path.dirname(yesterday_file), exist_ok=True)

    # ── 加载昨日数据 ──
    yesterday = {}
    if os.path.exists(yesterday_file):
        try:
            with open(yesterday_file) as f:
                yesterday = json.load(f)
        except Exception:
            pass

    # ── 解析今日 DeepSeek 推荐 ──
    today_reco_codes = []
    if not fine_skipped and fine_report:
        today_reco_codes = _parse_fine_recommendations(fine_report)

    if not today_reco_codes:
        # DeepSeek 未执行或未产出推荐 → 无法做有意义的对比
        # 不生成挂单表，不覆盖昨日文件
        logger.warning("⚠️ DeepSeek 细筛未执行/未产出推荐，跳过昨日对比")
        print("\n" + "=" * 80)
        print("  📊 昨日持仓 vs 今日推荐")
        print("=" * 80)
        print(f"\n  ⚠️ {'DeepSeek 细筛跳过' if fine_skipped else '未能从报告解析推荐代码'}，无法对比。")
        if fine_report:
            print(f"  报告长度: {len(fine_report)} 字")
        print("  💡 挂单指令请参见上方 DeepSeek 报告。\n")
        return []

    # ── 匹配今日推荐到 fine_candidates 以获取详细数据 ──
    today_picks = []
    fine_by_code = {}
    for _, r in fine_candidates.iterrows():
        fine_by_code[r["code"]] = r

    for code in today_reco_codes:
        r = fine_by_code.get(code)
        if r is not None:
            entry_price = round(r["sniper_high"], 2)
            stop_price = round(entry_price * (1 + STOP_LOSS_PCT), 2)
            target_price = round(entry_price * (1 + TAKE_PROFIT_PCT), 2)
            shares = int(principal / max(len(today_reco_codes), 1) / entry_price / 100) * 100
            lots = shares // 100

            today_picks.append(
                {
                    "code": r["code"],
                    "name": r["name"],
                    "entry_price": entry_price,
                    "stop_price": stop_price,
                    "target_price": target_price,
                    "pss": round(r.get("pss", 0), 1),
                    "dist_to_sniper": round(r["dist_to_sniper_pct"], 1),
                    "rr_ratio": round(r.get("rr_ratio", 0), 2),
                    "shares": shares,
                    "lots": lots,
                    "price": round(r["price"], 2),
                    "pe": r.get("pe", 0),
                }
            )

    if not today_picks:
        logger.warning("DeepSeek 推荐的代码在 fine_candidates 中未找到，跳过对比")
        return []

    # ── 对比 ──
    print("\n" + "=" * 80)
    print("  📊 昨日持仓 vs 今日推荐（来源：DeepSeek 细筛报告）")
    print("=" * 80)

    if not yesterday:
        print("\n  🆕 首次运行，无昨日数据可供对比。\n")
    else:
        y_codes = {p["code"] for p in yesterday.get("picks", [])}
        t_codes = {p["code"] for p in today_picks}
        kept = y_codes & t_codes
        dropped = y_codes - t_codes
        added = t_codes - y_codes

        print(f"\n  昨日推荐 ({yesterday.get('date', '?')}):")
        for p in yesterday.get("picks", []):
            status = "🔄 保留" if p["code"] in kept else "❌ 退出"
            print(f"    {p['code']} {p['name']} — 挂单 ¥{p['entry_price']} → {status}")

        if dropped:
            print(f"\n  🔴 已退出 ({len(dropped)}): DeepSeek 本轮否决/PSS落后 → 今日不挂")
        if added:
            print(f"\n  🟢 新入选 ({len(added)}): DeepSeek 本轮推荐")
        if kept:
            print(f"\n  🟡 持续推荐 ({len(kept)}): 两日 DeepSeek 均推荐，可续挂")

    # ── 保存今日真实推荐（只保存 DeepSeek 认可的代码）──
    today_record = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "picks": today_picks,
        "source": "deepseek_fine",
    }
    with open(yesterday_file, "w") as f:
        json.dump(today_record, f, ensure_ascii=False, indent=2)
    logger.info(f"💾 今日 DeepSeek 推荐 ({len(today_picks)} 只) 已保存至 {yesterday_file}")

    return today_picks


# ============================================================
#  输出
# ============================================================


def print_report(
    candidates, fine_df, coarse_raw, fine_report, elapsed,
    fine_skipped=False, fine_skip_reason=""
):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print("\\n" + "=" * 80)
    print(f"  🎯 回调强买候选池 — {now}")
    print(f"  策略: 回调强买(Pullback Strength) | 粗筛: Ollama({COARSE_MODEL}) | 细筛: 云端({FINE_MODEL})")
    print(f"  入场规则: 三个触发器(缩量止跌/V反/均线企稳) 任一满足即可")
    print("=" * 80)

    print("\\n📊 初筛统计:")
    print(f"   初筛候选: {len(candidates)} 只")
    in_zone = (candidates["sniper_status"] == "in_zone").sum()
    approaching = (candidates["sniper_status"] == "approaching").sum()
    healthy = (
        (candidates["trend_health"] >= 3).sum()
        if "trend_health" in candidates.columns
        else 0
    )
    print(f"   已在狙击区 🟢: {in_zone} 只 | 逼近中 🟡: {approaching} 只")
    print(f"   趋势健康 ≥3/4: {healthy} 只")

    print(f"\n🔍 粗筛 Top {len(fine_df)} 送入细筛 (PSS 评分):")
    for i, (_, r) in enumerate(fine_df.iterrows(), 1):
        e = {"in_zone": "🟢", "approaching": "🟡", "oversold": "🔵"}.get(
            r["sniper_status"], "⚪"
        )
        pss = r.get("pss", 0)
        print(
            f"   #{i} {e} {r['code']} {r['name']:6s} | PSS:{pss:.1f} | "
            f"¥{r['price']:.2f} | 距击球点 {r['dist_to_sniper_pct']:+.1f}% | PE:{r.get('pe', '?')}"
        )

    if fine_skipped:
        reason = fine_skip_reason or "未配置 DEEPSEEK_API_KEY"
        print(f"\n⚠️ 细筛未执行：{reason}。以下为粗筛AI原始输出:")
        print("-" * 80)
        print(coarse_raw[:2000])
        print("-" * 80)
    else:
        print("\\n🎯 候选池分析:")
        print("-" * 80)
        print(fine_report)
        print("-" * 80)

    print(f"\n⏱️ 总耗时: {elapsed:.1f} 秒")
    print("⚠️ 免责声明: 本报告由量化模型和AI生成，仅供研究参考，不构成投资建议。")
    print("=" * 80 + "\n")


# ============================================================
#  Main
# ============================================================


def main():
    global PRICE_MIN, PRICE_MAX, PE_MIN, PE_MAX, COARSE_N, FINE_N, FINAL_N

    p = argparse.ArgumentParser(description="A股回调强买扫描器 — 回调强买策略")
    p.add_argument("--price-min", type=float, default=PRICE_MIN)
    p.add_argument("--price-max", type=float, default=PRICE_MAX)
    p.add_argument("--pe-min", type=float, default=PE_MIN)
    p.add_argument("--pe-max", type=float, default=PE_MAX)
    p.add_argument("--coarse-n", type=int, default=COARSE_N)
    p.add_argument("--fine-n", type=int, default=FINE_N)
    p.add_argument("--final-n", type=int, default=FINAL_N)
    p.add_argument("--coarse-model", default=COARSE_MODEL)
    p.add_argument("--fine-model", default=FINE_MODEL)
    p.add_argument(
        "--fine-api-key",
        default=None,
        help="DeepSeek API Key（或设 DEEPSEEK_API_KEY 环境变量）",
    )
    p.add_argument("--fine-base-url", default=FINE_BASE_URL)
    p.add_argument("--skip-coarse", action="store_true")
    p.add_argument("--skip-fine", action="store_true")
    p.add_argument("--skip-veto", action="store_true", help="跳过 AnySearch 公告排雷")
    p.add_argument("--output", default=None, help="JSON 输出路径")
    args = p.parse_args()

    PRICE_MIN, PRICE_MAX = args.price_min, args.price_max
    PE_MIN, PE_MAX = args.pe_min, args.pe_max
    COARSE_N, FINE_N, FINAL_N = args.coarse_n, args.fine_n, args.final_n

    t0 = time.time()

    try:
        _main_impl(args, t0)
    except Exception:
        logger.exception("扫描器致命异常，输出错误报告")
        elapsed = time.time() - t0
        print("\n" + "=" * 80)
        print("  ❌ A股狙击扫描报告 — 执行异常")
        print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"  错误: {sys.exc_info()[1]}")
        print("=" * 80)
        print("⚠️ 请检查网络、Ollama 服务、API Key 等基础设施。")
        print(f"⏱️ 存活时间: {elapsed:.1f} 秒")
        print("=" * 80 + "\n")
        sys.exit(1)


def _main_impl(args, t0: float):
    # 1. 数据
    stocks = fetch_snapshot()
    df = snapshot_to_df(stocks)

    # 2. 狙击初筛
    df = sniper_filter(df)
    df = calc_sniper_metrics(df)
    candidates = pick_top(df, COARSE_N)

    if candidates.empty:
        logger.warning("无候选股票，放宽条件重试。")
        return

    # 2.5. 一票否决检查（强周期+趋势恶化 / 下跌加速崩溃）
    candidates, veto_log = veto_check(candidates)

    if candidates.empty:
        logger.warning("所有候选被一票否决，终止扫描。")
        return

    # 3. PSS 精准狙击评分（先筛：在所有50只上打分）
    candidates = calc_pss_scores(candidates)

    # 3.5. AnySearch 公告排雷（量化层最后一关：减持/质押/监管函）
    if not args.skip_veto:
        candidates, veto_log = anysearch_veto_scan(candidates, max_stocks=FINE_N)
        if candidates.empty:
            logger.warning("所有候选被公告排雷否决，终止扫描。")
            return

    # 4. Ollama 验证（后验：辨别 PSS Top 15 中的金子 vs 石块）
    pss_top15 = candidates.head(FINE_N)
    if args.skip_coarse:
        fine_candidates = pss_top15
        coarse_raw = "(已跳过)"
    else:
        cp = build_coarse_prompt(pss_top15)
        coarse_raw = call_ollama(cp, args.coarse_model)
        fine_candidates = parse_coarse(coarse_raw, pss_top15, FINE_N)

    # 5. DeepSeek 细筛
    api_key = args.fine_api_key or os.getenv("DEEPSEEK_API_KEY")
    logger.info(
        f"DeepSeek API Key: {'✅ 已配置' if api_key else '❌ 未配置'} ({len(api_key) if api_key else 0} chars)"
    )
    fine_skipped = False
    fine_skip_reason = ""
    fine_report = ""

    if args.skip_fine or not api_key:
        fine_skipped = True
        fine_skip_reason = "已跳过" if args.skip_fine else "未配置 DEEPSEEK_API_KEY"
        if not api_key and not args.skip_fine:
            logger.warning("未配置 DEEPSEEK_API_KEY，跳过细筛。")
    else:
        fp = build_fine_prompt(fine_candidates, args.final_n)
        try:
            fine_report = call_fine(fp, api_key, args.fine_base_url, args.fine_model)
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if hasattr(e, "response") else "?"
            fine_skip_reason = f"API 认证失败 (HTTP {status})"
            logger.error(
                f"细筛 API 认证失败 (HTTP {status})。请检查 ~/.hermes/.env 中 DEEPSEEK_API_KEY 是否正确。"
            )
            fine_skipped = True
        except Exception as e:
            fine_skip_reason = f"网络/API 连接异常"
            logger.error(f"细筛失败: {e}，输出粗筛结果。")
            fine_skipped = True

    # 6. 输出
    elapsed = time.time() - t0
    print_report(
        candidates, fine_candidates, coarse_raw, fine_report, elapsed,
        fine_skipped, fine_skip_reason
    )

    # 7. 昨日对比 + 保存候选池
    compare_yesterday(fine_candidates, fine_report, fine_skipped, PRINCIPAL)

    # 8. 保存候选池 JSON 供 14:30 尾盘分析使用
    try:
        sniper_candidates = []
        for _, r in fine_candidates.head(FINAL_N).iterrows():
            ma20 = round(r.get("ma20", 0), 2)
            entry = round(r["price"], 2)
            sniper_candidates.append({
                "code": r["code"],
                "name": r["name"],
                "price": entry,
                "ma20": ma20,
                "dist_ma20_pct": round((entry - ma20) / ma20 * 100, 1) if ma20 > 0 else 0,
                "stop": round(ma20 * (1 + STOP_MA20_MARGIN), 2) if ma20 > 0 else entry,
                "target": round(entry * (1 + TAKE_PROFIT_PCT_NEW), 2),
                "rr_ratio": round(abs((entry * (1 + TAKE_PROFIT_PCT_NEW) - entry) / (entry - ma20 * (1 + STOP_MA20_MARGIN))), 2) if ma20 > 0 and entry > ma20 else 0,
                "pss": round(r.get("pss", 0), 1),
                "pe": r.get("pe", 0),
                "trend_health": int(r.get("trend_health", 0)),
            })
        os.makedirs(os.path.dirname(CANDIDATES_FILE), exist_ok=True)
        with open(CANDIDATES_FILE, "w") as f:
            json.dump({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "time": datetime.now().strftime("%H:%M"),
                "candidates": sniper_candidates,
            }, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 候选池已保存至 {CANDIDATES_FILE} ({len(sniper_candidates)} 只)")
    except Exception as e:
        logger.warning(f"保存候选池失败: {e}")

    # 8. 保存
    if args.output:
        report = {
            "timestamp": datetime.now().isoformat(),
            "candidates": candidates.head(COARSE_N)
            .replace({np.nan: None})
            .to_dict("records"),
            "fine_candidates": fine_candidates.replace({np.nan: None}).to_dict(
                "records"
            ),
            "coarse_raw": coarse_raw,
            "fine_report": fine_report,
            "fine_skipped": fine_skipped,
            "elapsed_sec": elapsed,
        }
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"报告已保存: {args.output}")


if __name__ == "__main__":
    main()
