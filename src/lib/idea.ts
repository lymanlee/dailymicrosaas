export interface IdeaSection {
  title: string;
  body: string;
  bullets: string[];
  numbered: string[];
  paragraphs: string[];
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
