#!/usr/bin/env python3
"""
竞品爬取 Worker

从队列中获取任务，执行爬取，更新 Registry
"""
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from pipeline.competitor_analysis.task_queue import CompetitorCrawlQueue, calculate_competitor_priority
from pipeline.competitor_analysis.run_analysis import run_analysis_for_domain


def process_task(task) -> bool:
    """
    处理单个爬取任务

    Args:
        task: CrawlTask 对象

    Returns:
        是否成功
    """
    domain = task.domain
    print(f"[Worker] Processing: {domain} (priority: {task.priority})")

    try:
        # 执行爬取
        result = run_analysis_for_domain(domain, force_refresh=True)

        if result and result.get('success'):
            print(f"[Worker] ✓ {domain} - Success")
            return True
        else:
            print(f"[Worker] ✗ {domain} - Failed: {result.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"[Worker] ✗ {domain} - Exception: {e}")
        return False


def run_worker(
    max_tasks: int = 10,
    poll_interval: int = 60,
    batch_size: int = 3
):
    """
    运行 Worker

    Args:
        max_tasks: 最大处理任务数（0 = 无限制）
        poll_interval: 轮询间隔（秒）
        batch_size: 每批处理任务数
    """
    queue = CompetitorCrawlQueue()
    processed = 0

    print(f"[Worker] Starting worker...")
    print(f"[Worker] Max tasks: {max_tasks}, Poll interval: {poll_interval}s")

    while True:
        # 检查是否达到最大任务数
        if max_tasks > 0 and processed >= max_tasks:
            print(f"[Worker] Reached max tasks ({max_tasks}), stopping...")
            break

        # 获取下一个任务
        task = queue.get_next()

        if task is None:
            # 队列为空
            stats = queue.get_stats()
            print(f"[Worker] Queue empty. Stats: {stats}")

            if stats['failed'] > 0:
                print(f"[Worker] Warning: {stats['failed']} failed tasks in queue")
                # 可以发送告警通知

            if max_tasks > 0:
                # 单次运行模式
                break

            # 等待后重新检查
            print(f"[Worker] Waiting {poll_interval}s before next check...")
            time.sleep(poll_interval)
            continue

        # 处理任务
        success = process_task(task)

        # 更新队列
        queue.complete(task.domain, success=success)
        processed += 1

        # 批次间隔
        if batch_size > 0 and processed % batch_size == 0:
            print(f"[Worker] Processed {processed} tasks, taking a break...")
            time.sleep(5)

    print(f"[Worker] Done. Processed {processed} tasks.")
    return processed


def main():
    parser = argparse.ArgumentParser(description="竞品爬取 Worker")
    parser.add_argument(
        "--max-tasks",
        type=int,
        default=10,
        help="最大处理任务数（0 = 无限制，默认 10）"
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=60,
        help="轮询间隔秒数（默认 60）"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=3,
        help="每批处理任务数（默认 3）"
    )
    parser.add_argument(
        "--domain",
        type=str,
        help="直接处理指定域名（不使用队列）"
    )

    args = parser.parse_args()

    if args.domain:
        # 直接处理单个域名
        print(f"[Worker] Processing single domain: {args.domain}")
        from pipeline.competitor_analysis.run_analysis import run_analysis_for_domain
        result = run_analysis_for_domain(args.domain, force_refresh=True)
        if result and result.get('success'):
            print(f"✓ Success: {args.domain}")
        else:
            print(f"✗ Failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
    else:
        # 启动 Worker
        run_worker(
            max_tasks=args.max_tasks,
            poll_interval=args.poll_interval,
            batch_size=args.batch_size
        )


if __name__ == "__main__":
    main()
