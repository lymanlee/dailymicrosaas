#!/usr/bin/env python3
"""
基于已有报告（含 SERP 数据）+ 竞品 profile 缓存，重生成所有历史文章。

不重跑 discovery，直接调用 generate_idea.py，以 overwrite 模式覆盖已有文章。
"""
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

# 历史文章映射：slug -> (date, report_date)
# report_date: generate_idea.py --date 参数（决定读哪个报告文件）
# 对于同一报告多文章（2026-04-06），需要确认 generate_idea.py 如何选择 keyword
IDEA_MAP = [
    {"slug": "2025-04-02-merge-pdf-tool",    "date": "2025-04-02", "keyword": "merge pdf"},
    {"slug": "2025-04-03-ai-pdf-converter",  "date": "2025-04-03", "keyword": "pdf converter"},
    {"slug": "2026-04-04-pdf-to-word",       "date": "2026-04-04", "keyword": "pdf to word"},
    {"slug": "2026-04-05-ai-humanizer",      "date": "2026-04-05", "keyword": "ai humanizer"},
    {"slug": "2026-04-06-ai-video-editor",   "date": "2026-04-06", "keyword": "ai video editor"},
    {"slug": "2026-04-06-compress-pdf",      "date": "2026-04-06", "keyword": "compress pdf"},
    {"slug": "2026-04-07-ai-music-generator","date": "2026-04-07", "keyword": "ai music generator", "report_date": "2099-01-03"},
    {"slug": "2026-04-07-json-formatter",    "date": "2026-04-07", "keyword": "json formatter"},
]


def set_top_pick_for_keyword(report_date: str, keyword: str):
    """
    将报告的 top_pick 切换为指定 keyword 的 profile，
    确保 generate_idea.py 生成正确的文章。
    report_date: 报告文件对应的日期（opportunity_report_{report_date}.json）
    """
    import json
    reports_dir = ROOT_DIR / "pipeline" / "reports"
    report_file = reports_dir / f"opportunity_report_{report_date}.json"

    if not report_file.exists():
        print(f"  ⚠️ 报告不存在: {report_file}")
        return False

    with open(report_file) as f:
        report = json.load(f)

    profiles = report.get("profiles", [])
    target = None
    for p in profiles:
        if p.get("keyword", "").lower() == keyword.lower():
            target = p
            break

    if not target:
        print(f"  ⚠️ 报告中未找到 keyword: {keyword}")
        return False

    report["top_pick"] = target
    with open(report_file, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"  ✓ top_pick 切换为: {keyword} (score={target.get('score')})")
    return True


def regenerate(item: dict) -> bool:
    slug = item["slug"]
    date = item["date"]
    keyword = item["keyword"]
    # 报告文件日期，ai music generator 在 2099-01-03 报告里
    report_date = item.get("report_date", date)

    print(f"\n{'='*60}")
    print(f"重生成: {slug}")
    print(f"文章日期: {date}, 报告日期: {report_date}, 关键词: {keyword}")
    print(f"{'='*60}")

    # 如果报告日期与文章日期不同，需要先把 top_pick 写入文章日期对应的报告
    # generate_idea.py 默认读 opportunity_report_{date}.json
    if report_date != date:
        import json, shutil
        src = ROOT_DIR / "pipeline" / "reports" / f"opportunity_report_{report_date}.json"
        dst = ROOT_DIR / "pipeline" / "reports" / f"opportunity_report_{date}.json"
        if not src.exists():
            print(f"  ⚠️ 源报告不存在: {src}")
            return False
        # 读取源报告，找到目标 keyword 的 profile，写入文章日期报告
        with open(src) as f:
            src_report = json.load(f)
        profiles = src_report.get("profiles", [])
        target = None
        for p in profiles:
            if p.get("keyword", "").lower() == keyword.lower():
                target = p
                break
        if not target:
            print(f"  ⚠️ 源报告中未找到 keyword: {keyword}")
            return False
        # 构造临时报告（只含目标 profile）
        tmp_report = {
            "profiles": [target],
            "top_pick": target,
            "candidates": [target],
            "summary": {"total": 1, "worth_it": 1, "watch": 0, "skip": 0},
        }
        with open(dst, "w") as f:
            json.dump(tmp_report, f, ensure_ascii=False, indent=2)
        print(f"  ✓ 已将 {keyword} profile 写入报告: {dst}")
    else:
        # 切换 top_pick
        if not set_top_pick_for_keyword(report_date, keyword):
            return False

    # 调用 generate_idea.py
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT_DIR / "scripts" / "generate_idea.py"),
            "--date", date,
            "--mode", "overwrite",
            "--allow-repeat",
        ],
        capture_output=True,
        text=True,
        timeout=180,
        env={**__import__("os").environ},
    )

    print(result.stdout)
    if result.stderr:
        # 过滤掉 urllib3 警告
        stderr_lines = [l for l in result.stderr.splitlines() if "NotOpenSSLWarning" not in l and "warnings.warn" not in l and l.strip()]
        if stderr_lines:
            print("stderr:", "\n".join(stderr_lines))

    if result.returncode == 0:
        # 检查输出文件是否和目标 slug 一致
        import re
        output_match = re.search(r'输出: (.+\.md)', result.stdout)
        if output_match:
            generated_file = Path(output_match.group(1).strip())
            target_file = ROOT_DIR / "src" / "content" / "ideas" / f"{slug}.md"
            if generated_file.exists() and generated_file != target_file:
                # 将生成内容覆盖到目标 slug 文件
                content = generated_file.read_text(encoding="utf-8")
                target_file.write_text(content, encoding="utf-8")
                generated_file.unlink()  # 删除非目标文件
                print(f"  ✓ 内容已写入: {target_file.name}（临时文件 {generated_file.name} 已清除）")
            elif generated_file == target_file:
                print(f"  ✓ 输出路径正确: {generated_file.name}")
        print(f"✅ 成功: {slug}")
        return True
    else:
        print(f"❌ 失败: {slug} (exit={result.returncode})")
        return False


def main():
    print("="*60)
    print("重生成所有历史文章（基于已有报告 + 竞品 profiles）")
    print(f"共 {len(IDEA_MAP)} 篇")
    print("="*60)

    success = 0
    failed = []

    for item in IDEA_MAP:
        ok = regenerate(item)
        if ok:
            success += 1
        else:
            failed.append(item["slug"])
        time.sleep(2)

    print("\n" + "="*60)
    print(f"完成: {success}/{len(IDEA_MAP)}")
    if failed:
        print(f"失败: {failed}")
    print("="*60)


if __name__ == "__main__":
    main()
