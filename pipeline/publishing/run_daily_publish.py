#!/usr/bin/env python3
"""
统一编排内容自动发布链路：
1. 跑 discovery pipeline（或复用已有报告）
2. 生成今日 idea Markdown
3. 校验生成内容
4. 构建 Astro 站点
5. 只有在质量门槛通过后才允许 commit/push，交给 Cloudflare Pages 自动部署

额外职责：
- 为 CI 输出结构化运行摘要（JSON + Markdown）
- 在 GitHub Actions 中写入 job summary，方便直接排查失败原因
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_LOG_DIR = PROJECT_ROOT / "pipeline" / "logs"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.publishing.generate_idea import (
    find_report_path,
    generate_idea,
    load_report,
    normalize_report_payload,
    resolve_run_date,
)
from pipeline.publishing.validate_idea import audit_content_quality, validate_markdown

# 这里仅放“即使用户没开严格模式，也足以阻断发布”的 discovery 告警。
# 像 `--skip-serp` 这种显式开关触发的降级路径，只应保留为普通 warning，
# 否则 dry run / 手动验证会因为用户主动跳过 SERP 而被误判失败。
SEVERE_DISCOVERY_WARNING_MARKERS = [
    "超过 50% 被限流",
    "未获得任何信号",
    "所有 SERP 采集结果为空",
]


def run_command(command: list[str], cwd: Path = PROJECT_ROOT) -> str:
    result = subprocess.run(command, cwd=str(cwd), capture_output=True, text=True)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "命令执行失败"
        raise RuntimeError(f"命令失败: {' '.join(command)}\n{message}")
    return result.stdout.strip()


def build_site() -> None:
    print("\n[Build] 开始构建 Astro 站点...")
    run_command(["npm", "run", "build"])
    print("[Build] ✅ 构建通过")


def commit_generated_content(target_file: Path, date_str: str) -> bool:
    run_command(["git", "add", str(target_file.relative_to(PROJECT_ROOT))])
    status_after_add = run_command(["git", "status", "--porcelain"])
    if not status_after_add.strip():
        print("[Git] 没有可提交的内容变更")
        return False

    message = f"content: add daily idea for {date_str}"
    run_command(["git", "commit", "-m", message])
    print(f"[Git] ✅ 已提交: {message}")
    return True


def push_changes(branch: str) -> None:
    run_command(["git", "push", "origin", branch])
    print(f"[Git] ✅ 已推送到 origin/{branch}")


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def unique_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        output.append(normalized)
    return output


def derive_report_summary(report_payload: dict[str, Any]) -> dict[str, int]:
    summary = report_payload.get("summary")
    if isinstance(summary, dict):
        return {
            "total": int(summary.get("total", 0) or 0),
            "worth_it": int(summary.get("worth_it", 0) or 0),
            "watch": int(summary.get("watch", 0) or 0),
            "skip": int(summary.get("skip", 0) or 0),
        }

    opportunities = report_payload.get("opportunities", {})
    worth_it = opportunities.get("worth_it", []) or []
    watch = opportunities.get("watch", []) or []
    skip = opportunities.get("skip", []) or []
    total = report_payload.get("profiles") or []
    return {
        "total": len(total),
        "worth_it": len(worth_it),
        "watch": len(watch),
        "skip": len(skip),
    }


def audit_pipeline_health(
    report_payload: dict[str, Any],
    discovery_warnings: list[str],
    min_score: float,
    fail_on_soft_discovery_warning: bool = False,
) -> tuple[list[str], list[str]]:
    """根据 discovery 结果做发布前门槛校验。"""
    warnings: list[str] = []
    errors: list[str] = []

    summary = derive_report_summary(report_payload)
    top_pick = report_payload.get("top_pick") or {}

    if summary["total"] <= 0:
        errors.append("discovery 报告为空，没有任何候选关键词，发布被阻止")

    if summary["worth_it"] <= 0:
        errors.append("discovery 报告中 worth_it 候选为 0，发布被阻止")

    if not top_pick:
        errors.append("discovery 报告缺少 top_pick，无法继续生成内容")
    else:
        top_pick_score = float(top_pick.get("score", 0) or 0)
        if top_pick_score < min_score:
            errors.append(
                f"top_pick 分数过低（{top_pick_score} < {min_score}），发布被阻止"
            )

    severe_warnings: list[str] = []
    soft_warnings: list[str] = []
    for warning in discovery_warnings:
        if any(marker in warning for marker in SEVERE_DISCOVERY_WARNING_MARKERS):
            severe_warnings.append(warning)
        else:
            soft_warnings.append(warning)

    if severe_warnings:
        for warning in severe_warnings:
            errors.append(f"discovery 严重告警：{warning}")

    if soft_warnings:
        if fail_on_soft_discovery_warning:
            for warning in soft_warnings:
                errors.append(f"discovery 告警已按严格模式拦截：{warning}")
        else:
            warnings.extend(soft_warnings)

    return unique_keep_order(warnings), unique_keep_order(errors)


def create_run_summary(args: argparse.Namespace, resolved_date: str) -> dict[str, Any]:
    return {
        "date": resolved_date,
        "started_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "finished_at": None,
        "status": "running",
        "inputs": {
            "report": args.report,
            "skip_discovery": args.skip_discovery,
            "skip_trends": args.skip_trends,
            "skip_community": args.skip_community,
            "skip_serp": args.skip_serp,
            "max_serp_keywords": args.max_serp_keywords,
            "fresh_data": args.fresh_data,
            "min_score": args.min_score,
            "allow_repeat": args.allow_repeat,
            "mode": args.mode,
            "no_build": args.no_build,
            "commit": args.commit,
            "push": args.push,
            "branch": args.branch,
            "dry_run": args.dry_run,
            "fail_on_soft_discovery_warning": args.fail_on_soft_discovery_warning,
            "fail_on_quality_warning": args.fail_on_quality_warning,
        },
        "paths": {
            "project_root": str(PROJECT_ROOT),
            "report_json": None,
            "report_txt": None,
            "generated_markdown": None,
            "summary_json": str(Path(args.summary_json).resolve()) if args.summary_json else None,
            "summary_md": str(Path(args.summary_md).resolve()) if args.summary_md else None,
        },
        "candidate": None,
        "report_summary": None,
        "steps": [],
        "warnings": [],
        "errors": [],
        "git": {
            "committed": False,
            "pushed": False,
            "branch": args.branch,
        },
    }


def add_step(summary: dict[str, Any], name: str, status: str, details: dict[str, Any] | None = None) -> None:
    entry: dict[str, Any] = {
        "name": name,
        "status": status,
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    if details:
        entry["details"] = details
    summary["steps"].append(entry)


def build_summary_markdown(summary: dict[str, Any]) -> str:
    candidate = summary.get("candidate") or {}
    report_summary = summary.get("report_summary") or {}
    git_info = summary.get("git") or {}

    lines = [
        "# Daily Publish Summary",
        "",
        f"- 状态：**{summary.get('status', 'unknown')}**",
        f"- 日期：`{summary.get('date', '-')}`",
        f"- 开始时间：`{summary.get('started_at', '-')}`",
        f"- 结束时间：`{summary.get('finished_at', '-')}`",
        "",
        "## 候选结果",
        "",
        f"- 关键词：`{candidate.get('keyword', '-')}`",
        f"- 标题：{candidate.get('title', '-')}",
        f"- 分数：`{candidate.get('score', '-')}`",
        f"- 分级：`{candidate.get('grade', '-')}`",
        f"- 状态：`{candidate.get('status', '-')}`",
        "",
        "## Discovery 报告摘要",
        "",
        f"- total：`{report_summary.get('total', '-')}`",
        f"- worth_it：`{report_summary.get('worth_it', '-')}`",
        f"- watch：`{report_summary.get('watch', '-')}`",
        f"- skip：`{report_summary.get('skip', '-')}`",
        "",
        "## 执行步骤",
        "",
        "| 步骤 | 状态 | 说明 |",
        "| --- | --- | --- |",
    ]

    for step in summary.get("steps", []):
        details = step.get("details") or {}
        detail_str = "; ".join(f"{key}={value}" for key, value in details.items()) if details else "-"
        lines.append(f"| {step.get('name', '-')} | {step.get('status', '-')} | {detail_str} |")

    lines.extend([
        "",
        "## Git 状态",
        "",
        f"- committed：`{git_info.get('committed', False)}`",
        f"- pushed：`{git_info.get('pushed', False)}`",
        f"- branch：`{git_info.get('branch', '-')}`",
        "",
        "## 输出路径",
        "",
    ])

    for key, value in (summary.get("paths") or {}).items():
        lines.append(f"- {key}: `{value or '-'}`")

    warnings = summary.get("warnings") or []
    errors = summary.get("errors") or []

    lines.append("")
    lines.append("## 告警")
    lines.append("")
    if warnings:
        for warning in warnings:
            lines.append(f"- ⚠️ {warning}")
    else:
        lines.append("- 无")

    lines.append("")
    lines.append("## 错误")
    lines.append("")
    if errors:
        for error in errors:
            lines.append(f"- ❌ {error}")
    else:
        lines.append("- 无")

    return "\n".join(lines) + "\n"


def write_run_summary(summary: dict[str, Any], json_path: Path, md_path: Path) -> None:
    ensure_parent_dir(json_path)
    ensure_parent_dir(md_path)
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_summary_markdown(summary), encoding="utf-8")


def append_github_step_summary(markdown: str) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    path = Path(summary_path)
    ensure_parent_dir(path)
    with path.open("a", encoding="utf-8") as file:
        file.write(markdown)
        file.write("\n")


def resolve_summary_paths(args: argparse.Namespace, resolved_date: str) -> tuple[Path, Path]:
    PIPELINE_LOG_DIR.mkdir(parents=True, exist_ok=True)
    json_path = Path(args.summary_json) if args.summary_json else PIPELINE_LOG_DIR / f"daily_publish_{resolved_date}.summary.json"
    md_path = Path(args.summary_md) if args.summary_md else PIPELINE_LOG_DIR / f"daily_publish_{resolved_date}.summary.md"
    return json_path, md_path


def main() -> None:
    parser = argparse.ArgumentParser(description="执行 Daily Micro SaaS 内容自动发布")
    parser.add_argument("--date", default=None, help="发布日期 (YYYY-MM-DD)，默认今天")
    parser.add_argument("--report", default=None, help="复用已有报告路径，跳过自动发现")
    parser.add_argument("--skip-discovery", action="store_true", help="跳过 discovery pipeline，直接消费已有报告")
    parser.add_argument("--skip-trends", action="store_true", help="发现阶段跳过趋势抓取，使用缓存")
    parser.add_argument("--skip-community", action="store_true", help="发现阶段跳过社区扫描，使用缓存")
    parser.add_argument("--serp-data", default=None, help="可选的外部 SERP 数据文件路径（向下兼容）")
    parser.add_argument("--skip-serp", action="store_true", help="完全跳过 SERP 采集（网络受限时使用）")
    parser.add_argument("--max-serp-keywords", type=int, default=20, help="主动采集 SERP 的最大关键词数量")
    parser.add_argument("--fresh-data", action="store_true", help="忽略同日期已有 discovery 缓存，强制重新拉取真实数据")
    parser.add_argument("--output", default=None, help="内容输出目录，默认 src/content/ideas")
    parser.add_argument("--min-score", type=float, default=25, help="最低发布分数阈值")
    parser.add_argument("--allow-repeat", action="store_true", help="允许重复选中已发布过的 source keyword")
    parser.add_argument("--mode", choices=["skip", "overwrite", "fail"], default="overwrite", help="目标文件已存在时的处理方式")
    parser.add_argument("--no-build", action="store_true", help="跳过站点构建校验")
    parser.add_argument("--commit", action="store_true", help="生成成功后自动 git commit")
    parser.add_argument("--push", action="store_true", help="提交成功后自动推送到远端分支")
    parser.add_argument("--branch", default="main", help="推送目标分支，默认 main")
    parser.add_argument("--dry-run", action="store_true", help="只跑选择与校验前的预览，不写文件、不构建、不提交")
    parser.add_argument("--fail-on-soft-discovery-warning", action="store_true", help="严格模式：只要出现非致命 discovery 告警也阻止发布")
    parser.add_argument("--fail-on-quality-warning", action="store_true", help="严格模式：内容质量 warning 也视为错误")
    parser.add_argument("--summary-json", default=None, help="运行摘要 JSON 输出路径")
    parser.add_argument("--summary-md", default=None, help="运行摘要 Markdown 输出路径")
    args = parser.parse_args()

    if args.push:
        args.commit = True

    resolved_date = resolve_run_date(args.date)
    summary_json_path, summary_md_path = resolve_summary_paths(args, resolved_date)
    args.summary_json = str(summary_json_path)
    args.summary_md = str(summary_md_path)

    output_dir = Path(args.output) if args.output else PROJECT_ROOT / "src" / "content" / "ideas"
    summary = create_run_summary(args, resolved_date)

    try:
        report_payload: dict[str, Any]
        discovery_warnings: list[str] = []

        if args.skip_discovery or args.report:
            report_path = find_report_path(resolved_date, args.report)
            print(f"[Pipeline] 复用已有报告: {report_path}")
            raw_report = load_report(report_path)
            report_payload = normalize_report_payload(raw_report)
            if isinstance(raw_report, dict):
                discovery_warnings = list(raw_report.get("warnings", []) or [])
            add_step(summary, "discovery", "reused", {"report": report_path.name})
        else:
            from pipeline.discovery.run_pipeline import execute_pipeline

            pipeline_result = execute_pipeline(
                run_date=resolved_date,
                skip_trends=args.skip_trends,
                skip_community=args.skip_community,
                serp_data_path=args.serp_data,
                skip_serp=args.skip_serp,
                max_serp_keywords=args.max_serp_keywords,
                fresh_data=args.fresh_data,
            )
            report_path = Path(pipeline_result["json_path"])
            summary["paths"]["report_txt"] = pipeline_result.get("txt_path")
            report_payload = normalize_report_payload(pipeline_result["report"])
            discovery_warnings = list(pipeline_result.get("warnings", []) or [])
            add_step(
                summary,
                "discovery",
                "completed",
                {
                    "report": report_path.name,
                    "warnings": len(discovery_warnings),
                },
            )

        summary["paths"]["report_json"] = str(report_path)
        summary["report_summary"] = derive_report_summary(report_payload)

        audit_warnings, audit_errors = audit_pipeline_health(
            report_payload=report_payload,
            discovery_warnings=discovery_warnings,
            min_score=args.min_score,
            fail_on_soft_discovery_warning=args.fail_on_soft_discovery_warning,
        )
        summary["warnings"].extend(audit_warnings)
        summary["errors"].extend(audit_errors)

        if audit_warnings:
            print(f"[DiscoveryGate] ⚠️  发现 {len(audit_warnings)} 条非阻断告警：")
            for warning in audit_warnings:
                print(f"  - {warning}")
        if audit_errors:
            raise RuntimeError("；".join(audit_errors))
        print("[DiscoveryGate] ✅ discovery 质量门槛通过")

        generation_result = generate_idea(
            report_path=report_path,
            output_dir=output_dir,
            date_str=resolved_date,
            min_score=args.min_score,
            allow_repeat=args.allow_repeat,
            mode=args.mode,
            dry_run=args.dry_run,
        )

        summary["candidate"] = {
            "keyword": generation_result.get("keyword"),
            "title": generation_result.get("title"),
            "score": generation_result.get("score"),
            "grade": generation_result.get("grade"),
            "status": generation_result.get("status"),
        }
        summary["paths"]["generated_markdown"] = generation_result.get("output_path")
        add_step(
            summary,
            "generate",
            "completed" if generation_result.get("status") != "dry_run" else "dry_run",
            {
                "keyword": generation_result.get("keyword"),
                "score": generation_result.get("score"),
            },
        )

        print("\n[Generate] 选题完成")
        print(f"  关键词: {generation_result['keyword']}")
        print(f"  标题: {generation_result['title']}")
        print(f"  评分: {generation_result['score']} | 分级: {generation_result['grade']}")
        print(f"  输出: {generation_result['output_path']}")
        print(f"  状态: {generation_result['status']}")

        if args.dry_run or generation_result["status"] == "dry_run":
            summary["status"] = "dry_run"
            add_step(summary, "finish", "dry_run", {"reason": "preview_only"})
            print("\n[Done] Dry run 结束，未写入文件。")
            return

        target_file = Path(generation_result["output_path"])
        validation_errors = validate_markdown(target_file)
        if validation_errors:
            summary["errors"].extend(validation_errors)
            raise RuntimeError("生成内容未通过结构校验: " + "；".join(validation_errors))
        print(f"[Validate] ✅ 内容结构通过: {target_file}")
        add_step(summary, "validate_structure", "completed", {"file": target_file.name})

        quality_warnings, quality_errors = audit_content_quality(target_file)
        if quality_warnings:
            summary["warnings"].extend(quality_warnings)
            print(f"[Quality] ⚠️  内容质量警告（{len(quality_warnings)} 条）：")
            for warning in quality_warnings:
                print(f"  - {warning}")
        if args.fail_on_quality_warning and quality_warnings:
            quality_errors = list(quality_errors) + [
                f"严格模式启用：内容质量 warning 数量为 {len(quality_warnings)}，发布被阻止"
            ]
        if quality_errors:
            summary["errors"].extend(quality_errors)
            raise RuntimeError("生成内容质量不达标: " + "；".join(quality_errors))
        if not quality_warnings and not quality_errors:
            print("[Quality] ✅ 内容质量通过")
        add_step(
            summary,
            "validate_quality",
            "completed",
            {"warnings": len(quality_warnings), "errors": len(quality_errors)},
        )

        run_i18n_guard()
        add_step(summary, "validate_i18n", "completed", {"file": target_file.name})

        if not args.no_build:
            build_site()
            add_step(summary, "build", "completed")
        else:
            add_step(summary, "build", "skipped", {"reason": "--no-build"})

        committed = False
        if args.commit:
            committed = commit_generated_content(target_file, resolved_date)
            summary["git"]["committed"] = committed
            add_step(summary, "git_commit", "completed" if committed else "skipped")
        else:
            add_step(summary, "git_commit", "skipped", {"reason": "--commit not set"})

        if args.push and committed:
            push_changes(args.branch)
            summary["git"]["pushed"] = True
            add_step(summary, "git_push", "completed", {"branch": args.branch})
        elif args.push:
            add_step(summary, "git_push", "skipped", {"reason": "no new commit"})
        else:
            add_step(summary, "git_push", "skipped", {"reason": "--push not set"})

        summary["status"] = "success"
        add_step(summary, "finish", "completed")
        print("\n[Done] 自动发布链路执行完成")

    except Exception as error:
        summary["status"] = "failed"
        summary["errors"].append(str(error))
        add_step(summary, "finish", "failed", {"error": str(error)})
        raise

    finally:
        summary["warnings"] = unique_keep_order(summary.get("warnings", []))
        summary["errors"] = unique_keep_order(summary.get("errors", []))
        summary["finished_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        write_run_summary(summary, summary_json_path, summary_md_path)
        append_github_step_summary(build_summary_markdown(summary))
        print(f"[Summary] JSON: {summary_json_path}")
        print(f"[Summary] Markdown: {summary_md_path}")


if __name__ == "__main__":
    main()
