import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

// src/content/blog/<slug>/index.mdx is the English source; <slug>/<locale>.mdx (es.mdx,
// zh-Hans.mdx, ...) are its translations. Translations carry only the translated fields plus
// sourceHash; dates, related posts and draft state come from the English file.
const blog = defineCollection({
    loader: glob({
        pattern: '*/*.mdx',
        base: './src/content/blog',
        generateId: ({ entry }) => entry.replace(/\.mdx$/, ''),
    }),
    schema: z.object({
        title: z.string().min(1),
        seoTitle: z.string().optional(),
        description: z.string().min(1),
        date: z.coerce.date().optional(),
        updated: z.coerce.date().optional(),
        tags: z.array(z.string()).default([]),
        faq: z.array(z.object({ q: z.string().min(1), a: z.string().min(1) })).default([]),
        related: z.array(z.string()).default([]),
        image: z.string().optional(),
        draft: z.boolean().default(false),
        sourceHash: z.string().optional(),
        translation: z.enum(['draft', 'reviewed']).optional(),
    }),
});

export const collections = { blog };
