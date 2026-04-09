import { defineCollection, z } from 'astro:content';

const localizedTextSchema = z.object({
  en: z.string().trim().min(1, 'en translation must not be empty'),
  zh: z.string().trim().min(1, 'zh translation must not be empty'),
});

const pricingTierSchema = z.object({
  name: localizedTextSchema,
  price: z.number(),
  description: localizedTextSchema,
  limits: z.object({
    monthlyCredits: localizedTextSchema,
    commercialUse: localizedTextSchema,
  }),
});

const competitorProfileSchema = z.object({
  domain: z.string(),
  name: localizedTextSchema,
  keyFeatures: z.array(localizedTextSchema),
  pricingTiers: z.array(pricingTierSchema),
  weaknesses: z.array(localizedTextSchema),
});

const competitorAnalysisSchema = z.object({
  topCompetitors: z.array(competitorProfileSchema),
  marketGaps: z.array(localizedTextSchema),
});

const ideasCollection = defineCollection({
  type: 'content',
  schema: z.object({
    title: localizedTextSchema,
    date: z.string(),
    category: z.string(),
    difficulty: z.enum(['Easy', 'Medium', 'Hard']),
    description: localizedTextSchema,

    status: z.string().optional(),
    sourceKeyword: z.string().optional(),
    sourceScore: z.number().optional(),
    sourceGrade: z.enum(['worth_it', 'watch', 'skip']).optional(),

    verdict: z.enum(['Worth Building', 'Watch', 'Skip']),
    confidence: z.enum(['High', 'Medium', 'Low']),
    bestWedge: localizedTextSchema,
    dataDate: z.string().optional(),
    dataWindow: localizedTextSchema,
    buildWindow: localizedTextSchema,
    trendSeries: z.array(z.object({
      date: z.string(),
      value: z.number(),
    })).optional(),
    painClusters: z.array(localizedTextSchema).min(1, 'painClusters must include at least one bilingual item'),
    competitorGaps: z.array(localizedTextSchema).min(1, 'competitorGaps must include at least one bilingual item'),
    competitorAnalysis: competitorAnalysisSchema.optional(),
    evidenceLinks: z.array(z.object({
      url: z.string(),
      title: z.string(),
      source: z.string(),
    })).optional(),
    risks: z.array(z.object({
      risk: localizedTextSchema,
      mitigation: localizedTextSchema,
    })).optional(),
    unsuitableFor: z.array(localizedTextSchema).optional(),
  }),
});

export const collections = {
  ideas: ideasCollection,
};
