#!/usr/bin/env python3
"""
Closing Analysis — 策略 14:30 尾盘综合分析
===========================================
输入：早盘候选池 + 实时行情
输出：大盘状态 + 候选触发器检查 + 入场建议

架构：
  1. 拉实时行情（腾讯API）
  2. 读取早盘候选池 JSON
  3. 逐一检查入场触发器状态（策略二）+ 突破状态（策略一）
  4. 输出「尾盘快报」→ 用户14:30决策
"""
import os, sys, json, time, logging
from datetime import datetime
from typing import List, Dict, Optional

import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/.hermes/.env"), override=True)

# ── 配置 ──────────────────────────────────────────
CANDIDATE_DIR = os.path.expanduser("~/.hermes/data")
SNIPER_CANDIDATES = os.path.join(CANDIDATE_DIR, "sniper_candidates.json")
BREAKOUT_CANDIDATES = os.path.join(CANDIDATE_DIR, "breakout_yesterday.json")
TENCENT_URL = "https://qt.gtimg.cn/q={codes}"
BATCH_SIZE = 50
HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.qq.com/"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def fetch_realtime(codes: List[str]) -> Dict[str, Dict]:
    """从腾讯API拉取实时行情"""
    results = {}
    for i in range(0, len(codes), BATCH_SIZE):
        batch = codes[i:i + BATCH_SIZE]
        # 构造腾讯代码格式
        tcodes = [f"{'sh' if c.startswith(('6','5','9')) else 'sz'}{c}" for c in batch]
        url = TENCENT_URL.format(codes=",".join(tcodes))
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            r.encoding = "gbk"
            for line in r.text.strip().split("\n"):
                if not line.strip() or "=" not in line:
                    continue
                # 格式: v_sh600000="1~平安银行~000001~..."
                parts = line.split('"')[1].split("~")
                if len(parts) < 50:
                    continue
                code = parts[2]  # 纯数字代码
                results[code] = {
                    "name": parts[1],
                    "price": float(parts[3]) if parts[3] else 0,
                    "change_pct": float(parts[32]) if parts[32] else 0,
                    "high": float(parts[33]) if parts[33] else 0,
                    "low": float(parts[34]) if parts[34] else 0,
                    "volume": float(parts[36]) if parts[36] else 0,
                    "amount": float(parts[37]) if parts[37] else 0,
                    "pe": float(parts[39]) if parts[39] else 0,
                    "ret_5d": float(parts[62]) if parts[62] else 0,
                    "ret_20d": float(parts[64]) if parts[64] else 0,
                }
        except Exception as e:
            logger.error(f"获取行情失败 ({','.join(tcodes[:3])}...): {e}")
    return results


def load_candidates(filepath: str) -> List[Dict]:
    """加载早盘候选池"""
    if not os.path.exists(filepath):
        return []
    with open(filepath) as f:
        return json.load(f)


def check_triggers(
    morning: Dict, now: Dict
) -> Dict[str, str]:
    """
    检查策略二入场触发器状态

    返回: {trigger_name: status_emoji}
    🟢 = 已触发
    🔴 = 未触发
    ⚪ = 数据不足
    """
    triggers = {}

    # 触发器1: 缩量止跌
    # 今日量 < 昨日量 × 0.7 且 收阳
    # 早盘数据中有昨日量吗？需要从快照中获取
    # 这里用近似判断：如果涨跌幅 > 0 且开盘后可判断
    triggers["缩量止跌"] = "⚪"  # 数据不足，需要盘口判断

    # 触发器2: V反信号
    # 盘中低点接近 MA20 且当前价明显高于低点（真V反，非单纯靠拢）
    ma20 = morning.get("ma20", 0)
    low = now.get("low", 0)
    if ma20 > 0 and low > 0:
        dist_to_ma20 = (low - ma20) / ma20 * 100 if ma20 > 0 else 999
        recovery = (now["price"] - low) / low * 100 if low > 0 else 0
        if dist_to_ma20 <= 1 and recovery >= 1.0:
            triggers["V反信号"] = f"🟢 探底{low:.2f}→反弹+{recovery:.1f}%"
        elif dist_to_ma20 <= 1:
            triggers["V反信号"] = f"🔴 触及但反弹不足(+{recovery:.1f}%)"
        else:
            triggers["V反信号"] = f"🔴 距MA20{dist_to_ma20:+.1f}%"
    else:
        triggers["V反信号"] = "⚪"

    # 触发器3: 均线企稳
    # 盘中触及 MA20 后反弹 → 当前价 > MA20
    if ma20 > 0 and now["price"] > 0:
        above_ma = now["price"] > ma20
        dist_ma = (now["price"] - ma20) / ma20 * 100
        triggers["均线企稳"] = f"🔴 +{dist_ma:.1f}%" if above_ma and dist_ma > 1 else (
            "🟢 贴近" if abs(dist_ma) <= 1 else f"🔴 {dist_ma:+.1f}%"
        )
    else:
        triggers["均线企稳"] = "⚪"

    return triggers


def fetch_market_breadth() -> Dict:
    """获取大盘涨跌比"""
    # 用上证/深证/创业板指数近似
    indices = {
        "上证": "sh000001",
        "深证": "sz399001",
        "创业板": "sz399006",
        "上证50": "sh000016",
    }
    result = {}
    for name, code in indices.items():
        try:
            r = requests.get(f"{TENCENT_URL.format(codes=code)}", headers=HEADERS, timeout=5)
            r.encoding = "gbk"
            parts = r.text.split('"')[1].split("~")
            result[name] = {
                "price": float(parts[3]) if parts[3] else 0,
                "change_pct": float(parts[32]) if parts[32] else 0,
            }
        except Exception:
            result[name] = {"price": 0, "change_pct": 0}
    return result


def main():
    t0 = time.time()
    now_str = datetime.now().strftime("%H:%M")

    print("=" * 80)
    print(f"  📊 14:30 尾盘快报 — {datetime.now().strftime('%Y-%m-%d')} {now_str}")
    print(f"  策略: 回调强买(主线) + 量价突破(辅线) | 操作窗口: 14:30-15:00")
    print("=" * 80)

    # 1. 大盘环境
    print("\n📈 大盘环境")
    print("-" * 40)
    try:
        breadth = fetch_market_breadth()
        for name, data in breadth.items():
            emoji = "🟢" if data["change_pct"] > 0 else ("🔴" if data["change_pct"] < 0 else "⚪")
            print(f"  {emoji} {name}: {data['price']:.2f} ({data['change_pct']:+.2f}%)")
    except Exception as e:
        print(f"  ⚠️ 大盘数据获取失败: {e}")

    # 2. 策略二候选池检查
    sniper_raw = load_candidates(SNIPER_CANDIDATES)
    sniper = sniper_raw.get("candidates", sniper_raw) if isinstance(sniper_raw, dict) else sniper_raw
    breakout = load_candidates(BREAKOUT_CANDIDATES)
    breakout = breakout if isinstance(breakout, list) else breakout.get("candidates", []) if isinstance(breakout, dict) else []

    print(f"\n🎯 策略二 — 回调强买候选 ({len(sniper)} 只)")
    print("-" * 40)

    if not sniper:
        print("  📭 今日早盘无候选（可能市场环境不适合回调策略）")
    else:
        # 拉取候选实时行情
        sniper_codes = [s.get("code", "") for s in sniper if s.get("code")]
        if sniper_codes:
            live = fetch_realtime(sniper_codes)
        else:
            live = {}

        action_items = []
        for s in sniper:
            code = s.get("code", "")
            name = s.get("name", "")
            now = live.get(code, {})

            if not now:
                print(f"  ⚪ {code} {name}: 实时数据缺失")
                continue

            ma20 = s.get("ma20", 0)
            morning_price = s.get("price", 0)
            current_price = now.get("price", 0)
            dist_ma = (current_price - ma20) / ma20 * 100 if ma20 > 0 else 0

            triggers = check_triggers(s, now)
            trigger_hits = sum(1 for v in triggers.values() if v.startswith("🟢"))
            trigger_str = " | ".join(f"{k}:{v}" for k, v in triggers.items())

            entry_ready = trigger_hits >= 1
            status = "🟢 可入场" if entry_ready else "🔴 等待"

            print(f"  {status} {code} {name} ¥{current_price:.2f} "
                  f"({now.get('change_pct', 0):+.1f}%) | 距MA20: {dist_ma:+.1f}%")
            print(f"    触发器: {trigger_str}")
            print(f"    止损: ¥{s.get('stop', 0):.2f} | 目标: ¥{s.get('target', 0):.2f} | "
                  f"风报比: {s.get('rr_ratio', 0):.2f}")

            if entry_ready:
                action_items.append({
                    "code": code, "name": name, "price": current_price,
                    "stop": s.get("stop", 0), "target": s.get("target", 0),
                    "triggers": [k for k, v in triggers.items() if v.startswith("🟢")],
                })
            print()

    # 3. 策略一突破检查
    print(f"🚀 策略一 — 量价突破候选 ({len(breakout)} 只)")
    print("-" * 40)

    if not breakout:
        print("  📭 今日早盘无突破候选")
    else:
        breakout_codes = [b.get("code", "") for b in breakout if b.get("code")]
        if breakout_codes:
            live_bo = fetch_realtime(breakout_codes)
        else:
            live_bo = {}

        for b in breakout:
            code = b.get("code", "")
            name = b.get("name", "")
            now = live_bo.get(code, {})
            if not now:
                print(f"  ⚪ {code} {name}: 实时数据缺失")
                continue
            change = now.get("change_pct", 0)
            status = "🟢" if change > 0 else ("🔴" if change < -2 else "🟡")
            print(f"  {status} {code} {name} ¥{now['price']:.2f} ({change:+.1f}%) | "
                  f"止损: ¥{b.get('stop', 0):.2f} | 目标: ¥{b.get('target', 0):.2f}")
        print()

    # 4. 入场建议
    print("💡 入场建议")
    print("-" * 40)

    s_ready = sum(1 for s in sniper if any(
        v.startswith("🟢") for v in check_triggers(s, live.get(s.get("code", ""), {})).values()
    )) if sniper and sniper_codes else 0

    b_ok = sum(1 for b in breakout if live_bo.get(b.get("code", ""), {}).get("change_pct", 0) > 0) if breakout and breakout_codes else 0

    if s_ready == 0 and b_ok == 0:
        print("  🏁 今日建议: 观望")
        print("  理由: 候选池未触发入场条件，保留候选池等明日")
        print("  纪律: 宁可错过，不做勉强交易")
    else:
        if s_ready > 0:
            print(f"  🎯 策略二: {s_ready} 只触发入场条件，可考虑入场")
        if b_ok > 0:
            print(f"  🚀 策略一: {b_ok} 只上涨中，可考虑短线跟进")
        print(f"  ⏰ 操作窗口: 14:30-15:00，请决策后下单")

    print(f"\n⏱️ 总耗时: {time.time() - t0:.1f} 秒")
    print("⚠️ 免责声明: 本报告仅供参考，不构成投资建议。请自行判断。")
    print("=" * 80)


if __name__ == "__main__":
    main()
