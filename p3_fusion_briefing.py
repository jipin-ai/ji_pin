#!/usr/bin/env python3
"""
P3 每日情报融合简报 — 17:00 盘后，飞书推送
整合 P0(资金) + P1(商品) + P2(监管) → 交叉验证 → 输出结论
"""
import os
import sys
import json
import sqlite3
import requests
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

import numpy as np
import akshare as ak

# ─── 策略关注标的（可手动增删）───
WATCH_STOCKS = [
    {"code": "002156", "name": "通富微电", "sector": "半导体"},
    {"code": "300059", "name": "东方财富", "sector": "券商"},
]

# ─── 飞书 ───
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
FEISHU_CHAT_ID = os.getenv("FEISHU_DM_CHAT_ID", "oc_49ae95712081568f6dbacfdd702563d9")

# ─── DB 路径 ───
P1_DB = Path(os.path.expanduser("~/.hermes/data/commodity_prices.db"))
P2_DB = Path(os.path.expanduser("~/.hermes/data/regulatory_signals.db"))

# ═══════════════════════════════════════════════
# 行业 → 商品映射  +  行业 → 代表标的
# ═══════════════════════════════════════════════

SECTOR_MAP = {
    "有色金属": {
        "commodities": ["CU", "AL", "ZN", "PB", "NI", "SN"],
        "stocks": [("600362", "江西铜业"), ("601600", "中国铝业"), ("000630", "铜陵有色"), ("601899", "紫金矿业"), ("000807", "云铝股份")],
        "keywords": ["有色", "铜", "铝", "锌", "镍", "锡", "稀土", "黄金"],
    },
    "黑色系/钢铁": {
        "commodities": ["RB", "HC", "I", "J", "JM", "SF", "SM", "WR", "SS"],
        "stocks": [("600019", "宝钢股份"), ("600507", "方大特钢"), ("000898", "鞍钢股份"), ("601969", "海南矿业")],
        "keywords": ["钢铁", "螺纹", "铁矿", "焦炭", "焦煤", "硅铁"],
    },
    "新能源材料": {
        "commodities": ["LC", "SI", "PS"],
        "stocks": [("002460", "赣锋锂业"), ("002466", "天齐锂业"), ("603260", "合盛硅业")],
        "keywords": ["锂", "硅", "多晶硅", "碳酸锂", "新能源"],
    },
    "化工": {
        "commodities": ["MA", "TA", "EG", "PP", "L", "V", "UR", "SA", "FG", "EB", "PX", "SH"],
        "stocks": [("600346", "恒力石化"), ("600426", "华鲁恒升"), ("600989", "宝丰能源"), ("000683", "远兴能源"), ("002648", "卫星化学")],
        "keywords": ["化工", "甲醇", "PTA", "纯碱", "尿素", "乙烯"],
    },
    "贵金属": {
        "commodities": ["AU", "AG"],
        "stocks": [("600547", "山东黄金"), ("600489", "中金黄金"), ("000603", "盛达资源")],
        "keywords": ["黄金", "白银", "贵金属"],
    },
    "农产品": {
        "commodities": ["M", "A", "Y", "P", "C", "CF", "SR", "LH", "RM", "OI"],
        "stocks": [("002714", "牧原股份"), ("600598", "北大荒"), ("002311", "海大集团"), ("300498", "温氏股份")],
        "keywords": ["农业", "大豆", "玉米", "生猪", "棉花", "白糖"],
    },
    "能源": {
        "commodities": ["FU", "BU", "PG"],
        "stocks": [("600028", "中国石化"), ("600688", "上海石化")],
        "keywords": ["石油", "燃料油", "沥青", "能源"],
    },
}


def get_feishu_token():
    resp = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET},
        timeout=15,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"飞书token失败: {data}")
    return data["tenant_access_token"]


def send_feishu(token, text):
    requests.post(
        f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"receive_id": FEISHU_CHAT_ID, "msg_type": "text", "content": json.dumps({"text": text})},
        timeout=15,
    )


# ═══════════════════════════════
# P0 — 资金面（实时拉取）
# ═══════════════════════════════

def get_p0_capital_signals() -> dict:
    """返回 {signal: '', lhb: [], etf: []}"""
    result = {"lhb": [], "etf": [], "highlights": []}
    today = datetime.now().strftime("%Y%m%d")

    # 龙虎榜机构净买入
    try:
        df = ak.stock_lhb_jgstatistic_em()
        if df is not None and not df.empty:
            for _, r in df.head(10).iterrows():
                net = r.get("净买入额", 0) or 0
                if net > 0:
                    result["lhb"].append({
                        "code": str(r.get("代码", "")), "name": str(r.get("名称", "")),
                        "net": float(net),
                    })
            if result["lhb"]:
                result["highlights"].append(f"龙虎榜机构净买入 {len(result['lhb'])} 只")
    except Exception as e:
        print(f"[P3] 龙虎榜获取失败: {e}")

    # ETF异动
    try:
        df = ak.fund_etf_fund_daily_em()
        if df is not None and not df.empty:
            wides = ["沪深300", "中证500", "创业板", "科创50"]
            for _, r in df.iterrows():
                name = str(r.get("基金简称", ""))
                for kw in wides:
                    if kw in name:
                        change = r.get("净值日增长率", 0) or 0
                        if abs(change) >= 1.5:
                            result["etf"].append({"name": name, "change": float(change)})
                        break
            if result["etf"]:
                direction = "流入" if sum(e["change"] for e in result["etf"]) > 0 else "流出"
                result["highlights"].append(f"宽基ETF整体{direction}")
    except Exception as e:
        print(f"[P3] ETF获取失败: {e}")

    return result


# ═══════════════════════════════
# P1 — 商品面（读 SQLite）
# ═══════════════════════════════

def get_p1_commodity_signals() -> dict:
    """返回 {sector: {commodities: [], trend: ''}}"""
    if not P1_DB.exists():
        return {}

    conn = sqlite3.connect(str(P1_DB))
    cutoff = (datetime.now() - timedelta(days=3)).strftime("%Y%m%d")

    # 取最近3天的价格，计算变化
    rows = conn.execute(
        "SELECT symbol, date, spot_price, dom_basis_rate FROM prices WHERE date >= ? ORDER BY date ASC",
        (cutoff,),
    ).fetchall()
    conn.close()

    # 按品种聚合
    by_symbol = defaultdict(list)
    for sym, date, price, basis in rows:
        by_symbol[sym].append((date, price, basis))

    # 计算每个品种的3日涨跌幅 + 基差状态
    commodity_signals = {}
    for sym, records in by_symbol.items():
        if len(records) < 2:
            continue
        first_price = records[0][1]
        last_price = records[-1][1]
        last_basis = records[-1][2]
        if first_price <= 0:
            continue
        chg = (last_price - first_price) / first_price
        if abs(chg) >= 0.02 or abs(last_basis) >= 0.10:
            commodity_signals[sym] = {
                "change_3d": chg,
                "basis": last_basis,
                "trend": "up" if chg > 0.02 else "down" if chg < -0.02 else "stable",
            }

    # 聚合到行业
    sector_signals = {}
    for sector, info in SECTOR_MAP.items():
        sector_comms = []
        for sym in info["commodities"]:
            if sym in commodity_signals:
                sector_comms.append({"symbol": sym, **commodity_signals[sym]})
        if sector_comms:
            up_count = sum(1 for c in sector_comms if c["trend"] == "up")
            down_count = sum(1 for c in sector_comms if c["trend"] == "down")
            trend = "↑" if up_count > down_count else "↓" if down_count > up_count else "→"
            sector_signals[sector] = {"commodities": sector_comms, "trend": trend}

    return sector_signals


# ═══════════════════════════════
# P2 — 监管面（读 SQLite）
# ═══════════════════════════════

def get_p2_regulatory_signals() -> dict:
    """返回 {alerts: [], clusters: []}"""
    if not P2_DB.exists():
        return {"alerts": [], "clusters": []}

    conn = sqlite3.connect(str(P2_DB))
    cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    alerts = conn.execute(
        "SELECT code, name, inquiry_type, severity, inquiry_date FROM inquiries WHERE inquiry_date >= ? AND severity >= 5 ORDER BY severity DESC LIMIT 10",
        (cutoff,),
    ).fetchall()

    # 行业聚类
    clusters_rows = conn.execute(
        "SELECT code, name, COUNT(*) as cnt FROM inquiries WHERE inquiry_date >= ? GROUP BY substr(code,1,3) HAVING cnt >= 2 ORDER BY cnt DESC",
        (cutoff,),
    ).fetchall()

    conn.close()
    return {
        "alerts": [{"code": a[0], "name": a[1], "type": a[2], "severity": a[3], "date": a[4]} for a in alerts],
        "clusters": [{"prefix": c[0], "count": c[2]} for c in clusters_rows],
    }


# ═══════════════════════════════
# 市场状态判定 & 策略适配
# ═══════════════════════════════

def get_index_data(code: str, name: str, days: int = 60):
    """获取指数日线，计算 MA5/MA10/MA20 及斜率"""
    end = datetime.now().strftime("%Y%m%d")
    start = (datetime.now() - timedelta(days=days + 10)).strftime("%Y%m%d")
    try:
        df = ak.stock_zh_index_daily_em(symbol=code, start_date=start, end_date=end)
        if df is None or df.empty:
            return None
        close = df["close"].values
        if len(close) < 25:
            return None
        ma5 = float(np.mean(close[-5:]))
        ma10 = float(np.mean(close[-10:]))
        ma20 = float(np.mean(close[-20:]))
        latest = float(close[-1])
        # MA20 斜率：最近5个MA20值的线性回归斜率
        ma20s = [float(np.mean(close[max(0, i-20):i])) for i in range(len(close)-5, len(close))]
        slope = float(np.polyfit(range(5), ma20s, 1)[0]) if len(ma20s) >= 3 else 0
        # 量能
        vol_5 = float(np.mean(df["volume"].values[-5:]))
        vol_20 = float(np.mean(df["volume"].values[-20:]))
        vol_ratio = vol_5 / vol_20 if vol_20 > 0 else 1.0

        return {
            "name": name, "latest": latest,
            "ma5": ma5, "ma10": ma10, "ma20": ma20,
            "ma20_slope": slope, "vol_ratio": vol_ratio,
        }
    except Exception as e:
        print(f"[P3] 指数{name}获取失败: {e}")
        return None


def classify_regime(index_data: dict) -> dict:
    """分类市场状态"""
    if index_data is None:
        return {"regime": "unknown", "label": "⚠️ 数据缺失", "strategy": "观望"}

    above_ma20 = index_data["latest"] > index_data["ma20"]
    slope_up = index_data["ma20_slope"] > 0.5  # MA20 日涨 >0.5 点 = 向上
    slope_down = index_data["ma20_slope"] < -0.5
    high_vol = index_data["vol_ratio"] > 1.2

    if above_ma20 and slope_up:
        strength = "强" if high_vol else "弱"
        return {
            "regime": "bull",
            "label": f"🟢 多头确认（{strength}势）",
            "strategy": "趋势跟踪",
            "tactic": "回踩 MA10/MA20 即是买点，不等深度回调",
            "stop": "MA20 下方 -3% 止损",
        }
    elif not above_ma20 and slope_down:
        return {
            "regime": "bear",
            "label": "🔴 空头确认",
            "strategy": "空仓等待",
            "tactic": "不做多，耐心等 MA20 走平再考虑",
            "stop": "—",
        }
    else:
        return {
            "regime": "range",
            "label": "🟡 震荡/方向不明",
            "strategy": "狙击等待",
            "tactic": "预设精确击球点，等市场送上门",
            "stop": "入场价下方 -2% 硬止损",
        }


def get_market_regime():
    """返回大盘+个股的策略建议"""
    result = {"indices": [], "stocks": [], "summary": ""}

    # 大盘指数
    for code, name in [("sh000001", "上证指数"), ("sz399006", "创业板指")]:
        data = get_index_data(code, name)
        if data:
            regime = classify_regime(data)
            result["indices"].append({**data, **regime})

    # 判定综合大盘方向
    total = len(result["indices"])
    if total == 0:
        result["summary"] = "range"
    else:
        bull_count = sum(1 for i in result["indices"] if i["regime"] == "bull")
        bear_count = sum(1 for i in result["indices"] if i["regime"] == "bear")
        bull_ratio = bull_count / total
        bear_ratio = bear_count / total
        if bull_ratio >= 0.5:  # 半数以上指数多头即确认
            result["summary"] = "bull"
        elif bear_ratio >= 0.5:
            result["summary"] = "bear"
        else:
            result["summary"] = "range"

    # 对标个股建议
    for stock in WATCH_STOCKS:
        advice = _get_stock_advice(stock, result)
        result["stocks"].append(advice)

    return result


def _get_stock_advice(stock, market):
    """根据大盘+板块给个股策略建议，数据源：腾讯财经K线"""
    code = stock["code"]
    name = stock["name"]
    sector = stock["sector"]

    # 腾讯K线API
    prefix = "sh" if code.startswith(("6", "9")) else "sz"
    symbol = f"{prefix}{code}"

    try:
        url = "http://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        params = {"param": f"{symbol},day,,,60,qfq"}
        resp = requests.get(url, params=params, timeout=10)
        resp.encoding = "gbk"
        data = resp.json()
        kline = data.get("data", {}).get(symbol, {}).get("qfqday", []) or data.get("data", {}).get(symbol, {}).get("day", [])
    except Exception as e:
        print(f"[P3] 腾讯K线{name}获取失败: {e}")
        kline = []

    if kline and len(kline) >= 25:
        closes = [float(k[2]) for k in kline]  # index 2 = close
        latest_close = closes[-1]
        ma20_stock = sum(closes[-20:]) / 20.0
        above_ma20 = latest_close > ma20_stock
        chg_5d = (closes[-1] - closes[-6]) / closes[-6] * 100 if len(closes) >= 6 else 0
    else:
        latest_close = None
        above_ma20 = None
        chg_5d = 0
        ma20_stock = 0

    # 策略建议
    regime = market["summary"]
    if regime == "bull":
        if above_ma20 and chg_5d > 0:
            return {
                "code": code, "name": name, "sector": sector,
                "price": latest_close, "chg_5d": chg_5d,
                "regime": "bull", "advice": "🟢 趋势跟踪",
                "action": f"回踩 {ma20_stock:.0f}（MA20）附近可建仓，不等深度回调",
                "stop": f"{ma20_stock * 0.97:.0f}（MA20 × -3%）止损",
            }
        else:
            return {
                "code": code, "name": name, "sector": sector,
                "price": latest_close, "chg_5d": chg_5d,
                "regime": "bull", "advice": "🟡 等回踩",
                "action": "大盘多头但个股偏弱，等待个股站上 MA20 再跟",
                "stop": "—",
            }
    elif regime == "bear":
        return {
            "code": code, "name": name, "sector": sector,
            "price": latest_close, "chg_5d": chg_5d,
            "regime": "bear", "advice": "🔴 空仓",
            "action": "大盘空头，不做多",
            "stop": "—",
        }
    else:
        return {
            "code": code, "name": name, "sector": sector,
            "price": latest_close, "chg_5d": chg_5d,
            "regime": "range", "advice": "🟡 狙击等待",
            "action": "震荡市预设精确买点，等市场送上门",
            "stop": f"{latest_close * 0.98:.0f}（入场价 -2%）止损" if latest_close else "—",
        }


# ═══════════════════════════════
# 交叉验证引擎
# ═══════════════════════════════

def match_sector_for_stock(stock_name: str, stock_code: str) -> str:
    """根据股票名称/代码匹配行业"""
    for sector, info in SECTOR_MAP.items():
        for kw in info["keywords"]:
            if kw in stock_name:
                return sector
        for c, n in info["stocks"]:
            if stock_code == c:
                return sector
    return ""


def cross_reference(p0, p1, p2) -> dict:
    """交叉验证，输出三类信号"""
    cross_signals = []    # 2+ 维度对齐 → 结论
    single_signals = []   # 单维度 → 观察
    risk_flags = []       # 监管风险 → 警示

    # ── 1. 商品 Vs 资金 交叉 ──
    for sector, p1_data in p1.items():
        sector_stocks = SECTOR_MAP.get(sector, {}).get("stocks", [])

        # 检查是否有资金面信号匹配该行业
        capital_matches = []
        for lhb_item in p0.get("lhb", []):
            matched = match_sector_for_stock(lhb_item["name"], lhb_item["code"])
            if matched == sector:
                capital_matches.append(lhb_item)

        has_etf = any(
            any(kw in e["name"] for kw in SECTOR_MAP.get(sector, {}).get("keywords", []))
            for e in p0.get("etf", [])
        )

        # 商品异动明细
        up_comms = [c for c in p1_data["commodities"] if c["trend"] == "up"]
        down_comms = [c for c in p1_data["commodities"] if c["trend"] == "down"]

        # 判断交叉强度
        if capital_matches and (up_comms or down_comms):
            # 双向信号 → 强交叉
            direction = "看多" if up_comms else "看空"
            stocks_str = "、".join(f"{c}{n}" for c, n in sector_stocks[:3])
            cross_signals.append({
                "strength": "★★★",
                "sector": sector,
                "direction": direction,
                "commodity_detail": f"{len(up_comms)}涨{len(down_comms)}跌",
                "capital_detail": f"机构买入 {len(capital_matches)} 只",
                "stocks": stocks_str,
            })
        elif up_comms or down_comms:
            # 仅有商品信号
            direction = "↑" if up_comms else "↓"
            stocks_str = "、".join(f"{c}{n}" for c, n in sector_stocks[:3])
            single_signals.append({
                "source": "商品",
                "sector": sector,
                "direction": direction,
                "detail": f"{len(up_comms) + len(down_comms)}品种异动",
                "stocks": stocks_str,
            })

    # 资金面无商品匹配的单独记录
    for lhb_item in p0.get("lhb", [])[:5]:
        matched = match_sector_for_stock(lhb_item["name"], lhb_item["code"])
        if not matched and not any(s["sector"] == matched for s in cross_signals):
            net_str = f"{lhb_item['net']/1e8:.1f}亿" if lhb_item['net'] >= 1e8 else f"{lhb_item['net']/1e4:.0f}万"
            single_signals.append({
                "source": "资金",
                "sector": lhb_item["name"],
                "direction": "↑",
                "detail": f"机构净买入{net_str}",
                "stocks": f"{lhb_item['code']}{lhb_item['name']}",
            })

    # ── 2. 监管风险 ──
    for alert in p2.get("alerts", []):
        matched_sec = match_sector_for_stock(alert["name"], alert["code"])
        risk_flags.append({
            "code": alert["code"],
            "name": alert["name"],
            "type": alert["type"],
            "severity": alert["severity"],
            "sector": matched_sec or "—",
        })

    return {"cross": cross_signals, "single": single_signals, "risk": risk_flags}


# ═══════════════════════════════
# 格式化输出
# ═══════════════════════════════

def format_briefing(p0, p1, p2, xref, regime, today_str) -> str:
    lines = [f"🔭 每日情报融合 — {today_str}", ""]

    # ── 三路信号概览 ──
    lines.append("━━━ 三路信号总览 ━━━")
    p0_hl = "、".join(p0["highlights"]) if p0["highlights"] else "今日无显著异动"
    lines.append(f"📊 资金面：{p0_hl}")
    p1_count = sum(len(v["commodities"]) for v in p1.values())
    lines.append(f"🏭 产业面：{len(p1)}个行业 {p1_count}品种异动" if p1 else "🏭 产业面：价格平稳")
    p2_count = len(p2.get("alerts", []))
    lines.append(f"⚖️ 监管面：{p2_count} 项重点函件" if p2_count else "⚖️ 监管面：无新增预警")
    lines.append("")

    # ── 核心结论：交叉信号 ──
    cross = xref.get("cross", [])
    if cross:
        lines.append("━━━ 🎯 交叉信号（2+维度对齐）━━━")
        for item in sorted(cross, key=lambda x: x["strength"], reverse=True):
            lines.append(f"  {item['strength']} {item['sector']} {item['direction']}")
            lines.append(f"     商品面：{item['commodity_detail']}  |  资金面：{item['capital_detail']}")
            lines.append(f"     → 关注：{item['stocks']}")
        lines.append("")

    # ── 单边信号 ──
    single = xref.get("single", [])
    if single:
        lines.append("━━━ 👁️ 单边观察信号 ━━━")
        for item in single[:8]:
            lines.append(f"  [{item['source']}] {item['sector']} {item['direction']} — {item['detail']}")
            if "stocks" in item:
                lines.append(f"     → {item['stocks']}")
        lines.append("")

    # ── 风险警示 ──
    risk = xref.get("risk", [])
    if risk:
        lines.append("━━━ ⚠️ 监管风险提示 ━━━")
        for item in risk:
            sev_label = "🔴" if item["severity"] >= 8 else "🟠" if item["severity"] >= 5 else "🟡"
            lines.append(f"  {sev_label} {item['code']} {item['name']} — {item['type']} ({item['sector']})")
        lines.append("")

    if not cross and not single and not risk:
        lines.append("今日三路信号均无显著异动，市场消息面平静。")

    # ── 策略建议 ──
    if regime and regime.get("indices"):
        lines.append("")
        lines.append("━━━ 🎯 交易策略建议 ━━━")
        # 大盘状态
        for idx in regime["indices"]:
            lines.append(f"  {idx['label']}  {idx['name']} {idx['latest']:.0f}  "
                        f"(MA5:{idx['ma5']:.0f} MA20:{idx['ma20']:.0f})")
        lines.append(f"  → {regime['indices'][0]['strategy']}：{regime['indices'][0]['tactic']}")
        lines.append(f"  → 止损规则：{regime['indices'][0]['stop']}")

        # 个股建议
        for s in regime.get("stocks", []):
            p_str = f"¥{s['price']:.2f}" if s.get("price") else "—"
            lines.append(f"  {s['advice']} {s['name']}({s['code']}) {p_str} {s['sector']}")
            lines.append(f"     {s['action']}")

    lines.append("─" * 20)
    lines.append("数据来源：P0机构行为 + P1商品价格 + P2监管信号 + 大盘趋势判定")
    return "\n".join(lines)


# ═══════════════════════════════
# Main
# ═══════════════════════════════

def main():
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    print(f"[P3] 情报融合启动 — {today_str}")

    # 数据采集
    p0 = get_p0_capital_signals()
    p1 = get_p1_commodity_signals()
    p2 = get_p2_regulatory_signals()
    regime = get_market_regime()

    # 交叉验证
    xref = cross_reference(p0, p1, p2)

    # 生成简报
    briefing = format_briefing(p0, p1, p2, xref, regime, today_str)
    print(briefing)

    # 推送
    if FEISHU_APP_ID:
        try:
            token = get_feishu_token()
            send_feishu(token, briefing)
            print("[OK] 飞书推送成功")
        except Exception as e:
            print(f"[ERR] 推送失败: {e}")


if __name__ == "__main__":
    main()
