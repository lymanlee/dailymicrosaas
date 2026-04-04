#!/usr/bin/env python3
"""
Step 3: SERP 竞争分析。

支持两种模式：
1. 主动采集模式（默认）：通过 DuckDuckGo HTML 搜索采集 SERP 数据
2. 外部数据模式：SERP 数据由外部传入，本模块负责解析和评分

DuckDuckGo 不需要 API key，通过 HTML 解析获取搜索结果。
限速：每次请求后等待 2-4 秒，避免被封锁。
"""

from __future__ import annotations

import html
import json
import random
import re
import sys
import time
import urllib.parse
import urllib.request
import ssl
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pipeline.discovery.pipeline_common import DATA_DIR, load_seed_roots, save_json

TOOL_GIANTS = {
    "canva.com", "figma.com", "remove.bg", "photoroom.com",
    "smallpdf.com", "ilovepdf.com", "iloveimg.com", "tinypng.com",
    "adobe.com", "squarespace.com", "wix.com", "webflow.com",
    "grammarly.com", "deepl.com", "reverso.net", "snappa.com",
    "pixlr.com", "fotor.com", "picsart.com",
}

CONTENT_GIANTS = {
    "wikipedia.org", "medium.com", "reddit.com", "quora.com",
    "pinterest.com", "youtube.com", "tiktok.com", "instagram.com",
    "w3schools.com", "stackoverflow.com",
}

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

SERP_DELAY_MIN = 2.0
SERP_DELAY_MAX = 4.0
SERP_MAX_KEYWORDS = 20  # 每次 pipeline 最多主动采集的关键词数量


def _extract_domain(url: str) -> str:
    """从 URL 中提取域名。"""
    url = url.replace("https://", "").replace("http://", "")
    domain = url.split("/")[0].lower()
    domain = re.sub(r"^www\.", "", domain)
    return domain


def _fetch_ddg_html(keyword: str, timeout: int = 12) -> str:
    """通过 DuckDuckGo HTML 搜索获取 SERP 结果（无 JS 版本）。"""
    query = urllib.parse.quote_plus(keyword)
    url = f"https://html.duckduckgo.com/html/?q={query}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as response:
        return response.read().decode("utf-8", errors="replace")


def _normalize_result_url(raw_url: str) -> str:
    """把 DDG 的相对链接 / redirect 链接还原成真实目标 URL。"""
    if not raw_url:
        return ""

    url = html.unescape(raw_url.strip())
    if url.startswith("//"):
        url = f"https:{url}"

    parsed = urllib.parse.urlparse(url)
    if "duckduckgo.com" in parsed.netloc:
        uddg = urllib.parse.parse_qs(parsed.query).get("uddg", [""])[0]
        if uddg:
            url = urllib.parse.unquote(uddg)

    return url if url.startswith("http://") or url.startswith("https://") else ""


def _parse_ddg_results(html: str, max_results: int = 10) -> list[dict]:
    """从 DuckDuckGo HTML 页面解析搜索结果。"""
    results = []

    # DDG HTML 搜索结果格式：<a class="result__url" href="...">domain</a>
    # 先尝试提取 result__url 链接
    url_pattern = re.compile(
        r'<a[^>]+class=["\']result__url["\'][^>]*href=["\']([^"\']+)["\']',
        re.IGNORECASE,
    )
    urls = url_pattern.findall(html)

    if not urls:
        # 备用：提取 uddg= 参数（DDG redirect URL）
        uddg_pattern = re.compile(r'uddg=([^&"\'>\s]+)', re.IGNORECASE)
        raw_uddg = uddg_pattern.findall(html)
        urls = [urllib.parse.unquote(u) for u in raw_uddg]

    # 去重，保留前 N 个
    seen = set()
    for raw_url in urls:
        url = _normalize_result_url(raw_url)
        if not url or url in seen:
            continue

        seen.add(url)
        domain = _extract_domain(url)
        if domain:
            results.append({"url": url, "domain": domain})
        if len(results) >= max_results:
            break

    return results


def fetch_serp_for_keyword(keyword: str, max_retries: int = 2) -> list[dict]:
    """为单个关键词采集 SERP 数据，带重试。"""
    last_error = None
    for attempt in range(max_retries):
        try:
            html = _fetch_ddg_html(keyword)
            results = _parse_ddg_results(html)
            if results:
                return results
            # 结果为空可能是被封，稍作等待
            if attempt < max_retries - 1:
                wait = random.uniform(5, 10)
                print(f"    ⚠️ SERP 结果为空（第 {attempt + 1} 次），等待 {wait:.0f}s...")
                time.sleep(wait)
        except Exception as error:
            last_error = error
            if attempt < max_retries - 1:
                wait = random.uniform(3, 6)
                print(f"    ⚠️ SERP 采集失败（第 {attempt + 1} 次）: {error}，等待 {wait:.0f}s...")
                time.sleep(wait)

    if last_error:
        print(f"    ❌ SERP 采集最终失败: {last_error}")
    return []


def run_serp_collection(
    keywords: list[str],
    run_date: str,
    max_keywords: int = SERP_MAX_KEYWORDS,
    force_refresh: bool = False,
) -> dict:
    """
    主动采集一批关键词的 SERP 数据，并保存缓存。

    Args:
        keywords: 要采集的关键词列表（按优先级排序）
        run_date: 运行日期（用于缓存文件命名）
        max_keywords: 最多采集的关键词数量（控制时间成本）

    Returns:
        SERP 原始数据字典 {keyword: [{"url": ..., "domain": ...}, ...]}
    """
    cache_path = DATA_DIR / f"serp_data_{run_date}.json"
    cached: dict = {}

    if force_refresh:
        print("  [SERP] 缓存: 已启用强制刷新，忽略同日期已有 SERP 缓存")
    elif cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            print(f"  [SERP] 缓存: 已有 {len(cached)} 个关键词数据")
        except Exception:
            cached = {}

    cached_success_keywords = {
        key.lower()
        for key, value in cached.items()
        if isinstance(value, list) and len(value) > 0
    }
    target_keywords = [kw for kw in keywords[:max_keywords] if kw.lower() not in cached_success_keywords]

    if not target_keywords:
        print(f"  [SERP] ✅ 全部使用缓存（{len(cached)} 个关键词）")
        return cached

    print(f"  [SERP] 开始采集 {len(target_keywords)} 个关键词（最多 {max_keywords} 个）...")

    success_count = 0
    fail_count = 0

    for index, keyword in enumerate(target_keywords):
        print(f"  [SERP] [{index + 1}/{len(target_keywords)}] 采集: {keyword}")
        results = fetch_serp_for_keyword(keyword)

        if results:
            cached[keyword] = results
            success_count += 1
        else:
            # 记录失败，避免下次重复尝试
            cached[keyword] = []
            fail_count += 1

        # 保存中间缓存（避免中断后全部重来）
        save_json(cached, cache_path)

        # 限速
        if index < len(target_keywords) - 1:
            delay = random.uniform(SERP_DELAY_MIN, SERP_DELAY_MAX)
            time.sleep(delay)

    print(f"  [SERP] ✅ 采集完成：成功 {success_count} 个，失败 {fail_count} 个")

    if fail_count > 0 and success_count == 0:
        print(f"  [SERP] ⚠️ 警告：所有 SERP 采集均失败，可能是网络问题或被封锁，SERP 维度评分将为 0")

    return cached


def analyze_serp_data(raw_serp_items, keywords: list[str]) -> dict:
    """解析 SERP 数据（支持外部传入或 run_serp_collection 的输出）。"""
    # 兼容两种输入格式
    if isinstance(raw_serp_items, dict):
        # 可能是 {keyword: [{"url":..., "domain":...}]} 或 {keyword: [{"url":..}]}
        converted = []
        for keyword, results in raw_serp_items.items():
            if isinstance(results, list):
                # 统一转为 {"keyword": ..., "search_results": [...]} 格式
                converted.append({"keyword": keyword, "search_results": results})
        raw_serp_items = converted

    config = load_seed_roots()
    extra_big = {site.lower() for site in config.get("big_sites", [])}
    all_tool_giants = TOOL_GIANTS | {site for site in extra_big if any(site in giant for giant in TOOL_GIANTS)}
    all_content_giants = CONTENT_GIANTS | {site for site in extra_big if site not in all_tool_giants}

    results = {}
    for item in raw_serp_items:
        keyword = item.get("keyword", "").lower().strip()
        if not keyword:
            continue

        domains_raw = item.get("search_results", [])
        niche_sites = []
        tool_big_sites = []
        content_big_sites = []

        for result in domains_raw:
            # 兼容两种 result 格式：{"url": ..., "domain": ...} 或 {"url": ...}
            domain = result.get("domain", "")
            if not domain:
                url = result.get("url", "")
                domain = _extract_domain(url)
            if not domain:
                continue

            if any(giant in domain for giant in all_tool_giants):
                tool_big_sites.append(domain)
            elif any(giant in domain for giant in all_content_giants):
                content_big_sites.append(domain)
            else:
                niche_sites.append(domain)

        total = len(niche_sites) + len(tool_big_sites) + len(content_big_sites)
        niche_ratio = round(len(niche_sites) / total, 2) if total > 0 else 0
        is_worth = len(niche_sites) >= 3 and len(tool_big_sites) <= 3 and niche_ratio >= 0.4

        results[keyword] = {
            "keyword": keyword,
            "niche_count": len(niche_sites),
            "big_count": len(tool_big_sites) + len(content_big_sites),
            "tool_big_count": len(tool_big_sites),
            "content_big_count": len(content_big_sites),
            "niche_ratio": niche_ratio,
            "niche_sites": list(dict.fromkeys(niche_sites))[:5],
            "big_sites": list(dict.fromkeys(tool_big_sites + content_big_sites))[:5],
            "is_worth_entering": is_worth,
            "total_results": total,
        }

    # 对没有 SERP 数据的关键词补占位
    for keyword in keywords:
        normalized = keyword.lower().strip()
        if normalized not in results:
            results[normalized] = {
                "keyword": normalized,
                "niche_count": 0,
                "big_count": 0,
                "tool_big_count": 0,
                "content_big_count": 0,
                "niche_ratio": 0.5,
                "niche_sites": [],
                "big_sites": [],
                "is_worth_entering": False,
                "total_results": 0,
            }

    return results


if __name__ == "__main__":
    # 快速测试：采集 3 个关键词
    test_keywords = ["merge pdf", "json formatter", "ai headshot generator"]
    print("测试 SERP 主动采集...")
    raw = run_serp_collection(test_keywords, run_date="test", max_keywords=3)
    analyzed = analyze_serp_data(raw, test_keywords)
    for keyword, data in analyzed.items():
        print(f"\n{keyword}:")
        print(f"  niche={data['niche_count']}, big={data['big_count']}, enterable={data['is_worth_entering']}")
        print(f"  niche_sites: {data['niche_sites'][:3]}")
        print(f"  big_sites: {data['big_sites'][:3]}")
