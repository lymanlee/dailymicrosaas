"""
Recommend top competitors for an idea using LLM.
"""
import json
import os
from typing import List

import requests


COMPETITOR_RECOMMENDATION_PROMPT = """Based on the following idea, recommend the top 2-3 competitors in the market.

Idea Title: {title}
Idea Category: {category}
Idea Description: {description}

Return a JSON array of competitors:
[
  {{
    "domain": "competitor.com",
    "name": "Competitor Name",
    "reason": "Brief reason why this is a top competitor"
  }}
]

Requirements:
1. Recommend only well-known, established competitors (not side projects)
2. Include both direct competitors and adjacent players
3. Focus on those with clear pricing pages and public information
4. Return 2-3 competitors maximum
"""


class CompetitorRecommender:
    """Recommend competitors using SiliconFlow API."""
    
    def __init__(self, api_key: str = None, model: str = None, base_url: str = None):
        self.api_key = api_key or os.getenv("SILICONFLOW_API_KEY")
        self.model = model or os.getenv("SILICONFLOW_MODEL", "Qwen/Qwen2.5-32B-Instruct")
        # Support both CN (siliconflow.cn) and international (siliconflow.com) endpoints
        self.base_url = base_url or os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.com/v1")
        
        if not self.api_key:
            raise ValueError("SiliconFlow API key not provided.")
    
    def _call_llm(self, prompt: str) -> List[dict]:
        """Call SiliconFlow API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a market research assistant. Recommend relevant competitors based on the idea description. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "response_format": {"type": "json_object"}
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            data = json.loads(content)
            
            # Handle both array and object with competitors key
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "competitors" in data:
                return data["competitors"]
            else:
                return []
                
        except Exception as e:
            print(f"Failed to get competitor recommendations: {e}")
            return []
    
    def recommend(self, title: str, category: str, description: str = "") -> List[str]:
        """
        Recommend competitor domains for an idea.
        
        Args:
            title: Idea title
            category: Idea category
            description: Optional description
            
        Returns:
            List of competitor domains
        """
        prompt = COMPETITOR_RECOMMENDATION_PROMPT.format(
            title=title,
            category=category,
            description=description or "No description provided"
        )
        
        competitors = self._call_llm(prompt)
        
        # Extract domains
        domains = []
        for comp in competitors:
            domain = comp.get("domain", "")
            # Clean domain
            domain = domain.replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")
            if domain:
                domains.append(domain)
        
        return domains
