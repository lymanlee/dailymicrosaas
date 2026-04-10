#!/usr/bin/env python3
"""
高效重跑历史关键词的 discovery，只获取 SERP 数据。
跳过 community 和 trend（复用旧报告数据），大幅节省时间。
"""

import json
import subprocess
import sys
import time
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKUP_DIR = ROOT / "pipeline/reports_backup_20260410_002050"
REPORTS_DIR = ROOT / "pipeline/reports"
DATA_DIR = ROOT / "data"

KEYWORDS = [
    ("2025-04-03", "ai pdf converter"),
    ("2026-04-04", "pdf to word"),
    ("2026-04-05", "ai humanizer"),
    ("2026-04-06", "ai video editor"),
    ("2026-04-06", "compress pdf"),
    ("2026-04-07", "ai music generator"),
    ("2026-04-07", "json formatter"),
]


def normalize_kw(kw: str) -> str:
    """标准化关键词用于匹配"""
    import re
    kw = kw.lower().strip()
    kw = re.sub(r"[^a-z0-9\s]", "", kw)
    kw = re.sub(r"\s+", " ", kw)
    return kw


def patch_report_with_serp(old_report: dict, new_report: dict, keyword: str) -> bool:
    """把新报告的 SERP 数据 patch 进旧报告（保留旧报告的 trend + community）。"""
    kw_norm = normalize_kw(keyword)
    old_profile = None
    new_profile = None

    for p in old_report.get("profiles", []):
        if normalize_kw(p.get("keyword", "")) == kw_norm:
            old_profile = p
            break

    for p in new_report.get("profiles", []):
        if normalize_kw(p.get("keyword", "")) == kw_norm:
            new_profile = p
            break

    if not old_profile:
        print(f"  ⚠️ 旧报告中未找到关键词: {keyword}")
        return False
    if not new_profile:
        print(f"  ⚠️ 新报告中未找到关键词: {keyword}")
        return False

    serp_niche = new_profile.get("serp_niche_sites", [])
    serp_big = new_profile.get("serp_big_sites", [])
    if not serp_niche and not serp_big:
        print(f"  ⚠️ 新报告无 SERP 数据: {keyword}")
        return False

    old_profile["serp_niche_sites"] = serp_niche
    old_profile["serp_big_sites"] = serp_big

    print(f"  ✅ patch: niche={serp_niche[:3]}...({len(serp_niche)}个), big={serp_big[:3]}...({len(serp_big)}个)")
    return True


def run_pipeline_for_keyword(date: str, keyword: str) -> dict:
    """运行单个关键词的 pipeline（只跑 SERP），返回新报告内容。"""
    # 写临时 seed
    seed = {
        "seed_roots": [keyword],
        "blacklist_patterns": [],
        "trend_benchmark": "chatgpt",
    }
    with open(DATA_DIR / "seed_roots.json", "w") as f:
        json.dump(seed, f, indent=2)

    # 创建空 community cache 文件，防止 pipeline 触发 community scan
    # pipeline 发现 cache 存在但为空时会跳过，不会回退到扫描
    community_cache = DATA_DIR / f"community_signals_{date}.json"
    if not community_cache.exists():
        with open(community_cache, "w") as f:
            json.dump({"keywords": {}, "timestamp": date}, f)

    # 清理旧报告（防止 pipeline 读到旧的 serp 数据）
    report_file = REPORTS_DIR / f"opportunity_report_{date}.json"
    if report_file.exists():
        report_file.unlink()

    print(f"  🌐 跑 pipeline ({keyword})...")
    start = time.time()
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "pipeline/discovery/run_pipeline.py"),
            "--date", date,
            "--skip-trends",
            "--skip-community",
        ],
        capture_output=True,
        text=True,
        timeout=900,  # 15 分钟超时
        cwd=str(ROOT),
    )
    elapsed = time.time() - start
    print(f"  ⏱️  耗时 {elapsed:.0f}s，returncode={result.returncode}")

    if result.returncode != 0:
        print(f"  ❌ pipeline 失败: {result.stderr[-500:]}")
        return None

    # 读取新报告
    if report_file.exists():
        return json.load(open(report_file))
    return None


def main():
    print("=" * 60)
    print("高效 discovery：只跑 SERP，patch 进旧报告")
    print("=" * 60)

    success = 0
    failed = []

    for date, keyword in KEYWORDS:
        print(f"\n[{date}] {keyword}")

        old_report_file = BACKUP_DIR / f"opportunity_report_{date}.json"
        if not old_report_file.exists():
            print(f"  ⚠️ 无备份报告，跳过")
            failed.append(keyword)
            continue

        old_report = json.load(open(old_report_file))

        # 检查旧报告是否已有 serp 数据
        has_serp = any(
            p.get("serp_niche_sites") or p.get("serp_big_sites")
            for p in old_report.get("profiles", [])
            if p.get("keyword", "").lower() == keyword.lower()
        )
        if has_serp:
            # serp 已存在，直接用旧报告（之前跑过或已 patch）
            print(f"  ✅ serp 数据已存在，跳过 pipeline")
            shutil.copy2(old_report_file, REPORTS_DIR / f"opportunity_report_{date}.json")
            success += 1
            continue

        # 运行 pipeline 获取 SERP
        new_report = run_pipeline_for_keyword(date, keyword)

        if new_report:
            patched = patch_report_with_serp(old_report, new_report, keyword)
            if patched:
                with open(REPORTS_DIR / f"opportunity_report_{date}.json", "w") as f:
                    json.dump(old_report, f, indent=2)
                print(f"  ✅ 报告已更新")
                success += 1
            else:
                failed.append(keyword)
        else:
            failed.append(keyword)

        # 关键词间隔 3 秒
        time.sleep(3)

    # 恢复原始 seed
    original_seed = BACKUP_DIR / "seed_roots_original.json"
    if original_seed.exists():
        shutil.copy2(original_seed, DATA_DIR / "seed_roots.json")

    print("\n" + "=" * 60)
    print(f"完成：成功 {success}/{len(KEYWORDS)}")
    if failed:
        print(f"失败: {failed}")
    print("=" * 60)


if __name__ == "__main__":
    main()
