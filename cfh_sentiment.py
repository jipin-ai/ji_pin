#!/usr/bin/env python3
"""
CFH Sentiment Scanner — 财富号社区情绪扫描 (09:15)
================================================
数据源: caifuhao.eastmoney.com 热门推荐文章
功能:
  1. 抓取近期热门文章
  2. 提取 $股票代码$ 标记 → 统计提及频次
  3. 按作者热度加权
  4. 与策略候选池交叉标注
  5. 输出「今日社区风向」
"""
import os, sys, json, re, time, logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

import requests

# ── 配置 ──────────────────────────────────────────
CFH_API = "https://caifuhao.eastmoney.com/v1/recommend"
QUALITY_AUTHOR_API = (
    "https://caifuhaoapi.eastmoney.com/api/v1/webchannel/Author/"
    "GetHighQualityUserList"
)
ARTICLE_PAGES = 5  # 抓取页数（每页≈20篇）
PAGE_SIZE = 20
MIN_READ_COUNT = 500  # 最低阅读量阈值
HOURS_LOOKBACK = 24  # 只看最近N小时

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Referer": "https://caifuhao.eastmoney.com/",
    "Accept": "application/json",
}

# 候选池路径
CANDIDATES_FILE = os.path.expanduser("~/.hermes/data/sniper_candidates.json")
BREAKOUT_FILE = os.path.expanduser("~/.hermes/data/breakout_yesterday.json")
SENTIMENT_CACHE = os.path.expanduser("~/.hermes/data/cfh_sentiment.json")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def fetch_articles(pages: int = ARTICLE_PAGES) -> List[Dict]:
    """抓取财富号推荐文章列表"""
    articles = []
    seen = set()

    for page in range(1, pages + 1):
        try:
            r = requests.get(
                CFH_API,
                params={
                    "pagesize": PAGE_SIZE,
                    "pageindex": page,
                    "condition": "",
                    "isReload": "false" if page > 1 else "true",
                },
                headers=HEADERS,
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()

            items = data.get("result", {}).get("items", [])
            if not items:
                break

            for item in items:
                item_data = item.get("itemData", {})
                info_code = item_data.get("infoCode", "")
                if info_code in seen:
                    continue
                seen.add(info_code)

                # 时间过滤
                update_time = item_data.get("updateTime", 0)
                if update_time:
                    article_dt = datetime.fromtimestamp(update_time / 1000)
                    if (datetime.now() - article_dt) > timedelta(hours=HOURS_LOOKBACK):
                        continue

                # 阅读量过滤
                read_count = item_data.get("readCount", 0)
                if read_count < MIN_READ_COUNT:
                    continue

                articles.append(item_data)

            logger.info(f"  Page {page}: {len(items)} items, "
                        f"累计 {len(articles)} 篇")

        except Exception as e:
            logger.warning(f"Page {page} fetch failed: {e}")
            continue

    return articles


def extract_stock_codes(articles: List[Dict]) -> Dict[str, Dict]:
    """
    从文章标题/摘要中提取股票代码
    格式: $名称(SH600869)$ 或 $名称(SZ000001)$
    """
    # 正则: $任意文字(交易所代码)$ — SH/SZ + 6位数字
    stock_pattern = re.compile(r'\$[^(]*\((SH|SZ)(\d{6})\)\$')

    mentions = defaultdict(lambda: {
        "count": 0,
        "authors": set(),
        "total_reads": 0,
        "titles": [],
        "code": "",
        "name": "",
    })

    for article in articles:
        title = article.get("title", "")
        summary = article.get("summary", "")
        text = title + " " + summary

        codes = stock_pattern.findall(text)
        if not codes:
            continue

        author = article.get("nickname", article.get("accountName", "未知"))
        reads = article.get("readCount", 0)

        for exchange, suffix in codes:
            # 标准化: SH600869 → 600869
            code = suffix  # 6位纯数字
            raw_code = exchange + suffix

            # 提取名称（从 $名称(CODE)$ 中）
            name_match = re.search(
                rf'\$([^(]*)\({raw_code}\)\$', text
            )
            name = name_match.group(1) if name_match else ""

            mentions[code]["count"] += 1
            mentions[code]["authors"].add(author)
            mentions[code]["total_reads"] += reads
            mentions[code]["code"] = code
            mentions[code]["name"] = name
            if title not in mentions[code]["titles"]:
                mentions[code]["titles"].append(title[:80])

    return dict(mentions)


def load_candidates() -> Dict[str, str]:
    """加载早盘候选池（如果可用），返回 code→name 映射"""
    candidates = {}
    for fpath in [CANDIDATES_FILE, BREAKOUT_FILE]:
        if not os.path.exists(fpath):
            continue
        try:
            with open(fpath) as f:
                data = json.load(f)
            items = data.get("candidates", data) if isinstance(data, dict) else data
            if isinstance(items, list):
                for item in items:
                    code = str(item.get("code", ""))
                    name = item.get("name", "")
                    if code:
                        candidates[code] = name
        except Exception:
            pass
    return candidates


def rank_mentions(mentions: Dict) -> List[Tuple]:
    """按热度（提及次数×平均阅读量）排序"""
    scored = []
    for code, info in mentions.items():
        score = info["count"] * (info["total_reads"] / max(info["count"], 1))
        scored.append((score, code, info))
    scored.sort(reverse=True)
    return scored


def main():
    t0 = time.time()
    now = datetime.now()

    print("=" * 80)
    print(f"  📣 今日社区风向 — {now.strftime('%Y-%m-%d %H:%M')}")
    print(f"  数据源: 东方财富财富号 | 范围: {HOURS_LOOKBACK}h 热门文章 "
          f"(阅>{MIN_READ_COUNT})")
    print("=" * 80)

    # 1. 抓取文章
    print("\n📡 抓取财富号文章...")
    articles = fetch_articles()

    if not articles:
        print("  ⚠️ 未获取到文章，可能是API限制或非交易时段")
        print(f"\n⏱️ 耗时: {time.time() - t0:.1f}s")
        return

    # 统计作者
    authors = Counter(a.get("nickname", a.get("accountName", "?"))
                      for a in articles)
    top_authors = [f"{name}({cnt}篇)" for name, cnt in
                   authors.most_common(5)]

    print(f"  ✅ {len(articles)} 篇 | 作者: {', '.join(top_authors)}")

    # 2. 提取股票代码
    mentions = extract_stock_codes(articles)
    ranked = rank_mentions(mentions)

    # 3. 输出提及最多的标的
    print(f"\n🔥 提及最多的标的 ({len(mentions)} 只):")
    print("-" * 40)

    if not ranked:
        print("  📭 今日文章未提及具体A股标的")
    else:
        for i, (score, code, info) in enumerate(ranked[:10], 1):
            emoji = "🔥" if i <= 3 else "📊"
            authors_list = ", ".join(sorted(info["authors"]))
            print(f"  {emoji} {code} {info['name']} — {info['count']}次提及 "
                  f"({len(info['authors'])}位作者)")
            print(f"     作者: {authors_list}")
            if info["titles"]:
                print(f"     标题: {info['titles'][0]}")

    # 4. 与候选池交叉
    candidates = load_candidates()
    if candidates and ranked:
        print(f"\n🎯 与候选池交叉 ({len(candidates)} 只):")
        print("-" * 40)

        overlap = []
        for _, code, info in ranked:
            if code in candidates:
                overlap.append((code, info, candidates[code]))
                break  # only need first match for brief display

        if overlap:
            for code, info, cname in overlap:
                print(f"  🟢 {code} {cname} — 社区提及 {info['count']}次 "
                      f"({len(info['authors'])}位作者)")
        else:
            print(f"  ⚪ 无重叠（社区热点 ≠ 候选池，正常）")
    elif not candidates:
        print(f"\n  ⚪ 候选池未就绪（首次运行或非交易日）")

    # 5. 方向暗示
    if ranked:
        print(f"\n💡 方向暗示:")
        print("-" * 40)

        # 提取提及的主题词
        all_titles = []
        for _, _, info in ranked[:5]:
            all_titles.extend(info["titles"])

        # 简单关键词提取
        themes = Counter()
        keyword_map = {
            "AI": ["AI", "人工智能", "算力", "芯片", "大模型", "英伟达"],
            "新能源": ["新能源", "光伏", "锂电", "电池", "储能", "充电"],
            "半导体": ["半导体", "存储", "光刻", "晶圆", "封装"],
            "消费": ["消费", "电商", "零售", "品牌", "食品"],
            "金融": ["券商", "银行", "保险", "信托", "金融"],
            "医药": ["医药", "医疗", "疫苗", "药", "生物"],
            "周期": ["钢", "铝", "煤", "铜", "化工", "有色"],
            "军工": ["军工", "国防", "装备", "航天"],
            "黄金": ["黄金", "贵金属", "白银"],
        }

        for title in all_titles:
            for theme, keywords in keyword_map.items():
                for kw in keywords:
                    if kw in title:
                        themes[theme] += 1
                        break

        if themes:
            top_themes = themes.most_common(5)
            theme_str = " → ".join(f"{t}({c})" for t, c in top_themes)
            print(f"  📈 社区热议方向: {theme_str}")
        else:
            # fallback: just show top stocks' sectors
            top_names = [info["name"] for _, _, info in ranked[:3]]
            print(f"  📈 关注标的: {', '.join(top_names)}")

    # 6. 保存缓存
    os.makedirs(os.path.dirname(SENTIMENT_CACHE), exist_ok=True)
    with open(SENTIMENT_CACHE, "w") as f:
        json.dump({
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M"),
            "articles_count": len(articles),
            "mentions": {code: {
                "count": info["count"],
                "authors": list(info["authors"]),
                "total_reads": info["total_reads"],
                "name": info["name"],
            } for code, info in mentions.items()},
        }, f, ensure_ascii=False, indent=2)

    print(f"\n⏱️ 耗时: {time.time() - t0:.1f}s")
    print("═" * 80)


if __name__ == "__main__":
    main()
