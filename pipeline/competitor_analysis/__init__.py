"""
Competitor analysis module for dailymicrosaas.

Provides tools for:
- Fetching competitor websites with anti-detection measures
- Analyzing competitors using LLM (SiliconFlow API)
- Caching analysis results
- Generating bilingual competitor profiles
"""

from .models import (
    LocalizedPair,
    LocalizedPricingTier,
    CompetitorProfile,
    PainEvidence,
    PainPoint,
    PainAnalysis,
    DifferentiationStrategy,
    CompetitorAnalysisResult,
)
from .fetcher import CompetitorFetcher
from .analyzer import SiliconFlowAnalyzer
from .cache import CompetitorCache
from .recommender import CompetitorRecommender

__all__ = [
    "LocalizedPair",
    "LocalizedPricingTier",
    "CompetitorProfile",
    "PainEvidence",
    "PainPoint",
    "PainAnalysis",
    "DifferentiationStrategy",
    "CompetitorAnalysisResult",
    "CompetitorFetcher",
    "SiliconFlowAnalyzer",
    "CompetitorCache",
    "CompetitorRecommender",
]
