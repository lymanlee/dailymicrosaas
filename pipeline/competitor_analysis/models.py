"""
Data models for competitor analysis with bilingual support.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class LocalizedPair:
    """Bilingual text pair."""
    en: str
    zh: str
    
    def to_dict(self) -> Dict[str, str]:
        return {"en": self.en, "zh": self.zh}
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "LocalizedPair":
        return cls(en=data.get("en", ""), zh=data.get("zh", ""))


@dataclass
class LocalizedPricingTier:
    """Pricing tier with bilingual support."""
    name: LocalizedPair
    price: float  # USD per month, 0 for free
    description: LocalizedPair
    limits: Dict[str, LocalizedPair] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name.to_dict(),
            "price": self.price,
            "description": self.description.to_dict(),
            "limits": {k: v.to_dict() for k, v in self.limits.items()}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LocalizedPricingTier":
        return cls(
            name=LocalizedPair.from_dict(data["name"]),
            price=data["price"],
            description=LocalizedPair.from_dict(data["description"]),
            limits={k: LocalizedPair.from_dict(v) for k, v in data.get("limits", {}).items()}
        )


@dataclass
class CompetitorProfile:
    """Full competitor profile with bilingual support."""
    domain: str
    name: str  # Simple string name
    key_features: List[LocalizedPair] = field(default_factory=list)
    pricing_tiers: List[LocalizedPricingTier] = field(default_factory=list)
    weaknesses: List[LocalizedPair] = field(default_factory=list)
    target_audience: Optional[LocalizedPair] = None
    positioning: Optional[LocalizedPair] = None
    analyzed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        # Ensure name is always a simple string
        name_value = self.name
        if isinstance(name_value, dict):
            name_value = name_value.get("en", str(name_value))
        return {
            "domain": self.domain,
            "name": name_value,
            "keyFeatures": [f.to_dict() for f in self.key_features],
            "pricingTiers": [p.to_dict() for p in self.pricing_tiers],
            "weaknesses": [w.to_dict() for w in self.weaknesses],
            "targetAudience": self.target_audience.to_dict() if self.target_audience else None,
            "positioning": self.positioning.to_dict() if self.positioning else None,
            "analyzedAt": self.analyzed_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompetitorProfile":
        # Handle name that might be a dict (from older cached data)
        name_value = data.get("name", "")
        if isinstance(name_value, dict):
            name_value = name_value.get("en", str(name_value))
        return cls(
            domain=data["domain"],
            name=name_value,
            key_features=[LocalizedPair.from_dict(f) for f in data.get("keyFeatures", [])],
            pricing_tiers=[LocalizedPricingTier.from_dict(p) for p in data.get("pricingTiers", [])],
            weaknesses=[LocalizedPair.from_dict(w) for w in data.get("weaknesses", [])],
            target_audience=LocalizedPair.from_dict(data["targetAudience"]) if data.get("targetAudience") else None,
            positioning=LocalizedPair.from_dict(data["positioning"]) if data.get("positioning") else None,
            analyzed_at=data.get("analyzedAt", datetime.now().isoformat())
        )


@dataclass
class PainEvidence:
    """Evidence source for a pain point."""
    title: LocalizedPair
    url: str
    source: str
    quote: Optional[LocalizedPair] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "title": self.title.to_dict(),
            "url": self.url,
            "source": self.source
        }
        if self.quote:
            result["quote"] = self.quote.to_dict()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PainEvidence":
        return cls(
            title=LocalizedPair.from_dict(data["title"]),
            url=data["url"],
            source=data["source"],
            quote=LocalizedPair.from_dict(data["quote"]) if data.get("quote") else None
        )


@dataclass
class PainPoint:
    """User pain point with bilingual support."""
    description: LocalizedPair
    severity: str  # "high", "medium", "low"
    mentions: int
    evidence: List[PainEvidence] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "description": self.description.to_dict(),
            "severity": self.severity,
            "mentions": self.mentions,
            "evidence": [e.to_dict() for e in self.evidence]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PainPoint":
        return cls(
            description=LocalizedPair.from_dict(data["description"]),
            severity=data["severity"],
            mentions=data["mentions"],
            evidence=[PainEvidence.from_dict(e) for e in data.get("evidence", [])]
        )


@dataclass
class PainAnalysis:
    """Pain analysis result."""
    top_pains: List[PainPoint] = field(default_factory=list)
    extracted_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "topPains": [p.to_dict() for p in self.top_pains],
            "extractedAt": self.extracted_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PainAnalysis":
        return cls(
            top_pains=[PainPoint.from_dict(p) for p in data.get("topPains", [])],
            extracted_at=data.get("extractedAt", datetime.now().isoformat())
        )


@dataclass
class DifferentiationStrategy:
    """Differentiation strategy with bilingual support."""
    strategy: LocalizedPair
    rationale: LocalizedPair
    target_user: Optional[LocalizedPair] = None
    key_differentiators: List[LocalizedPair] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "strategy": self.strategy.to_dict(),
            "rationale": self.rationale.to_dict(),
            "keyDifferentiators": [d.to_dict() for d in self.key_differentiators]
        }
        if self.target_user:
            result["targetUser"] = self.target_user.to_dict()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DifferentiationStrategy":
        return cls(
            strategy=LocalizedPair.from_dict(data["strategy"]),
            rationale=LocalizedPair.from_dict(data["rationale"]),
            target_user=LocalizedPair.from_dict(data["targetUser"]) if data.get("targetUser") else None,
            key_differentiators=[LocalizedPair.from_dict(d) for d in data.get("keyDifferentiators", [])]
        )


@dataclass
class CompetitorAnalysisResult:
    """Complete competitor analysis for an idea."""
    top_competitors: List[CompetitorProfile] = field(default_factory=list)
    market_gaps: List[LocalizedPair] = field(default_factory=list)
    analyzed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "topCompetitors": [c.to_dict() for c in self.top_competitors],
            "marketGaps": [g.to_dict() for g in self.market_gaps],
            "analyzedAt": self.analyzed_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompetitorAnalysisResult":
        return cls(
            top_competitors=[CompetitorProfile.from_dict(c) for c in data.get("topCompetitors", [])],
            market_gaps=[LocalizedPair.from_dict(g) for g in data.get("marketGaps", [])],
            analyzed_at=data.get("analyzedAt", datetime.now().isoformat())
        )
