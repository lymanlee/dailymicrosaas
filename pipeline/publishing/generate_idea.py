#!/usr/bin/env python3
"""
把 discovery pipeline 的结构化报告转成站点可直接发布的 Markdown 内容。

生成原则：
- 每个章节内容随数据动态生成，而不是固定模板拼接
- 竞品对比要有真实样本和差异化分析
- 切角建议要结合关键词特性和市场空间给出具体方向
- 技术路径要有真实时间估算和关键风险
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable

# Import competitor analysis integration
from .competitor_integration import (
    get_competitor_data_cached,
    load_competitor_profiles,
    build_competitor_analysis_table,
    build_market_gaps_section,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "src" / "content" / "ideas"
DEFAULT_REPORTS_DIR = PROJECT_ROOT / "pipeline" / "reports"


def resolve_run_date(date_str: str | None = None) -> str:
    if not date_str:
        return datetime.now().strftime("%Y-%m-%d")
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")


def normalize_keyword(keyword: str) -> str:
    return " ".join(keyword.lower().split())


def slugify(text: str) -> str:
    value = normalize_keyword(text)
    value = re.sub(r"[^a-z0-9\s-]", "", value)
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-")


def quote_yaml(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def find_report_path(date_str: str, explicit_path: str | None = None) -> Path:
    if explicit_path:
        report_path = Path(explicit_path)
        if not report_path.exists():
            raise FileNotFoundError(f"找不到指定报告: {report_path}")
        return report_path

    report_path = DEFAULT_REPORTS_DIR / f"opportunity_report_{date_str}.json"
    if report_path.exists():
        return report_path

    candidates = sorted(DEFAULT_REPORTS_DIR.glob("opportunity_report_*.json"))
    if not candidates:
        raise FileNotFoundError("找不到任何 pipeline 报告，请先运行 discovery pipeline。")
    latest = candidates[-1]
    print(f"⚠️ 指定日期报告不存在，改用最新报告: {latest.name}")
    return latest


def load_report(report_path: Path):
    with open(report_path, "r", encoding="utf-8") as file:
        return json.load(file)


def normalize_report_payload(raw_report) -> dict:
    if isinstance(raw_report, list):
        profiles = raw_report
        worth_it = [item for item in profiles if item.get("grade") == "worth_it"]
        watch = [item for item in profiles if item.get("grade") == "watch"]
        skip = [item for item in profiles if item.get("grade") == "skip"]
        top_pick = worth_it[0] if worth_it else (watch[0] if watch else profiles[0] if profiles else None)
        return {
            "date": None,
            "profiles": profiles,
            "top_pick": top_pick,
            "opportunities": {"worth_it": worth_it, "watch": watch, "skip": skip},
        }

    if not isinstance(raw_report, dict):
        raise ValueError("不支持的报告格式。")

    opportunities = raw_report.get("opportunities") or {}
    profiles = raw_report.get("profiles")
    if profiles is None:
        profiles = []
        for key in ("worth_it", "watch", "skip"):
            profiles.extend(opportunities.get(key, []))
        profiles.sort(key=lambda item: item.get("score", 0), reverse=True)

    top_pick = raw_report.get("top_pick")
    if not top_pick and profiles:
        top_pick = profiles[0]

    return {
        "date": raw_report.get("date"),
        "profiles": profiles,
        "top_pick": top_pick,
        "opportunities": {
            "worth_it": opportunities.get("worth_it", [item for item in profiles if item.get("grade") == "worth_it"]),
            "watch": opportunities.get("watch", [item for item in profiles if item.get("grade") == "watch"]),
            "skip": opportunities.get("skip", [item for item in profiles if item.get("grade") == "skip"]),
        },
    }


def extract_frontmatter(markdown_text: str) -> str:
    match = re.match(r"^---\n(.*?)\n---\n", markdown_text, re.DOTALL)
    return match.group(1) if match else ""


SIMPLIFY_TOKENS = {"tool", "tools", "app", "website", "site", "online", "free", "best"}


def keyword_variants(keyword: str) -> set[str]:
    normalized = normalize_keyword(keyword)
    tokens = normalized.split()
    simplified_tokens = [token for token in tokens if token not in SIMPLIFY_TOKENS]

    variants = {normalized}
    if simplified_tokens:
        variants.add(" ".join(simplified_tokens))
    if len(tokens) > 1 and tokens[-1] in SIMPLIFY_TOKENS:
        variants.add(" ".join(tokens[:-1]))
    return {variant.strip() for variant in variants if variant.strip()}


def _token_set_similarity(a: str, b: str) -> float:
    """Jaccard 相似度（基于 token 集合）。"""
    tokens_a = set(normalize_keyword(a).split()) - SIMPLIFY_TOKENS
    tokens_b = set(normalize_keyword(b).split()) - SIMPLIFY_TOKENS
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


def _edit_distance(a: str, b: str) -> int:
    """简单编辑距离（词级别）。"""
    words_a = normalize_keyword(a).split()
    words_b = normalize_keyword(b).split()
    m, n = len(words_a), len(words_b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            temp = dp[j]
            if words_a[i - 1] == words_b[j - 1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j], dp[j - 1])
            prev = temp
    return dp[n]


def is_similar_keyword(candidate: str, existing: str, similarity_threshold: float = 0.6) -> bool:
    """综合 variant 匹配、Jaccard 相似度和词级编辑距离判断重复。"""
    # 1. 精确 variant 匹配
    candidate_variants = keyword_variants(candidate)
    existing_variants = keyword_variants(existing)
    if candidate_variants & existing_variants:
        return True

    # 2. Jaccard 相似度
    similarity = _token_set_similarity(candidate, existing)
    if similarity >= similarity_threshold:
        return True

    # 3. 子集匹配（短词包含在长词中）
    candidate_tokens = set(normalize_keyword(candidate).split()) - SIMPLIFY_TOKENS
    existing_tokens = set(normalize_keyword(existing).split()) - SIMPLIFY_TOKENS
    if candidate_tokens and existing_tokens:
        if candidate_tokens.issubset(existing_tokens) or existing_tokens.issubset(candidate_tokens):
            return True

    return False


def collect_existing_keywords(output_dir: Path) -> list[str]:
    existing = []
    if not output_dir.exists():
        return existing

    for file in output_dir.glob("*.md"):
        if file.name == "template.md":
            continue
        text = file.read_text(encoding="utf-8")
        frontmatter = extract_frontmatter(text)

        source_keyword_match = re.search(r'^sourceKeyword:\s*"?(.*?)"?$', frontmatter, re.MULTILINE)
        if source_keyword_match:
            existing.append(normalize_keyword(source_keyword_match.group(1)))

        title_match = re.search(r'^title:\s*"?(.*?)"?$', frontmatter, re.MULTILINE)
        localized_title_match = re.search(r'^title:\s*\n\s+en:\s*"?(.*?)"?$', frontmatter, re.MULTILINE)
        title_value = None
        if localized_title_match:
            title_value = localized_title_match.group(1)
        elif title_match:
            title_value = title_match.group(1)

        if title_value:
            title = title_value.split(" - ")[0].strip()
            if title:
                existing.append(normalize_keyword(title))

        stem = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", file.stem)
        if stem:
            existing.append(normalize_keyword(stem.replace("-", " ")))

    return existing


def pick_candidate(report_payload: dict, output_dir: Path, min_score: float, allow_repeat: bool) -> dict:
    opportunities = report_payload["opportunities"]
    ranked = opportunities.get("worth_it", []) + opportunities.get("watch", [])
    ranked.sort(key=lambda item: item.get("score", 0), reverse=True)

    existing_keywords = collect_existing_keywords(output_dir)
    for item in ranked:
        keyword = normalize_keyword(item.get("keyword", ""))
        if not keyword:
            continue
        if item.get("score", 0) < min_score:
            continue
        if not allow_repeat and any(is_similar_keyword(keyword, existing_keyword) for existing_keyword in existing_keywords):
            continue
        return item

    if allow_repeat and ranked:
        return ranked[0]

    raise RuntimeError("没有找到可发布的新 idea：要么分数不达标，要么候选已被发布。")


# ─── 分类与难度推断 ──────────────────────────────────────────────────────────────

CATEGORY_MAP = {
    "pdf": "文档处理",
    "document": "文档处理",
    "word": "文档处理",
    "resume": "文档处理",
    "invoice": "文档处理",
    "image": "图像处理",
    "photo": "图像处理",
    "logo": "图像处理",
    "avatar": "图像处理",
    "background": "图像处理",
    "upscal": "图像处理",
    "headshot": "图像处理",
    "video": "视频处理",
    "music": "AI 工具",
    "voice": "AI 工具",
    "ai ": "AI 工具",
    " ai": "AI 工具",
    "json": "开发者工具",
    "regex": "开发者工具",
    "base64": "开发者工具",
    "code": "开发者工具",
    "markdown": "开发者工具",
    "css": "开发者工具",
    "html": "开发者工具",
    "api": "开发者工具",
    "timer": "效率工具",
    "generator": "效率工具",
    "counter": "效率工具",
    "converter": "效率工具",
    "favicon": "效率工具",
    "sitemap": "效率工具",
    "og image": "效率工具",
    "meta tag": "效率工具",
    "qr code": "效率工具",
    "password": "效率工具",
    "pomodoro": "效率工具",
    "chinese": "语言学习",
    "pinyin": "语言学习",
    "hsk": "语言学习",
    "calligraphy": "语言学习",
    "idiom": "语言学习",
}


def derive_category(keyword: str) -> str:
    keyword_lower = keyword.lower()
    for token, category in CATEGORY_MAP.items():
        if token in keyword_lower:
            return category
    return "效率工具"


def derive_difficulty(idea: dict) -> str:
    score = idea.get("score", idea.get("total_score", 0))
    keyword = idea.get("keyword", "").lower()
    if any(token in keyword for token in ["video", "music", "voice"]):
        return "Hard"
    # 大站竞争激烈也算 Hard
    big_count = idea.get("serp_big_count", 0)
    tool_big_count = idea.get("serp_tool_big_count", 0)
    if tool_big_count >= 4:
        return "Hard"
    if score >= 52:
        return "Easy"
    if score >= 36:
        return "Medium"
    return "Hard"


# ─── 标题与描述 ─────────────────────────────────────────────────────────────────

def build_title_zh(keyword: str, category: str, idea: dict) -> str:
    """根据竞争环境和分数生成差异化中文标题，而不是固定后缀。"""
    score = idea.get("score", 0)
    niche_count = idea.get("serp_niche_count", 0)
    big_count = idea.get("serp_big_count", 0)
    enterable = idea.get("serp_worth_entering", False)
    trend_slope = idea.get("trend_slope", 0)
    keyword_title = keyword.title()

    if trend_slope > 0.5:
        if enterable and niche_count >= 4:
            return f"{keyword_title} — 趋势上升，市场还有切入空间"
        elif big_count >= 4:
            return f"{keyword_title} — 趋势上升但大站林立，怎么找差异化"
        else:
            return f"{keyword_title} — 需求在涨，值不值得现在入场"
    elif enterable and niche_count >= 3:
        return f"{keyword_title} — 已有 niche 样本，这个切角还没人做透"
    elif big_count >= 5:
        return f"{keyword_title} — 大站已经很挤，但还有一个缝隙"
    elif score >= 50:
        return f"{keyword_title} — 评分 {score} 分，需求信号够强，值得动手"
    else:
        category_suffix = {
            "AI 工具": "这个 AI 方向还能怎么切",
            "文档处理": "能不能做出差异化",
            "图像处理": "适不适合快速验证",
            "视频处理": "值不值得现在入场",
            "开发者工具": "还有没有切入口",
            "效率工具": "能不能做成小而美产品",
            "语言学习": "这个细分赛道还有机会吗",
        }
        return f"{keyword_title} — {category_suffix.get(category, '这个方向值不值得做')}"


def build_title_en(keyword: str, category: str, idea: dict) -> str:
    """Generate a concise English title from trend and competition signals."""
    score = idea.get("score", 0)
    niche_count = idea.get("serp_niche_count", 0)
    big_count = idea.get("serp_big_count", 0)
    enterable = idea.get("serp_worth_entering", False)
    trend_slope = idea.get("trend_slope", 0)
    keyword_title = keyword.title()

    if trend_slope > 0.5:
        if enterable and niche_count >= 4:
            return f"{keyword_title} — Demand is rising and the niche is still open"
        elif big_count >= 4:
            return f"{keyword_title} — Rising demand, but giants already crowd the SERP"
        return f"{keyword_title} — Search demand is climbing. Is now the time to enter?"
    if enterable and niche_count >= 3:
        return f"{keyword_title} — A proven niche with room for a sharper wedge"
    if big_count >= 5:
        return f"{keyword_title} — Crowded by big players, but not completely closed"
    if score >= 50:
        return f"{keyword_title} — Strong demand signals and a score of {score:.1f}"

    category_suffix = {
        "AI 工具": "Where an AI-first wedge still exists",
        "文档处理": "Can a more focused version still win?",
        "图像处理": "Is this small enough to validate fast?",
        "视频处理": "Is this worth entering right now?",
        "开发者工具": "Is there still a developer-focused wedge?",
        "效率工具": "Could this become a tight, useful niche tool?",
        "语言学习": "Is there still room in this sub-category?",
    }
    return f"{keyword_title} — {category_suffix.get(category, 'Is this direction worth building?')}"


def build_title(keyword: str, category: str, idea: dict) -> dict[str, str]:
    return localized_text(
        build_title_en(keyword, category, idea),
        build_title_zh(keyword, category, idea),
    )


def build_description_zh(keyword: str, category: str, idea: dict) -> str:
    score = idea.get("score", 0)
    trend_interest = idea.get("trend_interest", 0)
    community_signals = idea.get("community_signals", 0)
    niche_count = idea.get("serp_niche_count", 0)

    signals = []
    if trend_interest > 5:
        signals.append(f"搜索热度约 {trend_interest}")
    if community_signals > 0:
        signals.append(f"社区信号 {community_signals} 条")
    if niche_count > 0:
        signals.append(f"SERP 中有 {niche_count} 个 niche 样本")

    signal_str = "、".join(signals) if signals else f"综合评分 {score}/100"
    return f"对 {keyword} 这个{category}方向的一次深度拆解。{signal_str}，聚焦需求真实性、竞争空间和最快验证路径。"


def build_description_en(keyword: str, category: str, idea: dict) -> str:
    score = idea.get("score", 0)
    trend_interest = idea.get("trend_interest", 0)
    community_signals = idea.get("community_signals", 0)
    niche_count = idea.get("serp_niche_count", 0)
    category_label = {
        "AI 工具": "AI tools",
        "文档处理": "document tools",
        "图像处理": "image tools",
        "视频处理": "video tools",
        "效率工具": "productivity tools",
        "开发者工具": "developer tools",
        "语言学习": "language learning",
    }.get(category, "micro SaaS")

    signals = []
    if trend_interest > 5:
        signals.append(f"search interest around {trend_interest}")
    if community_signals > 0:
        signals.append(f"{community_signals} community signals")
    if niche_count > 0:
        signals.append(f"{niche_count} niche SERP players")

    signal_str = ", ".join(signals) if signals else f"an overall score of {score}/100"
    return (
        f"A deep dive into the {keyword} {category_label} opportunity: {signal_str} — "
        f"focused on real demand, competitive space, and the fastest validation path."
    )


def build_description(keyword: str, category: str, idea: dict) -> dict[str, str]:
    return localized_text(
        build_description_en(keyword, category, idea),
        build_description_zh(keyword, category, idea),
    )


# ─── 一句话描述（One Liner）──────────────────────────────────────────────────────

def build_one_liner(keyword: str, category: str, idea: dict) -> str:
    """结合实际竞品数量和趋势生成更具体的一句话。"""
    niche_count = idea.get("serp_niche_count", 0)
    big_count = idea.get("serp_big_count", 0)
    enterable = idea.get("serp_worth_entering", False)
    niche_sites = idea.get("serp_niche_sites", [])
    trend_slope = idea.get("trend_slope", 0)
    community_signals = idea.get("community_signals", 0)

    # 有具体竞品数据时，描述更有针对性
    if niche_sites:
        sample = niche_sites[0]
        if enterable and big_count <= 3:
            return (
                f"围绕 {keyword} 做一个更专注的在线工具。"
                f"市场上已有 {sample} 等 {niche_count} 个 niche 工具在跑，大站竞争相对可控（{big_count} 个），"
                f"有机会从速度、体验或更窄的使用场景切进去。"
            )
        elif big_count >= 4:
            return (
                f"围绕 {keyword} 找一个大工具没有做好的细分点，而不是正面竞争。"
                f"现有大站（{big_count} 个）功能庞杂，但有 {niche_count} 个小工具在存活，"
                f"说明还有用户愿意为更简单、更聚焦的解决方案付费。"
            )

    # 有趋势或社区信号时
    if trend_slope > 0.3 and community_signals >= 3:
        templates = {
            "AI 工具": f"趋势和社区信号双双上升，这是做一个专注版 {keyword} 工具的好时机——重点比现有产品更便宜或更易上手。",
            "文档处理": f"{keyword} 的搜索量和社区讨论都在增加，这类工具用户最在意的是速度和格式稳定性，从这两点切入最直接。",
            "图像处理": f"需求信号持续，做 {keyword} 工具优先把处理质量和速度做到让用户印象深刻，而不是堆功能。",
            "开发者工具": f"有开发者在持续讨论 {keyword}，这类工具最重要的是结果准确、可复制，做好这一点就能靠口碑扩散。",
            "效率工具": f"{keyword} 有持续的使用需求，重点是打开即用，零学习成本，然后通过某一个细分场景做出差异。",
            "语言学习": f"{keyword} 领域需求稳定，社区里还有明确的未被满足点——找到那个点，比做全功能产品更容易切入。",
        }
        return templates.get(category, f"围绕 {keyword} 做一个专注解决单一问题的小工具，先验证付费意愿，再决定是否扩展。")

    # 通用但比之前更实用
    templates = {
        "AI 工具": f"围绕 {keyword} 找一个现有大模型工具没有认真做的细分场景，用更低价格或更好体验打进去。",
        "文档处理": f"把 {keyword} 做成极简在线工具，核心优化格式稳定性、处理速度和批量能力——这三点是用户最常抱怨的。",
        "图像处理": f"围绕 {keyword} 做开箱即用的小工具，把结果质量和交付速度做到比通用大站更顺手，不需要注册，不需要学习。",
        "视频处理": f"把 {keyword} 聚焦到一个垂直场景，先用轻量 MVP 验证是否有人愿意为效率付费，而不是一开始就做完整编辑器。",
        "开发者工具": f"围绕 {keyword} 做一个开发者愿意收藏和重复使用的实用工具，结果准确是首要标准，其次才是界面。",
        "效率工具": f"把 {keyword} 做成一个无需学习成本、打开就能用的轻量工具，然后通过细分场景和更好的交互切出差异。",
        "语言学习": f"围绕 {keyword} 做一个针对特定学习阶段或使用场景的小工具，避免跟大型学习平台正面竞争。",
    }
    return templates.get(category, f"围绕 {keyword} 做一个专注解决单一问题的在线工具，先跑通一个核心功能，再用真实转化数据决定下一步。")


# ─── 真实需求来源 ────────────────────────────────────────────────────────────────

def build_demand_section(keyword: str, idea: dict) -> str:
    """生成真实需求来源章节，展示具体数据而不是模板话术。"""
    trend_interest = idea.get("trend_interest", 0)
    trend_slope = idea.get("trend_slope", 0)
    trend_peak = idea.get("trend_peak", 0)
    trend_relative = idea.get("trend_relative", 0)
    community_signals = idea.get("community_signals", 0)
    community_sources = idea.get("community_sources", [])
    community_items = idea.get("community_top_items", [])
    score = idea.get("score", 0)
    grade = idea.get("grade", "watch")

    lines = []

    # --- 趋势数据块 ---
    lines.append("### Google Trends")
    lines.append("")
    if trend_interest > 0:
        slope_desc = "斜率为正，搜索量处于上升通道" if trend_slope > 0.3 else (
            "斜率略负，但总量仍然稳定" if trend_slope < -0.2 else "趋势基本平稳"
        )
        lines.append(
            f"近 3 个月 `{keyword}` 的搜索热度均值约 **{trend_interest}**（相对指数，100 为历史峰值），"
            f"历史峰值达到 **{trend_peak}**，{slope_desc}（斜率 {trend_slope:+.2f}）。"
        )
        if trend_relative > 0:
            benchmark_desc = (
                "明显高于基准词" if trend_relative > 1.5 else
                "与基准词接近" if trend_relative > 0.5 else
                "低于基准词，属于细分方向"
            )
            lines.append(f"相对基准搜索量为 **{trend_relative:.2f}x**，{benchmark_desc}。")
    else:
        lines.append(f"当前 Google Trends 数据暂无 `{keyword}` 的有效抓取，可能受 API 限流影响，建议手动验证。")

    lines.append("")

    # --- 社区信号块 ---
    lines.append("### 社区信号")
    lines.append("")
    if community_signals > 0 and community_items:
        sources_str = "、".join(community_sources) if community_sources else "社区"
        lines.append(
            f"在 {sources_str} 中共捕获到 **{community_signals} 条**相关信号。"
            f"信号说明真实用户在讨论或者尝试解决这个问题："
        )
        lines.append("")
        for item in community_items[:3]:
            title = item.get("title", "").strip()
            source = item.get("source", "")
            strength = item.get("strength", 0)
            if title:
                lines.append(f"- **[{source}]** {title}（信号强度 {strength:.1f}）")
    elif community_signals > 0:
        sources_str = "、".join(community_sources) if community_sources else "社区"
        lines.append(f"在 {sources_str} 中共捕获到 **{community_signals} 条**相关信号，说明该方向有真实讨论热度。")
    else:
        lines.append("当前批次未采集到明显社区信号。建议手动搜索 Reddit / HN 确认是否有持续讨论。")

    lines.append("")

    # --- 综合判断 ---
    grade_desc = {
        "worth_it": f"综合评分 **{score}/100**，分级为 `worth_it` ——三个维度（趋势、社区、竞争可切入度）至少两个为正，建议优先考虑。",
        "watch": f"综合评分 **{score}/100**，分级为 `watch` ——有一定信号但数据不够充分，可以先做低成本验证再决定是否推进。",
        "skip": f"综合评分 **{score}/100**，分级为 `skip`，但仍出现在这里说明有某一维度有亮点，请结合具体数据判断。",
    }
    lines.append(grade_desc.get(grade, f"综合评分 **{score}/100**。"))

    return "\n".join(lines)


# ─── 竞争情况 ────────────────────────────────────────────────────────────────────

def build_competition_section(idea: dict, difficulty: str, keyword: str, category: str) -> str:
    """生成竞争分析章节，包含具体竞品和差异化切角建议。"""
    big_sites = idea.get("serp_big_sites", [])
    niche_sites = idea.get("serp_niche_sites", [])
    niche_count = idea.get("serp_niche_count", 0)
    big_count = idea.get("serp_big_count", 0)
    tool_big_count = idea.get("serp_tool_big_count", 0)
    enterable = idea.get("serp_worth_entering", False)
    community_signals = idea.get("community_signals", 0)
    community_items = idea.get("community_top_items", [])
    trend_slope = idea.get("trend_slope", 0)

    lines = []

    # --- 竞争格局总结 ---
    lines.append("### 竞争格局")
    lines.append("")

    if big_sites or niche_sites:
        if big_sites and niche_sites:
            giants_str = "、".join(big_sites[:3])
            niche_str = "、".join(niche_sites[:3])
            lines.append(
                f"SERP 前 10 大概是这样的格局：**{big_count} 个大站**（{giants_str} 等）占据头部，"
                f"同时有 **{niche_count} 个 niche 工具**（{niche_str} 等）在生存。"
            )
        elif big_sites:
            giants_str = "、".join(big_sites[:3])
            lines.append(
                f"SERP 头部以大站为主（{giants_str}，共 {big_count} 个），niche 样本偏少——"
                f"这意味着要么竞争很激烈，要么这个方向还没人认真做过垂直工具。"
            )
        elif niche_sites:
            niche_str = "、".join(niche_sites[:3])
            lines.append(
                f"SERP 里大站比较少，有 {niche_count} 个 niche 工具在跑（{niche_str} 等），"
                f"这是相对友好的竞争环境——说明有人能活下来，但还没被大平台收割。"
            )
    else:
        sample_titles = [item.get("title", "").strip() for item in community_items[:2] if item.get("title")]
        lines.append("这次竞争判断没有引用搜索结果页抽样，因此先用趋势和社区信号做一版保守估计。")
        if sample_titles:
            quoted_titles = "；".join(f"“{title}”" for title in sample_titles)
            lines.append(
                f"从已出现的 {community_signals} 条社区讨论看，市场上已经有人在做、也有人在持续评估同类方案（例如 {quoted_titles}），"
                f"说明这不是空白赛道；更稳的打法是先锁定一个更窄的工作流或用户角色。"
            )
        elif trend_slope > 0.3:
            lines.append("搜索需求处在上升通道，说明窗口期还在；但在没有搜索位样本前，先按“已有成熟方案、仍留细分空档”处理更稳妥。")
        else:
            lines.append("现有外部信号说明这个方向不是纯概念题，但要不要正面进入，还取决于你能否把场景切得足够窄。")

    lines.append("")

    # --- 竞品分析表格（如果有关联的竞品分析数据）---
    all_domains = list(set(niche_sites + big_sites))
    if all_domains:
        profiles = load_competitor_profiles(all_domains)
        if profiles:
            lines.append(build_competitor_analysis_table(profiles))
            
            # 获取 competitor gaps 用于市场空白板块
            competitor_data = get_competitor_data_cached(idea, category)
            competitor_gaps = competitor_data.get("competitor_weaknesses", [])
            lines.append(build_market_gaps_section(profiles, competitor_gaps))
        else:
            # 如果没有竞品分析数据但有 SERP 数据，显示提示
            lines.append("> 💡 已发现 {0} 个竞品，详细的定价和功能对比待下一轮补充。".format(len(all_domains)))
            lines.append("")

    lines.append("")

    # --- 可切入性判断 ---
    lines.append("### 可切入性")
    lines.append("")
    if enterable:
        lines.append(
            f"✅ **可以切入。** niche 工具数量（{niche_count}）说明有细分生存空间，"
            f"工具大站数量（{tool_big_count}）尚在可接受范围。"
        )
    else:
        if tool_big_count >= 4:
            lines.append(
                f"⚠️ **需要找更窄的切角。** 工具大站已有 {tool_big_count} 个，直接做通用版大概率拼不过。"
                f"建议聚焦特定文件格式、行业或使用场景。"
            )
        elif big_sites or niche_sites:
            lines.append(
                "⚠️ **先缩窄场景再进。** 现有样本已经能说明这个市场存在竞争，"
                "但还没有强到必须立刻做通用版；先用单功能 MVP 拿到一批真实用户更稳。"
            )
        elif community_signals >= 5:
            lines.append(
                f"⚠️ **先缩窄场景再进。** 社区里已经出现 {community_signals} 条相关信号，"
                "说明需求真实存在，但竞争边界还没摸透；更稳的做法是只盯住一个细分工作流。"
            )
        elif trend_slope > 0.3 or community_signals >= 2:
            lines.append(
                "🧪 **适合先做轻量验证。** 信号不算弱，但还不足以支持直接做通用版；"
                "先用 landing page、手工服务或单功能 MVP 验证付费意愿。"
            )
        else:
            lines.append(
                "🤔 **先把问题定义得更窄。** 当前外部信号偏弱，直接开做容易落进“有点需求但不够强”的灰区；"
                "先把目标人群和核心场景压到一个更小切口。"
            )

    lines.append("")

    # --- 差异化切角建议 ---
    lines.append("### 差异化方向")
    lines.append("")
    lines.append(_build_differentiation(keyword, category, idea))

    lines.append("")

    # --- 数据汇总表 ---
    lines.append("| 维度 | 评估 |")
    lines.append("|------|------|")
    lines.append(f"| 难度 | {difficulty} |")

    if big_sites:
        giants_cell = "、".join(big_sites[:3])
    elif community_signals >= 5:
        giants_cell = "本轮未抽样搜索结果，先按已有成熟玩家处理"
    else:
        giants_cell = "本轮未抽样搜索结果，头部格局待下一轮确认"
    lines.append(f"| SERP 头部大站 | {giants_cell} |")

    if niche_sites:
        niche_cell = f"{niche_count} 个：{'、'.join(niche_sites[:3])}"
    elif community_items:
        niche_cell = "社区已出现同类项目，优先核查 1 个细分工作流"
    else:
        niche_cell = "先验证 1 个细分场景，再决定是否扩展"
    lines.append(f"| Niche 样本 | {niche_cell} |")

    if enterable:
        enter_cell = "✅ 可切入"
    elif big_sites or niche_sites or community_signals >= 5:
        enter_cell = "⚠️ 先缩窄场景再进"
    elif trend_slope > 0.3 or community_signals >= 2:
        enter_cell = "🧪 先做轻量验证"
    else:
        enter_cell = "🤔 先收窄问题定义"
    lines.append(f"| 竞争可切入度 | {enter_cell} |")

    return "\n".join(lines)


def _build_differentiation(keyword: str, category: str, idea: dict) -> str:
    """给出具体差异化建议，而不是通用废话。"""
    niche_sites = idea.get("serp_niche_sites", [])
    big_sites = idea.get("serp_big_sites", [])
    tool_big_count = idea.get("serp_tool_big_count", 0)
    trend_slope = idea.get("trend_slope", 0)
    community_items = idea.get("community_top_items", [])

    # 看看社区里在抱怨什么
    pain_hint = ""
    for item in community_items[:3]:
        title = item.get("title", "").lower()
        if any(word in title for word in ["slow", "broken", "can't", "doesn't", "failed", "error", "problem", "issue"]):
            item_title = item.get('title', '')
            pain_hint = f"社区信号里有关于现有工具问题的讨论（\"{item_title}\"），这是具体的痛点切入口。"
            break
        elif any(word in title for word in ["show hn", "launch", "built", "made"]):
            item_title = item.get('title', '')
            pain_hint = f"有创业者在这个方向发布了产品（\"{item_title}\"），可以研究他们的切角和用户反馈。"
            break

    lines = []

    if category == "文档处理":
        lines.append("文档类工具用户最敏感的点通常是：")
        lines.append("- **格式保真度** — 转换后格式不乱是基本要求，但大多数免费工具在这里翻车")
        lines.append("- **批量处理** — 大站通常限制免费批量，这是付费门槛最自然的地方")
        lines.append("- **速度** — 特别是移动端，如果能快 2-3 倍，用户会明显感受到")
        if tool_big_count >= 3:
            lines.append(f"- **定价策略** — 现有大站（{', '.join(big_sites[:2])}）通常按文件数或月付，"
                         f"可以考虑按量付费或一次性买断吸引低频用户")
    elif category == "图像处理":
        lines.append("图像工具的差异化通常来自：")
        lines.append("- **处理质量** — 尤其是边缘细节，这是 AI 类工具最容易形成口碑的地方")
        lines.append("- **隐私** — 客户端处理（不上传图片）是一个越来越受关注的卖点")
        lines.append("- **速度与体验** — 拖入即处理，结果立即可下载，比需要注册的大站体验好得多")
        if niche_sites:
            lines.append(f"- 参考现有 niche 工具（{niche_sites[0]}）的定价和功能边界，找到他们没有做的点")
    elif category == "AI 工具":
        lines.append("AI 工具方向的差异化难在模型本身不是壁垒，重点要看：")
        lines.append("- **成本** — 如果大站贵，做一个更便宜但够用的版本往往有市场")
        lines.append("- **上手速度** — 大模型产品通常功能多、界面复杂，做一个「只干一件事」的版本反而更好卖")
        lines.append("- **垂直场景** — 针对特定行业或工作流（如「只给 SaaS landing page 用的文案工具」）往往比通用版更容易转化")
    elif category == "开发者工具":
        lines.append("开发者工具最重要的是：结果准确、快速、可信赖。差异化来自：")
        lines.append("- **准确性** — 很多现有工具在边界 case 上会出错，把这个做好就能建立口碑")
        lines.append("- **可分享性** — 永久链接、可嵌入、API 接口，让工具结果容易被引用传播")
        lines.append("- **离线/隐私** — 纯客户端处理，不发任何数据到服务器，这在开发者群体里是加分项")
    elif category == "效率工具":
        lines.append("效率工具的差异化通常靠：")
        lines.append("- **「零摩擦」体验** — 打开即用，无需注册，无需阅读说明，这一点做好了用户就会推荐")
        lines.append("- **细分场景** — 比通用工具更懂某个具体场景的用户，例如「专为 Notion 用户设计的 Pomodoro」")
        lines.append("- **嵌入/集成** — 提供 Web 组件或浏览器扩展，降低切换成本")
    elif category == "语言学习":
        lines.append("语言学习工具的差异化来自：")
        lines.append("- **场景细分** — 「准备 HSK 3」和「日常口语练习」是完全不同的需求，做细分比做全面更容易切入")
        lines.append("- **即时反馈** — 用户希望知道自己哪里错了，不只是答案是什么")
        lines.append("- **可离线** — 学语言场景常在地铁、飞机上，离线支持是真实需求")
    else:
        lines.append(f"围绕 {keyword} 找一个现有工具做得最差的点（可以从用户评论入手），从那里切入，不要试图做全功能版本。")

    if pain_hint:
        lines.append(f"\n> 💡 {pain_hint}")

    return "\n".join(lines)


# ─── 技术难度 ─────────────────────────────────────────────────────────────────────

def build_tech_section(keyword: str, category: str, difficulty: str, idea: dict) -> tuple[str, str]:
    """生成技术路径章节，时间估算更精确，风险点更具体。"""
    niche_count = idea.get("serp_niche_count", 0)
    community_items = idea.get("community_top_items", [])

    # 估算时间的参考依据
    time_factors = []
    if difficulty == "Easy":
        base_time = "1-2 周"
    elif difficulty == "Hard":
        base_time = "3-5 周"
    else:
        base_time = "2-3 周"

    presets = {
        "AI 工具": (
            "**技术栈参考**\n\n"
            "- 前端：React / Astro + 文件上传/编辑界面\n"
            "- 后端：API 层 + 异步任务队列（结果可能要几秒到几分钟）\n"
            "- 模型：优先用 OpenAI / Replicate API，不要一开始自部署\n"
            "- 存储：结果临时存 R2 / S3，不需要数据库起步\n\n"
            "**关键风险**\n\n"
            "- API 成本控制：每次调用的成本必须在定价里算好，否则免费用户会亏本\n"
            "- 结果质量稳定性：同一个输入，不同时间结果可能不同，用户对这个很敏感\n"
            "- 限流与重试：API 调用失败要有优雅降级，不能直接报 500",
            base_time,
        ),
        "文档处理": (
            "**技术栈参考**\n\n"
            "- 前端：拖拽上传 + 进度条 + 预览/下载\n"
            "- 后端：文档转换（LibreOffice headless / pdfjs / Pandoc）\n"
            "- 存储：临时文件存储，处理完立即删除（减少存储成本和隐私风险）\n"
            "- 部署：Cloudflare Workers / Railway，支持文件流处理\n\n"
            "**关键风险**\n\n"
            "- 格式边界问题：Word 文档格式千变万化，做好 fallback 很重要\n"
            "- 文件大小限制：大文件处理慢、成本高，需要明确限制和提示\n"
            "- 隐私合规：用户不希望文件被留存，要在 UI 和后端都明确处理",
            base_time,
        ),
        "图像处理": (
            "**技术栈参考**\n\n"
            "- 前端：Canvas API 或 WebAssembly（纯客户端处理性能更好）\n"
            "- 后端：Sharp / Jimp / Pillow，或者接入推理 API\n"
            "- 客户端处理优先：能在浏览器里做的，不要传到服务器，用户会更放心\n"
            "- CDN：处理结果可以直接走 CDN 边缘，加速下载\n\n"
            "**关键风险**\n\n"
            "- 结果质量：边缘处理（尤其是去背景）是技术难点，先调通再开放\n"
            "- 移动端性能：Canvas 处理大图在低端手机上容易 OOM，要做分辨率限制\n"
            "- 格式支持：HEIC / AVIF 等新格式覆盖度低，要明确说明支持范围",
            base_time,
        ),
        "视频处理": (
            "**技术栈参考**\n\n"
            "- 前端：任务提交 + 进度轮询 + 结果下载（不是同步处理）\n"
            "- 后端：FFmpeg 异步任务队列（BullMQ / Celery）\n"
            "- 存储：视频文件较大，需要专门的文件存储方案（R2 / S3）\n"
            "- 计算：视频处理 CPU/GPU 密集，注意按需扩容，避免排队过长\n\n"
            "**关键风险**\n\n"
            "- 成本：视频处理单次成本高，免费额度要控制好\n"
            "- 时间：处理时间可能从几秒到几分钟，用户体验难度高\n"
            "- 版权：某些视频处理功能可能涉及版权问题，要在 ToS 里明确",
            base_time,
        ),
        "开发者工具": (
            "**技术栈参考**\n\n"
            "- 前端：纯静态页面优先（React / Vue + Monaco Editor 或自定义输入组件）\n"
            "- 后端：能纯前端做的就不引入后端（JSON formatter、Base64 等）\n"
            "- 性能：WebWorker 处理大数据，避免 UI 阻塞\n"
            "- 分享：URL 参数编码状态，让结果可以直接分享链接\n\n"
            "**关键风险**\n\n"
            "- 准确性：开发者对工具错误零容忍，边界 case 要认真测试\n"
            "- 离线支持：PWA 或纯静态部署，让工具在断网时也能用\n"
            "- 安全：不要在客户端执行用户输入的代码，要做严格的沙箱隔离",
            base_time,
        ),
        "效率工具": (
            "**技术栈参考**\n\n"
            "- 前端：尽量简单，Next.js / Astro，核心是交互流畅\n"
            "- 后端：按需引入，大多数效率工具可以纯前端实现\n"
            "- 存储：LocalStorage 保存用户设置，减少登录摩擦\n"
            "- PWA：支持添加到主屏幕，提升复访率\n\n"
            "**关键风险**\n\n"
            "- 场景定义：「效率工具」太泛，要在 MVP 阶段就锁定一个具体场景\n"
            "- 竞争密度：这类工具很容易被竞争对手复制，差异化要靠细节体验\n"
            "- 转化路径：免费→付费的触发点要在设计阶段就想好",
            base_time,
        ),
        "语言学习": (
            "**技术栈参考**\n\n"
            "- 前端：React Native 或 PWA（学习场景多在移动端）\n"
            "- 后端：用户进度存储 + 题库管理\n"
            "- 内容：题库质量比技术更重要，先想清楚内容从哪来\n"
            "- 音频：如果涉及发音，需要 TTS API 或录音文件管理\n\n"
            "**关键风险**\n\n"
            "- 内容质量：错误的教学内容会直接损害用户信任\n"
            "- 学习动力：用户容易放弃，gamification 和通知设计很重要\n"
            "- 竞争：Duolingo 等大产品的阴影，要找到他们没有认真做的细分",
            base_time,
        ),
    }

    body, timeframe = presets.get(category, presets["效率工具"])

    # 难度修正
    if difficulty == "Hard" and "1-2" in timeframe:
        timeframe = "3-5 周"
    elif difficulty == "Easy" and "3-5" in timeframe:
        timeframe = "2-3 周"

    return body, timeframe


# ─── 变现方式 ─────────────────────────────────────────────────────────────────────

def build_monetization_section(keyword: str, category: str, idea: dict) -> str:
    """生成变现章节，给出具体数字参考，而不是模板三条。"""
    niche_sites = idea.get("serp_niche_sites", [])
    big_count = idea.get("serp_big_count", 0)
    trend_interest = idea.get("trend_interest", 0)

    lines = []

    # 通用原则
    lines.append(
        "变现节奏建议：**先让用户看到价值，再要求付费**。"
        "免费额度不是退而求其次，而是最有效的获客漏斗顶部。"
    )
    lines.append("")

    # 类别专属建议
    if category == "文档处理":
        lines.append("**推荐定价模式**：")
        lines.append("")
        lines.append("- **免费**: 每天 3-5 次文件处理（足够让用户验证效果）")
        lines.append("- **订阅**: $5-9/月，无限次数 + 批量 + 优先队列（参考 ilovepdf 的定价层级）")
        lines.append("- **按次包**: $2-3 一次性买断 10 次，适合低频但有真实需求的用户")
        lines.append("- **API**: 面向开发者和企业，按调用计费，客单价最高")
    elif category == "图像处理":
        lines.append("**推荐定价模式**：")
        lines.append("")
        lines.append("- **免费**: 每月 20-50 张（按分辨率限制，而不是次数限制，体验更好）")
        lines.append("- **订阅**: $6-12/月，高清输出 + 批量 + 无水印")
        lines.append("- **一次性**: $15-25 终身买断，对 lifetime deal 平台（AppSumo）效果好")
        lines.append("- **嵌入 API**: 按图片处理量收费，适合有自己产品的开发者")
    elif category == "AI 工具":
        lines.append("**推荐定价模式**（API 成本会影响定价空间）：")
        lines.append("")
        lines.append("- **免费**: 每月 X 次免费调用，让用户体验到结果质量")
        lines.append("- **订阅**: $8-15/月，提高额度 + 优先队列 + 更高质量模型")
        lines.append("- **点数包**: 一次性购买调用包，适合不想订阅的用户")
        lines.append("- **注意**: 定价要把 API 成本算进去，确保每个付费用户都是正毛利")
    elif category == "开发者工具":
        lines.append("**推荐定价模式**：")
        lines.append("")
        lines.append("- **免费 + 开源**: 个人永久免费，靠口碑和 GitHub 传播")
        lines.append("- **团队版**: $10-20/用户/月，历史记录、团队共享、SSO")
        lines.append("- **API**: 面向需要集成到自己工具链的开发者，按调用量收费")
        lines.append("- **一次性授权**: $49-99 终身授权，在开发者群体里转化率高")
    else:
        lines.append("**推荐定价模式**：")
        lines.append("")
        lines.append("- **免费**: 核心功能免费，先建立用户基础")
        lines.append("- **订阅**: $5-9/月，针对高频用户卖更高额度或高级功能")
        lines.append("- **买断**: 一次性付费选项，适合不想订阅的用户群体")

    lines.append("")

    # 定价参考
    if niche_sites:
        lines.append(f"> 💡 建议参考现有 niche 工具（{niche_sites[0]} 等）的定价页，了解这个市场的用户付费预期，再调整自己的价格带。")
    elif big_count >= 3:
        lines.append("> 💡 市场有大站，说明有人在付费。仔细看大站的定价页，找到他们定价最高但体验最差的那个功能——这里往往有机会以更低价格切入。")

    return "\n".join(lines)


# ─── 参考案例 ─────────────────────────────────────────────────────────────────────

def build_references_section(idea: dict) -> str:
    """生成参考案例章节，包含社区信号和 SERP 样本，并给出具体研究方向。"""
    community_items = idea.get("community_top_items", [])
    niche_sites = idea.get("serp_niche_sites", [])
    big_sites = idea.get("serp_big_sites", [])

    lines = []
    has_content = False

    if community_items:
        lines.append("**社区讨论（来自真实用户）**")
        lines.append("")
        for item in community_items[:3]:
            title = item.get("title", "").strip()
            source = item.get("source", "")
            strength = item.get("strength", 0)
            url = item.get("url", "")
            if title:
                if url:
                    lines.append(f"- [{title}]({url}) — **{source}**（信号强度 {strength:.1f}）")
                else:
                    lines.append(f"- {title} — **{source}**（信号强度 {strength:.1f}）")
        has_content = True
        lines.append("")

    if niche_sites:
        lines.append("**SERP 中的 Niche 工具**（直接竞品，建议逐一研究）")
        lines.append("")
        for site in niche_sites[:5]:
            lines.append(f"- `{site}` — 研究重点：定价、核心功能差异、用户评论")
        has_content = True
        lines.append("")

    if big_sites:
        lines.append("**头部大站**（参考，不要正面竞争）")
        lines.append("")
        for site in big_sites[:3]:
            lines.append(f"- `{site}` — 研究重点：他们定价最高但体验最差的功能")
        has_content = True
        lines.append("")

    if not has_content:
        lines.append("当前批次暂无外部样本数据。建议手动搜索以下内容补充：")
        lines.append("")
        lines.append("- 在 Google 搜索关键词，记录 SERP 前 10 的工具名和功能特点")
        lines.append("- 在 Reddit / HN 搜索相关讨论，找用户抱怨现有工具的帖子")
        lines.append("- 在 Product Hunt 搜索相关产品的 upvote 数和评论质量")

    lines.append("> ⚠️ 以上参考案例来自自动采集，建议在动手之前人工验证一遍，避免竞争判断偏差。")

    return "\n".join(lines)


# ─── 最快实现路径 ─────────────────────────────────────────────────────────────────

def build_execution_section(keyword: str, category: str, difficulty: str, idea: dict) -> str:
    """生成执行路径章节，更具体的里程碑和验证标准。"""
    niche_count = idea.get("serp_niche_count", 0)
    community_signals = idea.get("community_signals", 0)
    trend_interest = idea.get("trend_interest", 0)

    lines = []

    if difficulty == "Hard":
        lines.append("**节奏建议**：这个方向技术难度较高，建议把 MVP 范围压到最小，先验证付费意愿再加功能。")
        lines.append("")
        lines.append("1. **Week 1 — 最小闭环**")
        lines.append(f"   压缩核心场景：`{keyword}` 最高频的那一个输入→输出流程先跑通，不需要完整功能。")
        lines.append("   验证标准：能给 5 个真实用户用，他们理解这是什么、能完成核心动作。")
        lines.append("")
        lines.append("2. **Week 2 — 稳定与质量**")
        lines.append("   把核心处理流程稳定到可以演示的水平，加错误处理和失败反馈。")
        lines.append("   验证标准：连续跑 20 次，失败率 < 10%，结果质量用户可接受。")
        lines.append("")
        lines.append("3. **Week 3 — 付费门槛**")
        lines.append("   接入支付（Stripe / Paddle），设置免费额度，开放小范围测试。")
        lines.append("   验证标准：有至少 1 个人愿意付钱，不管金额多少。")
        lines.append("")
        lines.append("4. **Week 4 — 上线与分发**")
        lines.append("   发布 landing page，提交到 Product Hunt / HN / 相关社区，收集第一波真实反馈。")
        lines.append("   验证标准：100 个真实访客，付费转化率 > 2%（否则需要重新审视定价或产品点）。")
    elif category == "开发者工具":
        lines.append("**节奏建议**：开发者工具迭代快，先把核心准确性做好，再考虑付费和扩展。")
        lines.append("")
        lines.append("1. **Week 1 — 核心功能**")
        lines.append(f"   把 `{keyword}` 最核心的处理逻辑跑通，输出结果准确，边界 case 有处理。")
        lines.append("   验证标准：自己用 10 个真实 case 测试，结果全部正确。")
        lines.append("")
        lines.append("2. **Week 2 — 体验打磨**")
        lines.append("   优化输入输出 UI，加永久链接（结果可分享），补 SEO 页面。")
        lines.append("   验证标准：GitHub / Twitter 上发帖，有其他开发者转发或收藏。")
        lines.append("")
        lines.append("3. **Week 3 — 传播与反馈**")
        lines.append("   提交到开发者导航站（toolfolio、uneed 等），开发者论坛发帖。")
        lines.append("   验证标准：有 DAU > 50，用户自发分享链接。")
    else:
        lines.append("**节奏建议**：先跑通核心功能，再优化体验和付费转化。")
        lines.append("")
        lines.append("1. **Week 1 — 最小可用版本**")
        lines.append(f"   只做 `{keyword}` 最核心的一个功能，用现成组件或第三方服务拼出来。")
        lines.append("   验证标准：5 个目标用户能独立完成核心任务，不需要你解释。")
        lines.append("")
        lines.append("2. **Week 2 — 付费机制**")
        lines.append("   接入支付，设置免费额度，完善结果页和下载体验。")
        lines.append(f"   SEO 建议：发布 `{keyword} online free` 等长尾词的 landing page。")
        lines.append("   验证标准：有至少 1 个付费用户，不管金额多少。")
        lines.append("")
        lines.append("3. **Week 3 — 上线分发**")
        lines.append("   提交到 Product Hunt、相关 Reddit 社区、工具导航站。")
        if community_signals >= 3:
            lines.append("   （这个方向社区信号不错，在 HN/Reddit 的相关帖子下面互动是低成本的获客方式）")
        lines.append("   验证标准：DAU > 100，7 日留存 > 20%。")

    return "\n".join(lines)


# ─── SEO 关键词 ──────────────────────────────────────────────────────────────────

def build_seo_section(keyword: str, idea: dict) -> str:
    """生成 SEO 关键词章节，包含长尾词策略说明。"""
    niche_sites = idea.get("serp_niche_sites", [])
    trend_interest = idea.get("trend_interest", 0)

    lines = []

    lines.append("**核心关键词**（主页 H1 和 title）")
    lines.append("")
    lines.append(f"- `{keyword}`")
    lines.append(f"- `{keyword} online`")
    lines.append(f"- `{keyword} free`")

    lines.append("")
    lines.append("**长尾关键词**（落地页和博客文章）")
    lines.append("")
    lines.append(f"- `best {keyword} tool`")
    lines.append(f"- `how to {keyword}`")
    lines.append(f"- `{keyword} without software`")
    lines.append(f"- `{keyword} in browser`")

    if trend_interest < 5:
        lines.append("")
        lines.append("> ⚠️ 核心词搜索量偏低，建议优先做长尾词，或者研究搜索量更大的相邻词作为流量入口。")
    elif trend_interest > 30:
        lines.append("")
        lines.append(f"> 💡 核心词搜索量较高（热度 {trend_interest}），SEO 值得认真投入，建议在上线后优先做技术 SEO（页面速度、schema markup）。")

    return "\n".join(lines)


# ─── 为什么值得做 ─────────────────────────────────────────────────────────────────

def build_why_worth_section(keyword: str, idea: dict, category: str) -> str:
    """生成「为什么值得做」章节，给出真正有说服力的理由，而不是堆数字。"""
    score = idea.get("score", 0)
    community_signals = idea.get("community_signals", 0)
    niche_count = idea.get("serp_niche_count", 0)
    trend_slope = idea.get("trend_slope", 0)
    trend_interest = idea.get("trend_interest", 0)
    enterable = idea.get("serp_worth_entering", False)
    grade = idea.get("grade", "watch")
    niche_sites = idea.get("serp_niche_sites", [])

    lines = []

    # 按评分和证据给出主论点
    if grade == "worth_it":
        if trend_slope > 0.3 and community_signals >= 3 and enterable:
            lines.append(
                f"这个方向同时具备三个关键信号：**搜索量上升**（斜率 {trend_slope:+.2f}）、"
                f"**社区活跃**（{community_signals} 条讨论）、**竞争可切入**（{niche_count} 个 niche 样本）。"
                f"三者同时出现的方向不多，值得认真对待。"
            )
        elif enterable and niche_count >= 3:
            lines.append(
                f"有 {niche_count} 个 niche 工具在 SERP 上存活，说明**用户确实在为这类工具付钱**。"
                f"这比光看搜索量更有说服力——真实的竞品是最好的需求验证。"
            )
        elif trend_interest > 15:
            lines.append(
                f"这个关键词有足够大的搜索量基础（热度 {trend_interest}），"
                f"即使只抢到很小的市场份额，也能支撑一个 Micro SaaS 跑起来。"
            )
        else:
            lines.append(
                f"综合来看，这个方向在 {score}/100 的评分上支撑了较充分的数据——"
                f"趋势、社区和竞争三个维度都有正向信号。"
            )
    else:
        lines.append(
            f"这个方向评分 {score}/100（`watch` 级别），不是强推荐，但有一个值得关注的点："
        )
        if community_signals >= 2:
            lines.append(f"社区里有真实讨论（{community_signals} 条），说明有人在找解决方案。")
        elif niche_count >= 2:
            lines.append(f"SERP 中有 {niche_count} 个小工具在存活，市场有真实需求。")
        elif trend_interest > 5:
            lines.append(f"搜索量尚可（热度 {trend_interest}），属于有一定基础量的小赛道。")

    lines.append("")

    # 补充一些具体的机会点
    lines.append("**核心机会**")
    lines.append("")

    opportunity_lines = []
    if niche_sites:
        opportunity_lines.append(
            f"现有 niche 工具（{niche_sites[0]} 等）已经验证了用户付费意愿，"
            f"但这些工具通常在体验和性能上有明显短板，有机会靠更好的产品质量切走流量。"
        )
    if community_signals >= 3:
        opportunity_lines.append(
            f"社区里的 {community_signals} 条讨论告诉你有人在找解决方案——"
            f"这是免费的用户研究，建议在动手之前把这些讨论都读一遍，找到用户描述的真实痛点。"
        )
    if trend_slope > 0.2:
        opportunity_lines.append(
            f"搜索量处于上升通道（斜率 {trend_slope:+.2f}），现在入场比 6 个月后竞争少、SEO 窗口期更长。"
        )

    if opportunity_lines:
        for point in opportunity_lines[:2]:
            lines.append(f"- {point}")
    else:
        lines.append(f"- 这个方向适合小成本验证——先做一个最小版本，在真实用户那里测试付费意愿，再决定是否继续。")

    lines.append("")
    lines.append(
        f"> 最终是否值得做，还是要看你自己的资源和执行力。"
        f"数据只是说「这个方向不算差」，真正的决定因素是你能不能在 2-3 周内做出一个能让用户看到价值的版本。"
    )

    return "\n".join(lines)


# ─── 决策摘要字段 ────────────────────────────────────────────────────────────────

def localized_text(en: str, zh: str) -> dict[str, str]:
    return {"en": en, "zh": zh}


def yaml_localized_text(value: dict[str, str], indent: int = 2) -> str:
    prefix = " " * indent
    return f'{prefix}en: "{quote_yaml(value.get("en", ""))}"\n{prefix}zh: "{quote_yaml(value.get("zh", ""))}"'


def yaml_localized_list_block(field_name: str, items: list[dict[str, str]]) -> str:
    if not items:
        return f"{field_name}: []"

    lines = [f"{field_name}:"]
    for item in items:
        lines.append(f'  - en: "{quote_yaml(item.get("en", ""))}"')
        lines.append(f'    zh: "{quote_yaml(item.get("zh", ""))}"')
    return "\n".join(lines)


def yaml_trend_series_block(field_name: str, items: list[dict]) -> str:
    if not items:
        return f"{field_name}: []"

    lines = [f"{field_name}:"]
    for item in items:
        lines.append(f'  - date: "{quote_yaml(str(item.get("date", "")))}"')
        lines.append(f'    value: {int(item.get("value", 0) or 0)}')
    return "\n".join(lines)


def derive_verdict(idea: dict) -> str:
    """将 grade 映射为更清晰的决策结论。"""
    grade = idea.get("grade", "watch")
    if grade == "worth_it":
        return "Worth Building"
    elif grade == "watch":
        return "Watch"
    else:
        return "Skip"


def derive_confidence(idea: dict) -> str:
    """
    根据数据点数量、来源数量、SERP 覆盖率综合判断置信度。
    High: 趋势/社区/SERP 三维都有数据
    Medium: 有两维数据
    Low: 只有一维或无数据
    """
    score = 0
    if idea.get("trend_data_points", 0) >= 30:
        score += 1
    if idea.get("community_signals", 0) >= 2:
        score += 1
    if idea.get("serp_niche_count", 0) + idea.get("serp_big_count", 0) > 0:
        score += 1
    if score >= 3:
        return "High"
    elif score == 2:
        return "Medium"
    else:
        return "Low"


def derive_best_wedge(keyword: str, category: str, idea: dict) -> dict[str, str]:
    """
    提炼一句话「最佳切角」，优先基于竞争格局和社区信号判断。
    返回中英双语对象。
    """
    niche_count = idea.get("serp_niche_count", 0)
    tool_big_count = idea.get("serp_tool_big_count", 0)
    enterable = idea.get("serp_worth_entering", False)
    trend_slope = idea.get("trend_slope", 0)
    community_items = idea.get("community_top_items", [])

    pain_wedges: list[dict[str, str]] = []
    for item in community_items[:5]:
        title = item.get("title", "").lower()
        if any(w in title for w in ["slow", "broken", "error", "failed", "can't", "doesn't work", "issue", "problem"]):
            pain_wedges.append(localized_text("Fix reliability / error handling", "先打可靠性和报错处理"))
        elif any(w in title for w in ["free", "cheaper", "cost", "pricing", "alternative"]):
            pain_wedges.append(localized_text("Undercut pricing with a free-first tier", "用更友好的免费层压价格"))
        elif any(w in title for w in ["batch", "bulk", "multiple", "many"]):
            pain_wedges.append(localized_text("Unlock batch processing blocked by incumbents", "补上被老玩家卡住的批量处理能力"))
        elif any(w in title for w in ["mobile", "ios", "android", "phone"]):
            pain_wedges.append(localized_text("Mobile-first experience", "优先做移动端体验"))

    if pain_wedges:
        return pain_wedges[0]

    if enterable and niche_count >= 3 and tool_big_count <= 2:
        return localized_text(
            "Undercut niche incumbents on speed + UX (no account required)",
            "从速度和体验切入，压过细分老玩家（免登录）",
        )
    elif tool_big_count >= 4:
        return localized_text(
            "Narrow to one vertical/format the giants ignore",
            "聚焦一个巨头没认真做的垂直场景或格式",
        )
    elif trend_slope > 0.3:
        return localized_text(
            "Ride the rising search trend — enter now before competition catches up",
            "趁搜索趋势上升尽快入场，在竞争变挤之前先卡位",
        )
    elif category == "文档处理":
        return localized_text("Format fidelity + batch processing free tier", "主打格式还原 + 批量处理免费层")
    elif category == "图像处理":
        return localized_text("Client-side processing (privacy) + instant download", "主打本地处理（隐私）+ 即时下载")
    elif category == "AI 工具":
        return localized_text(
            "Cheaper & focused — do one thing, charge less than the generalists",
            "更便宜、更聚焦：只做好一件事，价格打过通用型产品",
        )
    elif category == "开发者工具":
        return localized_text("Accuracy + shareable permalinks + offline support", "主打准确性 + 可分享永久链接 + 离线支持")
    else:
        return localized_text("Zero-friction entry: no signup, instant result, one core job", "零摩擦切入：免注册、立刻出结果、只解决一个核心任务")


def derive_pain_clusters(idea: dict) -> list[dict[str, str]]:
    """
    从社区信号和竞品分析中归纳痛点聚类。
    
    数据优先级：
    1. 竞品分析的真实弱点（来自 LLM 深度分析）
    2. 社区信号标题关键词匹配
    3. 基于关键词/分类的默认痛点
    
    返回最多 4 条中英双语痛点。
    """
    category = derive_category(idea.get("keyword", ""))
    
    # 优先从竞品分析获取真实痛点
    competitor_data = get_competitor_data_cached(idea, category)
    
    if competitor_data.get("has_data"):
        # 使用竞品分析的真实弱点作为痛点
        pain_hints = competitor_data.get("pain_hints", [])
        if pain_hints:
            return pain_hints[:4]
        
        # 如果有竞品弱点但格式不适合作痛点，也使用
        competitor_weaknesses = competitor_data.get("competitor_weaknesses", [])
        if competitor_weaknesses:
            return competitor_weaknesses[:4]
    
    # 回退到社区信号提取
    community_items = idea.get("community_top_items", [])
    clusters: list[dict[str, str]] = []
    seen_clusters: set[str] = set()

    cluster_rules = [
        (["slow", "speed", "fast", "performance", "loading"], localized_text("Speed & performance issues", "速度和性能问题反复出现")),
        (["broken", "error", "failed", "bug", "doesn't work", "not working", "crash"], localized_text("Reliability / error-prone tools", "工具稳定性差，容易报错")),
        (["free", "cheaper", "cost", "pricing", "expensive", "paid", "alternative"], localized_text("Pricing frustration — users want free or cheaper options", "定价让人不爽，用户想要免费或更便宜的方案")),
        (["batch", "bulk", "multiple", "many", "all files"], localized_text("Batch processing not available in free tier", "免费层不支持批量处理")),
        (["mobile", "ios", "android", "phone", "app"], localized_text("Mobile experience lacking", "移动端体验明显缺位")),
        (["privacy", "data", "gdpr", "upload", "server"], localized_text("Privacy concerns — users don't want to upload files", "用户在意隐私，不想把文件上传到服务器")),
        (["format", "quality", "fidelity", "layout", "broken format"], localized_text("Output quality / format fidelity problems", "输出质量和格式还原问题明显")),
        (["show hn", "launch", "built", "made", "release", "new tool"], localized_text("Creators shipping in this space (proof of demand)", "这个方向持续有人发布产品，说明需求真实存在")),
    ]

    for item in community_items[:10]:
        title_lower = item.get("title", "").lower()
        for keywords, cluster_label in cluster_rules:
            cluster_key = cluster_label["en"]
            if cluster_key not in seen_clusters and any(kw in title_lower for kw in keywords):
                clusters.append(cluster_label)
                seen_clusters.add(cluster_key)
                break

        if len(clusters) >= 4:
            break

    # 如果没有从社区信号提取到痛点，使用基于关键词/分类的默认痛点
    if not clusters:
        keyword = idea.get("keyword", "").lower()
        
        # 根据关键词类型返回默认痛点
        clusters.append(localized_text("Manual & time-consuming workflow", "操作繁琐，效率低"))
        
        if any(k in keyword for k in ["pdf", "word", "converter"]):
            clusters.append(localized_text("Output quality / format fidelity problems", "输出质量和格式还原问题明显"))
            clusters.append(localized_text("Batch processing not available in free tier", "免费层不支持批量处理"))
        elif any(k in keyword for k in ["ai", "image", "video", "music"]):
            clusters.append(localized_text("Speed & performance issues", "速度和性能问题反复出现"))
            clusters.append(localized_text("Output quality inconsistency", "AI 生成结果质量不稳定"))
        else:
            clusters.append(localized_text("Pricing frustration — users want free or cheaper options", "定价让人不爽，用户想要免费或更便宜的方案"))

    return clusters


def derive_competitor_gaps(idea: dict, category: str) -> list[dict[str, str]]:
    """
    从竞品分析和 SERP 数据推断竞品弱点。
    
    数据优先级：
    1. 竞品分析的 LLM 深度分析弱点（来自真实抓取的竞品页面）
    2. SERP 数据推断
    3. 基于分类的默认弱点
    
    返回最多 3 条中英双语竞品弱点。
    """
    # 优先从竞品分析获取真实弱点
    competitor_data = get_competitor_data_cached(idea, category)
    
    if competitor_data.get("has_data"):
        competitor_weaknesses = competitor_data.get("competitor_weaknesses", [])
        if competitor_weaknesses:
            return competitor_weaknesses[:3]
    
    # 回退到 SERP 数据推断
    big_sites = idea.get("serp_big_sites", [])
    tool_big_count = idea.get("serp_tool_big_count", 0)
    niche_sites = idea.get("serp_niche_sites", [])

    gaps: list[dict[str, str]] = []

    if tool_big_count >= 3:
        sites_en = ", ".join(big_sites[:2])
        sites_zh = "、".join(big_sites[:2])
        gaps.append(localized_text(
            f"Incumbents ({sites_en}) hide key features behind paid plans",
            f"头部产品（{sites_zh}）把关键功能放在付费墙后",
        ))
    if tool_big_count >= 2:
        gaps.append(localized_text(
            "Big tools require account creation — most users abandon before converting",
            "大站要求先注册账号，很多用户在转化前就流失了",
        ))
    if category == "文档处理":
        gaps.append(localized_text(
            "Free tier limited to 1-2 files/day; power users are underserved",
            "免费层通常限制为每天 1-2 个文件，重度用户没人认真服务",
        ))
    elif category == "图像处理":
        gaps.append(localized_text(
            "Output watermarked or resolution-capped on free tier",
            "免费层要么加水印，要么限制分辨率",
        ))
    elif category == "AI 工具":
        gaps.append(localized_text(
            "Generalist AI tools are overpriced for single-use-case needs",
            "通用型 AI 工具对单一需求来说定价过高",
        ))
    elif category == "开发者工具":
        gaps.append(localized_text(
            "Results not shareable / no permalink support in most tools",
            "多数工具结果不可分享，也没有永久链接支持",
        ))

    if niche_sites:
        gaps.append(localized_text(
            f"Existing niche tools ({niche_sites[0]}) have outdated UI and no mobile support",
            f"现有细分工具（{niche_sites[0]}）界面老旧，也没做好移动端支持",
        ))

    # 如果没有从 SERP 数据提取到竞品弱点，使用基于分类的默认弱点
    if not gaps:
        if category == "文档处理":
            gaps.append(localized_text(
                "Free tier limited to 1-2 files/day; power users are underserved",
                "免费层通常限制为每天 1-2 个文件，重度用户没人认真服务",
            ))
            gaps.append(localized_text(
                "Big tools require account creation — most users abandon before converting",
                "大站要求先注册账号，很多用户在转化前就流失了",
            ))
        elif category == "图像处理":
            gaps.append(localized_text(
                "Output watermarked or resolution-capped on free tier",
                "免费层要么加水印，要么限制分辨率",
            ))
        elif category == "AI 工具":
            gaps.append(localized_text(
                "Generalist AI tools are overpriced for single-use-case needs",
                "通用型 AI 工具对单一需求来说定价过高",
            ))
        elif category == "开发者工具":
            gaps.append(localized_text(
                "Results not shareable / no permalink support in most tools",
                "多数工具结果不可分享，也没有永久链接支持",
            ))
        else:
            gaps.append(localized_text(
                "Big tools require account creation — most users abandon before converting",
                "大站要求先注册账号，很多用户在转化前就流失了",
            ))

    return gaps[:3]


def derive_data_window(idea: dict) -> dict[str, str]:
    """数据窗口：趋势默认 3 个月，返回中英双语对象。"""
    data_points = idea.get("trend_data_points", 0)
    if data_points >= 90:
        return localized_text("Last 90 days", "近 90 天")
    elif data_points >= 30:
        return localized_text("Last 30 days", "近 30 天")
    elif data_points > 0:
        return localized_text(f"Last {data_points} days", f"近 {data_points} 天")
    else:
        return localized_text("N/A", "暂无")


def derive_build_window(keyword: str, category: str, idea: dict) -> dict[str, str]:
    """开发周期：根据分类和关键词难度估算，返回中英双语对象。"""
    difficulty = derive_difficulty(idea)
    difficulty_map = {
        "Easy": localized_text("3-5 days", "3-5 天"),
        "Medium": localized_text("1-2 weeks", "1-2 周"),
        "Hard": localized_text("3-5 weeks", "3-5 周"),
    }
    return difficulty_map.get(difficulty, localized_text("1-2 weeks", "1-2 周"))


# ─── 主构建函数 ──────────────────────────────────────────────────────────────────

def build_markdown(idea: dict, date_str: str) -> tuple[str, str, str]:
    keyword = normalize_keyword(idea["keyword"])
    category = derive_category(keyword)
    difficulty = derive_difficulty(idea)
    title = build_title(keyword, category, idea)
    description = build_description(keyword, category, idea)
    title_yaml = yaml_localized_text(title, indent=2)
    description_yaml = yaml_localized_text(description, indent=2)
    slug = f"{date_str}-{slugify(keyword)}"
    tech_body, timeframe = build_tech_section(keyword, category, difficulty, idea)

    one_liner = build_one_liner(keyword, category, idea)
    demand_section = build_demand_section(keyword, idea)
    competition_section = build_competition_section(idea, difficulty, keyword, category)
    monetization_section = build_monetization_section(keyword, category, idea)
    references_section = build_references_section(idea)
    execution_section = build_execution_section(keyword, category, difficulty, idea)
    seo_section = build_seo_section(keyword, idea)
    why_worth_section = build_why_worth_section(keyword, idea, category)

    # 决策摘要字段
    verdict = derive_verdict(idea)
    confidence = derive_confidence(idea)
    best_wedge = derive_best_wedge(keyword, category, idea)
    pain_clusters = derive_pain_clusters(idea)
    competitor_gaps = derive_competitor_gaps(idea, category)
    data_window = derive_data_window(idea)
    build_window = derive_build_window(keyword, category, idea)

    best_wedge_yaml = yaml_localized_text(best_wedge)
    data_window_yaml = yaml_localized_text(data_window)
    build_window_yaml = yaml_localized_text(build_window)
    trend_series_yaml = yaml_trend_series_block("trendSeries", idea.get("trend_time_series", []))
    pain_clusters_yaml = yaml_localized_list_block("painClusters", pain_clusters)
    competitor_gaps_yaml = yaml_localized_list_block("competitorGaps", competitor_gaps)

    evidence_links = []
    for item in idea.get("community_top_items", [])[:3]:
        url = item.get("url", "")
        title_text = item.get("title", "")
        source = item.get("source", "")
        if url and title_text:
            evidence_links.append({"url": url, "title": title_text, "source": source})

    if evidence_links:
        evidence_links_yaml = "evidenceLinks:\n" + "\n".join(
            f'  - url: "{quote_yaml(e["url"])}"\n    title: "{quote_yaml(e["title"])}"\n    source: "{quote_yaml(e["source"])}"'
            for e in evidence_links
        )
    else:
        evidence_links_yaml = "evidenceLinks: []"

    markdown = f"""---
title:
{title_yaml}
date: "{date_str}"
category: "{quote_yaml(category)}"
difficulty: "{difficulty}"
description:
{description_yaml}
status: "New"
sourceKeyword: "{quote_yaml(keyword)}"
sourceScore: {idea.get('score', 0)}
sourceGrade: "{idea.get('grade', 'watch')}"
verdict: "{verdict}"
confidence: "{confidence}"
bestWedge:
{best_wedge_yaml}
dataDate: "{date_str}"
dataWindow:
{data_window_yaml}
buildWindow:
{build_window_yaml}
{trend_series_yaml}
{pain_clusters_yaml}
{competitor_gaps_yaml}
{evidence_links_yaml}
---

## 一句话描述

{one_liner}

## 真实需求来源

{demand_section}

## 竞争情况

{competition_section}

## 技术难度

{tech_body}

**预估开发时间**: {timeframe}

## 变现方式

{monetization_section}

## 参考案例

{references_section}

## 最快实现路径

{execution_section}

## SEO 关键词

{seo_section}

## 为什么值得做

{why_worth_section}
"""
    return slug, title.get("zh", title.get("en", keyword.title())), markdown


def write_idea_file(markdown: str, output_path: Path, mode: str, dry_run: bool) -> str:
    if output_path.exists():
        if mode == "skip":
            return "skipped"
        if mode == "fail":
            raise FileExistsError(f"目标文件已存在: {output_path}")
        if mode != "overwrite":
            raise ValueError(f"不支持的模式: {mode}")

    if dry_run:
        return "dry_run"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    return "written"


def generate_idea(
    report_path: Path,
    output_dir: Path,
    date_str: str,
    min_score: float,
    allow_repeat: bool,
    mode: str,
    dry_run: bool,
) -> dict:
    raw_report = load_report(report_path)
    report_payload = normalize_report_payload(raw_report)
    candidate = pick_candidate(report_payload, output_dir, min_score=min_score, allow_repeat=allow_repeat)
    slug, title, markdown = build_markdown(candidate, date_str)
    output_path = output_dir / f"{slug}.md"
    status = write_idea_file(markdown, output_path, mode=mode, dry_run=dry_run)

    return {
        "status": status,
        "output_path": str(output_path),
        "slug": slug,
        "title": title,
        "keyword": candidate.get("keyword"),
        "score": candidate.get("score", 0),
        "grade": candidate.get("grade", "watch"),
        "report_path": str(report_path),
        "date": date_str,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="从 pipeline 报告生成 Daily Micro SaaS 内容")
    parser.add_argument("--date", default=None, help="发布日期 (YYYY-MM-DD)，默认今天")
    parser.add_argument("--report", default=None, help="显式指定报告路径")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_DIR), help="输出目录，默认 src/content/ideas")
    parser.add_argument("--min-score", type=float, default=25, help="最低分数阈值，默认 25")
    parser.add_argument("--allow-repeat", action="store_true", help="允许重复选中已发布过的 source keyword")
    parser.add_argument("--mode", choices=["skip", "overwrite", "fail"], default="skip", help="目标文件已存在时的处理方式")
    parser.add_argument("--dry-run", action="store_true", help="只预览选中的题目与输出路径，不写文件")
    args = parser.parse_args()

    resolved_date = resolve_run_date(args.date)
    report_path = find_report_path(resolved_date, args.report)
    result = generate_idea(
        report_path=report_path,
        output_dir=Path(args.output),
        date_str=resolved_date,
        min_score=args.min_score,
        allow_repeat=args.allow_repeat,
        mode=args.mode,
        dry_run=args.dry_run,
    )

    print("\n✅ 内容生成完成")
    print(f"  状态: {result['status']}")
    print(f"  题目: {result['title']}")
    print(f"  关键词: {result['keyword']} | 评分: {result['score']} | 分级: {result['grade']}")
    print(f"  报告: {result['report_path']}")
    print(f"  输出: {result['output_path']}")


if __name__ == "__main__":
    main()
