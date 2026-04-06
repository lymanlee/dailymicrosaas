import type { Lang } from './i18n';

export interface LocalizedTextObject {
  en?: string;
  zh?: string;
}

export type LocalizedText = string | LocalizedTextObject;

export interface IdeaSection {
  title: string;
  body: string;
  bullets: string[];
  numbered: string[];
  paragraphs: string[];
}

export interface CategoryInfo {
  en: string;
  zh: string;
  classes: string;
}

export const categoryMeta: Record<string, CategoryInfo> = {
  'AI 工具': { en: 'AI Tools', zh: 'AI 工具', classes: 'bg-violet-50 text-violet-700 ring-violet-200' },
  '文档处理': { en: 'Document Tools', zh: '文档处理', classes: 'bg-sky-50 text-sky-700 ring-sky-200' },
  '图像处理': { en: 'Image Tools', zh: '图像处理', classes: 'bg-pink-50 text-pink-700 ring-pink-200' },
  '视频处理': { en: 'Video Tools', zh: '视频处理', classes: 'bg-orange-50 text-orange-700 ring-orange-200' },
  '效率工具': { en: 'Productivity Tools', zh: '效率工具', classes: 'bg-teal-50 text-teal-700 ring-teal-200' },
  '开发者工具': { en: 'Developer Tools', zh: '开发者工具', classes: 'bg-slate-100 text-slate-700 ring-slate-200' },
  '语言学习': { en: 'Language Learning', zh: '语言学习', classes: 'bg-cyan-50 text-cyan-700 ring-cyan-200' },
};

export function getCategoryInfo(category: string): CategoryInfo {
  return categoryMeta[category] ?? {
    en: category,
    zh: category,
    classes: 'bg-slate-100 text-slate-700 ring-slate-200',
  };
}

export function getCategoryLabel(category: string, lang: Lang): string {
  const info = getCategoryInfo(category);
  return lang === 'zh' ? info.zh : info.en;
}

export function getLocalizedText(value: LocalizedText | undefined, lang: Lang, fallback = '—'): string {
  if (!value) {
    return fallback;
  }

  if (typeof value === 'string') {
    return value || fallback;
  }

  return value[lang] ?? value.en ?? value.zh ?? fallback;
}

export function hasLocalizedText(value: LocalizedText | undefined): boolean {
  return Boolean(getLocalizedText(value, 'en', '').trim() || getLocalizedText(value, 'zh', '').trim());
}

export function parseIdeaSections(markdown: string): IdeaSection[] {
  const normalized = markdown.replace(/\r\n/g, '\n').trim();
  const matches = [...normalized.matchAll(/^##\s+(.+)$/gm)];

  if (!matches.length) {
    return [];
  }

  return matches.map((match, index) => {
    const title = match[1].trim();
    const bodyStart = (match.index ?? 0) + match[0].length;
    const bodyEnd = index + 1 < matches.length ? (matches[index + 1].index ?? normalized.length) : normalized.length;
    const body = normalized.slice(bodyStart, bodyEnd).trim();
    const lines = body
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean);

    const bullets = lines
      .filter((line) => /^-\s+/.test(line))
      .map((line) => line.replace(/^-\s+/, '').trim());

    const numbered = lines
      .filter((line) => /^\d+\.\s+/.test(line))
      .map((line) => line.replace(/^\d+\.\s+/, '').trim());

    const paragraphs = lines.filter(
      (line) =>
        !/^[-*]\s+/.test(line) &&
        !/^\d+\.\s+/.test(line) &&
        !/^\|/.test(line) &&
        !/^\*\*/.test(line)
    );

    return { title, body, bullets, numbered, paragraphs };
  });
}

export function getSection(sections: IdeaSection[], titles: string[]): IdeaSection | undefined {
  return sections.find((section) => titles.includes(section.title));
}

export function estimateReadingTime(markdown: string): number {
  const plain = markdown
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`[^`]*`/g, ' ')
    .replace(/\[[^\]]+\]\([^\)]+\)/g, ' ')
    .replace(/[#>*_|-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  const cjkUnits = (plain.match(/[\u4e00-\u9fff]/g) || []).length;
  const latinWords = plain.split(/\s+/).filter(Boolean).length;
  const estimatedWords = latinWords + cjkUnits / 2;

  return Math.max(1, Math.ceil(estimatedWords / 220));
}

export function extractLabeledValue(markdown: string, label: string): string | null {
  const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const regex = new RegExp(`\\*\\*${escaped}\\*\\*\\s*:?\\s*(.+)`);
  const match = markdown.match(regex);
  return match?.[1]?.trim() ?? null;
}
