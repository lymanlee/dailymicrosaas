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

/**
 * 宽松取值（保持兼容）：找不到目标语言时静默 fallback，用于非关键区域。
 */
export function getLocalizedText(value: LocalizedText | undefined, lang: Lang, fallback = '—'): string {
  if (!value) {
    return fallback;
  }

  if (typeof value === 'string') {
    return value || fallback;
  }

  return value[lang] ?? value.en ?? value.zh ?? fallback;
}

/**
 * 严格取值：目标语言必须存在且非空，否则在开发环境抛 Error、生产环境返回带警告前缀的占位符。
 * 用于详情页的所有关键展示区域（标题、描述、bestWedge、painClusters、competitorGaps、dataWindow）。
 */
export function getLocalizedTextStrict(value: LocalizedText | undefined, lang: Lang, debugLabel = ''): string {
  if (!value) {
    throw new Error(`[i18n] Missing localized field${debugLabel ? ` (${debugLabel})` : ''}: value is undefined`);
  }

  if (typeof value === 'string') {
    throw new Error(`[i18n] Strict localized field${debugLabel ? ` (${debugLabel})` : ''} must use { en, zh } object, plain string received`);
  }

  const result = value[lang]?.trim();
  if (!result) {
    throw new Error(`[i18n] Missing "${lang}" translation${debugLabel ? ` for ${debugLabel}` : ''}`);
  }

  return result;
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

export interface LocalizedPair {
  en: string;
  zh: string;
}

export interface SourceSignalCard {
  title: LocalizedPair;
  source: LocalizedPair;
  meta: LocalizedPair;
  url?: string;
}

export interface LocalizedBreakdownSection {
  title: LocalizedPair;
  paragraphs?: LocalizedPair[];
  bullets?: LocalizedPair[];
  numbered?: LocalizedPair[];
}

interface DemandMetrics {
  keyword?: string;
  avg?: number;
  peak?: number;
  slope?: number;
  relative?: number;
  communitySignals?: number;
}

function pair(en: string, zh: string): LocalizedPair {
  return { en, zh };
}

export function getLocalizedPairText(value: LocalizedPair, lang: Lang): string {
  return lang === 'zh' ? value.zh : value.en;
}

function sourceLabel(source: string): LocalizedPair {
  const normalized = source.trim().toLowerCase();
  const labels: Record<string, LocalizedPair> = {
    github: pair('GitHub', 'GitHub'),
    hackernews: pair('Hacker News', 'Hacker News'),
    hn: pair('Hacker News', 'Hacker News'),
    reddit: pair('Reddit', 'Reddit'),
    producthunt: pair('Product Hunt', 'Product Hunt'),
  };

  return labels[normalized] ?? pair(source || 'Source', source || '来源');
}

function parseSignalBullet(bullet: string): { source: string; title: string; strength?: number } | null {
  const normalized = bullet.trim();
  const richMatch = normalized.match(/^\*\*\[(.+?)\]\*\*\s+(.+?)(?:（信号强度\s*([\d.]+)）|\(Signal strength\s*([\d.]+)\))?$/i);
  if (richMatch) {
    const strengthValue = richMatch[3] ?? richMatch[4];
    return {
      source: richMatch[1].trim(),
      title: richMatch[2].trim(),
      strength: strengthValue ? Number(strengthValue) : undefined,
    };
  }

  const plainMatch = normalized.match(/^\[(.+?)\]\s+(.+)$/);
  if (plainMatch) {
    return {
      source: plainMatch[1].trim(),
      title: plainMatch[2].trim(),
    };
  }

  return normalized ? { source: 'source', title: normalized } : null;
}

function extractDemandMetrics(section?: IdeaSection): DemandMetrics {
  const body = section?.body ?? '';
  const keyword = body.match(/`([^`]+)`/)?.[1]?.trim();
  const avg = Number(body.match(/搜索热度均值约\s*\*\*([\d.]+)\*\*/)?.[1] ?? body.match(/averaged?\s*\*\*([\d.]+)\*\*/i)?.[1] ?? '');
  const peak = Number(body.match(/历史峰值(?:达到)?\s*\*\*([\d.]+)\*\*/)?.[1] ?? body.match(/peak(?:ed)?(?: at)?\s*\*\*([\d.]+)\*\*/i)?.[1] ?? '');
  const slope = Number(body.match(/斜率\s*([+-]?[\d.]+)/)?.[1] ?? body.match(/slope\s*([+-]?[\d.]+)/i)?.[1] ?? '');
  const relative = Number(body.match(/相对基准搜索量为\s*\*\*([\d.]+)x\*\*/)?.[1] ?? body.match(/relative.*?\*\*([\d.]+)x\*\*/i)?.[1] ?? '');
  const communitySignals = Number(body.match(/共捕获到\s*\*\*(\d+)\s*条\*\*/)?.[1] ?? body.match(/captured\s*\*\*(\d+)\*\*\s*community/i)?.[1] ?? '');

  return {
    keyword,
    avg: Number.isFinite(avg) && avg > 0 ? avg : undefined,
    peak: Number.isFinite(peak) && peak > 0 ? peak : undefined,
    slope: Number.isFinite(slope) ? slope : undefined,
    relative: Number.isFinite(relative) && relative > 0 ? relative : undefined,
    communitySignals: Number.isFinite(communitySignals) && communitySignals > 0 ? communitySignals : undefined,
  };
}

function gradeLabel(grade: string | undefined): LocalizedPair {
  switch (grade) {
    case 'worth_it':
      return pair('Worth prioritising', '值得优先推进');
    case 'skip':
      return pair('Low priority / likely skip', '优先级低，倾向跳过');
    default:
      return pair('Watch and validate', '继续观察并验证');
  }
}

function trendDirectionLabel(slope: number | undefined): LocalizedPair {
  if (typeof slope !== 'number') {
    return pair('Direction unclear', '方向待确认');
  }
  if (slope > 0.3) {
    return pair('Demand is climbing', '需求在上升');
  }
  if (slope < -0.2) {
    return pair('Demand is cooling', '需求在回落');
  }
  return pair('Demand is roughly flat', '需求基本横盘');
}

export function buildSourceSignalCards(demandSection: IdeaSection | undefined, evidenceLinks: Array<{ url?: string; title?: string; source?: string }> = []): SourceSignalCard[] {
  const parsedSignals = (demandSection?.bullets ?? [])
    .map((bullet) => parseSignalBullet(bullet))
    .filter((item): item is NonNullable<typeof item> => Boolean(item));

  const cardsFromEvidence = evidenceLinks.map((link) => {
    const matchedSignal = parsedSignals.find((item) => item.title === (link.title ?? '').trim());
    const source = sourceLabel(link.source ?? matchedSignal?.source ?? 'source');
    const strength = matchedSignal?.strength;
    return {
      title: pair(link.title ?? matchedSignal?.title ?? 'Untitled source', link.title ?? matchedSignal?.title ?? '未命名来源'),
      source,
      meta: typeof strength === 'number'
        ? pair(`Signal strength ${strength.toFixed(1)}`, `信号强度 ${strength.toFixed(1)}`)
        : pair('Evidence link', '证据链接'),
      url: link.url,
    };
  });

  if (cardsFromEvidence.length > 0) {
    return cardsFromEvidence.slice(0, 3);
  }

  return parsedSignals.slice(0, 3).map((item) => ({
    title: pair(item.title, item.title),
    source: sourceLabel(item.source),
    meta: typeof item.strength === 'number'
      ? pair(`Signal strength ${item.strength.toFixed(1)}`, `信号强度 ${item.strength.toFixed(1)}`)
      : pair('Source signal', '来源信号'),
  }));
}

export function buildLocalizedWhyNow(frontmatter: Record<string, any>, demandSection: IdeaSection | undefined): LocalizedPair[] {
  const metrics = extractDemandMetrics(demandSection);
  const evidenceCount = Array.isArray(frontmatter.evidenceLinks) ? frontmatter.evidenceLinks.length : 0;
  const bestWedgeEn = getLocalizedTextStrict(frontmatter.bestWedge, 'en', 'bestWedge');
  const bestWedgeZh = getLocalizedTextStrict(frontmatter.bestWedge, 'zh', 'bestWedge');
  const cards: LocalizedPair[] = [];

  if (metrics.communitySignals || evidenceCount) {
    const count = metrics.communitySignals ?? evidenceCount;
    cards.push(pair(
      `${count} public demand signals already exist. Read them before building — that is free user research you do not need to fake.`,
      `社区里的 ${count} 条公开信号已经足够说明有人在找方案。先把这些样本读完，这就是最便宜的用户研究。`
    ));
  }

  if (typeof metrics.avg === 'number') {
    const direction = trendDirectionLabel(metrics.slope);
    const peakTextEn = typeof metrics.peak === 'number' ? `, with a peak of ${metrics.peak}` : '';
    const peakTextZh = typeof metrics.peak === 'number' ? `，峰值到 ${metrics.peak}` : '';
    cards.push(pair(
      `Search demand averages ${metrics.avg}${peakTextEn}. ${direction.en} — not breakout traffic, but enough to support a focused wedge.`,
      `搜索热度均值约 ${metrics.avg}${peakTextZh}。${direction.zh}——不是大众流量词，但足够支撑一个聚焦切口。`
    ));
  }

  if (frontmatter.sourceScore) {
    const label = gradeLabel(frontmatter.sourceGrade);
    cards.push(pair(
      `This opportunity scores ${Number(frontmatter.sourceScore).toFixed(1)} / 100. Current call: ${label.en}.`,
      `这个方向当前评分 ${Number(frontmatter.sourceScore).toFixed(1)} / 100。当前判断：${label.zh}。`
    ));
  }

  cards.push(pair(
    `Best entry angle: ${bestWedgeEn}. Do that first instead of shipping a broad product.`,
    `当前最稳的切入角度是：${bestWedgeZh}。先把这个点做透，不要一上来铺成通用产品。`
  ));

  return cards.slice(0, 4);
}

export function buildLocalizedDemandOverview(frontmatter: Record<string, any>, demandSection: IdeaSection | undefined): LocalizedPair[] {
  const metrics = extractDemandMetrics(demandSection);
  const keyword = frontmatter.sourceKeyword ?? metrics.keyword ?? getLocalizedTextStrict(frontmatter.title, 'en', 'title');
  const evidenceCount = Array.isArray(frontmatter.evidenceLinks) ? frontmatter.evidenceLinks.length : 0;
  const overview: LocalizedPair[] = [];

  if (typeof metrics.avg === 'number') {
    const direction = trendDirectionLabel(metrics.slope);
    const peakTextEn = typeof metrics.peak === 'number' ? `, with a peak of ${metrics.peak}` : '';
    const peakTextZh = typeof metrics.peak === 'number' ? `，峰值到 ${metrics.peak}` : '';
    const relativeTextEn = typeof metrics.relative === 'number' ? ` Relative scale vs the baseline term: ${metrics.relative.toFixed(2)}x.` : '';
    const relativeTextZh = typeof metrics.relative === 'number' ? ` 相对基准词规模约 ${metrics.relative.toFixed(2)}x。` : '';
    overview.push(pair(
      `Over the latest window, \`${keyword}\` averages ${metrics.avg}${peakTextEn}. ${direction.en}.${relativeTextEn}`,
      `最近一个窗口里，\`${keyword}\` 的搜索热度均值约 ${metrics.avg}${peakTextZh}。${direction.zh}。${relativeTextZh}`
    ));
  }

  const communityCount = metrics.communitySignals ?? evidenceCount;
  if (communityCount > 0) {
    overview.push(pair(
      `We found ${communityCount} community signals around this workflow. That is enough to confirm the problem is real, even if the market is still niche.`,
      `这个工作流至少能看到 ${communityCount} 条社区信号，已经足够证明问题真实存在，只是市场仍偏细分。`
    ));
  }

  if (frontmatter.sourceScore) {
    const label = gradeLabel(frontmatter.sourceGrade);
    overview.push(pair(
      `Overall score: ${Number(frontmatter.sourceScore).toFixed(1)} / 100. Current call: ${label.en}.`,
      `综合评分：${Number(frontmatter.sourceScore).toFixed(1)} / 100。当前判断：${label.zh}。`
    ));
  }

  return overview;
}

export function buildLocalizedCompetitionOverview(frontmatter: Record<string, any>): LocalizedPair[] {
  const bestWedgeEn = getLocalizedTextStrict(frontmatter.bestWedge, 'en', 'bestWedge');
  const bestWedgeZh = getLocalizedTextStrict(frontmatter.bestWedge, 'zh', 'bestWedge');
  const competitorGaps = (frontmatter.competitorGaps ?? []).slice(0, 2);
  const verdict = frontmatter.verdict ?? 'Watch';
  const confidence = frontmatter.confidence ?? 'Medium';

  // 用本地化标签，避免英文枚举值出现在中文段落里
  const verdictLabelMap: Record<string, { en: string; zh: string }> = {
    'Worth Building': { en: 'Worth Building', zh: '值得做' },
    'Watch': { en: 'Watch', zh: '继续观察' },
    'Skip': { en: 'Skip', zh: '先跳过' },
  };
  const confidenceLabelMap: Record<string, { en: string; zh: string }> = {
    'High': { en: 'High', zh: '高' },
    'Medium': { en: 'Medium', zh: '中' },
    'Low': { en: 'Low', zh: '低' },
  };
  const verdictLabel = verdictLabelMap[verdict] ?? { en: verdict, zh: verdict };
  const confidenceLabel = confidenceLabelMap[confidence] ?? { en: confidence, zh: confidence };

  const overview = [pair(
    `Current verdict: ${verdictLabel.en}. Confidence: ${confidenceLabel.en}. This is not a green light to build a broad product — it is a signal that a narrow wedge may work.`,
    `当前结论：${verdictLabel.zh}。数据置信度：${confidenceLabel.zh}。这不代表适合直接做大而全产品，只代表存在一个更窄切角可以先试。`
  ), pair(
    `Best wedge right now: ${bestWedgeEn}.`,
    `当前最该先打的切角：${bestWedgeZh}。`
  )];

  competitorGaps.forEach((gap: LocalizedText, index: number) => {
    overview.push(pair(
      `Competitor gap: ${getLocalizedTextStrict(gap, 'en', `competitorGaps[${index}]`)}`,
      `竞品缺口：${getLocalizedTextStrict(gap, 'zh', `competitorGaps[${index}]`)}`
    ));
  });

  return overview.slice(0, 4);
}

export function buildLocalizedMonetizationItems(category: string): LocalizedPair[] {
  const byCategory: Record<string, LocalizedPair[]> = {
    '文档处理': [
      pair('Free tier: enough daily usage to prove quality before asking for money.', '免费层：先给足够次数，让用户确认效果再谈付费。'),
      pair('Subscription: sell batch processing, higher limits, and priority speed.', '订阅：把批量处理、更高额度和优先速度做成付费层。'),
      pair('One-off credits: useful for low-frequency users who refuse subscriptions.', '按次点数包：适合低频但有真实需求、又不想订阅的人群。'),
    ],
    '视频处理': [
      pair('Free tier: limit render length or queue priority to control compute cost.', '免费层：限制处理时长或队列优先级，先把计算成本卡住。'),
      pair('Subscription: sell faster exports, higher limits, and better output quality.', '订阅：卖更快导出、更高额度和更稳定的结果质量。'),
      pair('Usage-based pricing: heavy users pay by render minute or credits.', '按量计费：重度用户按渲染分钟数或点数包付费。'),
    ],
    'AI 工具': [
      pair('Free tier: let users experience one high-value result first.', '免费层：先让用户跑出一次真正有价值的结果。'),
      pair('Subscription: charge for higher limits, better models, and faster turnaround.', '订阅：把更高额度、更好的模型和更快结果放进付费层。'),
      pair('Credits: serve users who want output without a recurring commitment.', '点数包：服务那些有需求但不想长期订阅的用户。'),
    ],
  };

  return byCategory[category] ?? [
    pair('Free tier first, then charge for volume, speed, or convenience.', '先免费获客，再把额度、速度或便利性做成付费点。'),
    pair('Subscription for repeat users who need the tool every week.', '订阅卖给高频复用、每周都要用的人。'),
    pair('One-off purchase or credits for low-frequency users.', '买断或点数包卖给低频用户。'),
  ];
}

export function buildLocalizedExecutionSteps(sourceKeyword: string, difficulty: string): LocalizedPair[] {
  if (difficulty === 'Hard') {
    return [
      pair(`Week 1: ship one narrow ${sourceKeyword} workflow end to end.`, `第 1 周：只打通 ${sourceKeyword} 最核心的一个输入到输出流程。`),
      pair('Week 2: harden reliability, edge cases, and user-facing error handling.', '第 2 周：把稳定性、边界情况和错误提示补到可演示水平。'),
      pair('Week 3: add payment, limits, and a tiny closed beta.', '第 3 周：接支付、配额度、做一个小范围内测。'),
    ];
  }

  return [
    pair(`Week 1: build the smallest usable version of ${sourceKeyword}.`, `第 1 周：做出 ${sourceKeyword} 的最小可用版本。`),
    pair('Week 2: polish the result page and add a basic payment wall.', '第 2 周：补结果页体验，并加上基础付费门槛。'),
    pair('Week 3: launch, distribute, and measure real conversion.', '第 3 周：上线分发，拿真实转化数据做判断。'),
  ];
}

export function buildLocalizedFullBreakdown(frontmatter: Record<string, any>, demandSection: IdeaSection | undefined, keywordItems: string[]): LocalizedBreakdownSection[] {
  const sourceKeyword = frontmatter.sourceKeyword ?? getLocalizedTextStrict(frontmatter.title, 'en', 'title').toLowerCase();
  const difficulty = frontmatter.difficulty ?? 'Medium';

  // Technical implementation details - unique to deep dive
  const technicalDetails: LocalizedPair[] = [];
  if (frontmatter.category === 'AI 工具') {
    technicalDetails.push(
      pair('Use existing APIs (OpenAI, Anthropic, Replicate) to avoid training costs.', '使用现有 API（OpenAI、Anthropic、Replicate），避免训练成本。'),
      pair('Focus on prompt engineering and output formatting rather than model building.', '重点放在提示词工程和输出格式化，而非模型训练。'),
      pair('Consider rate limiting and caching to manage API costs.', '考虑限流和缓存策略来控制 API 成本。')
    );
  } else {
    technicalDetails.push(
      pair('Start with a simple web app (Next.js, Astro, or vanilla HTML/JS).', '从简单 Web 应用开始（Next.js、Astro 或原生 HTML/JS）。'),
      pair('Use serverless functions for backend logic to avoid infrastructure overhead.', '使用 Serverless 函数处理后端逻辑，避免基础设施开销。'),
      pair('Prioritize mobile responsiveness — many users will access via phone.', '优先保证移动端体验——很多用户会用手机访问。')
    );
  }

  // User research insights - unique to deep dive
  const userInsights: LocalizedPair[] = [
    pair(
      `Based on community analysis, users searching for "${sourceKeyword}" typically fall into three groups: (1) complete beginners wanting templates, (2) professionals seeking efficiency gains, and (3) hobbyists exploring possibilities.`,
      `根据社区分析，搜索"${sourceKeyword}"的用户通常分为三类：(1)想要模板的纯新手，(2)寻求效率提升的专业人士，(3)探索可能性的爱好者。`
    ),
    pair(
      'The biggest frustration mentioned across forums is "too many options, no clear starting point." Your product should guide users through a specific workflow rather than offering everything.',
      '论坛中最常提到的痛点是"选择太多，没有明确起点"。你的产品应该引导用户完成特定工作流，而不是提供所有功能。'
    )
  ];

  // Validation strategy - unique to deep dive
  const validationStrategy: LocalizedPair[] = [
    pair(
      `Before building, validate with a simple landing page describing your ${sourceKeyword} solution. Drive $50-100 in ads to test conversion. If <2% sign up, refine the messaging or pivot.`,
      `在开发前，先用一个简单的落地页描述你的 ${sourceKeyword} 解决方案。投入 $50-100 广告费测试转化。如果注册率<2%，调整文案或转向。`
    ),
    pair(
      difficulty === 'Easy' 
        ? 'Build a working prototype in 3-5 days and share with 5 potential users. Their feedback will be more valuable than any market research.'
        : 'Break the project into 2-week milestones. Validate each milestone with real users before proceeding.',
      difficulty === 'Easy'
        ? '用 3-5 天做一个可用原型，分享给 5 个潜在用户。他们的反馈比任何市场调研都更有价值。'
        : '把项目拆成 2 周一个里程碑。每个里程碑都用真实用户验证后再继续。'
    )
  ];

  return [
    {
      title: pair('Technical Implementation', '技术实现'),
      bullets: technicalDetails,
    },
    {
      title: pair('User Research Insights', '用户调研洞察'),
      paragraphs: userInsights,
    },
    {
      title: pair('Validation Strategy', '验证策略'),
      numbered: validationStrategy,
    },
  ].filter((section) => (section.paragraphs?.length ?? 0) > 0 || (section.bullets?.length ?? 0) > 0 || (section.numbered?.length ?? 0) > 0);
}
