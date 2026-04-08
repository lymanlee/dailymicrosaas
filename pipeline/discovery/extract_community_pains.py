"""
社区痛点提取模块

从社区讨论中提取真实用户痛点：
1. Hacker News 帖子及评论
2. Reddit 相关 subreddit 讨论

使用 LLM 分析并提取：
- 用户抱怨的具体问题
- 原话引用作为证据
- 来源 URL
"""
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
import json
import os
from pathlib import Path

# LLM 调用（复用共享模块）
try:
    from pipeline.utils.llm import call_llm
except ImportError:
    # 兼容：直接从父级导入
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from pipeline.utils.llm import call_llm


@dataclass
class CommunityPain:
    """社区提取的痛点"""
    text_zh: str
    text_en: str
    severity: str  # high | medium | low
    source_url: str
    source_name: str  # hackernews | reddit
    quote_zh: str
    quote_en: str


# Prompt 模板
COMMUNITY_PAIN_PROMPT = """Analyze the following community discussions about "{keyword}" and extract user pain points and frustrations.

Extract ONLY genuine complaints and frustrations expressed by users. DO NOT extract:
- Feature requests or suggestions
- Neutral observations
- Praise or positive comments
- Questions about the product

For each pain point found, provide:
1. The specific pain point in English
2. The specific pain point in Chinese (简明翻译)
3. The severity (high/medium/low based on how critical the issue is)
4. A direct quote from the discussion as evidence
5. The source URL

Return as JSON array:
{{
  "painPoints": [
    {{
      "pain_en": "Specific pain point in English",
      "pain_zh": "中文痛点描述",
      "severity": "high|medium|low",
      "quote_en": "Direct quote from discussion in English",
      "quote_zh": "引用中文翻译",
      "source_url": "https://...",
      "source_name": "hackernews|reddit"
    }}
  ]
}}

Community Discussions:
{discussions}

If no genuine complaints are found, return: {{"painPoints": []}}
"""


def extract_pain_from_community(
    community_items: List[Dict[str, Any]],
    keyword: str,
    max_items: int = 10
) -> List[Dict[str, Any]]:
    """
    从社区讨论中提取痛点

    Args:
        community_items: 社区帖子列表 [{title, url, source, content/text, score?}]
        keyword: 关键词
        max_items: 最大处理数量

    Returns:
        [{
            "text": {"en": "...", "zh": "..."},
            "source": "community",
            "severity": "high|medium|low",
            "evidence": [{
                "url": "https://...",
                "source": "hackernews|reddit",
                "quote": {"en": "...", "zh": "..."}
            }]
        }]
    """
    if not community_items:
        return []

    # 限制处理数量
    items_to_process = community_items[:max_items]

    # 格式化讨论内容
    discussions_text = "\n\n".join([
        f"Source: {item.get('source', 'unknown')}\n"
        f"Title: {item.get('title', '')}\n"
        f"URL: {item.get('url', '')}\n"
        f"Content: {item.get('content', item.get('text', ''))[:500]}"
        for item in items_to_process
    ])

    prompt = COMMUNITY_PAIN_PROMPT.format(
        keyword=keyword,
        discussions=discussions_text
    )

    # 调用 LLM
    try:
        result = call_llm(prompt, model="deepseek-ai/DeepSeek-V3.2")
    except Exception as e:
        print(f"[extract_community_pains] LLM call failed: {e}")
        return []

    if not result:
        return []

    # 解析结果
    pains = []
    pain_points = result.get("painPoints", [])

    for item in pain_points:
        # 找到对应的原始帖子
        matching_item = None
        quote_en = item.get("quote_en", "")
        for ci in items_to_process:
            content = ci.get("content", ci.get("text", ""))
            if quote_en and quote_en[:50] in content:
                matching_item = ci
                break
        matching_item = matching_item or items_to_process[0] if items_to_process else {}

        pains.append({
            "text": {
                "en": item.get("pain_en", ""),
                "zh": item.get("pain_zh", "")
            },
            "source": "community",
            "severity": item.get("severity", "medium"),
            "evidence": [{
                "url": item.get("source_url", matching_item.get("url", "")),
                "source": item.get("source_name", matching_item.get("source", "community")),
                "quote": {
                    "en": item.get("quote_en", ""),
                    "zh": item.get("quote_zh", "")
                }
            }]
        })

    return pains


def extract_community_pains(
    idea_keyword: str,
    community_items: List[Dict[str, Any]],
    max_items: int = 10
) -> List[Dict[str, Any]]:
    """
    从社区讨论中提取痛点（供 generate_idea.py 调用）。

    Args:
        idea_keyword: 核心关键词
        community_items: 社区帖子列表
        max_items: 最大处理数量

    Returns:
        [{
            "text_en": "...",
            "text_zh": "...",
            "severity": "high|medium|low",
            "source_url": "https://...",
            "source_name": "hackernews|reddit",
            "quote_en": "...",
            "quote_zh": "..."
        }]
    """
    raw = extract_pain_from_community(community_items, idea_keyword, max_items)
    # 转换格式以匹配 generate_idea.py 的预期
    result = []
    for item in raw:
        result.append({
            "text_en": item.get("text", {}).get("en", ""),
            "text_zh": item.get("text", {}).get("zh", ""),
            "severity": item.get("severity", "medium"),
            "source_url": item.get("evidence", [{}])[0].get("url", "") if item.get("evidence") else "",
            "source_name": item.get("evidence", [{}])[0].get("source", "community") if item.get("evidence") else "community",
            "quote_en": item.get("evidence", [{}])[0].get("quote", {}).get("en", "") if (item.get("evidence") and len(item.get("evidence", [])) > 0) else "",
            "quote_zh": item.get("evidence", [{}])[0].get("quote", {}).get("zh", "") if (item.get("evidence") and len(item.get("evidence", [])) > 0) else "",
        })
    return result


def derive_pain_clusters_enhanced(
    idea_keyword: str,
    community_items: List[Dict[str, Any]],
    competitor_data: Optional[Dict[str, Any]] = None,
    keyword_fallback: Optional[List[Dict[str, Any]]] = None,
    max_pains: int = 4
) -> List[Dict[str, Any]]:
    """
    增强版痛点聚类生成

    数据来源优先级：
    1. 社区真实讨论提取（带引用）
    2. 竞品弱点推断
    3. 关键词匹配回退

    Args:
        idea_keyword: 核心关键词
        community_items: 社区帖子列表
        competitor_data: 竞品数据 {"weaknesses": [...], "has_data": bool}
        keyword_fallback: 关键词回退数据
        max_pains: 最大痛点数量

    Returns:
        [{
            "text": {"en": "...", "zh": "..."},
            "source": "community|competitor|keyword",
            "sourceDomain": "xxx.com",  # 仅 competitor
            "evidence": [...]  # 仅 community
        }]
    """
    pains = []
    seen_en = set()

    # 1. 社区真实讨论提取
    community_pains = extract_pain_from_community(community_items, idea_keyword)
    for pain in community_pains:
        key = pain["text"]["en"].lower()[:30]
        if key and key not in seen_en and len(pain["text"]["en"]) > 10:
            pains.append(pain)
            seen_en.add(key)

    # 2. 竞品弱点推断
    if competitor_data and competitor_data.get("has_data"):
        pain_hints = competitor_data.get("pain_hints", [])
        for hint in pain_hints[:3]:
            key = hint.get("en", "").lower()[:30]
            if key and key not in seen_en and len(hint.get("en", "")) > 10:
                pains.append({
                    "text": {"en": hint.get("en", ""), "zh": hint.get("zh", "")},
                    "source": "competitor",
                    "sourceDomain": hint.get("domain", "")
                })
                seen_en.add(key)

    # 3. 关键词匹配回退
    if keyword_fallback and len(pains) < max_pains:
        for pain in keyword_fallback:
            if len(pains) >= max_pains:
                break
            key = pain["text"]["en"].lower()[:30]
            if key and key not in seen_en:
                pains.append({**pain, "source": "keyword"})
                seen_en.add(key)

    return pains[:max_pains]


# 测试
if __name__ == "__main__":
    # 模拟数据测试
    test_community = [
        {
            "title": "Is Soundraw worth it for video creators?",
            "url": "https://reddit.com/r/videography/comments/xxx",
            "source": "reddit",
            "content": "I've been using Soundraw for a month. The music all sounds the same after a while. Very disappointed with the lack of variety."
        },
        {
            "title": "Boomy's AI is getting worse",
            "url": "https://news.ycombinator.com/item?id=xxx",
            "source": "hackernews",
            "content": "Boomy used to generate decent tracks but recently everything sounds generic and repetitive. Their quality has really dropped."
        }
    ]

    result = extract_pain_from_community(test_community, "ai music generator")
    print(f"Extracted {len(result)} pain points:")
    for p in result:
        print(f"  - [{p['severity']}] {p['text']['en'][:50]}...")
        if p.get('evidence'):
            print(f"    Source: {p['evidence'][0]['source']}")
