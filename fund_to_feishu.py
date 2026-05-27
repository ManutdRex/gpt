"""
盘后资金流向 → 飞书推送（GitHub Actions 版）
每天 UTC 7:00 (= 北京时间 15:00) 自动执行
"""
import requests
import time
import os

STOCKS = {
    "002185": "华天科技", "002475": "立讯精密", "603011": "合锻智能", "600105": "永鼎股份",
    "002157": "正邦科技", "000582": "北部湾港", "513310": "中韩半导体ETF", "589130": "科创芯片ETF",
    "588710": "科创半导体ETF", "589800": "科创综指ETF", "588000": "科创50ETF", "605066": "天正电气",
    "601126": "四方股份", "603601": "再升科技", "601016": "节能风电", "000400": "许继电气",
    "600406": "国电南瑞", "002028": "思源电气", "000682": "东方电子",
}

FEISHU_URL = os.environ.get("FEISHU_URL", "")


def fetch_one(code):
    market = "1" if code.startswith("6") else "0"
    try:
        r = requests.get(
            "https://push2.eastmoney.com/api/qt/stock/get",
            params={"secid": f"{market}.{code}", "fields": "f43,f58,f62,f184,f66,f69"},
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://data.eastmoney.com/zjlx/",
            },
            timeout=15,
        )
        d = r.json().get("data", {})
        if d and d.get("f62") is not None:
            return {
                "name": d.get("f58", ""),
                "price": round(float(d.get("f43", 0)) / 100, 2) if d.get("f43") else 0,
                "flow": (d.get("f62", 0) or 0),
                "flow_pct": round((d.get("f184", 0) or 0) / 100, 2),
                "super_flow": (d.get("f66", 0) or 0),
                "super_pct": round((d.get("f69", 0) or 0) / 100, 2),
            }
    except:
        pass
    return None


def format_yuan(val):
    val = val or 0
    if abs(val) >= 1_0000_0000:
        return f"{val/1_0000_0000:+.2f}亿"
    elif abs(val) >= 1_0000:
        return f"{val/1_0000:+.0f}万"
    return f"{val:+.0f}元"


def main():
    if not FEISHU_URL:
        print("未设置 FEISHU_URL 环境变量")
        return

    print(f"开始抓取 {len(STOCKS)} 只股票...")
    results = []
    for code, name in STOCKS.items():
        d = fetch_one(code)
        if d:
            d["code"] = code
            d["display_name"] = name
            results.append(d)
            emoji = "🔴" if (d["flow"] or 0) > 0 else ("🟢" if (d["flow"] or 0) < 0 else "⚪")
            print(f"  {emoji} {name}: {format_yuan(d['flow'])}")
        time.sleep(1)

    if not results:
        print("无数据！")
        return

    results.sort(key=lambda x: x["flow"] or 0, reverse=True)

    content = [
        [{"tag": "text", "text": f"📊 盘后资金流向"}],
        [{"tag": "text", "text": ""}],
    ]

    for r in results:
        emoji = "🔴" if (r["flow"] or 0) > 0 else ("🟢" if (r["flow"] or 0) < 0 else "⚪")
        line = f"{emoji} {r['display_name']:<8} {format_yuan(r['flow']):>10} ({r['flow_pct']:+.1f}%)"
        content.append([{"tag": "text", "text": line}])

    total = sum(r["flow"] or 0 for r in results)
    up = sum(1 for r in results if (r["flow"] or 0) > 0)
    down = sum(1 for r in results if (r["flow"] or 0) < 0)
    content.append([{"tag": "text", "text": ""}])
    content.append([{"tag": "text", "text": f"📈 合计 {format_yuan(total)} | 流入{up}只 流出{down}只"}])

    r = requests.post(FEISHU_URL, json={
        "msg_type": "post",
        "content": {"post": {"zh_cn": {"title": "盘后资金流向", "content": content}}},
    }, timeout=10)
    print(f"飞书: {'OK' if r.status_code == 200 else 'FAIL ' + r.text}")


if __name__ == "__main__":
    main()
