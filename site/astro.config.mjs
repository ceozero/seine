// @ts-check
import mdx from '@astrojs/mdx';
import { defineConfig } from 'astro/config';

export default defineConfig({
    site: 'https://seineminer.com',
    trailingSlash: 'always',
    build: { format: 'directory' },
    integrations: [mdx()],
    markdown: { shikiConfig: { theme: 'github-dark-dimmed' } },
});
