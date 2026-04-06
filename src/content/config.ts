import { defineCollection, z } from 'astro:content';

const localizedTextSchema = z.object({
  en: z.string(),
  zh: z.string(),
});

const localizedTextField = z.union([z.string(), localizedTextSchema]);

const ideasCollection = defineCollection({
  type: 'content',
  schema: z.object({
    title: localizedTextField,
    date: z.string(),
    category: z.string(),
    difficulty: z.enum(['Easy', 'Medium', 'Hard']),
    description: localizedTextField,
    status: z.string().optional(),
    sourceKeyword: z.string().optional(),
    sourceScore: z.number().optional(),
    sourceGrade: z.enum(['worth_it', 'watch', 'skip']).optional(),
    // Decision summary fields (P0)
    verdict: z.enum(['Worth Building', 'Watch', 'Skip']).optional(),
    confidence: z.enum(['High', 'Medium', 'Low']).optional(),
    bestWedge: localizedTextField.optional(),
    dataDate: z.string().optional(),
    dataWindow: localizedTextField.optional(),
    trendSeries: z.array(z.object({
      date: z.string(),
      value: z.number(),
    })).optional(),
    painClusters: z.array(localizedTextField).optional(),
    competitorGaps: z.array(localizedTextField).optional(),
    evidenceLinks: z.array(z.object({
      url: z.string(),
      title: z.string(),
      source: z.string(),
    })).optional(),
  }),
});

export const collections = {
  'ideas': ideasCollection,
};
