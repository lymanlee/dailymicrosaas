"""
Competitor Analysis Integration Layer

Bridge between competitor_analysis module and generate_idea.py.
Provides functions to load cached competitor analysis and inject into idea generation.
"""
import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from competitor_analysis.models import (
    CompetitorProfile,
    CompetitorAnalysisResult,
)
from competitor_analysis.cache import CompetitorCache


# Cache directory for competitor profiles
COMPETITOR_CACHE_DIR = Path(__file__).parent.parent / "competitor_analysis" / "cache" / "competitor_profiles"


def load_competitor_profiles(domains: List[str], cache_dir: Path = None) -> List[CompetitorProfile]:
    """
    Load cached competitor profiles for given domains.
    
    Args:
        domains: List of competitor domains
        cache_dir: Optional custom cache directory
        
    Returns:
        List of CompetitorProfile objects (only valid cached ones)
    """
    cache_dir = cache_dir or COMPETITOR_CACHE_DIR
    cache = CompetitorCache(cache_dir=str(cache_dir), ttl_days=30)  # Longer TTL for analysis
    
    profiles = []
    for domain in domains:
        profile = cache.get(domain)
        if profile:
            profiles.append(profile)
    
    return profiles


def extract_competitor_weaknesses(profiles: List[CompetitorProfile]) -> List[Dict[str, str]]:
    """
    Extract weaknesses from competitor profiles for use in competitorGaps.
    
    Args:
        profiles: List of CompetitorProfile objects
        
    Returns:
        List of bilingual weakness dictionaries
    """
    weaknesses = []
    seen = set()
    
    for profile in profiles:
        for weakness in profile.weaknesses:
            # Deduplicate by English text
            key = weakness.en.lower().strip()
            if key and key not in seen:
                weaknesses.append({
                    "en": weakness.en,
                    "zh": weakness.zh,
                })
                seen.add(key)
    
    return weaknesses


def extract_pain_hints_from_competitors(profiles: List[CompetitorProfile]) -> List[Dict[str, str]]:
    """
    Extract pain point hints from competitor profiles.
    
    Since competitor weaknesses often reflect user pain points,
    we can use them as pain clusters too.
    
    Args:
        profiles: List of CompetitorProfile objects
        
    Returns:
        List of bilingual pain point dictionaries
    """
    pains = []
    seen = set()
    
    for profile in profiles:
        # Get competitor name (handle both LocalizedPair and string)
        competitor_name = profile.name.en if hasattr(profile.name, 'en') else str(profile.name)
        
        # Use weaknesses as pain indicators
        for weakness in profile.weaknesses:
            key = weakness.en.lower().strip()
            if key and key not in seen and len(key) > 10:  # Filter out very short ones
                pains.append({
                    "en": f"【{competitor_name}】" + weakness.en,
                    "zh": f"【{competitor_name}】" + weakness.zh,
                })
                seen.add(key)
    
    return pains


def get_competitor_analysis_data(idea: dict, category: str) -> Dict[str, Any]:
    """
    Get competitor analysis data for an idea.
    
    Priority:
    1. Load cached profiles for domains found in SERP data
    2. If no cached data, return empty result
    
    Args:
        idea: Idea dict from discovery pipeline
        category: Idea category
        
    Returns:
        Dict with competitor_weaknesses and pain_hints
    """
    # Get domains from SERP data
    niche_sites = idea.get("serp_niche_sites", [])
    big_sites = idea.get("serp_big_sites", [])
    
    # Combine and deduplicate domains
    all_domains = list(set(niche_sites + big_sites))
    
    if not all_domains:
        return {
            "competitor_weaknesses": [],
            "pain_hints": [],
            "has_data": False,
        }
    
    # Load cached profiles
    profiles = load_competitor_profiles(all_domains)
    
    if not profiles:
        return {
            "competitor_weaknesses": [],
            "pain_hints": [],
            "has_data": False,
        }
    
    return {
        "competitor_weaknesses": extract_competitor_weaknesses(profiles),
        "pain_hints": extract_pain_hints_from_competitors(profiles),
        "has_data": True,
        "analyzed_competitors": [p.domain for p in profiles],
    }


def format_competitor_summary(profiles: List[CompetitorProfile]) -> str:
    """
    Format competitor profiles into a readable summary for article sections.
    
    Args:
        profiles: List of CompetitorProfile objects
        
    Returns:
        Markdown formatted competitor summary
    """
    if not profiles:
        return ""
    
    lines = []
    
    for profile in profiles:
        lines.append(f"### {profile.name} ({profile.domain})")
        lines.append("")
        
        if profile.key_features:
            lines.append("**核心功能**:")
            for feature in profile.key_features[:3]:
                lines.append(f"- {feature.zh} / {feature.en}")
            lines.append("")
        
        if profile.pricing_tiers:
            lines.append("**定价**:")
            for tier in profile.pricing_tiers[:3]:
                if tier.price == 0:
                    price_str = "免费"
                else:
                    price_str = f"${tier.price}/月"
                lines.append(f"- {tier.name.zh}: {price_str}")
            lines.append("")
        
        if profile.weaknesses:
            lines.append("**弱点**:")
            for weakness in profile.weaknesses[:2]:
                lines.append(f"- {weakness.zh}")
            lines.append("")
    
    return "\n".join(lines)


# ─── Lazy-loaded analysis result ─────────────────────────────────────────────

_competitor_cache: Dict[str, Any] = {}


def get_competitor_data_cached(idea: dict, category: str, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Get competitor data with caching to avoid repeated loads.
    
    Args:
        idea: Idea dict from discovery pipeline
        category: Idea category
        force_refresh: Force reload from cache
        
    Returns:
        Competitor analysis data dict
    """
    global _competitor_cache
    
    # Create cache key from SERP domains
    domains = list(set(idea.get("serp_niche_sites", []) + idea.get("serp_big_sites", [])))
    cache_key = ",".join(sorted(domains)) if domains else "no_domains"
    
    if force_refresh or cache_key not in _competitor_cache:
        _competitor_cache[cache_key] = get_competitor_analysis_data(idea, category)
    
    return _competitor_cache[cache_key]


def clear_competitor_cache():
    """Clear the in-memory competitor cache."""
    global _competitor_cache
    _competitor_cache = {}


def build_competitor_analysis_table(profiles: List[CompetitorProfile]) -> str:
    """
    Build a markdown table of competitor analysis.
    
    Args:
        profiles: List of CompetitorProfile objects
        
    Returns:
        Markdown formatted table with competitor details
    """
    if not profiles:
        return ""
    
    lines = []
    lines.append("### 竞品分析")
    lines.append("")
    
    # Build table header
    lines.append("| 竞品 | 定价 | 核心功能 | 弱点 |")
    lines.append("|------|------|----------|------|")
    
    for profile in profiles:
        competitor_name = profile.name.en if hasattr(profile.name, 'en') else str(profile.name)
        
        # Format pricing
        if profile.pricing_tiers:
            pricing_parts = []
            for tier in profile.pricing_tiers[:2]:
                tier_name = tier.name.zh if hasattr(tier.name, 'zh') else str(tier.name)
                if tier.price == 0:
                    pricing_parts.append(f"{tier_name}: 免费")
                else:
                    pricing_parts.append(f"{tier_name}: ${tier.price}")
            pricing = "<br>".join(pricing_parts)
        else:
            pricing = "未知"
        
        # Format key features
        if profile.key_features:
            features = [f.zh if hasattr(f, 'zh') else str(f) for f in profile.key_features[:2]]
            features_str = "<br>".join(features)
        else:
            features_str = "-"
        
        # Format weaknesses
        if profile.weaknesses:
            weaknesses = [w.zh if hasattr(w, 'zh') else str(w) for w in profile.weaknesses[:2]]
            weaknesses_str = "<br>".join(weaknesses)
        else:
            weaknesses_str = "-"
        
        # Escape pipe characters in content
        pricing = pricing.replace("|", "\\|")
        features_str = features_str.replace("|", "\\|")
        weaknesses_str = weaknesses_str.replace("|", "\\|")
        
        lines.append(f"| [{competitor_name}](https://{profile.domain}) | {pricing} | {features_str} | {weaknesses_str} |")
    
    lines.append("")
    
    return "\n".join(lines)


def build_market_gaps_section(profiles: List[CompetitorProfile], gaps: List[Dict[str, str]]) -> str:
    """
    Build the market gaps section with competitor weaknesses.
    
    Args:
        profiles: List of CompetitorProfile objects
        gaps: List of competitor gap dictionaries
        
    Returns:
        Markdown formatted market gaps section
    """
    if not profiles and not gaps:
        return ""
    
    lines = []
    lines.append("### 市场空白")
    lines.append("")
    
    if gaps:
        lines.append("从竞品弱点可以直接推导当前市场的未满足需求：")
        lines.append("")
        for i, gap in enumerate(gaps[:3], 1):
            gap_zh = gap.get("zh", "")
            lines.append(f"{i}. {gap_zh}")
        lines.append("")
    
    return "\n".join(lines)
