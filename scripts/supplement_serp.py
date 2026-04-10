#!/usr/bin/env python3
"""
直接补抓缺失 SERP 数据的关键词（不走完整 pipeline）。
"""
import sys
import json
from pathlib import Path
import time
import random

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.discovery.step3_serp_analysis import (
    fetch_serp_for_keyword,
    analyze_serp_data,
    SERP_DELAY_MIN,
    SERP_DELAY_MAX,
)

MISSING_KEYWORDS = [
    "pdf converter",
    "pdf to word",
    "compress pdf",
    "ai music generator",
    "json formatter",
]

results = {}
for kw in MISSING_KEYWORDS:
    print(f"\n🌐 补抓: {kw}")
    raw, is_error = fetch_serp_for_keyword(kw)
    if raw and not is_error:
        analyzed = analyze_serp_data([{"keyword": kw, "search_results": raw}], [kw])
        item = analyzed.get(kw.lower().strip(), {})
        serp_niche = item.get("niche_sites", [])
        serp_big = item.get("big_sites", [])
        results[kw] = {"niche": serp_niche, "big": serp_big}
        print(f"  ✅ niche: {serp_niche[:5]}")
        print(f"  ✅ big:   {serp_big[:5]}")
    else:
        results[kw] = {"niche": [], "big": []}
        print(f"  ❌ 抓取失败")
    # 间隔
    delay = random.uniform(SERP_DELAY_MIN, SERP_DELAY_MAX)
    print(f"  ⏱ 等待 {delay:.1f}s...")
    time.sleep(delay)

# 保存结果
out = ROOT / "data/supplement_serp_results.json"
with open(out, "w") as f:
    json.dump(results, f, indent=2)
print(f"\n✅ 结果已保存: {out}")
print(json.dumps(results, indent=2, ensure_ascii=False))

