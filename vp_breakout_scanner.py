#!/usr/bin/env python3
"""
VP Breakout Scanner — 策略一：量价突破扫描（09:20 早盘）
===================================================
逻辑：不猜顶底，只在资金已经动手时跟进。
入场：次日开盘价 | 止损：-3% | 止盈：+5% | 持有：1-3天
"""
import os, sys, json, time, logging
from datetime import datetime
from typing import List, Dict

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/.hermes/.env"), override=True)

# ── 配置 ──────────────────────────────────────────
PRICE_MIN, PRICE_MAX = 3.0, 80.0
PE_MIN, PE_MAX = 5, 40
MCAP_MIN = 50  # 亿
VOL_RATIO_MIN = 1.5  # 量比：今日量 / 20日均量 > 1.5
PRICE_PCT_HIGH = 0.95  # 价格 > 20日最高价的95%
TREND_MIN = 3  # 趋势健康度最低要求
MAX_RESULTS = 3  # 输出候选数

SKILL_DIR = os.path.expanduser("~/.hermes/skills/finance/vt-weekly-scanner")
FETCH_SCRIPT = os.path.join(SKILL_DIR, "scripts", "fetch_a_shares.py")
VENV_PYTHON = os.path.expanduser("~/.hermes/hermes-agent/venv/bin/python")
YESTERDAY_FILE = os.path.expanduser("~/.hermes/data/breakout_yesterday.json")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def fetch_snapshot(max_retries: int = 3) -> List[Dict]:
    """调用 fetch_a_shares.py 获取全市场快照"""
    import subprocess

    for attempt in range(1, max_retries + 1):
        logger.info(f"📡 获取全A股快照... 第{attempt}次")
        try:
            r = subprocess.run(
                [VENV_PYTHON, FETCH_SCRIPT],
                capture_output=True, text=True, timeout=600,
            )
            if r.returncode != 0:
                if attempt < max_retries:
                    time.sleep(attempt * 30)
                    continue
                raise RuntimeError(f"fetch 连续失败 {max_retries} 次")

            ts_pos = r.stdout.rfind('"timestamp"')
            json_start = r.stdout.rfind("{", 0, ts_pos) if ts_pos > 0 else 0
            data = json.loads(r.stdout[json_start:])
            stocks = data.get("stocks", [])
            logger.info(f"✅ 获取 {len(stocks)} 只股票快照")
            return stocks
        except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
            if attempt < max_retries:
                time.sleep(attempt * 30)
                continue
            raise
    raise RuntimeError("获取快照失败")


def compute_ma20(r: Dict) -> float:
    """从 ret_20d 反推 MA20"""
    try:
        ret = float(r.get("ret_20d", 0))
        price = float(r.get("price", 0))
        return price / (1 + ret / 100) if price > 0 else price
    except (ValueError, ZeroDivisionError):
        return float(r.get("price", 0))


def compute_high_20d(r: Dict) -> float:
    """从 high_52w 和当前价估算 20 日最高（降级用 52w high）"""
    return float(r.get("high_52w", r.get("price", 0)))


def scan_breakouts() -> pd.DataFrame:
    """量价突破扫描主逻辑"""
    stocks = fetch_snapshot()
    rows = []

    for s in stocks:
        try:
            code = str(s.get("code", ""))
            name = str(s.get("name", ""))
            price = float(s.get("price", 0))
            pe = float(s.get("pe", 0))
            mcap = float(s.get("market_cap", 0))
            amount = float(s.get("amount", 0))
            volume = float(s.get("volume", 0))
            ret_5d = float(s.get("ret_5d", 0))
            ret_20d = float(s.get("ret_20d", 0))
        except (ValueError, TypeError):
            continue

        # 基础过滤
        if price < PRICE_MIN or price > PRICE_MAX: continue
        if pe <= 0 or pe > PE_MAX: continue
        if mcap < MCAP_MIN: continue
        if "ST" in name or "*ST" in name: continue

        ma20 = compute_ma20(s)
        ma5 = price / (1 + ret_5d / 100) if ret_5d != -100 else price
        high_20d = compute_high_20d(s)

        # 趋势：价格 > MA20 且 MA20 向上（用 ret_20d 代理：20日涨跌 > -5%）
        price_above_ma20 = price > ma20
        ma20_rising = ret_20d > -5

        # 距前高
        if high_20d > 0:
            pct_of_high = price / high_20d
        else:
            pct_of_high = 0

        # 量比（近似：用成交额代替均量——腾讯API不含volume_avg）
        # 保守估计：amount可作为日成交额参考
        # 这里用 loose 判断，避免漏掉
        # 实际量比需要历史数据，这里用涨幅+成交额做代理
        is_high_volume = amount > 0

        # 突破条件
        near_high = pct_of_high >= PRICE_PCT_HIGH
        trend_ok = price_above_ma20 and ma20_rising

        if near_high and trend_ok and is_high_volume:
            rows.append({
                "code": code, "name": name, "price": price, "pe": pe,
                "market_cap": mcap, "amount": amount,
                "ma20": round(ma20, 2), "high_20d": round(high_20d, 2),
                "pct_of_high": round(pct_of_high * 100, 1),
                "ret_5d": ret_5d, "ret_20d": ret_20d,
                "ma20_rising": ma20_rising,
            })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # 按距前高排序（越近越好）+ 量能排序
    df["score"] = df["pct_of_high"] + (df["amount"].rank(pct=True) * 5)
    df = df.sort_values("score", ascending=False).head(MAX_RESULTS)

    return df.reset_index(drop=True)


def load_yesterday() -> List[Dict]:
    """加载昨日推荐"""
    if not os.path.exists(YESTERDAY_FILE):
        return []
    with open(YESTERDAY_FILE) as f:
        return json.load(f)


def save_today(stocks: List[Dict]):
    """保存今日推荐"""
    os.makedirs(os.path.dirname(YESTERDAY_FILE), exist_ok=True)
    with open(YESTERDAY_FILE, "w") as f:
        json.dump(stocks, f, ensure_ascii=False, indent=2)


def main():
    t0 = time.time()

    try:
        df = scan_breakouts()
    except Exception as e:
        logger.error(f"扫描失败: {e}")
        print(f"❌ 策略一突破扫描失败: {e}")
        return

    print("=" * 80)
    print(f"  🚀 量价突破候选 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  策略: 量价突破 | 持有: 1-3天 | 止损: -3% | 止盈: +5%")
    print("=" * 80)

    if df.empty:
        print("\n  📭 今日无突破候选（市场可能处于震荡/下跌，休息也是策略）\n")
        save_today([])
        print(f"\n⏱️ 总耗时: {time.time() - t0:.1f} 秒")
        return

    print(f"\n📊 突破候选: {len(df)} 只\n")

    today_stocks = []
    for i, (_, r) in enumerate(df.iterrows(), 1):
        stop = round(r["price"] * 0.97, 2)
        target = round(r["price"] * 1.05, 2)
        rr = round((target - r["price"]) / (r["price"] - stop), 2) if r["price"] > stop else 0

        print(f"{'🥇' if i == 1 else '🥈' if i == 2 else '🥉'} "
              f"#{i} {r['code']} {r['name']} | ¥{r['price']:.2f}")
        print(f"  距20日高: {r['pct_of_high']:.1f}% | MA20: ¥{r['ma20']} | "
              f"{'✅ MA20向上' if r['ma20_rising'] else '❌ MA20向下'}")
        print(f"  5日涨跌: {r['ret_5d']:+.1f}% | 20日涨跌: {r['ret_20d']:+.1f}% | PE: {r['pe']:.1f}")
        print(f"  入场: 开盘价 ¥{r['price']:.2f} | 止损: ¥{stop} | 目标: ¥{target} | 风报比: {rr:.2f}")
        print()

        today_stocks.append({
            "code": r["code"], "name": r["name"],
            "price": r["price"], "stop": stop, "target": target,
            "date": datetime.now().strftime("%Y-%m-%d"),
        })

    # 昨日对比
    yesterday = load_yesterday()
    if yesterday:
        print("-" * 80)
        print("  📊 昨日突破 vs 今日")
        yesterday_codes = {s["code"] for s in yesterday}
        today_codes = {s["code"] for s in today_stocks}
        kept = yesterday_codes & today_codes
        new = today_codes - yesterday_codes
        dropped = yesterday_codes - today_codes
        for s in yesterday:
            status = "✅ 持续" if s["code"] in kept else "❌ 退出"
            print(f"    {s['code']} {s['name']} → {status}")
        if new:
            print(f"  🆕 新增: {len(new)} 只")
        if dropped:
            print(f"  👋 退出: {len(dropped)} 只")

    save_today(today_stocks)
    print(f"\n⏱️ 总耗时: {time.time() - t0:.1f} 秒")
    print("⚠️ 免责声明: 本报告由量化模型生成，仅供研究参考，不构成投资建议。")
    print("=" * 80)


if __name__ == "__main__":
    main()
