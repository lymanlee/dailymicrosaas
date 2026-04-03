import type { APIRoute } from 'astro';

const site = 'https://dailymicrosaas.pages.dev';

export const GET: APIRoute = () => {
  const body = [`User-agent: *`, `Allow: /`, `Sitemap: ${site}/sitemap-index.xml`].join('\n');

  return new Response(body, {
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
    },
  });
};
