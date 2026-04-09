#!/usr/bin/env python3
"""
重新生成所有已有文章，使用新的数据获取方案。
如果期间出现被目标网站反爬机制命中，重试三次仍然异常则中断剩余关键词的爬取。
"""

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from pipeline.discovery.pipeline_common import DATA_DIR, REPORTS_DIR, load_json, save_json

# 已有文章的关键词映射（从文件名和标题推断）
IDEA_KEYWORDS = [
    {"slug": "2025-04-02-merge-pdf-tool", "keyword": "merge pdf", "date": "2025-04-02"},
    {"slug": "2025-04-03-ai-pdf-converter", "keyword": "ai pdf converter", "date": "2025-04-03"},
    {"slug": "2026-04-04-pdf-to-word", "keyword": "pdf to word", "date": "2026-04-04"},
    {"slug": "2026-04-05-ai-humanizer", "keyword": "ai humanizer", "date": "2026-04-05"},
    {"slug": "2026-04-06-ai-video-editor", "keyword": "ai video editor", "date": "2026-04-06"},
    {"slug": "2026-04-06-compress-pdf", "keyword": "compress pdf", "date": "2026-04-06"},
    {"slug": "2026-04-07-ai-music-generator", "keyword": "ai music generator", "date": "2026-04-07"},
    {"slug": "2026-04-07-json-formatter", "keyword": "json formatter", "date": "2026-04-07"},
]

MAX_RETRIES = 3
RETRY_DELAY = 10


def backup_seed_roots() -> Path:
    """备份原始 seed_roots.json"""
    seed_file = DATA_DIR / "seed_roots.json"
    backup_file = DATA_DIR / "seed_roots.json.backup"
    if seed_file.exists():
        shutil.copy2(seed_file, backup_file)
    return backup_file


def restore_seed_roots(backup_file: Path):
    """恢复原始 seed_roots.json"""
    seed_file = DATA_DIR / "seed_roots.json"
    if backup_file.exists():
        shutil.copy2(backup_file, seed_file)
        backup_file.unlink()


def create_temp_seed(keyword: str):
    """创建临时 seed 文件只包含单个关键词"""
    seed_data = {
        "seed_roots": [keyword],
        "blacklist_patterns": [],
        "trend_benchmark": "chatgpt"
    }
    save_json(seed_data, DATA_DIR / "seed_roots.json")


def run_discovery_pipeline(date: str, retry_count: int = 0) -> tuple[bool, str]:
    """
    运行 discovery pipeline。
    返回 (success, error_message)
    """
    print(f"\n[Discovery] 运行 pipeline (尝试 {retry_count + 1}/{MAX_RETRIES})...")
    
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT_DIR / "pipeline" / "discovery" / "run_pipeline.py"),
                "--date", date,
                "--skip-serp",  # 跳过 SERP 以加快速度
            ],
            capture_output=True,
            text=True,
            timeout=600  # 10 分钟超时
        )
        
        print(result.stdout)
        if result.stderr:
            print(f"stderr: {result.stderr}")
        
        if result.returncode == 0:
            return True, ""
        else:
            return False, f"Pipeline 返回非零退出码: {result.returncode}"
            
    except subprocess.TimeoutExpired:
        return False, "超时"
    except Exception as e:
        return False, str(e)


def regenerate_idea(keyword: str, date: str, slug: str, mode: str = "overwrite") -> bool:
    """基于报告生成文章"""
    print(f"\n[Generate] 生成文章: {slug}")
    
    # 检查报告是否存在
    report_file = REPORTS_DIR / f"opportunity_report_{date}.json"
    if not report_file.exists():
        print(f"⚠️ 报告不存在: {report_file}")
        return False
    
    # 加载报告并检查是否包含目标关键词
    report = load_json(report_file)
    profiles = report.get("profiles", [])
    
    # 查找目标关键词的 profile
    keyword_lower = keyword.lower()
    target_profile = None
    for p in profiles:
        if p.get("keyword", "").lower() == keyword_lower:
            target_profile = p
            break
    
    if not target_profile:
        print(f"⚠️ 报告中未找到关键词 '{keyword}'，尝试使用 top_pick")
        target_profile = report.get("top_pick")
        if not target_profile:
            print("⚠️ 报告中没有可用数据")
            return False
    
    print(f"✅ 找到关键词数据: {target_profile.get('keyword')} (评分: {target_profile.get('score')})")
    
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
    
    print(result.stdout)
    if result.stderr:
        print(f"stderr: {result.stderr}")
    
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="重新生成所有已有文章")
    parser.add_argument("--mode", default="overwrite", choices=["skip", "overwrite", "fail"], 
                        help="文件已存在时的处理方式")
    parser.add_argument("--dry-run", action="store_true", help="只运行 discovery，不生成文章")
    args = parser.parse_args()
    
    print("="*60)
    print("开始重新生成所有文章")
    print(f"模式: {args.mode}")
    print(f"关键词数量: {len(IDEA_KEYWORDS)}")
    print("="*60)
    
    # 备份原始 seed 文件
    backup_file = backup_seed_roots()
    print(f"[Setup] 已备份 seed_roots.json")
    
    success_count = 0
    failed_keywords = []
    
    try:
        for item in IDEA_KEYWORDS:
            keyword = item["keyword"]
            date = item["date"]
            slug = item["slug"]
            
            print(f"\n{'='*60}")
            print(f"处理: {keyword} ({date})")
            print(f"{'='*60}")
            
            # 创建临时 seed
            create_temp_seed(keyword)
            
            # 尝试运行 discovery（带重试）
            discovery_success = False
            last_error = ""
            
            for attempt in range(MAX_RETRIES):
                if attempt > 0:
                    print(f"\n第 {attempt + 1} 次重试，等待 {RETRY_DELAY * attempt}s...")
                    time.sleep(RETRY_DELAY * attempt)
                
                success, error = run_discovery_pipeline(date, attempt)
                if success:
                    discovery_success = True
                    break
                else:
                    last_error = error
                    print(f"尝试 {attempt + 1}/{MAX_RETRIES} 失败: {error}")
            
            if not discovery_success:
                print(f"\n❌ 关键词 '{keyword}' 在 {MAX_RETRIES} 次尝试后仍然失败")
                print(f"错误: {last_error}")
                print("\n⚠️ 根据要求，中断剩余关键词的爬取")
                failed_keywords.append(keyword)
                break
            
            if args.dry_run:
                print(f"✅  discovery 完成 (dry-run，跳过文章生成)")
                success_count += 1
                continue
            
            # 生成文章
            if regenerate_idea(keyword, date, slug, args.mode):
                print(f"✅ 文章生成成功: {slug}")
                success_count += 1
            else:
                print(f"⚠️ 文章生成可能有问题: {slug}")
                failed_keywords.append(keyword)
            
            # 关键词间延迟
            time.sleep(2)
        
    finally:
        # 恢复原始 seed 文件
        restore_seed_roots(backup_file)
        print(f"\n[Cleanup] 已恢复原始 seed_roots.json")
    
    print("\n" + "="*60)
    print("重新生成完成")
    print(f"成功: {success_count}/{len(IDEA_KEYWORDS)}")
    if failed_keywords:
        print(f"失败/中断: {failed_keywords}")
    print("="*60)


if __name__ == "__main__":
    main()
