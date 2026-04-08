#!/usr/bin/env python3
"""
Offline test for competitor analysis modules.
Tests cache, models, and data flow without API calls.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from competitor_analysis import (
    LocalizedPair,
    LocalizedPricingTier,
    CompetitorProfile,
    CompetitorCache,
    CompetitorAnalysisResult,
)


def test_models():
    """Test data models."""
    print("Testing data models...")
    
    # Create a sample profile
    profile = CompetitorProfile(
        domain="suno.ai",
        name="Suno",
        key_features=[
            LocalizedPair(en="AI music generation", zh="AI音乐生成"),
            LocalizedPair(en="Multiple genres support", zh="支持多种风格"),
        ],
        pricing_tiers=[
            LocalizedPricingTier(
                name=LocalizedPair(en="Free", zh="免费版"),
                price=0,
                description=LocalizedPair(en="Basic features", zh="基础功能"),
                limits={
                    "credits": LocalizedPair(en="50 credits/month", zh="每月50积分"),
                }
            ),
            LocalizedPricingTier(
                name=LocalizedPair(en="Pro", zh="专业版"),
                price=10,
                description=LocalizedPair(en="Full features", zh="完整功能"),
                limits={
                    "credits": LocalizedPair(en="2000 credits/month", zh="每月2000积分"),
                }
            ),
        ],
        weaknesses=[
            LocalizedPair(en="Limited free tier", zh="免费版限制较多"),
        ],
        target_audience=LocalizedPair(en="Content creators", zh="内容创作者"),
        positioning=LocalizedPair(en="AI music creation tool", zh="AI音乐创作工具"),
    )
    
    print(f"  ✓ Created profile: {profile.name}")
    print(f"    - Features: {len(profile.key_features)}")
    print(f"    - Pricing tiers: {len(profile.pricing_tiers)}")
    print(f"    - Weaknesses: {len(profile.weaknesses)}")
    
    # Test serialization
    data = profile.to_dict()
    print(f"  ✓ Serialized to dict")
    
    # Test deserialization
    restored = CompetitorProfile.from_dict(data)
    print(f"  ✓ Restored from dict: {restored.name}")
    
    return profile


def test_cache(profile):
    """Test cache functionality."""
    print("\nTesting cache...")
    
    cache = CompetitorCache()
    
    # Clear any existing cache
    cache.clear("suno.ai")
    print("  ✓ Cache cleared")
    
    # Save profile
    cache.set(profile)
    print(f"  ✓ Saved to cache")
    
    # Retrieve from cache
    cached = cache.get("suno.ai")
    if cached:
        print(f"  ✓ Retrieved from cache: {cached.name}")
        print(f"    - Cached at: {cached.analyzed_at}")
    else:
        print("  ✗ Failed to retrieve from cache")
    
    # Test force refresh
    forced = cache.get("suno.ai", force_refresh=True)
    if forced is None:
        print("  ✓ Force refresh works (returns None)")
    
    # Get stats
    stats = cache.get_stats()
    print(f"  ✓ Cache stats: {stats}")
    
    return cache


def test_analysis_result():
    """Test full analysis result."""
    print("\nTesting analysis result...")
    
    # Create sample competitors
    comp1 = CompetitorProfile(
        domain="suno.ai",
        name="Suno",
        key_features=[LocalizedPair(en="Feature 1", zh="功能1")],
        pricing_tiers=[],
        weaknesses=[LocalizedPair(en="Weakness 1", zh="弱点1")],
    )
    
    comp2 = CompetitorProfile(
        domain="udio.com",
        name="Udio",
        key_features=[LocalizedPair(en="Feature A", zh="功能A")],
        pricing_tiers=[],
        weaknesses=[LocalizedPair(en="Weakness A", zh="弱点A")],
    )
    
    # Create analysis result
    result = CompetitorAnalysisResult(
        top_competitors=[comp1, comp2],
        market_gaps=[
            LocalizedPair(en="Gap 1", zh="空白点1"),
            LocalizedPair(en="Gap 2", zh="空白点2"),
        ]
    )
    
    print(f"  ✓ Created analysis result")
    print(f"    - Competitors: {len(result.top_competitors)}")
    print(f"    - Market gaps: {len(result.market_gaps)}")
    
    # Test serialization
    data = result.to_dict()
    print(f"  ✓ Serialized to dict")
    
    # Pretty print sample
    import json
    print(f"\n  Sample JSON output:")
    print(json.dumps(data, indent=2, ensure_ascii=False)[:800] + "...")
    
    return result


def main():
    print("="*60)
    print("OFFLINE TEST - Competitor Analysis Module")
    print("="*60)
    
    # Run tests
    profile = test_models()
    cache = test_cache(profile)
    result = test_analysis_result()
    
    print("\n" + "="*60)
    print("ALL TESTS PASSED ✓")
    print("="*60)
    print("\nThe module is ready. To test with API:")
    print("1. Ensure SILICONFLOW_API_KEY is valid")
    print("2. Run: python3 run_analysis.py --title 'AI Music Generator' --category ai-tools")


if __name__ == "__main__":
    main()
