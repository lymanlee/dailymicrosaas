import type { Lang } from './i18n';

export interface LocalizedPair {
  en: string;
  zh: string;
}

export interface PricingTier {
  name: LocalizedPair;
  price: number;
  description: LocalizedPair;
  limits: {
    monthlyCredits: LocalizedPair;
    commercialUse: LocalizedPair;
  };
}

export interface CompetitorProfile {
  domain: string;
  name: LocalizedPair;
  keyFeatures: LocalizedPair[];
  pricingTiers: PricingTier[];
  weaknesses: LocalizedPair[];
}

export interface CompetitorAnalysis {
  topCompetitors: CompetitorProfile[];
  marketGaps: LocalizedPair[];
}

export function getLocalizedPairText(value: LocalizedPair, lang: Lang): string {
  return lang === 'zh' ? value.zh : value.en;
}

export function parseCompetitorAnalysis(frontmatter: Record<string, any>): CompetitorAnalysis | null {
  const rawAnalysis = frontmatter.competitorAnalysis;
  if (!rawAnalysis || typeof rawAnalysis !== 'object') {
    return null;
  }

  // Handle legacy format (simple array of domains)
  if (Array.isArray(rawAnalysis)) {
    return null;
  }

  // Handle new structured format
  const topCompetitors: CompetitorProfile[] = [];
  const marketGaps: LocalizedPair[] = [];

  // Parse topCompetitors
  if (Array.isArray(rawAnalysis.topCompetitors)) {
    rawAnalysis.topCompetitors.forEach((comp: any) => {
      if (!comp.domain) return;

      const profile: CompetitorProfile = {
        domain: comp.domain,
        name: parseLocalizedPair(comp.name, comp.domain),
        keyFeatures: parseLocalizedPairArray(comp.keyFeatures),
        pricingTiers: parsePricingTiers(comp.pricingTiers),
        weaknesses: parseLocalizedPairArray(comp.weaknesses),
      };
      topCompetitors.push(profile);
    });
  }

  // Parse marketGaps
  if (Array.isArray(rawAnalysis.marketGaps)) {
    rawAnalysis.marketGaps.forEach((gap: any) => {
      if (typeof gap === 'object' && gap.en && gap.zh) {
        marketGaps.push({ en: gap.en, zh: gap.zh });
      }
    });
  }

  if (topCompetitors.length === 0 && marketGaps.length === 0) {
    return null;
  }

  return { topCompetitors, marketGaps };
}

function parseLocalizedPair(value: any, fallback: string): LocalizedPair {
  if (typeof value === 'object' && value.en && value.zh) {
    return { en: value.en, zh: value.zh };
  }
  if (typeof value === 'string') {
    return { en: value, zh: value };
  }
  return { en: fallback, zh: fallback };
}

function parseLocalizedPairArray(items: any[]): LocalizedPair[] {
  if (!Array.isArray(items)) return [];
  return items
    .map((item) => {
      if (typeof item === 'object' && item.en && item.zh) {
        return { en: item.en, zh: item.zh };
      }
      if (typeof item === 'string') {
        return { en: item, zh: item };
      }
      return null;
    })
    .filter((item): item is LocalizedPair => item !== null);
}

function parsePricingTiers(tiers: any[]): PricingTier[] {
  if (!Array.isArray(tiers)) return [];
  return tiers
    .map((tier) => {
      if (!tier || typeof tier !== 'object') return null;
      return {
        name: parseLocalizedPair(tier.name, 'Plan'),
        price: typeof tier.price === 'number' ? tier.price : 0,
        description: parseLocalizedPair(tier.description, ''),
        limits: {
          monthlyCredits: parseLocalizedPair(tier.limits?.monthlyCredits, ''),
          commercialUse: parseLocalizedPair(tier.limits?.commercialUse, ''),
        },
      };
    })
    .filter((tier): tier is PricingTier => tier !== null);
}

export function formatPrice(price: number, currency: string = '$'): string {
  if (price === 0) return 'Free';
  return `${currency}${price.toFixed(2)}`;
}

export function getCompetitorUrl(domain: string): string {
  if (domain.startsWith('http')) return domain;
  return `https://${domain}`;
}
