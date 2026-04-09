"""
竞品爬取任务队列

支持：
- 优先级队列（SERP 出现频率高的优先）
- 重试机制
- 失败告警
"""
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
import json
from pathlib import Path
from datetime import datetime, timezone
import os


@dataclass
class CrawlTask:
    """爬取任务"""
    domain: str
    priority: int  # 1-10, 越高越优先
    source_keyword: str  # 发现该域名的关键词
    created_at: str
    retry_count: int = 0
    status: str = "pending"  # pending | running | done | failed


class CompetitorCrawlQueue:
    """竞品爬取任务队列"""

    def __init__(
        self,
        queue_file: Optional[str] = None,
        max_retries: int = 3
    ):
        if queue_file is None:
            project_root = Path(__file__).parent.parent.parent
            queue_file = str(project_root / "data/competitor_crawl_queue.json")

        self.queue_file = Path(queue_file)
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)
        self.max_retries = max_retries

    def _load(self) -> List[Dict[str, Any]]:
        """加载队列"""
        if not self.queue_file.exists():
            return []
        try:
            with open(self.queue_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save(self, tasks: List[Dict[str, Any]]):
        """保存队列"""
        with open(self.queue_file, "w", encoding="utf-8") as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)

    def add(
        self,
        domain: str,
        priority: int = 5,
        source_keyword: str = ""
    ) -> bool:
        """
        添加爬取任务

        Args:
            domain: 竞品域名
            priority: 优先级 1-10
            source_keyword: 发现该域名的关键词

        Returns:
            是否添加成功（False 表示已在队列中）
        """
        tasks = self._load()

        # 检查是否已存在
        existing = next((t for t in tasks if t['domain'] == domain), None)
        if existing:
            # 提升优先级
            existing['priority'] = max(existing['priority'], priority)
            existing['retry_count'] = 0
            existing['status'] = 'pending'
            self._save(tasks)
            return False

        # 添加新任务
        tasks.append(CrawlTask(
            domain=domain,
            priority=priority,
            source_keyword=source_keyword,
            created_at=datetime.now(timezone.utc).isoformat()
        ).__dict__)

        self._save(tasks)
        return True

    def add_batch(
        self,
        items: List[Dict[str, Any]],
        min_priority: int = 5
    ):
        """
        批量添加任务

        Args:
            items: [{"domain": "...", "priority": 8, "source_keyword": "..."}]
            min_priority: 最小优先级
        """
        for item in items:
            self.add(
                domain=item['domain'],
                priority=item.get('priority', min_priority),
                source_keyword=item.get('source_keyword', '')
            )

    def get_next(self) -> Optional[CrawlTask]:
        """获取下一个待处理任务"""
        tasks = self._load()
        if not tasks:
            return None

        # 过滤出 pending 任务
        pending = [t for t in tasks if t['status'] == 'pending']
        if not pending:
            return None

        # 按优先级排序（优先级相同时按创建时间）
        pending.sort(key=lambda t: (-t['priority'], t['created_at']))

        task = pending[0]
        task['status'] = 'running'
        self._save(tasks)

        return CrawlTask(**task)

    def complete(self, domain: str, success: bool = True):
        """
        标记任务完成

        Args:
            domain: 竞品域名
            success: 是否成功
        """
        tasks = self._load()

        for task in tasks:
            if task['domain'] == domain:
                if success:
                    # 成功：移除任务
                    tasks.remove(task)
                else:
                    # 失败：增加重试计数
                    task['retry_count'] += 1
                    task['status'] = 'pending' if task['retry_count'] < self.max_retries else 'failed'

        self._save(tasks)

    def get_stats(self) -> Dict[str, int]:
        """获取队列统计"""
        tasks = self._load()
        return {
            'total': len(tasks),
            'pending': len([t for t in tasks if t['status'] == 'pending']),
            'running': len([t for t in tasks if t['status'] == 'running']),
            'failed': len([t for t in tasks if t['status'] == 'failed']),
        }

    def get_pending_domains(self) -> List[str]:
        """获取待处理的域名列表"""
        tasks = self._load()
        return [t['domain'] for t in tasks if t['status'] == 'pending']

    def clear_completed(self):
        """清除已完成任务"""
        tasks = self._load()
        tasks = [t for t in tasks if t['status'] in ('pending', 'running')]
        self._save(tasks)


def calculate_competitor_priority(
    domain: str,
    ideas: List[Dict[str, Any]],
    last_crawl_time: Optional[str] = None
) -> int:
    """
    计算竞品爬取优先级

    因素：
    1. SERP 出现次数（越多越重要）
    2. 相关 idea 的评分（高分 idea 中的竞品更重要）
    3. 距离上次爬取时间（越久越优先）
    """
    appearances = 0
    total_score = 0

    for idea in ideas:
        sites = idea.get('serp_niche_sites', []) + idea.get('serp_big_sites', [])
        if domain in sites:
            appearances += 1
            total_score += idea.get('score', 0)

    # 基础分：出现次数 × 10
    base = appearances * 10

    # 加权分：平均 idea 评分 × 5
    weighted = (total_score / appearances * 5) if appearances else 0

    # 上次爬取时间惩罚
    if last_crawl_time:
        try:
            last = datetime.fromisoformat(last_crawl_time.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            days_since = (now - last).total_seconds() / (24 * 3600)
            time_bonus = min(days_since * 2, 20)  # 最多加20分
        except Exception:
            time_bonus = 10
    else:
        time_bonus = 30  # 新发现的+30分

    return min(int(base + weighted + time_bonus), 100)


# 测试
if __name__ == "__main__":
    queue = CompetitorCrawlQueue()

    # 添加测试任务
    queue.add("test1.com", priority=8, source_keyword="ai tool")
    queue.add("test2.com", priority=5, source_keyword="productivity")
    queue.add("test1.com", priority=10, source_keyword="ai tool v2")  # 提升优先级

    # 获取统计
    print(f"Queue stats: {queue.get_stats()}")
    print(f"Pending: {queue.get_pending_domains()}")

    # 获取下一个任务
    next_task = queue.get_next()
    if next_task:
        print(f"Next task: {next_task.domain} (priority: {next_task.priority})")

    # 标记完成
    queue.complete("test1.com", success=True)
    print(f"After complete: {queue.get_stats()}")
