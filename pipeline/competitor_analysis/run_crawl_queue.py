#!/usr/bin/env python3
"""
竞品爬取队列消费者。

从 data/competitor_crawl_queue.json 读取待爬域名，逐个执行竞品分析，
分析结果写入 pipeline/competitor_analysis/cache/competitor_profiles/。

Usage:
    python run_crawl_queue.py                      # 消费所有 pending 域名
    python run_crawl_queue.py --limit 5            # 最多处理 5 个
    python run_crawl_queue.py --domains a.com,b.com # 指定域名（绕过队列）
    python run_crawl_queue.py --dry-run            # 只看队列状态，不执行
    python run_crawl_queue.py --force-refresh      # 强制重新爬取已缓存的域名
"""
import argparse
import sys
import time
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load .env if present (local dev); in CI env vars are set directly
_dotenv_path = Path(__file__).parent.parent / ".env"
if _dotenv_path.exists():
    load_dotenv(_dotenv_path)

from competitor_analysis import (
    CompetitorFetcher,
    SiliconFlowAnalyzer,
    CompetitorCache,
)
from task_queue import CompetitorCrawlQueue


def analyze_domain(domain: str, force_refresh: bool = False) -> bool:
    """
    对单个域名执行竞品分析。

    Returns:
        True if analysis succeeded, False otherwise.
    """
    fetcher = CompetitorFetcher()
    analyzer = SiliconFlowAnalyzer()
    cache = CompetitorCache()

    # 检查缓存（无 force_refresh 时跳过）
    if not force_refresh:
        cached = cache.get(domain)
        if cached:
            print(f"  ✓ 已缓存: {domain} (上次分析: {cached.analyzed_at[:10]})")
            return True

    # 抓取网页
    print(f"  抓取 {domain}...")
    pages = fetcher.fetch_all(domain)

    if not pages.get("landing"):
        print(f"  ✗ 无法获取 landing page，跳过")
        return False

    # LLM 分析
    print(f"  LLM 分析中...")
    profile = analyzer.analyze_competitor(
        domain=domain,
        landing_html=pages["landing"],
        pricing_html=pages.get("pricing", ""),
    )

    if profile:
        cache.set(profile)
        print(f"  ✓ 分析完成: {profile.name}")
        return True
    else:
        print(f"  ✗ LLM 分析失败")
        return False


def run_queue(max_domains: int = 20, force_refresh: bool = False, verbose: bool = False) -> dict:
    """
    消费队列，返回统计结果。
    """
    queue = CompetitorCrawlQueue()
    stats = queue.get_stats()

    print(f"\n{'='*60}")
    print(f"竞品爬取队列消费者")
    print(f"{'='*60}")
    print(f"队列状态: {stats}")
    print(f"本次最大处理: {max_domains}")
    print(f"强制刷新: {force_refresh}")
    print()

    pending = queue.get_pending_domains()
    if not pending:
        print("队列为空，无待处理域名")
        return {"processed": 0, "success": 0, "failed": 0, "skipped": 0}

    to_process = pending[:max_domains]
    print(f"本次待处理域名 ({len(to_process)}): {to_process}\n")

    processed = 0
    success = 0
    failed = 0
    skipped = 0

    for domain in to_process:
        processed += 1
        print(f"[{processed}/{len(to_process)}] 处理 {domain}...")

        task = queue.get_next()
        if task and task.domain != domain:
            # domain 在并发情况下顺序可能变化，安全处理
            pass

        ok = analyze_domain(domain, force_refresh=force_refresh)
        queue.complete(domain, success=ok)

        if ok:
            success += 1
        else:
            failed += 1

        # 防止 API 过载
        time.sleep(2)

    final_stats = queue.get_stats()
    print(f"\n{'='*60}")
    print(f"完成: 成功 {success}, 失败 {failed}, 剩余 pending {final_stats['pending']}")
    print(f"{'='*60}")

    return {
        "processed": processed,
        "success": success,
        "failed": failed,
        "skipped": skipped,
        "remaining_pending": final_stats["pending"],
    }


def main():
    parser = argparse.ArgumentParser(description="竞品爬取队列消费者")
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="本次最多处理的域名数量（默认 20）",
    )
    parser.add_argument(
        "--domains",
        help="指定域名（逗号分隔），绕过队列直接爬取",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="强制重新爬取已缓存的域名",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只显示队列状态，不执行爬取",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细输出",
    )
    args = parser.parse_args()

    # 指定域名模式
    if args.domains:
        domains = [d.strip() for d in args.domains.split(",")]
        print(f"\n直接处理指定域名: {domains}\n")

        if args.dry_run:
            print("[dry-run] 不执行实际爬取")
            return

        success = 0
        failed = 0
        for domain in domains:
            ok = analyze_domain(domain, force_refresh=args.force_refresh)
            if ok:
                success += 1
            else:
                failed += 1
            time.sleep(2)

        print(f"\n完成: 成功 {success}, 失败 {failed}")
        return

    # 队列模式
    if args.dry_run:
        queue = CompetitorCrawlQueue()
        stats = queue.get_stats()
        pending = queue.get_pending_domains()
        print(f"\n队列状态: {stats}")
        print(f"待处理域名: {pending}")
        return

    result = run_queue(
        max_domains=args.limit,
        force_refresh=args.force_refresh,
        verbose=args.verbose,
    )

    # 退出码：有失败就非零
    if result["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
