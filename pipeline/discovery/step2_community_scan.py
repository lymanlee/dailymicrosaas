#!/usr/bin/env python3
"""
Step 2: 社区信号扫描 - Hacker News (Algolia API) + GitHub API。
"""

from __future__ import annotations

import json
import sys
import math
import os
import ssl
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pipeline.discovery.pipeline_common import DATA_DIR, PROJECT_ROOT, load_seed_roots, resolve_run_date, save_json

ENV_FILES = [PROJECT_ROOT / ".env", DATA_DIR.parent / ".env"]
for env_file in ENV_FILES:
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").strip().splitlines():
            if line and "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


def safe_request(url: str, timeout: int = 12, max_retries: int = 3):
    """安全的 HTTP 请求，带重试。"""
    last_error = None
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
            with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as response:
                return json.loads(response.read())
        except Exception as error:
            last_error = error
            if attempt < max_retries - 1:
                wait = (attempt + 1) * 2
                print(f"    ⚠️ 请求失败 (尝试 {attempt + 1}/{max_retries}): {error}，{wait}s 后重试...")
                time.sleep(wait)
            else:
                print(f"    ❌ 请求彻底失败: {error}")

    raise last_error


def is_relevant_to_keyword(title: str, keyword: str) -> bool:
    """判断标题是否与关键词相关。"""
    stop_words = {
        "tool", "generator", "maker", "free", "online", "ai", "app",
        "website", "web", "best", "top", "how", "to", "for", "the",
        "a", "an", "with", "and", "or", "of",
    }
    core_words = [word for word in keyword.lower().split() if word not in stop_words and len(word) > 2]
    if not core_words:
        return True
    title_lower = title.lower()
    return any(word in title_lower for word in core_words)


def scan_hackernews(keywords: list[str], days: int = 30) -> list[dict]:
    """扫描 Hacker News 最近的帖子。"""
    print("  [HN] 扫描 Hacker News (Algolia API)...")
    results = []
    seen_ids = set()
    since_ts = int(time.time()) - days * 86400

    search_terms = list(keywords[:20]) + ["online tool", "free tool website", "micro saas", "indie hacker", "build in public"]

    for keyword in search_terms:
        try:
            data = safe_request(
                f"https://hn.algolia.com/api/v1/search"
                f"?query={urllib.parse.quote_plus(keyword)}"
                f"&tags=story&numericFilters=created_at_i>{since_ts}"
                f"&hitsPerPage=5"
            )

            for hit in data.get("hits", []):
                object_id = hit.get("objectID", "")
                if object_id in seen_ids:
                    continue
                seen_ids.add(object_id)

                points = hit.get("points", 0)
                comments = hit.get("num_comments", 0)
                title = hit.get("title", "")

                if not is_relevant_to_keyword(title, keyword):
                    continue

                raw_strength = points + comments * 2
                strength = round(math.log1p(raw_strength) * 15, 1)

                if raw_strength >= 5:
                    results.append(
                        {
                            "keyword": keyword,
                            "title": title,
                            "url": hit.get("url") or f"https://news.ycombinator.com/item?id={object_id}",
                            "points": points,
                            "comments": comments,
                            "signal_strength": strength,
                            "source": "hackernews",
                        }
                    )

            time.sleep(0.3)
        except Exception as error:
            print(f"  [HN] ⚠️ '{keyword}' 出错: {error}")
            continue

    results.sort(key=lambda item: item["signal_strength"], reverse=True)
    print(f"  [HN] ✅ 找到 {len(results)} 条信号")
    return results


def scan_github(keywords: list[str], days: int = 30) -> list[dict]:
    """扫描 GitHub 快速增长的仓库。"""
    print("  [GitHub] 扫描 GitHub API...")
    results = []
    seen_repos = set()
    since_date = time.strftime("%Y-%m-%d", time.gmtime(time.time() - days * 86400))

    gh_token = os.environ.get("GITHUB_TOKEN", "")
    gh_headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/vnd.github.v3+json",
    }
    if gh_token:
        gh_headers["Authorization"] = f"token {gh_token}"
        print("  [GitHub] ✅ 使用 GitHub Token（更高 rate limit）")
    else:
        print("  [GitHub] ⚠️ 未设置 GITHUB_TOKEN，使用匿名请求（60 次/h）")

    search_terms = list(keywords[:25])

    for keyword in search_terms:
        try:
            url = (
                f"https://api.github.com/search/repositories"
                f"?q={urllib.parse.quote_plus(keyword + ' created:>' + since_date)}"
                f"&sort=stars&order=desc&per_page=5"
            )
            req = urllib.request.Request(url, headers=gh_headers)
            with urllib.request.urlopen(req, timeout=12, context=SSL_CTX) as response:
                data = json.loads(response.read())

            for repo in data.get("items", []):
                full_name = repo.get("full_name", "")
                if full_name in seen_repos:
                    continue
                seen_repos.add(full_name)

                stars = repo.get("stargazers_count", 0)
                if stars >= 5:
                    strength = round(math.log1p(stars * 2) * 15, 1)
                    results.append(
                        {
                            "keyword": keyword,
                            "repo_name": full_name,
                            "description": (repo.get("description") or "")[:100],
                            "stars": stars,
                            "url": repo.get("html_url", ""),
                            "topics": repo.get("topics", []),
                            "signal_strength": strength,
                            "source": "github",
                        }
                    )

            time.sleep(3)
        except Exception as error:
            print(f"  [GitHub] ⚠️ '{keyword}' 出错: {error}")
            time.sleep(5)
            continue

    results.sort(key=lambda item: item["signal_strength"], reverse=True)
    print(f"  [GitHub] ✅ 找到 {len(results)} 条信号")
    return results


def run_community_scan(run_date: str | None = None) -> dict:
    """执行完整社区信号扫描。"""
    resolved_date = resolve_run_date(run_date)
    print(f"[Step 2] 开始社区信号扫描 - {resolved_date}...")
    config = load_seed_roots()
    seeds = config["seed_roots"]

    hn_results = scan_hackernews(seeds)
    time.sleep(1)
    gh_results = scan_github(seeds)

    all_signals = {
        "date": resolved_date,
        "hackernews": hn_results,
        "github": gh_results,
        "summary": {
            "hn_count": len(hn_results),
            "github_count": len(gh_results),
            "total": len(hn_results) + len(gh_results),
        },
    }

    output_path = DATA_DIR / f"community_signals_{resolved_date}.json"
    save_json(all_signals, output_path)
    print(f"[Step 2] ✅ 完成！共 {all_signals['summary']['total']} 条信号 → {output_path}")
    return all_signals


def extract_keywords_from_signals(signals: dict) -> list[dict]:
    """从社区信号中提取关键词及其信号强度。"""
    keyword_map = {}

    for source in ["hackernews", "github"]:
        for item in signals.get(source, []):
            keyword = item.get("keyword", "")
            strength = item.get("signal_strength", 0)

            if keyword not in keyword_map:
                keyword_map[keyword] = {
                    "keyword": keyword,
                    "total_signals": 0,
                    "total_strength": 0,
                    "sources": [],
                    "top_items": [],
                }

            keyword_map[keyword]["total_signals"] += 1
            keyword_map[keyword]["total_strength"] += strength
            if source not in keyword_map[keyword]["sources"]:
                keyword_map[keyword]["sources"].append(source)
            if len(keyword_map[keyword]["top_items"]) < 3:
                keyword_map[keyword]["top_items"].append(
                    {
                        "title": item.get("title") or item.get("repo_name") or item.get("description", ""),
                        "source": source,
                        "strength": strength,
                    }
                )

    return sorted(keyword_map.values(), key=lambda item: item["total_strength"], reverse=True)


if __name__ == "__main__":
    signals = run_community_scan()
    keywords = extract_keywords_from_signals(signals)
    print(f"\n提取 {len(keywords)} 个关键词，Top 10：")
    for keyword in keywords[:10]:
        print(f"  [{keyword['total_signals']} signals, str={keyword['total_strength']}] {keyword['keyword']}")
