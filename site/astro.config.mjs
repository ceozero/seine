// @ts-check
import mdx from '@astrojs/mdx';
import { defineConfig } from 'astro/config';

export default defineConfig({
    site: 'https://seineminer.com',
    trailingSlash: 'always',
    // The complete styles are small; avoid a blocking round trip before first paint.
    build: { format: 'directory', inlineStylesheets: 'always' },
    integrations: [mdx()],
    markdown: { shikiConfig: { theme: 'github-dark-dimmed' } },
});
