#!/usr/bin/env python3
"""
内容发现 pipeline 的公共工具函数。
负责目录定位、种子词加载、日期解析与评分逻辑。
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = PIPELINE_DIR.parent
DATA_DIR = PIPELINE_DIR / "data"
REPORTS_DIR = PIPELINE_DIR / "reports"
LOGS_DIR = PIPELINE_DIR / "logs"

for directory in (DATA_DIR, REPORTS_DIR, LOGS_DIR):
    directory.mkdir(parents=True, exist_ok=True)


def resolve_run_date(date_str: str | None = None) -> str:
    """解析运行日期，统一格式为 YYYY-MM-DD。"""
    if not date_str:
        return date.today().strftime("%Y-%m-%d")
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")


def load_seed_roots() -> dict:
    """加载种子词库。"""
    with open(DATA_DIR / "seed_roots.json", "r", encoding="utf-8") as file:
        return json.load(file)


def save_json(data, filepath: str | Path, sort_keys: bool = False) -> None:
    """保存 JSON 文件。"""
    target = Path(filepath)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2, sort_keys=sort_keys)


def load_json(filepath: str | Path):
    """加载 JSON 文件，不存在时返回空对象。"""
    target = Path(filepath)
    if not target.exists():
        return {}
    with open(target, "r", encoding="utf-8") as file:
        return json.load(file)


def get_today_str() -> str:
    return resolve_run_date()


def get_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def is_blacklisted(keyword: str, blacklist_patterns: list[str]) -> bool:
    """检查关键词是否命中黑名单。"""
    kw_lower = keyword.lower()
    return any(pattern.lower() in kw_lower for pattern in blacklist_patterns)


def is_brand_word(keyword: str) -> bool:
    """判断是否为纯品牌词（精确匹配才跳过）。"""
    brands = {
        "chatgpt", "openai", "claude", "gemini", "copilot", "midjourney",
        "figma", "canva", "notion", "slack", "discord", "zoom",
        "photoshop", "illustrator", "excel", "word", "powerpoint",
    }
    return keyword.lower() in brands


def normalize_keyword(keyword: str) -> str:
    """标准化关键词。"""
    return " ".join(keyword.lower().split())


def keyword_hash(keyword: str) -> str:
    """关键词哈希（用于去重）。"""
    return hashlib.md5(keyword.encode()).hexdigest()[:12]


def score_keyword(item: dict) -> float:
    """
    综合评分（0-100）。

    权重：
    - Google Trends 真实数据：45
    - 社区信号：25
    - SERP 可切入度：30
    """
    import math

    score = 0.0

    slope = item.get("trend_slope", 0)
    recent_avg = item.get("trend_recent_avg", 0)
    relative_heat = item.get("trend_relative", 0)

    if slope > 0.5:
        slope_score = min((slope - 0.5) * 10 + 5, 20)
    elif slope > 0:
        slope_score = slope * 10
    else:
        slope_score = max(slope * 5, -10)
    score += slope_score

    interest_score = min(math.log1p(recent_avg) / math.log1p(50) * 15, 15)
    score += interest_score

    relative_score = min(relative_heat * 8, 10)
    score += relative_score

    community_strength = item.get("community_strength", 0)
    community_sources_count = item.get("community_sources_count", 0)
    sig_score = min(math.log1p(community_strength) / math.log1p(200) * 15, 15)
    source_score = min(community_sources_count * 5, 10)
    score += sig_score + source_score

    serp_niche_count = item.get("serp_niche_count", 0)
    serp_big_count = item.get("serp_big_count", 0)
    serp_tool_big_count = item.get("serp_tool_big_count", serp_big_count)

    niche_score = min(serp_niche_count * 4, 20)
    big_penalty = min(serp_tool_big_count * 4 + (serp_big_count - serp_tool_big_count) * 2, 10)
    score += niche_score - big_penalty

    return round(max(0, min(score, 100)), 1)


def classify_keyword(item: dict) -> str:
    """
    多维度分级：worth_it / watch / skip。
    """
    score = item.get("score", 0)
    recent_avg = item.get("trend_recent_avg", 0)
    serp_enterable = item.get("serp_worth_entering", False)
    community_signals = item.get("community_signals", 0)
    community_strength = item.get("community_strength", 0)

    has_trend = recent_avg >= 1
    has_community = community_signals >= 2 and community_strength >= 10
    has_serp = serp_enterable

    worth = (has_community and (has_trend or has_serp)) or (has_trend and has_serp)

    if worth:
        return "worth_it"
    if has_community or has_trend or has_serp or score >= 15:
        return "watch"
    return "skip"
