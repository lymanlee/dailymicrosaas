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
    title: 'Daily Micro SaaS 中文订阅',
    description: '每天一个可落地的 Micro SaaS 方向，附带需求信号、竞争判断和最快 MVP 路径。',
    site,
    items: ideas.map((idea) => ({
      title: getLocalizedText(idea.data.title, 'zh', idea.slug),
      description: getLocalizedText(idea.data.description, 'zh', ''),
      pubDate: new Date(idea.data.date),
      link: withLangPath(`/ideas/${idea.slug}`, 'zh'),
      categories: [idea.data.category],
    })),
    customData: '<language>zh-cn</language>',
  });
}
