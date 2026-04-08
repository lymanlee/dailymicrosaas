#!/usr/bin/env python3
"""
使用已有缓存数据重新生成文章。
跳过 discovery 阶段，直接基于已有报告或缓存数据生成文章。
"""

from __future__ import annotations
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from pipeline.discovery.pipeline_common import DATA_DIR, REPORTS_DIR, load_json, save_json

# 已有文章的关键词映射
# 优先使用已有报告，否则从 trend_data_2099-01-03.json 缓存获取
IDEA_KEYWORDS = [
    {"slug": "2025-04-02-merge-pdf-tool", "keyword": "merge pdf", "date": "2025-04-02", "trend_date": "2099-01-03"},
    {"slug": "2025-04-03-ai-pdf-converter", "keyword": "pdf converter", "date": "2025-04-03", "trend_date": "2099-01-03"},
    {"slug": "2026-04-04-pdf-to-word", "keyword": "pdf to word", "date": "2026-04-04", "trend_date": "2099-01-03"},
    {"slug": "2026-04-05-ai-humanizer", "keyword": "ai humanizer", "date": "2026-04-05", "trend_date": "2099-01-03"},
    {"slug": "2026-04-06-ai-video-editor", "keyword": "ai video editor", "date": "2026-04-06", "trend_date": "2099-01-03"},
    {"slug": "2026-04-06-compress-pdf", "keyword": "compress pdf", "date": "2026-04-06", "trend_date": "2099-01-03"},
    {"slug": "2026-04-07-ai-music-generator", "keyword": "ai music generator", "date": "2026-04-07", "trend_date": "2099-01-03"},
    {"slug": "2026-04-07-json-formatter", "keyword": "json formatter", "date": "2026-04-07", "trend_date": "2099-01-03"},
]


def find_keyword_in_trend_cache(keyword: str) -> Optional[dict]:
    """从多个缓存文件中查找关键词数据，优先使用有 time_series 的数据"""
    # 缓存文件列表（按优先级排序）
    cache_files = [
        DATA_DIR / "trend_data_2026-04-07.json",  # 最新且有 time_series
        DATA_DIR / "trend_data_2026-04-06.json",
        DATA_DIR / "trend_data_2099-01-03.json",  # 后备
    ]
    
    keyword_lower = keyword.lower()
    result = None
    
    for cache_file in cache_files:
        if not cache_file.exists():
            continue
        
        data = load_json(cache_file)
        for item in data:
            if item.get("keyword", "").lower() == keyword_lower:
                # 如果这个缓存有 time_series，直接使用
                if item.get("time_series"):
                    return item
                # 否则保存这个结果作为后备
                if result is None:
                    result = item
    
    # 返回后备结果（可能没有 time_series）
    return result


def find_keyword_in_community_cache(keyword: str, community_data: dict) -> Optional[dict]:
    """从社区信号缓存中查找关键词"""
    for source in ["hackernews", "github", "reddit"]:
        for item in community_data.get(source, []):
            if item.get("keyword", "").lower() == keyword.lower():
                return item
    return None


def build_minimal_report_for_keyword(item: dict, keyword: str) -> dict:
    """为单个关键词构建最小化报告结构"""
    # 简化评分
    interest = item.get("interest", 0)
    slope = item.get("slope", 0)
    score = min(100, int(interest * 2 + abs(slope) * 100))
    
    profile = {
        "keyword": keyword,
        "trend_slope": slope,
        "trend_interest": interest,
        "trend_recent_avg": item.get("recent_avg", interest),
        "trend_peak": item.get("peak", 0),
        "trend_relative": item.get("relative_to_benchmark", 0),
        "trend_data_points": item.get("data_points", 0),
        "trend_time_series": item.get("time_series", []),
        "community_signals": 1,
        "community_strength": 30,
        "community_sources_count": 1,
        "community_sources": ["cached"],
        "community_top_items": [],
        "score": score,
        "grade": "watch" if score < 30 else "worth_it",
    }
    
    return {
        "profiles": [profile],
        "top_pick": profile,
        "candidates": [profile],
        "summary": {"total": 1, "worth_it": 1 if score >= 30 else 0, "watch": 1 if score < 30 else 0, "skip": 0},
    }


def generate_idea_from_cache(keyword: str, date: str, slug: str, mode: str = "overwrite") -> bool:
    """基于缓存数据生成文章"""
    print(f"\n{'='*60}")
    print(f"生成文章: {slug} (关键词: {keyword})")
    print(f"{'='*60}")
    
    # 检查已有报告
    report_file = REPORTS_DIR / f"opportunity_report_{date}.json"
    community_file = DATA_DIR / "community_signals_2099-01-03.json"
    
    # 从趋势缓存获取数据
    trend_item = find_keyword_in_trend_cache(keyword)
    if not trend_item:
        print(f"⚠️ 未找到关键词 '{keyword}' 的趋势数据")
        return False
    
    print(f"✅ 找到趋势数据: 热度={trend_item.get('interest')}, 斜率={trend_item.get('slope')}")
    
    # 构建报告
    report = build_minimal_report_for_keyword(trend_item, keyword)
    
    # 保存报告
    save_json(report, report_file)
    print(f"✅ 已保存报告: {report_file}")
    
    # 运行生成脚本
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT_DIR / "scripts" / "generate_idea.py"),
            "--date", date,
            "--mode", mode,
            "--allow-repeat"
        ],
        capture_output=True,
        text=True,
        timeout=120
    )
    
    if result.returncode == 0:
        print(f"✅ 文章生成成功: {slug}")
        return True
    else:
        print(f"❌ 文章生成失败")
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="使用缓存数据重新生成所有文章")
    parser.add_argument("--mode", default="overwrite", choices=["skip", "overwrite", "fail"], 
                        help="文件已存在时的处理方式")
    parser.add_argument("--dry-run", action="store_true", help="只检查数据，不生成文章")
    args = parser.parse_args()
    
    print("="*60)
    print("使用缓存数据重新生成文章")
    print(f"模式: {args.mode}")
    print(f"关键词数量: {len(IDEA_KEYWORDS)}")
    print("="*60)
    
    success_count = 0
    failed_keywords = []
    
    for item in IDEA_KEYWORDS:
        keyword = item["keyword"]
        date = item["date"]
        slug = item["slug"]
        
        print(f"\n处理: {keyword} ({date})")
        
        # 检查数据
        trend_item = find_keyword_in_trend_cache(keyword)
        if not trend_item:
            print(f"❌ 未找到趋势数据: {keyword}")
            failed_keywords.append(keyword)
            continue
        
        print(f"  热度: {trend_item.get('interest')}, 斜率: {trend_item.get('slope')}, 数据点: {trend_item.get('data_points')}")
        
        if args.dry_run:
            print("  (dry-run，跳过生成)")
            success_count += 1
            continue
        
        # 生成文章
        if generate_idea_from_cache(keyword, date, slug, args.mode):
            success_count += 1
        else:
            failed_keywords.append(keyword)
        
        time.sleep(1)
    
    print("\n" + "="*60)
    print("生成完成")
    print(f"成功: {success_count}/{len(IDEA_KEYWORDS)}")
    if failed_keywords:
        print(f"失败: {failed_keywords}")
    print("="*60)


if __name__ == "__main__":
    main()
