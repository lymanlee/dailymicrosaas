import { defineCollection, z } from 'astro:content';

const ideasCollection = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    date: z.string(),
    category: z.string(),
    difficulty: z.enum(['Easy', 'Medium', 'Hard']),
    description: z.string(),
    status: z.string().optional(),
    sourceKeyword: z.string().optional(),
    sourceScore: z.number().optional(),
    sourceGrade: z.enum(['worth_it', 'watch', 'skip']).optional(),
  }),
});

export const collections = {
  'ideas': ideasCollection,
};