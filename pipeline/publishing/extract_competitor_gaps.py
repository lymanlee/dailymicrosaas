"""
竞品弱点独立提取模块

专门用于生成 competitorGaps，与 painClusters 完全分离：
- painClusters: 社区真实讨论 + 竞品弱点 + 关键词匹配
- competitorGaps: 纯粹从竞品 Registry 的 weaknesses 提取

特点：
- 保留来源域名信息
- 不做去重（同一弱点不同竞品可重复）
- 纯粹提取，不添加任何推断
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import json


def extract_competitor_gaps(
    competitor_profiles: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    从竞品 profiles 纯粹提取弱点作为 market gaps

    与 painClusters 的区别：
    - 保留来源域名信息
    - 不做去重（同一弱点不同竞品可重复）
    - 纯粹提取，不添加任何推断

    Args:
        competitor_profiles: 竞品数据列表，每个包含:
            - domain: 竞品域名
            - weaknesses: [{en: str, zh: str}]

    Returns:
        [{
            "domain": "boomy.com",
            "text": {"en": "...", "zh": "..."}
        }]
    """
    gaps = []

    for profile in competitor_profiles:
        domain = profile.get("domain", "")
        weaknesses = profile.get("weaknesses", [])

        for weakness in weaknesses:
            # 支持多种格式
            if isinstance(weakness, dict):
                text_en = weakness.get("en", "")
                text_zh = weakness.get("zh", "")
            elif isinstance(weakness, str):
                text_en = weakness
                text_zh = weakness
            else:
                continue

            if text_en:  # 至少要有英文内容
                gaps.append({
                    "domain": domain,
                    "text": {
                        "en": text_en,
                        "zh": text_zh or text_en
                    }
                })

    return gaps


def load_competitor_profiles_from_registry(
    domains: List[str],
    registry_dir: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    从 Registry 加载竞品数据

    Args:
        domains: 竞品域名列表
        registry_dir: Registry 目录路径，默认从项目根目录加载

    Returns:
        竞品数据列表
    """
    if registry_dir is None:
        # 默认路径
        project_root = Path(__file__).parent.parent.parent
        registry_dir = project_root / "src/data/competitors"

    profiles = []

    for domain in domains:
        # 转换域名为文件名
        filename = domain.replace(".", "_") + ".json"
        filepath = Path(registry_dir) / filename

        if filepath.exists():
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    profile = json.load(f)
                    profiles.append(profile)
            except Exception as e:
                print(f"[extract_competitor_gaps] Failed to load {domain}: {e}")
        else:
            print(f"[extract_competitor_gaps] Registry file not found: {filepath}")

    return profiles


def extract_gaps_from_domains(
    domains: List[str],
    registry_dir: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    从域名列表直接提取竞品弱点

    便捷函数：加载 Registry 并提取弱点

    Args:
        domains: 竞品域名列表
        registry_dir: Registry 目录路径

    Returns:
        [{
            "domain": "boomy.com",
            "text": {"en": "...", "zh": "..."}
        }]
    """
    profiles = load_competitor_profiles_from_registry(domains, registry_dir)
    return extract_competitor_gaps(profiles)


# 测试
if __name__ == "__main__":
    # 模拟竞品数据
    test_profiles = [
        {
            "domain": "boomy.com",
            "weaknesses": [
                {"en": "Limited control over AI-generated music quality", "zh": "对AI生成的音乐质量控制有限"},
                {"en": "Revenue sharing model reduces earnings", "zh": "收入分成模式减少收益"}
            ]
        },
        {
            "domain": "soundraw.io",
            "weaknesses": [
                {"en": "Outputs can sound repetitive", "zh": "输出可能听起来重复"},
                {"en": "Limited customization options", "zh": "自定义选项有限"}
            ]
        }
    ]

    gaps = extract_competitor_gaps(test_profiles)
    print(f"Extracted {len(gaps)} competitor gaps:")
    for gap in gaps:
        print(f"  [{gap['domain']}] {gap['text']['en'][:50]}...")
