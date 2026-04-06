#!/usr/bin/env python3
"""
需求挖掘主流程。
统一执行趋势发现、社区扫描、SERP 解析、评分与结构化报告生成。
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pipeline.discovery.pipeline_common import (
    DATA_DIR,
    REPORTS_DIR,
    classify_keyword,
    get_timestamp,
    load_json,
    load_seed_roots,
    normalize_keyword,
    resolve_run_date,
    save_json,
    score_keyword,
)
from pipeline.discovery.step1_trend_discovery import discover_trending_keywords
from pipeline.discovery.step2_community_scan import extract_keywords_from_signals, run_community_scan
from pipeline.discovery.step3_serp_analysis import analyze_serp_data, run_serp_collection

# ─── 质量门槛配置 ──────────────────────────────────────────────────────────────
# 这些阈值控制哪些 keyword 能进入最终报告，设置得太低会导致生成"半骨架稿"
MIN_TREND_INTEREST_FOR_REPORT = 2      # 最低趋势热度（低于此值的 keyword 会降级为 skip）
MIN_COMMUNITY_SIGNALS_FOR_WATCH = 1    # 进入 watch 级别的最低社区信号数
MIN_SCORE_FOR_WORTH_IT = 30            # worth_it 级别的最低综合分数
MIN_SCORE_FOR_WATCH = 10               # watch 级别的最低综合分数


def load_trend_data(run_date: str) -> list[dict]:
    path = DATA_DIR / f"trend_data_{run_date}.json"
    if path.exists():
        return load_json(path)
    return []


def load_community_data(run_date: str) -> dict:
    path = DATA_DIR / f"community_signals_{run_date}.json"
    if path.exists():
        return load_json(path)
    return {}


def build_keyword_profiles(trend_data: list[dict], community_data: dict, serp_data: dict | None = None) -> list[dict]:
    """合并多路数据，构建每个关键词的完整画像。"""
    print("[合并] 构建关键词画像...")

    trend_map = {item["keyword"].lower(): item for item in trend_data}
    community_keywords = extract_keywords_from_signals(community_data)
    community_map = {item["keyword"].lower(): item for item in community_keywords}

    all_keywords = set(trend_map.keys()) | set(community_map.keys())
    config = load_seed_roots()
    for seed in config["seed_roots"]:
        all_keywords.add(normalize_keyword(seed))

    profiles = []
    for keyword in all_keywords:
        trend_item = trend_map.get(keyword, {})
        community_item = community_map.get(keyword, {})
        serp_item = (serp_data or {}).get(keyword, {})

        item = {
            "keyword": keyword,
            "trend_slope": trend_item.get("slope", 0),
            "trend_interest": trend_item.get("interest", 0),
            "trend_recent_avg": trend_item.get("recent_avg", 0),
            "trend_peak": trend_item.get("peak", 0),
            "trend_relative": trend_item.get("relative_to_benchmark", 0),
            "trend_data_points": trend_item.get("data_points", 0),
            "trend_time_series": trend_item.get("time_series", []),
            "community_signals": community_item.get("total_signals", 0),
            "community_strength": community_item.get("total_strength", 0),
            "community_sources_count": len(community_item.get("sources", [])),
            "community_sources": community_item.get("sources", []),
            "community_top_items": community_item.get("top_items", []),
            "serp_niche_count": serp_item.get("niche_count", 0),
            "serp_big_count": serp_item.get("big_count", 0),
            "serp_tool_big_count": serp_item.get("tool_big_count", 0),
            "serp_niche_ratio": serp_item.get("niche_ratio", 0.5),
            "serp_niche_sites": serp_item.get("niche_sites", []),
            "serp_big_sites": serp_item.get("big_sites", []),
            "serp_worth_entering": serp_item.get("is_worth_entering", False),
        }

        item["score"] = score_keyword(item)
        item["grade"] = classify_keyword(item)

        # 质量门槛过滤：低质量信号降级为 skip，避免生成空洞内容
        if item["grade"] != "skip":
            trend_ok = item.get("trend_recent_avg", 0) >= MIN_TREND_INTEREST_FOR_REPORT
            community_ok = item.get("community_signals", 0) >= MIN_COMMUNITY_SIGNALS_FOR_WATCH
            serp_ok = item.get("serp_niche_count", 0) >= 2 or item.get("serp_worth_entering", False)
            score = item["score"]

            # worth_it 门槛更严
            if item["grade"] == "worth_it":
                if score < MIN_SCORE_FOR_WORTH_IT or not (trend_ok or community_ok or serp_ok):
                    item["grade"] = "watch"

            # watch 门槛
            if item["grade"] == "watch":
                if score < MIN_SCORE_FOR_WATCH and not (trend_ok or community_ok or serp_ok):
                    item["grade"] = "skip"

        profiles.append(item)

    profiles.sort(key=lambda item: item["score"], reverse=True)
    return profiles


def format_report(run_date: str, profiles: list[dict]) -> str:
    """格式化为可读文本报告。"""
    timestamp = get_timestamp()
    worth_it = [item for item in profiles if item["grade"] == "worth_it"]
    watch = [item for item in profiles if item["grade"] == "watch"]
    skip = [item for item in profiles if item["grade"] == "skip"]

    lines = []
    lines.append("🔍 每日需求挖掘报告（统一仓库版）")
    lines.append(f"📅 {run_date} | {timestamp}")
    lines.append("")
    lines.append(f"📊 总览：{len(profiles)} 个关键词")
    lines.append(f"  ✅ 值得继续：{len(worth_it)} 个")
    lines.append(f"  ⚠️ 可观察：{len(watch)} 个")
    lines.append(f"  ❌ 跳过：{len(skip)} 个")
    lines.append("")

    if worth_it:
        lines.append("=" * 70)
        lines.append("🟢 【值得继续】— 评分 >= 45 且有上升信号或社区热度")
        lines.append("=" * 70)
        for index, item in enumerate(worth_it, 1):
            slope_icon = "📈" if item["trend_slope"] > 0 else "📉"
            lines.append("")
            lines.append(f"  {index}. {item['keyword']}  评分:{item['score']}  {slope_icon}")
            lines.append(
                f"     趋势：热度={item['trend_interest']}, 斜率={item['trend_slope']}, 峰值={item['trend_peak']}"
            )
            if item["community_signals"] > 0:
                lines.append(
                    f"     社区：{item['community_signals']} 条信号（{', '.join(item['community_sources'])}）强度={item['community_strength']}"
                )
            if item["serp_niche_count"] > 0:
                enter = "✅可切入" if item["serp_worth_entering"] else "⚠️竞争大"
                lines.append(f"     SERP：niche={item['serp_niche_count']} 大站={item['serp_big_count']} {enter}")
                if item["serp_niche_sites"]:
                    lines.append(f"     Niche站：{', '.join(item['serp_niche_sites'][:3])}")

    if watch:
        lines.append("")
        lines.append("=" * 70)
        lines.append("🟡 【可观察】— 有潜力但数据不足")
        lines.append("=" * 70)
        for index, item in enumerate(watch[:20], 1):
            slope_icon = "📈" if item["trend_slope"] > 0 else " "
            lines.append(f"  {index}. {item['keyword']}  评分:{item['score']}  {slope_icon}")
            lines.append(
                f"     趋势：热度={item['trend_interest']}, 斜率={item['trend_slope']} | 社区：{item['community_signals']} 信号"
            )

    lines.append("")
    lines.append("=" * 70)
    lines.append("💡 建议：优先挑 worth_it Top 3 做内容生产，再决定是否进入 MVP 验证。")
    lines.append("   趋势数据来源：Google Trends | 社区：HN + GitHub + Reddit | SERP：可选增强")

    return "\n".join(lines)


def serialize_report(run_date: str, profiles: list[dict], report_text: str, elapsed_seconds: float) -> dict:
    worth_it = [item for item in profiles if item["grade"] == "worth_it"]
    watch = [item for item in profiles if item["grade"] == "watch"]
    skip = [item for item in profiles if item["grade"] == "skip"]
    top_pick = worth_it[0] if worth_it else (watch[0] if watch else profiles[0] if profiles else None)

    return {
        "date": run_date,
        "generated_at": get_timestamp(),
        "elapsed_seconds": round(elapsed_seconds, 1),
        "summary": {
            "total": len(profiles),
            "worth_it": len(worth_it),
            "watch": len(watch),
            "skip": len(skip),
        },
        "top_pick": top_pick,
        "opportunities": {
            "worth_it": worth_it,
            "watch": watch,
            "skip": skip,
        },
        "profiles": profiles,
        "report_text": report_text,
    }


def execute_pipeline(
    run_date: str | None = None,
    skip_trends: bool = False,
    skip_community: bool = False,
    serp_data_path: str | None = None,
    skip_serp: bool = False,
    max_serp_keywords: int = 20,
    fresh_data: bool = False,
) -> dict:
    """执行完整 pipeline，并返回报告与输出路径。

    新增参数：
        skip_serp: 完全跳过 SERP 采集（GitHub Actions 中网络受限时使用）
        max_serp_keywords: 最多主动采集的 SERP 关键词数量（默认 20）
        fresh_data: 强制忽略同日期已有缓存，重新拉取趋势与 SERP 数据
    """
    resolved_date = resolve_run_date(run_date)
    start_time = time.time()
    warnings: list[str] = []  # 收集所有告警，最后统一输出

    print("\n" + "=" * 70)
    print(f"🚀 需求挖掘流水线 - {get_timestamp()}")
    print("=" * 70 + "\n")
    if fresh_data:
        print("[Cache] 已启用 fresh_data：本次会忽略同日期已有趋势/SERP 缓存并重新采集")

    # ─── Step 1: 趋势发现 ────────────────────────────────────────────────────────
    if skip_trends:
        print("[Step 1] ⏭️ 跳过，使用缓存数据")
        trend_data = load_trend_data(resolved_date)
        if not trend_data:
            print("  ⚠️ 无缓存数据，将执行趋势发现...")
            trend_data = discover_trending_keywords(resolved_date, force_refresh=fresh_data)
    else:
        trend_data = discover_trending_keywords(resolved_date, force_refresh=fresh_data)

    if not trend_data:
        raise RuntimeError("趋势数据为空，无法继续执行内容发现流水线。")

    # 统计 rate_limited 情况
    rate_limited_count = sum(1 for item in trend_data if item.get("_status") == "rate_limited")
    if rate_limited_count > len(trend_data) * 0.5:
        msg = f"趋势抓取超过 50% 被限流（{rate_limited_count}/{len(trend_data)} 个关键词），评分准确性降低"
        warnings.append(f"⚠️  [Step 1] {msg}")
        print(f"  ⚠️ {msg}")

    # ─── Step 2: 社区扫描 ────────────────────────────────────────────────────────
    if skip_community:
        print("\n[Step 2] ⏭️ 跳过，使用缓存数据")
        community_data = load_community_data(resolved_date)
        if not community_data:
            print("  ⚠️ 无缓存数据，将执行社区扫描...")
            community_data = run_community_scan(resolved_date)
    else:
        community_data = run_community_scan(resolved_date)

    # 统计社区信号质量
    hn_count = community_data.get("summary", {}).get("hn_count", 0)
    gh_count = community_data.get("summary", {}).get("github_count", 0)
    reddit_count = community_data.get("summary", {}).get("reddit_count", 0)
    total_community = hn_count + gh_count + reddit_count
    if total_community == 0:
        msg = "社区扫描未获得任何信号（HN + GitHub + Reddit 均为 0），社区评分维度将缺失"
        warnings.append(f"⚠️  [Step 2] {msg}")
        print(f"  ⚠️ {msg}")
    elif total_community < 5:
        msg = f"社区信号偏少（HN: {hn_count}, GitHub: {gh_count}, Reddit: {reddit_count}），建议检查网络连通性"
        warnings.append(f"⚠️  [Step 2] {msg}")

    # ─── Step 3: SERP 分析 ────────────────────────────────────────────────────────
    serp_data = None

    if skip_serp:
        print("\n[Step 3] ⏭️ 跳过 SERP 分析（--skip-serp 已设置）")
        warnings.append("⚠️  [Step 3] SERP 分析被跳过，竞争格局评分将为 0")

    elif serp_data_path:
        # 外部传入模式（向下兼容）
        serp_path = Path(serp_data_path)
        if serp_path.exists():
            print(f"\n[Step 3] 📂 加载外部 SERP 数据: {serp_path}")
            raw_serp = load_json(serp_path)
            keywords = [normalize_keyword(item.get("keyword", "")) for item in trend_data]
            serp_data = analyze_serp_data(raw_serp, keywords)
        else:
            msg = f"外部 SERP 文件不存在: {serp_path}，将改用主动采集"
            warnings.append(f"⚠️  [Step 3] {msg}")
            print(f"\n[Step 3] ⚠️ {msg}")
            serp_data_path = None  # fallthrough 到主动采集

    if not skip_serp and not serp_data_path:
        # 主动采集模式（默认）
        print("\n[Step 3] 🌐 主动采集 SERP 数据（DuckDuckGo）...")
        # 优先采集 trend_data 中分数较高的关键词
        sorted_trend_keywords = sorted(
            [normalize_keyword(item.get("keyword", "")) for item in trend_data if item.get("keyword")],
            key=lambda kw: next(
                (item.get("interest", 0) * 2 + item.get("slope", 0) * 10
                 for item in trend_data if normalize_keyword(item.get("keyword", "")) == kw),
                0,
            ),
            reverse=True,
        )
        raw_serp = run_serp_collection(
            sorted_trend_keywords,
            resolved_date,
            max_keywords=max_serp_keywords,
            force_refresh=fresh_data,
        )
        serp_data = analyze_serp_data(raw_serp, sorted_trend_keywords)

        # SERP 质量检查
        non_empty = sum(1 for v in serp_data.values() if v.get("total_results", 0) > 0)
        if non_empty == 0:
            msg = "所有 SERP 采集结果为空，竞争格局评分将缺失（可能是网络问题或被 DDG 限流）"
            warnings.append(f"⚠️  [Step 3] {msg}")
            print(f"  ⚠️ {msg}")
        elif non_empty < len(serp_data) * 0.3:
            msg = f"SERP 采集成功率偏低（{non_empty}/{len(serp_data)} 个有数据），建议检查网络"
            warnings.append(f"⚠️  [Step 3] {msg}")

    # ─── 合并评分、生成报告 ────────────────────────────────────────────────────────
    print("\n" + "─" * 70)
    profiles = build_keyword_profiles(trend_data, community_data, serp_data)
    report_text = format_report(resolved_date, profiles)
    elapsed = time.time() - start_time

    # 输出告警摘要
    if warnings:
        print("\n" + "─" * 70)
        print(f"⚠️  本次运行共有 {len(warnings)} 条质量告警：")
        for warning in warnings:
            print(f"  {warning}")

    report_payload = serialize_report(resolved_date, profiles, report_text, elapsed)
    report_payload["warnings"] = warnings  # 告警也写入报告

    json_path = REPORTS_DIR / f"opportunity_report_{resolved_date}.json"
    txt_path = REPORTS_DIR / f"opportunity_report_{resolved_date}.txt"

    save_json(report_payload, json_path)
    txt_path.write_text(report_text, encoding="utf-8")

    print("\n" + "=" * 70)
    print(f"✅ 报告生成完成！耗时 {elapsed:.1f}s")
    print(f"  JSON: {json_path}")
    print(f"  TXT:  {txt_path}")
    print("\n📈 今日结果：")
    print(f"  ✅ 值得继续: {report_payload['summary']['worth_it']} 个")
    print(f"  ⚠️ 可观察:   {report_payload['summary']['watch']} 个")
    if report_payload["top_pick"]:
        top_pick = report_payload["top_pick"]
        slope_icon = "📈" if top_pick["trend_slope"] > 0 else "📉"
        print(
            f"\n  🏆 Top pick：{slope_icon} {top_pick['keyword']} "
            f"(评分:{top_pick['score']}, 热度:{top_pick['trend_interest']}, 斜率:{top_pick['trend_slope']})"
        )

    # 最终质量评估：如果 worth_it 为 0，发出强告警
    if report_payload["summary"]["worth_it"] == 0:
        print("\n  ❌ 告警：本次没有任何 worth_it 级别的关键词！")
        print("     可能原因：① Trends 被限流  ② 社区信号稀少  ③ SERP 采集失败  ④ 评分门槛过高")
        print("     建议：运行 --skip-trends --skip-community 复用缓存后重新评分，或调低 --min-score")

    return {
        "report": report_payload,
        "json_path": str(json_path),
        "txt_path": str(txt_path),
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="需求挖掘流水线")
    parser.add_argument("--date", default=None, help="运行日期 (YYYY-MM-DD)，默认今天")
    parser.add_argument("--skip-trends", action="store_true", help="跳过趋势发现，直接使用缓存")
    parser.add_argument("--skip-community", action="store_true", help="跳过社区扫描，直接使用缓存")
    parser.add_argument("--serp-data", type=str, default=None, help="外部 SERP 数据文件路径（向下兼容）")
    parser.add_argument("--skip-serp", action="store_true", help="完全跳过 SERP 采集（网络受限时使用）")
    parser.add_argument("--max-serp-keywords", type=int, default=20, help="主动采集 SERP 的最大关键词数量（默认 20）")
    parser.add_argument("--fresh-data", action="store_true", help="忽略同日期已有缓存，强制重新拉取趋势与 SERP 数据")
    args = parser.parse_args()

    execute_pipeline(
        run_date=args.date,
        skip_trends=args.skip_trends,
        skip_community=args.skip_community,
        serp_data_path=args.serp_data,
        skip_serp=args.skip_serp,
        max_serp_keywords=args.max_serp_keywords,
        fresh_data=args.fresh_data,
    )


if __name__ == "__main__":
    main()
