#!/usr/bin/env python3
"""VT A股数据获取 — 腾讯API通道（AKShare离线代码 + 腾讯实时行情）"""
import akshare as ak, requests, re, json, time, sys, pandas as pd
from datetime import datetime

TENCENT_URL = "https://qt.gtimg.cn/q={codes}"
BATCH_SIZE = 50
HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.qq.com/"}

def get_all_a_share_snapshot():
    """获取全A股实时行情快照 — 腾讯通道（绕开BSE，避免超时）"""
    # Step 1: AKShare代码清单（沪深分别获取，不碰BSE）
    def _get_codes_with_timeout(timeout_sec=60):
        """带超时的代码列表获取"""
        import threading
        result = [None]
        exception = [None]
        
        def _fetch():
            try:
                sh = ak.stock_info_sh_name_code()
                sz = ak.stock_info_sz_name_code()
                # 归一化列名
                sh = sh.rename(columns={'证券代码': 'code', '证券简称': 'name'})
                sz = sz.rename(columns={'A股代码': 'code', 'A股简称': 'name'})
                sh['code'] = sh['code'].astype(str).str.zfill(6)
                sz['code'] = sz['code'].astype(str).str.zfill(6)
                combined = pd.concat([sh[['code','name']], sz[['code','name']]], ignore_index=True)
                result[0] = combined
            except Exception as e:
                exception[0] = e
        
        t = threading.Thread(target=_fetch, daemon=True)
        t.start()
        t.join(timeout=timeout_sec)
        if t.is_alive():
            raise TimeoutError(f"获取代码清单超时({timeout_sec}s)")
        if exception[0]:
            raise exception[0]
        return result[0]
    
    for attempt in range(1, 4):
        try:
            codes_df = _get_codes_with_timeout(timeout_sec=60)
            break
        except Exception as e:
            if attempt < 3:
                print(f"获取代码清单失败(第{attempt}次): {e}，等{attempt*10}s重试...", file=sys.stderr)
                time.sleep(attempt * 10)
                continue
            raise
    
    # Step 2: 过滤
    exclude = []
    for _, row in codes_df.iterrows():
        name, code = row['name'], row['code']
        if any(kw in name for kw in ['ST', '*ST', '退']):
            exclude.append(code)
        elif code.startswith('8') or code.startswith('68'):
            exclude.append(code)
    
    valid = [c for c in codes_df['code'].tolist() if c not in exclude]
    print(f"基础过滤: {len(codes_df)} → {len(valid)} 只", file=sys.stderr)
    
    # Step 3: 腾讯批量查询
    results = []
    for i in range(0, len(valid), BATCH_SIZE):
        batch = valid[i:i+BATCH_SIZE]
        codes_str = ",".join(
            f"{'sh' if c.startswith('6') else 'sz'}{c}" for c in batch
        )
        try:
            r = requests.get(TENCENT_URL.format(codes=codes_str), 
                           headers=HEADERS, timeout=30)
            r.encoding = 'gbk'  # 腾讯返回GBK编码
            for line in r.text.strip().split('\n'):
                m = re.search(r'="([^"]+)"', line)
                if not m: continue
                parts = m.group(1).split('~')
                if len(parts) < 50: continue
                
                # 解析成交额: field[35]格式 "price/volume/amount" 或 "price/0/0"（休市）
                amount_raw = parts[35].split('/')[-1] if '/' in parts[35] else '0'
                try: amount = float(amount_raw)
                except: amount = 0
                
                # 市值: field[44]=总市值(亿), field[72]=总市值(元)
                mcap = float(parts[44]) if parts[44] and parts[44] != '0' else (
                    float(parts[72])/1e8 if parts[72] and parts[72] != '0' else 0)
                
                results.append({
                    "code": parts[2],
                    "name": parts[1],
                    "price": float(parts[3]) if parts[3] else 0,
                    "change_pct": float(parts[32]) if parts[32] else 0,
                    "volume": float(parts[6]) if parts[6] else 0,
                    "amount": amount,
                    "pe": float(parts[39]) if parts[39] else 0,
                    "market_cap": mcap,  # 亿元
                    "ret_5d": float(parts[62]) if parts[62] else 0,
                    "ret_10d": float(parts[63]) if parts[63] else 0,
                    "ret_20d": float(parts[64]) if parts[64] else 0,
                    "high_52w": float(parts[47]) if parts[47] else 0,
                    "low_52w": float(parts[48]) if parts[48] else 0,
                })
            if i % 500 == 0:
                print(f"  进度: {min(i+BATCH_SIZE, len(valid))}/{len(valid)}", file=sys.stderr)
        except Exception as e:
            print(f"  批次 {i} 失败: {e}", file=sys.stderr)
        time.sleep(0.3)  # 避免腾讯限流
    
    print(f"实时数据: {len(results)} 只", file=sys.stderr)
    return results

if __name__ == "__main__":
    data = get_all_a_share_snapshot()
    output = {
        "timestamp": datetime.now().isoformat(),
        "count": len(data),
        "stocks": data
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
