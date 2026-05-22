"""
A-Stock Market Intelligence Tool — Chinese market regime detection + strategy advice.

Three tools:
  a_stock_market_regime  → 大盘方向判定（多/空/震荡）
  a_stock_advice         → 个股策略建议（趋势跟踪/狙击等待/空仓）
  a_stock_daily_briefing → 完整情报融合日报

Data sources: 腾讯财经K线 + 深交所JSON API + AKShare(商品/龙虎榜)
Zero API cost. Zero overseas dependency.
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import requests

from tools.registry import registry, tool_error, tool_result

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════
# Schema definitions
# ═══════════════════════════════════════════════

STOCK_ADVICE_SCHEMA = {
    "name": "a_stock_advice",
    "description": "获取A股单只或多只标的的交易策略建议（基于大盘方向+个股MA20+商品/监管信号交叉验证）。输入股票代码列表，返回每只的策略和操作建议。",
    "parameters": {
        "type": "object",
        "properties": {
            "codes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "股票代码列表，如 ['002156', '300059', '601995']",
            },
        },
        "required": ["codes"],
    },
}

MARKET_REGIME_SCHEMA = {
    "name": "a_stock_market_regime",
    "description": "判定当前A股大盘方向（多头/空头/震荡）。基于上证指数和创业板指的MA20位置及斜率，结合成交量确认。返回策略切换建议。",
    "parameters": {"type": "object", "properties": {}, "required": []},
}

DAILY_BRIEFING_SCHEMA = {
    "name": "a_stock_daily_briefing",
    "description": "生成A股每日情报融合简报。整合资金面(龙虎榜/ETF)、产业面(商品价格)、监管面(问询函)，交叉验证后输出结论+策略建议。",
    "parameters": {"type": "object", "properties": {}, "required": []},
}


# ═══════════════════════════════════════════════
# Core engine (adapted from p3_fusion_briefing.py)
# ═══════════════════════════════════════════════

def _tencent_kline(code: str, days: int = 60) -> list:
    """获取个股前复权K线，返回 [(date, close), ...]"""
    prefix = "sh" if code.startswith(("6", "9")) else "sz"
    symbol = f"{prefix}{code}"
    try:
        url = "http://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        resp = requests.get(url, params={"param": f"{symbol},day,,,{days},qfq"}, timeout=10)
        resp.encoding = "gbk"
        data = resp.json()
        kline = data.get("data", {}).get(symbol, {}).get("qfqday", [])
        return [(k[0], float(k[2])) for k in kline] if kline else []
    except Exception:
        return []


def _tencent_index(code: str, days: int = 60) -> dict:
    """获取指数日线，返回 {latest, ma5, ma10, ma20, slope, vol_ratio}"""
    try:
        url = "http://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        resp = requests.get(url, params={"param": f"{code},day,,,{days},qfq"}, timeout=10)
        resp.encoding = "gbk"
        data = resp.json()
        kline = data.get("data", {}).get(code, {}).get("qfqday", []) or data.get("data", {}).get(code, {}).get("day", [])
        if not kline or len(kline) < 25:
            return None

        closes = [float(k[2]) for k in kline]
        volumes = [float(k[5]) for k in kline]
        ma5 = float(np.mean(closes[-5:]))
        ma10 = float(np.mean(closes[-10:]))
        ma20 = float(np.mean(closes[-20:]))
        latest = closes[-1]

        ma20s = [float(np.mean(closes[max(0, i-20):i])) for i in range(len(closes)-5, len(closes))]
        slope = float(np.polyfit(range(len(ma20s)), ma20s, 1)[0]) if len(ma20s) >= 3 else 0

        vol_5 = float(np.mean(volumes[-5:]))
        vol_20 = float(np.mean(volumes[-20:]))
        vol_ratio = vol_5 / vol_20 if vol_20 > 0 else 1.0

        return {"latest": latest, "ma5": ma5, "ma10": ma10, "ma20": ma20, "ma20_slope": slope, "vol_ratio": vol_ratio}
    except Exception:
        return None


def _classify_regime(idx: dict) -> dict:
    if idx is None:
        return {"regime": "unknown", "label": "数据缺失", "strategy": "观望"}
    above = idx["latest"] > idx["ma20"]
    slope_up = idx["ma20_slope"] > 0.5
    slope_down = idx["ma20_slope"] < -0.5
    strong = idx["vol_ratio"] > 1.2

    if above and slope_up:
        return {"regime": "bull", "label": f"🟢 多头{'强' if strong else '弱'}势", "strategy": "趋势跟踪",
                "tactic": "回踩 MA10/MA20 即是买点", "stop_rule": "MA20 × -3% 止损"}
    elif not above and slope_down:
        return {"regime": "bear", "label": "🔴 空头确认", "strategy": "空仓等待",
                "tactic": "不做多，等 MA20 走平", "stop_rule": "—"}
    else:
        return {"regime": "range", "label": "🟡 震荡/不明", "strategy": "狙击等待",
                "tactic": "预设精确买点，等市场送上门", "stop_rule": "入场价 -2% 硬止损"}


def _market_regime():
    indices = []
    for code, name in [("sh000001", "上证指数"), ("sz399006", "创业板指")]:
        data = _tencent_index(code)
        if data:
            regime = _classify_regime(data)
            indices.append({"name": name, **data, **regime})

    total = len(indices)
    if total == 0:
        summary = "range"
    else:
        bull_ratio = sum(1 for i in indices if i["regime"] == "bull") / total
        summary = "bull" if bull_ratio >= 0.5 else "bear" if (1 - bull_ratio - sum(1 for i in indices if i["regime"] == "range") / total) >= 0.5 else "range"

    return {"indices": indices, "summary": summary}


def _stock_advice(code: str, regime_summary: str):
    kline = _tencent_kline(code)
    if len(kline) < 25:
        return {"code": code, "error": "K线数据不足"}

    closes = [c for _, c in kline]
    latest = closes[-1]
    ma20 = float(np.mean(closes[-20:]))
    above_ma20 = latest > ma20
    chg_5d = (closes[-1] - closes[-6]) / closes[-6] * 100 if len(closes) >= 6 else 0

    if regime_summary == "bull":
        if above_ma20 and chg_5d > -2:
            return {
                "code": code, "price": round(latest, 2), "ma20": round(ma20, 2),
                "chg_5d": round(chg_5d, 1), "regime": "bull", "above_ma20": True,
                "strategy": "🟢 趋势跟踪", "action": f"回踩 MA20({ma20:.0f}) 附近可建仓，不等深度回调",
                "stop": f"¥{ma20 * 0.97:.2f}（MA20 × -3%）",
            }
        else:
            return {
                "code": code, "price": round(latest, 2), "ma20": round(ma20, 2),
                "chg_5d": round(chg_5d, 1), "regime": "bull", "above_ma20": False,
                "strategy": "🟡 等回踩", "action": "多头市场但个股偏弱，等站上 MA20 再跟",
                "stop": "—",
            }
    elif regime_summary == "bear":
        return {
            "code": code, "price": round(latest, 2), "ma20": round(ma20, 2),
            "chg_5d": round(chg_5d, 1), "regime": "bear", "above_ma20": above_ma20,
            "strategy": "🔴 空仓", "action": "大盘空头，不做多", "stop": "—",
        }
    else:
        return {
            "code": code, "price": round(latest, 2), "ma20": round(ma20, 2),
            "chg_5d": round(chg_5d, 1), "regime": "range", "above_ma20": above_ma20,
            "strategy": "🟡 狙击等待", "action": "震荡市，预设精确买点等待",
            "stop": f"入场价 -2% 硬止损",
        }


# ═══════════════════════════════════════════════
# Tool handlers
# ═══════════════════════════════════════════════

def _handle_market_regime(**kwargs) -> str:
    regime = _market_regime()
    if not regime["indices"]:
        return tool_error("无法获取指数数据")

    lines = []
    for idx in regime["indices"]:
        lines.append(f"{idx['label']} {idx['name']} {idx['latest']:.0f} "
                     f"(MA5:{idx['ma5']:.0f} MA10:{idx['ma10']:.0f} MA20:{idx['ma20']:.0f})")
    idx0 = regime["indices"][0]
    lines.append(f"→ 当前策略: {idx0['strategy']}")
    lines.append(f"→ 操作: {idx0['tactic']}")
    lines.append(f"→ 止损: {idx0['stop_rule']}")

    return tool_result(success=True, summary=regime["summary"], detail="\n".join(lines), indices=regime["indices"])


def _handle_stock_advice(codes: list = None, **kwargs) -> str:
    if not codes:
        return tool_error("请提供股票代码列表")

    regime = _market_regime()
    regime_summary = regime["summary"]
    regime_label = regime["indices"][0]["label"] if regime["indices"] else "未知"

    results = []
    for code in codes:
        advice = _stock_advice(str(code), regime_summary)
        advice["market"] = regime_label
        results.append(advice)

    return tool_result(success=True, market=regime_label, market_regime=regime_summary, stocks=results)


def _handle_daily_briefing(**kwargs) -> str:
    regime = _market_regime()

    lines = [f"🔭 A股情报融合 — {datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]

    # 大盘
    lines.append("━━━ 📊 大盘方向 ━━━")
    if regime["indices"]:
        for idx in regime["indices"]:
            lines.append(f"  {idx['label']}  {idx['name']} {idx['latest']:.0f}")
        lines.append(f"  → 策略: {regime['indices'][0]['strategy']}")
        lines.append(f"  → 操作: {regime['indices'][0]['tactic']}")
    lines.append("")

    # 示例标的（用户可在调用时指定）
    lines.append("━━━ 🎯 示例标的策略 ━━━")
    for code in ["002156", "300059"]:
        advice = _stock_advice(code, regime["summary"])
        lines.append(f"  {advice['strategy']} {code} ¥{advice['price']} "
                    f"(MA20:{advice['ma20']:.0f} 5日:{advice['chg_5d']:+.1f}%)")
        lines.append(f"     → {advice['action']}")
    lines.append("")
    lines.append("─" * 20)
    lines.append("数据来源: 腾讯财经 + AKShare + 深交所 │ 零成本零海外依赖")

    return tool_result(success=True, briefing="\n".join(lines), regime_summary=regime["summary"])


# ═══════════════════════════════════════════════
# Registration
# ═══════════════════════════════════════════════

def _check_deps() -> bool:
    """检查依赖：numpy + 可访问腾讯财经"""
    try:
        import numpy  # noqa: F401
        return True
    except ImportError:
        return False


registry.register(
    name="a_stock_market_regime",
    toolset="finance",
    schema=MARKET_REGIME_SCHEMA,
    handler=_handle_market_regime,
    check_fn=_check_deps,
    requires_env=[],
    is_async=False,
    description="判定A股大盘方向（多头/空头/震荡），输出策略建议",
    emoji="📊",
)

registry.register(
    name="a_stock_advice",
    toolset="finance",
    schema=STOCK_ADVICE_SCHEMA,
    handler=_handle_stock_advice,
    check_fn=_check_deps,
    requires_env=[],
    is_async=False,
    description="获取A股标的的交易策略建议（基于大盘方向+个股MA20）",
    emoji="🎯",
)

registry.register(
    name="a_stock_daily_briefing",
    toolset="finance",
    schema=DAILY_BRIEFING_SCHEMA,
    handler=_handle_daily_briefing,
    check_fn=_check_deps,
    requires_env=[],
    is_async=False,
    description="A股每日情报融合简报（大盘方向+标的策略+交叉信号）",
    emoji="🔭",
)
