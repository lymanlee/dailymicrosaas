import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';
import { getLocalizedText } from '../lib/idea';
import { withLangPath } from '../lib/i18n';

export async function GET(context: { site?: URL }) {
  const site = context.site ?? new URL('https://dailymicrosaas.pages.dev');
  const ideas = (await getCollection('ideas'))
    .filter((idea) => idea.slug !== 'template')
    .sort((a, b) => new Date(b.data.date).getTime() - new Date(a.data.date).getTime());

  return rss({
    title: 'Daily Micro SaaS',
    description: 'One buildable Micro SaaS direction every day, with demand signals, competition context, and the fastest path to an MVP.',
    site,
    items: ideas.map((idea) => ({
      title: getLocalizedText(idea.data.title, 'en', idea.slug),
      description: getLocalizedText(idea.data.description, 'en', ''),
      pubDate: new Date(idea.data.date),
      link: withLangPath(`/ideas/${idea.slug}`, 'en'),
      categories: [idea.data.category],
    })),
    customData: '<language>en-us</language>',
  });
}
