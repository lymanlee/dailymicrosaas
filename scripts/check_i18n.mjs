import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = path.resolve(SCRIPT_DIR, '..');
const IDEAS_DIR = path.join(ROOT_DIR, 'src', 'content', 'ideas');
const DETAIL_PAGE = path.join(ROOT_DIR, 'src', 'pages', 'ideas', '[slug].astro');
const IDEA_HELPER = path.join(ROOT_DIR, 'src', 'lib', 'idea.ts');
const LAYOUT_FILE = path.join(ROOT_DIR, 'src', 'layouts', 'Layout.astro');

const REQUIRED_LOCALIZED_FIELDS = ['title', 'description', 'bestWedge', 'dataWindow', 'buildWindow'];
const REQUIRED_SCALAR_FIELDS = ['verdict', 'confidence'];
const REQUIRED_LOCALIZED_LIST_FIELDS = ['painClusters', 'competitorGaps'];
const REQUIRED_LAYOUT_KEYS = [
  'detail.trend.title',
  'detail.trend.desc',
  'detail.trend.peak',
  'detail.trend.avg',
  'detail.trend.window',
  'footer.subscribe',
];

function extractFrontmatter(content) {
  const match = content.match(/^---\n([\s\S]*?)\n---\n/);
  return match?.[1] ?? null;
}

function getFieldBlock(frontmatter, fieldName) {
  const lines = frontmatter.split('\n');
  const startIndex = lines.findIndex((line) => line.startsWith(`${fieldName}:`));
  if (startIndex === -1) {
    return null;
  }

  const header = lines[startIndex];
  const body = [];
  for (let index = startIndex + 1; index < lines.length; index += 1) {
    const line = lines[index];
    if (/^[A-Za-z][A-Za-z0-9]*:/.test(line)) {
      break;
    }
    body.push(line);
  }

  return { header, body };
}

function hasNonEmptyLocalizedLine(lines, lang) {
  const regex = new RegExp(`^\\s+${lang}:\\s*["']?.*\\S.*["']?\\s*$`);
  return lines.some((line) => regex.test(line));
}

function validateLocalizedField(frontmatter, fieldName, filePath, errors) {
  const block = getFieldBlock(frontmatter, fieldName);
  if (!block) {
    errors.push(`${filePath}: missing required localized field \`${fieldName}\``);
    return;
  }

  if (block.header.trim() !== `${fieldName}:`) {
    errors.push(`${filePath}: field \`${fieldName}\` must be a multiline { en, zh } object`);
    return;
  }

  if (!hasNonEmptyLocalizedLine(block.body, 'en') || !hasNonEmptyLocalizedLine(block.body, 'zh')) {
    errors.push(`${filePath}: field \`${fieldName}\` must provide non-empty \`en\` and \`zh\` values`);
  }
}

function validateScalarField(frontmatter, fieldName, filePath, errors) {
  const regex = new RegExp(`^${fieldName}:\\s*["'][^"']+["']\\s*$`, 'm');
  if (!regex.test(frontmatter)) {
    errors.push(`${filePath}: missing required scalar field \`${fieldName}\``);
  }
}

function validateLocalizedListField(frontmatter, fieldName, filePath, errors) {
  const block = getFieldBlock(frontmatter, fieldName);
  if (!block) {
    errors.push(`${filePath}: missing required localized list \`${fieldName}\``);
    return;
  }

  if (/^\s*\[\s*\]\s*$/.test(block.header.replace(`${fieldName}:`, ''))) {
    errors.push(`${filePath}: localized list \`${fieldName}\` must not be empty`);
    return;
  }

  let itemCount = 0;
  let pendingEn = false;
  for (const line of block.body) {
    if (/^\s*-\s*en:\s*["']?.*\S.*["']?\s*$/.test(line)) {
      itemCount += 1;
      pendingEn = true;
      continue;
    }
    if (pendingEn && /^\s+zh:\s*["']?.*\S.*["']?\s*$/.test(line)) {
      pendingEn = false;
    }
  }

  if (itemCount === 0 || pendingEn) {
    errors.push(`${filePath}: localized list \`${fieldName}\` must contain complete { en, zh } items`);
  }
}

function countKeyOccurrences(content, key) {
  const regex = new RegExp(`'${key.replace(/[.*+?^${}()|[\\]\\]/g, '\\$&')}'\\s*:`, 'g');
  return (content.match(regex) ?? []).length;
}

async function validateContentFiles(errors) {
  const entries = await readdir(IDEAS_DIR, { withFileTypes: true });
  const ideaFiles = entries
    .filter((entry) => entry.isFile() && entry.name.endsWith('.md'))
    .map((entry) => path.join(IDEAS_DIR, entry.name));

  for (const filePath of ideaFiles) {
    const content = await readFile(filePath, 'utf8');
    const frontmatter = extractFrontmatter(content);
    if (!frontmatter) {
      errors.push(`${filePath}: missing frontmatter block`);
      continue;
    }

    for (const fieldName of REQUIRED_LOCALIZED_FIELDS) {
      validateLocalizedField(frontmatter, fieldName, filePath, errors);
    }
    for (const fieldName of REQUIRED_SCALAR_FIELDS) {
      validateScalarField(frontmatter, fieldName, filePath, errors);
    }
    for (const fieldName of REQUIRED_LOCALIZED_LIST_FIELDS) {
      validateLocalizedListField(frontmatter, fieldName, filePath, errors);
    }
  }
}

async function validateDetailPage(errors) {
  const content = await readFile(DETAIL_PAGE, 'utf8');
  const bannedPatterns = [
    { regex: /extractLabeledValue\(/, reason: 'detail page must not extract build window from Markdown body' },
    { regex: /\bgetLocalizedText\(/, reason: 'detail page must not use loose getLocalizedText for key visible content' },
    { regex: /hasLocalizedText\(/, reason: 'detail page must not silently filter malformed localized content' },
  ];

  for (const { regex, reason } of bannedPatterns) {
    if (regex.test(content)) {
      errors.push(`${DETAIL_PAGE}: ${reason}`);
    }
  }
}

async function validateIdeaHelpers(errors) {
  const content = await readFile(IDEA_HELPER, 'utf8');
  const bannedPatterns = [
    { regex: /getLocalizedText\(frontmatter\.bestWedge/, reason: 'idea helpers must use strict helper for bestWedge' },
    { regex: /getLocalizedText\(gap,\s*'en'/, reason: 'competition overview must not use loose helper for competitor gaps' },
    { regex: /getLocalizedText\(frontmatter\.title,\s*'en'/, reason: 'full breakdown must not use loose helper for title fallback' },
  ];

  for (const { regex, reason } of bannedPatterns) {
    if (regex.test(content)) {
      errors.push(`${IDEA_HELPER}: ${reason}`);
    }
  }
}

async function validateLayout(errors) {
  const content = await readFile(LAYOUT_FILE, 'utf8');

  for (const key of REQUIRED_LAYOUT_KEYS) {
    const count = countKeyOccurrences(content, key);
    if (count < 2) {
      errors.push(`${LAYOUT_FILE}: runtime translation key \`${key}\` must exist in both en and zh dictionaries`);
    }
  }

  if (/data-l10n-en="Subscribe"/.test(content) || /data-l10n-zh="订阅更新"/.test(content)) {
    errors.push(`${LAYOUT_FILE}: subscribe link must use shared i18n keys instead of hardcoded footer text`);
  }
}

async function main() {
  const errors = [];

  await validateContentFiles(errors);
  await validateDetailPage(errors);
  await validateIdeaHelpers(errors);
  await validateLayout(errors);

  if (errors.length > 0) {
    console.error('❌ Bilingual integrity check failed:\n');
    for (const error of errors) {
      console.error(`- ${error}`);
    }
    process.exit(1);
  }

  console.log('✅ Bilingual integrity check passed.');
}

main().catch((error) => {
  console.error('❌ Bilingual integrity check crashed.');
  console.error(error instanceof Error ? error.stack || error.message : String(error));
  process.exit(1);
});
