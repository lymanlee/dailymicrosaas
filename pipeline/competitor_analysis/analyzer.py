"""
LLM-based competitor analysis using SiliconFlow API.
Extracts structured data with bilingual support.
"""
import json
import os
from typing import List, Optional, Dict, Any

import requests

from .models import (
    CompetitorProfile, 
    LocalizedPair, 
    LocalizedPricingTier,
    PainPoint,
    PainEvidence,
    PainAnalysis,
    DifferentiationStrategy,
    CompetitorAnalysisResult
)


# Prompts for LLM analysis
COMPETITOR_ANALYSIS_PROMPT = """Analyze the following competitor website content and extract key information in bilingual format (English and Chinese).

Website Domain: {domain}
Landing Page Content:
{landing_content}

Pricing Page Content:
{pricing_content}

Extract the following information and return as JSON:

{{
  "name": "Company/Product name",
  "keyFeatures": [
    {{"en": "Feature description in English", "zh": "中文功能描述"}}
  ],
  "pricingTiers": [
    {{
      "name": {{"en": "Tier name (e.g., Free, Pro, Enterprise)", "zh": "套餐名称"}},
      "price": 0,
      "description": {{"en": "What's included", "zh": "包含内容"}},
      "limits": {{
        "monthlyCredits": {{"en": "e.g., 50 credits/month", "zh": "例如：每月50积分"}},
        "maxFileSize": {{"en": "e.g., Up to 10MB", "zh": "例如：最大10MB"}},
        "commercialUse": {{"en": "Allowed or Not allowed", "zh": "允许或不允许"}}
      }}
    }}
  ],
  "weaknesses": [
    {{"en": "Weakness from user perspective", "zh": "从用户角度的弱点描述"}}
  ],
  "targetAudience": {{"en": "Who is this for", "zh": "目标用户群体"}},
  "positioning": {{"en": "Market positioning", "zh": "市场定位"}}
}}

Important:
1. Provide BOTH English and Chinese for ALL user-facing text
2. Price should be in USD per month (0 for free tiers)
3. Be specific about limitations and weaknesses
4. If information is not available, use "Not clearly stated" / "未明确说明"
5. Focus on 2-3 most important features and weaknesses
"""

PAIN_ANALYSIS_PROMPT = """Analyze the following community discussions and extract user pain points in bilingual format.

Idea/Topic: {idea_title}
Category: {category}

Community Discussions:
{discussions}

Extract the top 3-5 pain points and return as JSON:

{{
  "painPoints": [
    {{
      "description": {{
        "en": "Clear description of the pain point",
        "zh": "中文痛点描述"
      }},
      "severity": "high|medium|low",
      "mentions": 5,
      "evidence": [
        {{
          "title": {{"en": "Discussion title", "zh": "讨论标题"}},
          "url": "https://...",
          "source": "hackernews|reddit|indiehackers",
          "quote": {{"en": "Key quote from discussion", "zh": "关键引用"}}
        }}
      ]
    }}
  ]
}}

Important:
1. Provide BOTH English and Chinese for ALL text
2. Severity: high = frequently mentioned + high impact, medium = moderate, low = minor
3. Include actual quotes from discussions as evidence
4. Focus on genuine pain points, not feature requests
"""

DIFFERENTIATION_PROMPT = """Based on the following competitor analysis and user pain points, generate a differentiation strategy in bilingual format.

Idea: {idea_title}
Category: {category}

Competitor Weaknesses:
{weaknesses}

User Pain Points:
{pains}

Generate a differentiation strategy and return as JSON:

{{
  "strategy": {{
    "en": "1-2 sentence differentiation strategy",
    "zh": "1-2句话的差异化策略"
  }},
  "rationale": {{
    "en": "Why this wedge works - specific reasoning",
    "zh": "为什么这个切角有机会的具体分析"
  }},
  "targetUser": {{
    "en": "Specific target user segment",
    "zh": "具体的目标用户群体"
  }},
  "keyDifferentiators": [
    {{"en": "Differentiator 1", "zh": "差异点1"}},
    {{"en": "Differentiator 2", "zh": "差异点2"}}
  ]
}}

Important:
1. Strategy must be specific and actionable, not generic
2. Explain WHY this wedge has opportunity
3. Target user should be specific (not "everyone")
4. Provide BOTH English and Chinese
"""

MARKET_GAPS_PROMPT = """Based on the competitor analysis, identify market gaps and opportunities.

Competitors Analyzed:
{competitor_summaries}

Identify 2-3 market gaps and return as JSON:

{{
  "marketGaps": [
    {{"en": "Gap description in English", "zh": "中文描述"}},
    {{"en": "Another gap", "zh": "另一个空白点"}}
  ]
}}

Important:
1. Gaps should be based on actual competitor weaknesses
2. Focus on underserved user segments or unmet needs
3. Provide BOTH English and Chinese
"""


class SiliconFlowAnalyzer:
    """Analyze competitors using SiliconFlow API."""
    
    def __init__(self, api_key: str = None, model: str = None, base_url: str = None):
        self.api_key = api_key or os.getenv("SILICONFLOW_API_KEY")
        self.model = model or os.getenv("SILICONFLOW_MODEL", "Qwen/Qwen2.5-32B-Instruct")
        # Support both CN (siliconflow.cn) and international (siliconflow.com) endpoints
        self.base_url = base_url or os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.com/v1")
        
        if not self.api_key:
            raise ValueError("SiliconFlow API key not provided. Set SILICONFLOW_API_KEY env var.")
    
    def _call_llm(self, prompt: str, temperature: float = 0.3) -> Optional[Dict[str, Any]]:
        """Call SiliconFlow API with structured output."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that analyzes competitor websites and extracts structured information. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"}
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            return json.loads(content)
            
        except requests.RequestException as e:
            print(f"API request failed: {e}")
            return None
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Failed to parse API response: {e}")
            return None
    
    def analyze_competitor(self, domain: str, landing_html: str, pricing_html: str) -> Optional[CompetitorProfile]:
        """
        Analyze a competitor website and extract structured profile.
        
        Args:
            domain: Competitor domain
            landing_html: Landing page HTML content
            pricing_html: Pricing page HTML content
            
        Returns:
            CompetitorProfile or None if analysis failed
        """
        # Truncate HTML to avoid token limits
        landing_truncated = landing_html[:15000] if landing_html else "Not available"
        pricing_truncated = pricing_html[:15000] if pricing_html else "Not available"
        
        prompt = COMPETITOR_ANALYSIS_PROMPT.format(
            domain=domain,
            landing_content=landing_truncated,
            pricing_content=pricing_truncated
        )
        
        result = self._call_llm(prompt)
        if not result:
            return None
        
        try:
            # Parse pricing tiers
            pricing_tiers = []
            for tier_data in result.get("pricingTiers", []):
                limits = {}
                for key, value in tier_data.get("limits", {}).items():
                    if isinstance(value, dict):
                        limits[key] = LocalizedPair.from_dict(value)
                    else:
                        limits[key] = LocalizedPair(en=str(value), zh=str(value))
                
                pricing_tiers.append(LocalizedPricingTier(
                    name=LocalizedPair.from_dict(tier_data["name"]),
                    price=tier_data.get("price", 0),
                    description=LocalizedPair.from_dict(tier_data["description"]),
                    limits=limits
                ))
            
            # Parse key features
            key_features = [
                LocalizedPair.from_dict(f) 
                for f in result.get("keyFeatures", [])
            ]
            
            # Parse weaknesses
            weaknesses = [
                LocalizedPair.from_dict(w)
                for w in result.get("weaknesses", [])
            ]
            
            return CompetitorProfile(
                domain=domain,
                name=result.get("name", domain),
                key_features=key_features,
                pricing_tiers=pricing_tiers,
                weaknesses=weaknesses,
                target_audience=LocalizedPair.from_dict(result["targetAudience"]) if result.get("targetAudience") else None,
                positioning=LocalizedPair.from_dict(result["positioning"]) if result.get("positioning") else None
            )
            
        except (KeyError, TypeError) as e:
            print(f"Failed to parse competitor analysis result: {e}")
            return None
    
    def analyze_pain_points(self, idea_title: str, category: str, discussions: List[Dict]) -> PainAnalysis:
        """
        Analyze community discussions to extract pain points.
        
        Args:
            idea_title: Title of the idea
            category: Category of the idea
            discussions: List of discussion data
            
        Returns:
            PainAnalysis with extracted pain points
        """
        # Format discussions for prompt
        discussions_text = "\n\n".join([
            f"Source: {d.get('source', 'unknown')}\n"
            f"Title: {d.get('title', 'Untitled')}\n"
            f"URL: {d.get('url', 'N/A')}\n"
            f"Content: {d.get('content', '')[:2000]}"
            for d in discussions[:5]  # Limit to 5 discussions
        ])
        
        prompt = PAIN_ANALYSIS_PROMPT.format(
            idea_title=idea_title,
            category=category,
            discussions=discussions_text
        )
        
        result = self._call_llm(prompt)
        if not result:
            return PainAnalysis()
        
        try:
            pain_points = []
            for pain_data in result.get("painPoints", []):
                evidence = []
                for ev_data in pain_data.get("evidence", []):
                    evidence.append(PainEvidence(
                        title=LocalizedPair.from_dict(ev_data["title"]),
                        url=ev_data.get("url", ""),
                        source=ev_data.get("source", "unknown"),
                        quote=LocalizedPair.from_dict(ev_data["quote"]) if ev_data.get("quote") else None
                    ))
                
                pain_points.append(PainPoint(
                    description=LocalizedPair.from_dict(pain_data["description"]),
                    severity=pain_data.get("severity", "medium"),
                    mentions=pain_data.get("mentions", 1),
                    evidence=evidence
                ))
            
            return PainAnalysis(top_pains=pain_points)
            
        except (KeyError, TypeError) as e:
            print(f"Failed to parse pain analysis result: {e}")
            return PainAnalysis()
    
    def generate_differentiation_strategy(
        self, 
        idea_title: str, 
        category: str,
        competitors: List[CompetitorProfile],
        pain_analysis: PainAnalysis
    ) -> Optional[DifferentiationStrategy]:
        """
        Generate differentiation strategy based on analysis.
        
        Args:
            idea_title: Title of the idea
            category: Category of the idea
            competitors: List of competitor profiles
            pain_analysis: Pain analysis result
            
        Returns:
            DifferentiationStrategy or None if generation failed
        """
        # Format weaknesses
        weaknesses_text = "\n".join([
            f"- {comp.name}: {[w.en for w in comp.weaknesses]}"
            for comp in competitors
        ])
        
        # Format pains
        pains_text = "\n".join([
            f"- {pain.description.en} (severity: {pain.severity}, mentions: {pain.mentions})"
            for pain in pain_analysis.top_pains
        ])
        
        prompt = DIFFERENTIATION_PROMPT.format(
            idea_title=idea_title,
            category=category,
            weaknesses=weaknesses_text,
            pains=pains_text
        )
        
        result = self._call_llm(prompt, temperature=0.5)
        if not result:
            return None
        
        try:
            return DifferentiationStrategy(
                strategy=LocalizedPair.from_dict(result["strategy"]),
                rationale=LocalizedPair.from_dict(result["rationale"]),
                target_user=LocalizedPair.from_dict(result["targetUser"]) if result.get("targetUser") else None,
                key_differentiators=[
                    LocalizedPair.from_dict(d)
                    for d in result.get("keyDifferentiators", [])
                ]
            )
        except (KeyError, TypeError) as e:
            print(f"Failed to parse differentiation strategy: {e}")
            return None
    
    def identify_market_gaps(self, competitors: List[CompetitorProfile]) -> List[LocalizedPair]:
        """
        Identify market gaps based on competitor analysis.
        
        Args:
            competitors: List of competitor profiles
            
        Returns:
            List of market gaps as LocalizedPairs
        """
        # Format competitor summaries
        summaries = "\n".join([
            f"- {comp.name} ({comp.domain}): {[w.en for w in comp.weaknesses]}"
            for comp in competitors
        ])
        
        prompt = MARKET_GAPS_PROMPT.format(competitor_summaries=summaries)
        
        result = self._call_llm(prompt)
        if not result:
            return []
        
        try:
            return [
                LocalizedPair.from_dict(gap)
                for gap in result.get("marketGaps", [])
            ]
        except (KeyError, TypeError) as e:
            print(f"Failed to parse market gaps: {e}")
            return []
