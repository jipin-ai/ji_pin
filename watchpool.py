#!/usr/bin/env python3
"""统一关注池：狙击区监控 + 仪表盘
用法:
  python watchpool.py              # 仪表盘模式：显示全部关注标的当前状态
  python watchpool.py --silent     # 静默模式：仅当有标的进入狙击区时输出(cron用)
"""
import requests
import datetime
import json
import sys
import os

POOL_FILE = os.path.expanduser("~/.hermes/data/watchpool.json")
ALERT_FILE = os.path.expanduser("~/.hermes/data/watchpool_alerts.json")

# ============ 关注池配置 ============
# 每只标的: {code, market, name, sniper_low, sniper_high, entry, stop_loss_pct, target_pct, note}
POOL = [
    {
        "code": "002156", "market": "sz", "name": "通富微电",
        "sniper_low": 54.70, "sniper_high": 57.05,
        "entry": 57.05, "stop_loss_pct": -0.02, "target_pct": 0.10,
        "note": "先进封装 AMD/NVIDIA Chiplet"
    },
    {
        "code": "300059", "market": "sz", "name": "东方财富",
        "sniper_low": 18.81, "sniper_high": 19.21,
        "entry": 19.21, "stop_loss_pct": -0.02, "target_pct": 0.10,
        "note": "互联网券商 牛市弹性标的"
    },
    {
        "code": "603613", "market": "sh", "name": "国联股份",
        "sniper_low": 24.63, "sniper_high": 25.13,
        "entry": 25.13, "stop_loss_pct": -0.02, "target_pct": 0.10,
        "note": "B2B产业电商 PSS 71.9"
    },
    {
        "code": "601995", "market": "sh", "name": "中金公司",
        "sniper_low": 32.47, "sniper_high": 33.13,
        "entry": 33.13, "stop_loss_pct": -0.02, "target_pct": 0.10,
        "note": "头部投行/券商 PSS 70.4"
    },
    {
        "code": "000902", "market": "sz", "name": "新洋丰",
        "sniper_low": 13.59, "sniper_high": 13.87,
        "entry": 13.87, "stop_loss_pct": -0.02, "target_pct": 0.10,
        "note": "磷复肥龙头 PE11.24 弱周期+春耕+粮食安全 PSS85"
    },
    {
        "code": "002236", "market": "sz", "name": "大华股份",
        "sniper_low": 16.95, "sniper_high": 17.30,
        "entry": 17.30, "stop_loss_pct": -0.02, "target_pct": 0.10,
        "note": "AI+安防 海外地缘风险 ⚠️观望 置信度7/10 优先度低于新洋丰"
    },
]

def fetch_price(code, market):
    url = f"http://qt.gtimg.cn/q={market}{code}"
    r = requests.get(url, timeout=10)
    r.encoding = "gbk"
    parts = r.text.split("~")
    if len(parts) < 50:
        return None
    return {
        "price": float(parts[3]),
        "change_pct": float(parts[32]),
        "volume_lots": int(parts[6]),
        "turnover_pct": float(parts[38]),
        "high": float(parts[33]),
        "low": float(parts[34]),
        "pe": float(parts[39]) if parts[39] else 0,
        "high_52w": float(parts[47]) if parts[47] else 0,
        "low_52w": float(parts[48]) if parts[48] else 0,
    }

def is_trading_time():
    now = datetime.datetime.now()
    if now.weekday() >= 5:
        return False
    t = now.time()
    return (datetime.time(9, 30) <= t <= datetime.time(11, 30)) or \
           (datetime.time(13, 0) <= t <= datetime.time(15, 0))

def load_alerts():
    if os.path.exists(ALERT_FILE):
        with open(ALERT_FILE) as f:
            return json.load(f)
    return {}

def save_alerts(data):
    os.makedirs(os.path.dirname(ALERT_FILE), exist_ok=True)
    with open(ALERT_FILE, "w") as f:
        json.dump(data, f)

def check_all():
    """检查所有关注标的，返回结果列表"""
    results = []
    for stock in POOL:
        d = fetch_price(stock["code"], stock["market"])
        if not d:
            results.append({**stock, "error": "数据获取失败"})
            continue
        
        price = d["price"]
        sniper_low = stock["sniper_low"]
        sniper_high = stock["sniper_high"]
        entry = stock["entry"]
        
        in_zone = sniper_low <= price <= sniper_high
        dist = round((price - sniper_high) / sniper_high * 100, 1) if not in_zone else 0
        
        stop_loss = round(entry * (1 + stock["stop_loss_pct"]), 2)
        target = round(entry * (1 + stock["target_pct"]), 2)
        
        results.append({
            **stock,
            "price": price,
            "change_pct": d["change_pct"],
            "pe": d["pe"],
            "turnover_pct": d["turnover_pct"],
            "high_52w": d["high_52w"],
            "low_52w": d["low_52w"],
            "in_zone": in_zone,
            "dist": dist,
            "stop_loss": stop_loss,
            "target": target,
            "risk_reward": round((target - entry) / (entry - stop_loss), 2),
        })
    return results

def render_dashboard(results):
    """完整仪表盘输出"""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    is_trade = is_trading_time()
    status = "🟢 交易中" if is_trade else "⚫ 休市"
    
    lines = [
        f"╔══════════════════════════════════════════════════════╗",
        f"║  🔭 狙击关注池  {now}  {status}       ║",
        f"╠══════════════════════════════════════════════════════╣",
    ]
    
    in_zone_count = 0
    for r in results:
        if r.get("error"):
            lines.append(f"║  ❌ {r['code']} {r['name']}: {r['error']}")
            continue
        
        code = r["code"]
        name = r["name"]
        price = r["price"]
        chg = r["change_pct"]
        sniper_low = r["sniper_low"]
        sniper_high = r["sniper_high"]
        dist = r["dist"]
        pe = r["pe"]
        note = r.get("note", "")
        
        if r["in_zone"]:
            in_zone_count += 1
            icon = "🎯"
            status_line = f"在狙击区内！挂单 ¥{r['entry']}"
        else:
            # 更精细的距离显示
            if dist <= 5:
                icon = "🟡"
            elif dist <= 10:
                icon = "🟠"
            else:
                icon = "🔴"
            status_line = f"距狙击区 {dist:+.1f}% | 还差 ¥{abs(round(price - sniper_high, 2))}"
        
        lines.append(f"║                                              ║")
        lines.append(f"║  {icon} {code} {name}")
        lines.append(f"║     现价 ¥{price:.2f} ({chg:+.2f}%)  PE {pe:.1f}")
        lines.append(f"║     狙击区 ¥{sniper_low:.2f} - ¥{sniper_high:.2f}")
        lines.append(f"║     {status_line}")
        if r["in_zone"]:
            lines.append(f"║     止损 ¥{r['stop_loss']} | 目标 ¥{r['target']} | 风报比 {r['risk_reward']}")
        if note:
            lines.append(f"║     📝 {note}")
    
    lines.append(f"╠══════════════════════════════════════════════════════╣")
    summary = f"🎯 狙击区内: {in_zone_count}/{len(results)} 只" if in_zone_count > 0 else f"🔭 关注 {len(results)} 只，暂无标的在狙击区"
    lines.append(f"║  {summary}")
    lines.append(f"╚══════════════════════════════════════════════════════╝")
    
    return "\n".join(lines)

def render_alert(results):
    """仅输出进入狙击区的标的（用于 cron 通知）"""
    alerts = []
    alert_data = load_alerts()
    today = datetime.date.today().isoformat()
    
    for r in results:
        if r.get("error"):
            continue
        if not r["in_zone"]:
            continue
        
        code = r["code"]
        # 同一天不重复通知
        if alert_data.get(code) == today:
            continue
        
        alert_data[code] = today
        
        alerts.append(
            f"🎯 【狙击警报】{r['code']} {r['name']} 已进入狙击区！\n"
            f"\n"
            f"当前价:   ¥{r['price']:.2f} ({r['change_pct']:+.2f}%)\n"
            f"PE:       {r['pe']:.1f}\n"
            f"换手率:   {r['turnover_pct']:.2f}%\n"
            f"\n"
            f"狙击区:   ¥{r['sniper_low']:.2f} - ¥{r['sniper_high']:.2f}\n"
            f"挂单价:   ¥{r['entry']:.2f}\n"
            f"止损:     ¥{r['stop_loss']:.2f}\n"
            f"目标:     ¥{r['target']:.2f}\n"
            f"风报比:   {r['risk_reward']}\n"
        )
    
    if alerts:
        save_alerts(alert_data)
        return "\n---\n".join(alerts)
    return ""

def main():
    results = check_all()
    
    if "--silent" in sys.argv:
        # Cron 模式：仅通知进入狙击区的
        msg = render_alert(results)
        if msg:
            print(msg)
        # 静默退出时显式返回0，避免 cron 误判为错误
    else:
        # 仪表盘模式
        print(render_dashboard(results))

if __name__ == "__main__":
    main()
