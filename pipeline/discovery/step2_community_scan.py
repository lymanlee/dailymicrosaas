#!/usr/bin/env python3
"""
Step 2: 社区信号扫描 - Hacker News (Algolia API) + GitHub API + Reddit。
"""

from __future__ import annotations

import base64
import json
import math
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pipeline.discovery.pipeline_common import DATA_DIR, PROJECT_ROOT, load_json, load_seed_roots, resolve_run_date, save_json

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
DEFAULT_USER_AGENT = os.environ.get("REDDIT_USER_AGENT", "DailyMicroSaaS/0.1 by dailymicrosaas")
REDDIT_TOKEN_CACHE = {"token": "", "expires_at": 0.0}
COMMUNITY_CACHE_DIR = DATA_DIR / "community_cache"
COMMUNITY_CACHE_DIR.mkdir(parents=True, exist_ok=True)
GITHUB_CACHE_PATH = COMMUNITY_CACHE_DIR / "github_search_cache.json"
REDDIT_CACHE_PATH = COMMUNITY_CACHE_DIR / "reddit_search_cache.json"
GITHUB_CACHE_TTL_SECONDS = 12 * 3600
REDDIT_CACHE_TTL_SECONDS = 6 * 3600
GITHUB_DELAY_AUTHENTICATED_SECONDS = 2.5
GITHUB_DELAY_ANONYMOUS_SECONDS = 7.0
REDDIT_PUBLIC_ENDPOINTS = [
    "https://www.reddit.com/search.json",
    "https://old.reddit.com/search.json",
]


class RequestError(Exception):
    """携带状态码/响应头的请求异常，便于上层做限流和 fallback 判断。"""

    def __init__(self, message: str, status: int | None = None, headers: dict[str, str] | None = None, body: str = "", transient: bool = False):
        super().__init__(message)
        self.status = status
        self.headers = headers or {}
        self.body = body
        self.transient = transient


def load_query_cache(cache_path: Path) -> dict[str, dict]:
    cache = load_json(cache_path)
    return cache if isinstance(cache, dict) else {}


def build_query_cache_key(source: str, keyword: str, window: str) -> str:
    return f"{source}|{window}|{' '.join(keyword.lower().split())}"


def get_cached_query_items(
    cache: dict[str, dict],
    cache_key: str,
    ttl_seconds: int,
    allow_stale: bool = False,
) -> list[dict] | None:
    payload = cache.get(cache_key)
    if not isinstance(payload, dict):
        return None

    items = payload.get("items")
    fetched_at = float(payload.get("fetched_at", 0) or 0)
    if not isinstance(items, list) or not fetched_at:
        return None

    age_seconds = time.time() - fetched_at
    if allow_stale or age_seconds <= ttl_seconds:
        return items
    return None


def save_cached_query_items(cache: dict[str, dict], cache_path: Path, cache_key: str, items: list[dict]) -> None:
    cache[cache_key] = {
        "fetched_at": int(time.time()),
        "items": items,
    }
    save_json(cache, cache_path)


def safe_request(
    url: str,
    timeout: int = 12,
    max_retries: int = 3,
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
):
    """安全的 HTTP JSON 请求，带重试与可识别的错误元数据。"""
    last_error: Exception | None = None
    request_headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept-Encoding": "identity",
        "Connection": "close",
    }
    if headers:
        request_headers.update(headers)

    retryable_statuses = {408, 409, 425, 429, 500, 502, 503, 504}

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, data=data, headers=request_headers)
            with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="ignore")
            response_headers = {key.lower(): value for key, value in error.headers.items()}
            reason = body.strip()[:180] or error.reason
            last_error = RequestError(
                f"HTTP Error {error.code}: {reason}",
                status=error.code,
                headers=response_headers,
                body=body,
                transient=error.code in retryable_statuses,
            )
        except (urllib.error.URLError, ssl.SSLError, TimeoutError, ConnectionResetError) as error:
            last_error = RequestError(str(error), transient=True)
        except Exception as error:
            last_error = error

        should_retry = isinstance(last_error, RequestError) and last_error.transient
        if attempt < max_retries - 1 and should_retry:
            wait = (attempt + 1) * 2
            print(f"    ⚠️ 请求失败 (尝试 {attempt + 1}/{max_retries}): {last_error}，{wait}s 后重试...")
            time.sleep(wait)
            continue

        print(f"    ❌ 请求彻底失败: {last_error}")
        break

    raise last_error or RuntimeError(f"请求失败: {url}")


def is_relevant_to_keyword(title: str, keyword: str) -> bool:
    """判断标题是否与关键词相关。"""
    stop_words = {
        "tool", "tools", "generator", "maker", "free", "online", "ai", "app",
        "website", "web", "best", "top", "how", "to", "for", "the",
        "a", "an", "with", "and", "or", "of", "use", "using",
    }
    title_lower = title.lower()
    keyword_lower = keyword.lower().strip()
    if keyword_lower and keyword_lower in title_lower:
        return True

    core_words = [word for word in keyword_lower.split() if word not in stop_words and len(word) > 2]
    if not core_words:
        return True

    matches = [word for word in core_words if word in title_lower]
    min_matches = 1 if len(core_words) <= 2 else 2
    return len(matches) >= min_matches


HN_QUERY_TEMPLATES = [
    ("direct", "{keyword}"),
    ("ask_hn", "Ask HN {keyword}"),
    ("ask_hn", "Ask HN alternative to {keyword}"),
    ("intent", "alternative to {keyword}"),
    ("intent", "looking for {keyword}"),
    ("intent", "{keyword} problem"),
    ("workflow", "{keyword} workflow"),
    ("workflow", "{keyword} automate"),
]

HN_INTENT_MULTIPLIERS = {
    "pain": 1.6,
    "workflow": 1.2,
    "validation": 0.8,
    "generic": 0.5,
}


def build_hn_query_specs(keywords: list[str]) -> list[dict[str, str]]:
    """构建 HN 查询组合，优先抓 seed 本身，再扩大到 Ask HN / pain / workflow 模板。"""
    specs = []
    seen_queries = set()
    for keyword in keywords[:20]:
        for query_type, template in HN_QUERY_TEMPLATES:
            query = template.format(keyword=keyword).strip()
            query_key = query.lower()
            if query_key in seen_queries:
                continue
            seen_queries.add(query_key)
            specs.append(
                {
                    "keyword": keyword,
                    "query": query,
                    "query_type": query_type,
                }
            )
    return specs


def classify_hn_intent(title: str) -> str:
    """把 HN 标题粗分成痛点、工作流、验证、泛讨论。"""
    title_lower = title.lower()
    pain_terms = [
        "alternative", "alternatives", "recommend", "recommendation", "looking for",
        "problem", "problems", "issue", "issues", "slow", "broken", "manual",
        "automate", "automation", "need", "needs", "wish there was", "can't", "cannot",
        "struggle", "frustrating", "pain", "annoying",
    ]
    workflow_terms = [
        "ask hn", "workflow", "workflows", "process", "how do you", "what do you use",
        "best way", "stack", "setup", "tool for", "routine",
    ]
    validation_terms = [
        "show hn", "launched", "launch", "built", "made", "release", "introducing",
    ]

    if any(term in title_lower for term in pain_terms):
        return "pain"
    if any(term in title_lower for term in validation_terms):
        return "validation"
    if any(term in title_lower for term in workflow_terms):
        return "workflow"
    return "generic"


def normalize_hn_result_url(url: str) -> str:
    """标准化外链 URL，用于跨查询去重。"""
    if not url:
        return ""

    parsed = urllib.parse.urlsplit(url)
    if not parsed.netloc:
        return ""

    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    return urllib.parse.urlunsplit((scheme, netloc, path, "", ""))



def tokenize_hn_title(title: str) -> set[str]:
    """把标题标准化成 token 集合，用于近似去重。"""
    normalized = title.lower().strip()
    normalized = re.sub(r"^(show|ask|launch)\s+hn[:\-\s]+", "", normalized)
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    stop_words = {
        "show", "ask", "launch", "hn", "the", "and", "for", "with", "from",
        "tool", "tools", "free", "using", "built", "build", "make", "made",
        "app", "apps", "your",
    }
    return {word for word in normalized.split() if len(word) > 2 and word not in stop_words}



def is_near_duplicate_hn_title(title_tokens: set[str], existing_token_sets: list[set[str]]) -> bool:
    """基于 token overlap 判断是否与已收录标题高度重复。"""
    if not title_tokens:
        return False

    for existing in existing_token_sets:
        intersection = title_tokens & existing
        if len(intersection) < 3:
            continue

        union = title_tokens | existing
        overlap = len(intersection) / max(1, len(union))
        if overlap >= 0.75:
            return True
        if (title_tokens <= existing or existing <= title_tokens) and len(intersection) >= 3:
            return True

    return False



def get_hn_freshness(created_at_ts: int | None) -> tuple[str, float]:
    """根据发布时间给 HN 结果做简单时效分桶。"""
    if not created_at_ts:
        return "unknown", 1.0

    age_days = max(0.0, (time.time() - created_at_ts) / 86400)
    if age_days <= 7:
        return "0_7", 1.3
    if age_days <= 14:
        return "8_14", 1.1
    return "15_30", 1.0



def compute_hn_signal_strength(points: int, comments: int, intent_label: str, created_at_ts: int | None) -> tuple[float, float, str, float, float]:
    """综合热度、意图类型和时效性计算 HN 信号强度。"""
    base_strength = max(points, 0) + max(comments, 0) * 2.5
    freshness_bucket, freshness_multiplier = get_hn_freshness(created_at_ts)
    type_multiplier = HN_INTENT_MULTIPLIERS.get(intent_label, 0.5)
    raw_strength = base_strength * type_multiplier * freshness_multiplier
    strength = round(math.log1p(raw_strength) * 14, 1)
    return raw_strength, strength, freshness_bucket, type_multiplier, freshness_multiplier



def scan_hackernews(keywords: list[str], days: int = 30) -> list[dict]:
    """扫描 Hacker News 最近的帖子，优先抓需求/工作流相关信号。"""
    print("  [HN] 扫描 Hacker News (Algolia API, demand-first)...")
    results = []
    seen_ids = set()
    seen_urls = set()
    seen_title_tokens_by_keyword: dict[str, list[set[str]]] = {}
    since_ts = int(time.time()) - days * 86400
    query_specs = build_hn_query_specs(keywords)

    for spec in query_specs:
        keyword = spec["keyword"]
        query = spec["query"]
        query_type = spec["query_type"]
        try:
            data = safe_request(
                f"https://hn.algolia.com/api/v1/search"
                f"?query={urllib.parse.quote_plus(query)}"
                f"&tags=story&numericFilters=created_at_i>{since_ts}"
                f"&hitsPerPage=5"
            )

            for hit in data.get("hits", []):
                object_id = hit.get("objectID", "")
                if object_id in seen_ids:
                    continue

                title = (hit.get("title") or "").strip()
                if not title or not is_relevant_to_keyword(title, keyword):
                    continue

                target_url = hit.get("url", "")
                canonical_url = normalize_hn_result_url(target_url)
                if canonical_url and canonical_url in seen_urls:
                    continue

                title_tokens = tokenize_hn_title(title)
                keyword_seen_title_tokens = seen_title_tokens_by_keyword.setdefault(keyword, [])
                if is_near_duplicate_hn_title(title_tokens, keyword_seen_title_tokens):
                    continue

                points = int(hit.get("points", 0) or 0)
                comments = int(hit.get("num_comments", 0) or 0)
                intent_label = classify_hn_intent(title)
                created_at_ts = hit.get("created_at_i")
                raw_strength, strength, freshness_bucket, type_multiplier, freshness_multiplier = compute_hn_signal_strength(
                    points,
                    comments,
                    intent_label,
                    int(created_at_ts) if created_at_ts else None,
                )

                if raw_strength < 6:
                    continue

                seen_ids.add(object_id)
                if canonical_url:
                    seen_urls.add(canonical_url)
                if title_tokens:
                    keyword_seen_title_tokens.append(title_tokens)

                results.append(
                    {
                        "keyword": keyword,
                        "title": title,
                        "url": target_url or f"https://news.ycombinator.com/item?id={object_id}",
                        "points": points,
                        "comments": comments,
                        "query_type": query_type,
                        "matched_query": query,
                        "intent_label": intent_label,
                        "freshness_bucket": freshness_bucket,
                        "raw_strength": round(raw_strength, 1),
                        "type_multiplier": type_multiplier,
                        "freshness_multiplier": freshness_multiplier,
                        "signal_strength": strength,
                        "source": "hackernews",
                    }
                )

            time.sleep(0.15)
        except Exception as error:
            print(f"  [HN] ⚠️ '{query}' 出错: {error}")
            continue

    results.sort(key=lambda item: item["signal_strength"], reverse=True)
    print(f"  [HN] ✅ 找到 {len(results)} 条信号")
    return results


def is_github_rate_limit_error(error: Exception) -> bool:
    if not isinstance(error, RequestError):
        return False

    body = error.body.lower()
    remaining = str(error.headers.get("x-ratelimit-remaining", "")).strip()
    return error.status == 403 and ("rate limit" in body or remaining == "0")



def get_github_rate_limit_reset_label(error: Exception) -> str:
    if not isinstance(error, RequestError):
        return ""

    reset_at = str(error.headers.get("x-ratelimit-reset", "")).strip()
    if not reset_at.isdigit():
        return ""

    return time.strftime("%H:%M:%S", time.localtime(int(reset_at)))



def append_github_repo_results(results: list[dict], seen_repos: set[str], keyword: str, repos: list[dict]) -> int:
    added = 0
    for repo in repos:
        if not isinstance(repo, dict):
            continue

        full_name = repo.get("full_name", "")
        if not full_name or full_name in seen_repos:
            continue
        seen_repos.add(full_name)

        stars = int(repo.get("stargazers_count", 0) or 0)
        if stars < 5:
            continue

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
        added += 1

    return added



def scan_github(keywords: list[str], days: int = 30) -> list[dict]:
    """扫描 GitHub 快速增长的仓库。"""
    print("  [GitHub] 扫描 GitHub API...")
    results = []
    seen_repos = set()
    since_date = time.strftime("%Y-%m-%d", time.gmtime(time.time() - days * 86400))
    cache = load_query_cache(GITHUB_CACHE_PATH)
    rate_limited = False

    gh_token = os.environ.get("GITHUB_TOKEN", "")
    gh_headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "application/vnd.github.v3+json",
    }
    if gh_token:
        gh_headers["Authorization"] = f"token {gh_token}"
        print("  [GitHub] ✅ 使用 GitHub Token（更高 rate limit）")
    else:
        print("  [GitHub] ⚠️ 未设置 GITHUB_TOKEN，使用匿名请求（自动降速 + 缓存回退）")

    search_terms = list(keywords[:25 if gh_token else 20])
    sleep_seconds = GITHUB_DELAY_AUTHENTICATED_SECONDS if gh_token else GITHUB_DELAY_ANONYMOUS_SECONDS

    for keyword in search_terms:
        cache_key = build_query_cache_key("github", keyword, since_date)
        cached_repos = get_cached_query_items(cache, cache_key, GITHUB_CACHE_TTL_SECONDS)
        if cached_repos is not None:
            append_github_repo_results(results, seen_repos, keyword, cached_repos)
            continue

        if rate_limited:
            stale_repos = get_cached_query_items(cache, cache_key, GITHUB_CACHE_TTL_SECONDS, allow_stale=True)
            if stale_repos is not None:
                append_github_repo_results(results, seen_repos, keyword, stale_repos)
            continue

        try:
            url = (
                f"https://api.github.com/search/repositories"
                f"?q={urllib.parse.quote_plus(keyword + ' created:>' + since_date)}"
                f"&sort=stars&order=desc&per_page=5"
            )
            data = safe_request(url, timeout=12, headers=gh_headers)
            repos = data.get("items", [])
            save_cached_query_items(cache, GITHUB_CACHE_PATH, cache_key, repos)
            append_github_repo_results(results, seen_repos, keyword, repos)
            time.sleep(sleep_seconds)
        except Exception as error:
            if is_github_rate_limit_error(error):
                rate_limited = True
                reset_label = get_github_rate_limit_reset_label(error)
                suffix = f"，预计 {reset_label} 后恢复" if reset_label else ""
                print(f"  [GitHub] ⚠️ 命中 Search API rate limit，停止新的 GitHub 请求，后续仅使用缓存{suffix}")
                stale_repos = get_cached_query_items(cache, cache_key, GITHUB_CACHE_TTL_SECONDS, allow_stale=True)
                if stale_repos is not None:
                    append_github_repo_results(results, seen_repos, keyword, stale_repos)
                continue

            print(f"  [GitHub] ⚠️ '{keyword}' 出错: {error}")
            time.sleep(3)
            continue

    results.sort(key=lambda item: item["signal_strength"], reverse=True)
    print(f"  [GitHub] ✅ 找到 {len(results)} 条信号")
    return results


def get_reddit_access_token() -> str | None:
    """优先使用 Reddit OAuth app-only token；未配置凭据时返回 None。"""
    now = time.time()
    cached_token = REDDIT_TOKEN_CACHE.get("token")
    if cached_token and REDDIT_TOKEN_CACHE.get("expires_at", 0) > now + 60:
        return cached_token

    client_id = os.environ.get("REDDIT_CLIENT_ID", "")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        return None

    basic_auth = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("utf-8")
    payload = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode("utf-8")
    data = safe_request(
        "https://www.reddit.com/api/v1/access_token",
        timeout=15,
        headers={
            "Authorization": f"Basic {basic_auth}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        data=payload,
    )

    access_token = data.get("access_token")
    if not access_token:
        return None

    expires_in = int(data.get("expires_in", 3600) or 3600)
    REDDIT_TOKEN_CACHE["token"] = access_token
    REDDIT_TOKEN_CACHE["expires_at"] = now + expires_in
    return access_token


def build_reddit_search_candidates(keyword: str, time_filter: str, reddit_token: str | None) -> list[dict[str, object]]:
    query = (
        f"?q={urllib.parse.quote_plus(keyword)}"
        f"&sort=relevance&t={time_filter}&limit=5&type=link&raw_json=1"
    )
    candidates: list[dict[str, object]] = []

    if reddit_token:
        candidates.append(
            {
                "label": "oauth",
                "url": f"https://oauth.reddit.com/search{query}",
                "headers": {
                    "Authorization": f"Bearer {reddit_token}",
                    "Accept": "application/json",
                },
            }
        )

    for endpoint in REDDIT_PUBLIC_ENDPOINTS:
        candidates.append(
            {
                "label": urllib.parse.urlsplit(endpoint).netloc,
                "url": f"{endpoint}{query}",
                "headers": {"Accept": "application/json"},
            }
        )

    return candidates



def extract_reddit_posts(data: dict) -> list[dict]:
    posts = []
    for child in data.get("data", {}).get("children", []):
        if not isinstance(child, dict):
            continue
        post = child.get("data", {})
        if isinstance(post, dict):
            posts.append(post)
    return posts



def append_reddit_posts(results: list[dict], seen_posts: set[str], keyword: str, posts: list[dict]) -> int:
    added = 0
    for post in posts:
        if not isinstance(post, dict):
            continue

        object_id = post.get("name") or post.get("id") or post.get("permalink", "")
        if not object_id or object_id in seen_posts:
            continue
        seen_posts.add(object_id)

        title = (post.get("title") or "").strip()
        if not title or not is_relevant_to_keyword(title, keyword):
            continue

        score = int(post.get("score", 0) or 0)
        comments = int(post.get("num_comments", 0) or 0)
        raw_strength = max(score, 0) + comments * 1.5
        if raw_strength < 5:
            continue

        permalink = post.get("permalink", "")
        result_url = f"https://www.reddit.com{permalink}" if permalink else post.get("url", "")
        strength = round(math.log1p(raw_strength) * 14, 1)
        results.append(
            {
                "keyword": keyword,
                "title": title,
                "url": result_url,
                "subreddit": post.get("subreddit", ""),
                "score": score,
                "comments": comments,
                "signal_strength": strength,
                "source": "reddit",
            }
        )
        added += 1

    return added



def scan_reddit(keywords: list[str], days: int = 30) -> list[dict]:
    """扫描 Reddit 搜索结果，优先 OAuth，缺凭据时回退到公开 JSON 端点。"""
    print("  [Reddit] 扫描 Reddit 搜索...")
    results = []
    seen_posts = set()
    search_terms = list(keywords[:20])
    cache = load_query_cache(REDDIT_CACHE_PATH)

    time_filter = "week" if days <= 7 else "month" if days <= 30 else "year" if days <= 365 else "all"

    reddit_token = None
    try:
        reddit_token = get_reddit_access_token()
    except Exception as error:
        print(f"  [Reddit] ⚠️ OAuth 取 token 失败，改用公开 JSON 端点: {error}")

    if reddit_token:
        print("  [Reddit] ✅ 使用 OAuth token")
    else:
        print("  [Reddit] ⚠️ 未配置 Reddit OAuth，回退到公开 JSON 端点（自动切换 www / old + 缓存）")

    for keyword in search_terms:
        cache_key = build_query_cache_key("reddit", keyword, time_filter)
        cached_posts = get_cached_query_items(cache, cache_key, REDDIT_CACHE_TTL_SECONDS)
        if cached_posts is not None:
            append_reddit_posts(results, seen_posts, keyword, cached_posts)
            continue

        posts: list[dict] | None = None
        errors: list[str] = []
        candidates = build_reddit_search_candidates(keyword, time_filter, reddit_token)

        for candidate in candidates:
            try:
                data = safe_request(
                    str(candidate["url"]),
                    timeout=15,
                    max_retries=2,
                    headers=dict(candidate["headers"]),
                )
                posts = extract_reddit_posts(data)
                save_cached_query_items(cache, REDDIT_CACHE_PATH, cache_key, posts)
                break
            except Exception as error:
                label = str(candidate["label"])
                errors.append(f"{label}: {error}")
                if label == "oauth" and isinstance(error, RequestError) and error.status in {401, 403}:
                    reddit_token = None
                continue

        if posts is None:
            stale_posts = get_cached_query_items(cache, cache_key, REDDIT_CACHE_TTL_SECONDS, allow_stale=True)
            if stale_posts is not None:
                append_reddit_posts(results, seen_posts, keyword, stale_posts)
                continue

            if errors:
                print(f"  [Reddit] ⚠️ '{keyword}' 出错: {' | '.join(errors)}")
            time.sleep(1.5)
            continue

        append_reddit_posts(results, seen_posts, keyword, posts)
        time.sleep(0.8)

    results.sort(key=lambda item: item["signal_strength"], reverse=True)
    print(f"  [Reddit] ✅ 找到 {len(results)} 条信号")
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
    time.sleep(1)
    reddit_results = scan_reddit(seeds)

    all_signals = {
        "date": resolved_date,
        "hackernews": hn_results,
        "github": gh_results,
        "reddit": reddit_results,
        "summary": {
            "hn_count": len(hn_results),
            "github_count": len(gh_results),
            "reddit_count": len(reddit_results),
            "total": len(hn_results) + len(gh_results) + len(reddit_results),
        },
    }

    output_path = DATA_DIR / f"community_signals_{resolved_date}.json"
    save_json(all_signals, output_path)
    print(f"[Step 2] ✅ 完成！共 {all_signals['summary']['total']} 条信号 → {output_path}")
    return all_signals


def extract_keywords_from_signals(signals: dict) -> list[dict]:
    """从社区信号中提取关键词及其信号强度。"""
    keyword_map = {}

    for source in ["hackernews", "github", "reddit"]:
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
            keyword_map[keyword]["top_items"].append(
                {
                    "title": item.get("title") or item.get("repo_name") or item.get("description", ""),
                    "source": source,
                    "strength": strength,
                    "url": item.get("url", ""),
                }
            )

    for payload in keyword_map.values():
        payload["sources"].sort()
        payload["top_items"].sort(key=lambda item: item.get("strength", 0), reverse=True)
        payload["top_items"] = payload["top_items"][:3]

    return sorted(keyword_map.values(), key=lambda item: item["total_strength"], reverse=True)


if __name__ == "__main__":
    signals = run_community_scan()
    keywords = extract_keywords_from_signals(signals)
    print(f"\n提取 {len(keywords)} 个关键词，Top 10：")
    for keyword in keywords[:10]:
        print(f"  [{keyword['total_signals']} signals, str={keyword['total_strength']}] {keyword['keyword']}")
