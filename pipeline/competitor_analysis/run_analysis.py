#!/usr/bin/env python3
"""
Run competitor analysis for an idea.

Usage:
    python run_analysis.py --title "AI Music Generator" --category "ai-tools"
    python run_analysis.py --title "AI Music Generator" --category "ai-tools" --force-refresh
    python run_analysis.py --domains "suno.ai,udio.com" --title "AI Music Generator"
"""
import argparse
import json
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from competitor_analysis import (
    CompetitorFetcher,
    SiliconFlowAnalyzer,
    CompetitorCache,
    CompetitorRecommender,
    CompetitorAnalysisResult,
)


def main():
    parser = argparse.ArgumentParser(description="Analyze competitors for an idea")
    parser.add_argument("--title", required=True, help="Idea title")
    parser.add_argument("--category", default="saas", help="Idea category")
    parser.add_argument("--description", default="", help="Idea description")
    parser.add_argument("--domains", help="Comma-separated list of competitor domains (optional)")
    parser.add_argument("--force-refresh", action="store_true", help="Ignore cache and re-fetch")
    parser.add_argument("--output", help="Output JSON file path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
    
    # Initialize components
    fetcher = CompetitorFetcher()
    analyzer = SiliconFlowAnalyzer()
    cache = CompetitorCache()
    recommender = CompetitorRecommender()
    
    # Get competitor domains
    if args.domains:
        domains = [d.strip() for d in args.domains.split(",")]
        print(f"Using provided domains: {domains}")
    else:
        print(f"Recommending competitors for: {args.title}")
        domains = recommender.recommend(args.title, args.category, args.description)
        print(f"Recommended domains: {domains}")
    
    if not domains:
        print("No competitors to analyze. Exiting.")
        sys.exit(1)
    
    # Analyze each competitor
    profiles = []
    for domain in domains:
        print(f"\nAnalyzing {domain}...")
        
        # Check cache
        cached = cache.get(domain, force_refresh=args.force_refresh)
        if cached and not args.force_refresh:
            print(f"  Using cached data (analyzed at {cached.analyzed_at})")
            profiles.append(cached)
            continue
        
        # Fetch website
        print(f"  Fetching website...")
        pages = fetcher.fetch_all(domain)
        
        if not pages["landing"]:
            print(f"  Failed to fetch landing page, skipping")
            continue
        
        # Analyze with LLM
        print(f"  Analyzing with LLM...")
        profile = analyzer.analyze_competitor(
            domain=domain,
            landing_html=pages["landing"],
            pricing_html=pages.get("pricing", "")
        )
        
        if profile:
            # Cache result
            cache.set(profile)
            profiles.append(profile)
            print(f"  ✓ Analyzed: {profile.name}")
            print(f"    - Features: {len(profile.key_features)}")
            print(f"    - Pricing tiers: {len(profile.pricing_tiers)}")
            print(f"    - Weaknesses: {len(profile.weaknesses)}")
        else:
            print(f"  ✗ Analysis failed")
    
    if not profiles:
        print("\nNo competitors successfully analyzed. Exiting.")
        sys.exit(1)
    
    # Identify market gaps
    print("\nIdentifying market gaps...")
    market_gaps = analyzer.identify_market_gaps(profiles)
    print(f"  Found {len(market_gaps)} market gaps")
    
    # Build result
    result = CompetitorAnalysisResult(
        top_competitors=profiles,
        market_gaps=market_gaps
    )
    
    # Output
    result_dict = result.to_dict()
    
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result_dict, f, ensure_ascii=False, indent=2)
        print(f"\n✓ Results saved to {args.output}")
    else:
        print("\n" + "="*60)
        print("ANALYSIS RESULT")
        print("="*60)
        print(json.dumps(result_dict, ensure_ascii=False, indent=2))
    
    return result_dict


if __name__ == "__main__":
    main()
