#!/usr/bin/env python3
"""
Step 1: 趋势发现 - Google Trends (pytrends)
对种子词库批量获取真实趋势数据：热度值 + 趋势斜率。
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import ssl
import time
import warnings

import pandas as pd
from pytrends.request import TrendReq

from pipeline.discovery.pipeline_common import (
    DATA_DIR,
    is_blacklisted,
    load_json,
    load_seed_roots,
    resolve_run_date,
    save_json,
)

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore")

try:
    from urllib3.util.retry import Retry

    original_init = Retry.__init__

    def patched_init(self, *args, **kwargs):
        if "method_whitelist" in kwargs:
            kwargs["allowed_methods"] = kwargs.pop("method_whitelist")
        return original_init(self, *args, **kwargs)

    Retry.__init__ = patched_init
except Exception:
    pass

BATCH_SIZE = 4
TIMEFRAME = "today 3-m"
BATCH_DELAY_MIN = 35
BATCH_DELAY_MAX = 55
RATE_LIMIT_WAIT = 300


def create_trend_req() -> TrendReq:
    """创建兼容 macOS LibreSSL 的 TrendReq 实例。"""
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.ssl_ import create_urllib3_context

    class SSLAdapter(HTTPAdapter):
        def init_poolmanager(self, *args, **kwargs):
            ctx = create_urllib3_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            kwargs["ssl_context"] = ctx
            return super().init_poolmanager(*args, **kwargs)

    session = requests.Session()
    session.mount("https://", SSLAdapter())

    return TrendReq(
        hl="en-US",
        tz=360,
        timeout=(15, 30),
        retries=2,
        backoff_factor=0.5,
        requests_args={
            "verify": False,
            "headers": {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
        },
    )


def build_trend_payload(pytrends: TrendReq, keywords: list[str], retries: int = 3) -> pd.DataFrame:
    """安全地构建 pytrends 请求，带指数退避重试。"""
    for attempt in range(retries):
        try:
            pytrends.build_payload(keywords, timeframe=TIMEFRAME)
            df = pytrends.interest_over_time()
            if not df.empty:
                return df
        except Exception as error:
            err_str = str(error)
            if "429" in err_str or "sorry" in err_str:
                wait = RATE_LIMIT_WAIT * (attempt + 1) // 2
                print(f"    ⚠️ 被限流（第 {attempt + 1} 次），等待 {wait}s...")
            else:
                wait = 10 * (attempt + 1) + random.uniform(1, 3)
                print(f"    ⚠️ 请求失败（第 {attempt + 1} 次）: {error}，等待 {wait:.0f}s...")
            time.sleep(wait)
            pytrends = create_trend_req()
    return pd.DataFrame()


def compute_trend_metrics(df: pd.DataFrame, keyword: str) -> dict:
    """从 Google Trends DataFrame 中提取趋势指标。"""
    if df.empty or keyword not in df.columns:
        return {"interest": 0, "slope": 0.0, "recent_avg": 0, "peak": 0, "data_points": 0}

    series = df[keyword].dropna()

    if len(series) < 7:
        avg_val = round(series.mean(), 1) if len(series) > 0 else 0
        return {
            "interest": avg_val,
            "slope": 0.0,
            "recent_avg": avg_val,
            "peak": int(series.max()) if len(series) > 0 else 0,
            "data_points": len(series),
        }

    values = series.values.tolist()
    n = len(values)
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    numerator = sum((i - x_mean) * (value - y_mean) for i, value in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    slope = round(numerator / denominator, 4) if denominator != 0 else 0.0

    recent_avg = sum(values[-7:]) / min(7, n)
    interest_val = round(recent_avg, 1)

    if abs(slope) < 0.01 or (interest_val < 2 and abs(slope) < 0.05):
        slope = 0.0

    return {
        "interest": interest_val,
        "slope": slope,
        "recent_avg": round(recent_avg, 1),
        "peak": int(max(values)),
        "data_points": n,
    }


def discover_trending_keywords(run_date: str | None = None, force_refresh: bool = False) -> list[dict]:
    """对种子词库执行 Google Trends 趋势发现。"""
    resolved_date = resolve_run_date(run_date)
    print(f"[Step 1] 开始趋势发现（Google Trends） - {resolved_date}...")

    config = load_seed_roots()
    seeds = config["seed_roots"]
    blacklist = config.get("blacklist_patterns", [])
    benchmark = config.get("trend_benchmark", "chatgpt")

    valid_seeds = [seed for seed in seeds if not is_blacklisted(seed, blacklist)]
    total_batches = (len(valid_seeds) + BATCH_SIZE - 1) // BATCH_SIZE

    print(f"  种子词: {len(valid_seeds)} 个")
    print(f"  批次: {total_batches} 批（每批 {BATCH_SIZE} 词 + 基准）")
    print(f"  批间延迟: {BATCH_DELAY_MIN}-{BATCH_DELAY_MAX}s")

    cache_path = DATA_DIR / f"trend_data_{resolved_date}.json"
    cached = []
    results = {}
    if force_refresh:
        print("  缓存: 已启用强制刷新，忽略同日期已有趋势缓存")
    else:
        cached = load_json(cache_path)
        if cached:
            for item in cached:
                results[item["keyword"]] = item
            print(f"  缓存: 已有 {len(results)} 个关键词数据")

    pytrends = create_trend_req()
    rate_limited = False

    for index in range(0, len(valid_seeds), BATCH_SIZE):
        batch = valid_seeds[index:index + BATCH_SIZE]
        batch_num = index // BATCH_SIZE + 1

        uncached = [keyword for keyword in batch if keyword not in results]
        if not uncached:
            print(f"  批次 {batch_num}/{total_batches}: ⏭️ 已缓存，跳过")
            continue

        if rate_limited:
            print(f"  批次 {batch_num}/{total_batches}: ⏭️ 被限流，使用缓存继续")
            for keyword in uncached:
                results[keyword] = {
                    "keyword": keyword,
                    "interest": 0,
                    "slope": 0.0,
                    "recent_avg": 0,
                    "peak": 0,
                    "data_points": 0,
                    "relative_to_benchmark": 0,
                    "benchmark_keyword": benchmark,
                    "_status": "rate_limited",
                }
            continue

        all_keywords = uncached + [benchmark]
        print(f"  批次 {batch_num}/{total_batches}: {uncached}")

        df = build_trend_payload(pytrends, all_keywords)

        if df.empty:
            rate_limited = True
            for keyword in uncached:
                results[keyword] = {
                    "keyword": keyword,
                    "interest": 0,
                    "slope": 0.0,
                    "recent_avg": 0,
                    "peak": 0,
                    "data_points": 0,
                    "relative_to_benchmark": 0,
                    "benchmark_keyword": benchmark,
                    "_status": "rate_limited",
                }
            print("    ❌ 数据为空，后续批次将跳过")
            continue

        if benchmark in df.columns:
            bench_values = df[benchmark].dropna()
            bench_avg = bench_values.mean() if len(bench_values) > 0 else 1
        else:
            bench_avg = 1

        for keyword in uncached:
            metrics = compute_trend_metrics(df, keyword)
            if not df.empty and keyword in df.columns:
                keyword_values = df[keyword].dropna()
                keyword_avg = keyword_values.mean() if len(keyword_values) > 0 else 0
                metrics["relative_to_benchmark"] = round(keyword_avg / max(bench_avg, 1), 4)
            else:
                metrics["relative_to_benchmark"] = 0
            metrics["benchmark_keyword"] = benchmark
            metrics["keyword"] = keyword
            results[keyword] = metrics

            direction = "📈" if metrics["slope"] > 0 else "📉"
            print(
                f"    {direction} {keyword}: 热度={metrics['interest']}, "
                f"斜率={metrics['slope']}, 相对={metrics['relative_to_benchmark']}"
            )

        sorted_cache = sorted(results.values(), key=lambda item: item.get("slope", 0) * 10 + item.get("interest", 0), reverse=True)
        save_json(sorted_cache, cache_path)

        if index + BATCH_SIZE < len(valid_seeds):
            delay = random.uniform(BATCH_DELAY_MIN, BATCH_DELAY_MAX)
            print(f"    💤 等待 {delay:.0f}s...")
            time.sleep(delay)
            pytrends = create_trend_req()

    sorted_results = sorted(results.values(), key=lambda item: item.get("slope", 0) * 10 + item.get("interest", 0), reverse=True)
    save_json(sorted_results, cache_path)

    collected = [item for item in sorted_results if item.get("_status") != "rate_limited"]
    rising = [item for item in collected if item.get("slope", 0) > 0.5]

    print("\n[Step 1] ✅ 完成！")
    print(f"  总计: {len(sorted_results)} 个关键词")
    print(f"  成功采集: {len(collected)} 个")
    print(f"  被限流: {len(sorted_results) - len(collected)} 个（已标记为 0 分）")
    print(f"  上升趋势: {len(rising)} 个")
    print(f"  保存至: {cache_path}")

    return sorted_results


if __name__ == "__main__":
    results = discover_trending_keywords()
    print("\n📈 Top 15：")
    for item in results[:15]:
        status = "⚠️" if item.get("_status") == "rate_limited" else ("📈" if item.get("slope", 0) > 0 else "📉")
        print(f"  {status} {item['keyword']}: 热度={item['interest']}, 斜率={item['slope']}")
