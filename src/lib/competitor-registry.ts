/**
 * 竞品 Registry 动态加载模块
 *
 * 支持：
 * 1. 从 src/data/competitors/ 加载独立数据源
 * 2. 降级到 frontmatter 内嵌数据（兼容旧格式）
 */
import type { CompetitorProfile } from './competitor';

const COMPETITOR_DATA_BASE = '/data/competitors/';

/**
 * 将域名转换为安全的文件名
 * 例如: boomy.com -> boomy_com.json
 */
function domainToFilename(domain: string): string {
  return domain.replace(/\./g, '_') + '.json';
}

/**
 * 从独立数据源加载竞品数据
 */
export async function loadCompetitorFromRegistry(domain: string): Promise<CompetitorProfile | null> {
  try {
    const filename = domainToFilename(domain);
    const url = `${COMPETITOR_DATA_BASE}${filename}`;
    const response = await fetch(url);

    if (!response.ok) {
      console.warn(`[CompetitorRegistry] Failed to load ${domain}: ${response.status}`);
      return null;
    }

    const data = await response.json();

    // 转换数据格式以匹配 CompetitorProfile
    return {
      domain: data.domain,
      name: data.name,
      keyFeatures: data.keyFeatures || [],
      pricingTiers: data.pricingTiers || [],
      weaknesses: data.weaknesses || [],
      // 额外字段（用于元数据展示）
      _meta: {
        targetAudience: data.targetAudience,
        positioning: data.positioning,
        lastChecked: data.lastChecked,
        dataStatus: data.dataStatus || 'unknown',
        dataSources: data.dataSources,
      }
    } as CompetitorProfile & { _meta: CompetitorProfileMeta };
  } catch (error) {
    console.warn(`[CompetitorRegistry] Error loading ${domain}:`, error);
    return null;
  }
}

/**
 * 元数据结构
 */
interface CompetitorProfileMeta {
  targetAudience?: { en: string; zh: string };
  positioning?: { en: string; zh: string };
  lastChecked?: string;
  dataStatus?: 'fresh' | 'stale' | 'failed' | 'unknown';
  dataSources?: {
    landingPage?: string;
    pricingPage?: string;
    llmModel?: string;
  };
}

/**
 * 竞品数据加载结果
 */
export interface CompetitorLoadResult {
  competitor: CompetitorProfile;
  source: 'registry' | 'fallback';
  dataStatus: 'fresh' | 'stale' | 'failed' | 'unknown';
  lastChecked?: string;
}

/**
 * 加载多个竞品的最新数据
 *
 * @param domains 域名列表
 * @param fallbackData 降级数据（frontmatter 中的内嵌数据）
 * @returns 按域名分组的加载结果
 */
export async function getCompetitorRegistry(
  domains: string[],
  fallbackData?: Record<string, CompetitorProfile>
): Promise<Map<string, CompetitorLoadResult>> {
  const results = new Map<string, CompetitorLoadResult>();

  if (!domains || domains.length === 0) {
    return results;
  }

  // 并行加载所有竞品
  const loadPromises = domains.map(async (domain) => {
    // 1. 优先从 Registry 加载
    const registryData = await loadCompetitorFromRegistry(domain);

    if (registryData) {
      const meta = (registryData as any)._meta || {};
      results.set(domain, {
        competitor: registryData,
        source: 'registry',
        dataStatus: meta.dataStatus || 'unknown',
        lastChecked: meta.lastChecked,
      });
      return { domain, success: true };
    }

    // 2. 降级到 frontmatter 数据
    if (fallbackData && fallbackData[domain]) {
      results.set(domain, {
        competitor: fallbackData[domain],
        source: 'fallback',
        dataStatus: 'unknown',
      });
      return { domain, success: true, usedFallback: true };
    }

    console.warn(`[CompetitorRegistry] No data found for ${domain}`);
    return { domain, success: false };
  });

  await Promise.all(loadPromises);

  return results;
}

/**
 * 获取竞品元数据（用于展示数据新鲜度）
 */
export async function getCompetitorMetadata(
  domains: string[]
): Promise<Map<string, { lastChecked?: string; dataStatus?: string }>> {
  const metadata = new Map<string, { lastChecked?: string; dataStatus?: string }>();

  for (const domain of domains) {
    const data = await loadCompetitorFromRegistry(domain);
    if (data) {
      const meta = (data as any)._meta || {};
      metadata.set(domain, {
        lastChecked: meta.lastChecked,
        dataStatus: meta.dataStatus,
      });
    }
  }

  return metadata;
}

/**
 * 检查竞品数据是否需要刷新
 */
export async function needsRefresh(domain: string, maxAgeHours: number = 24): Promise<boolean> {
  const data = await loadCompetitorFromRegistry(domain);
  if (!data) return true;

  const meta = (data as any)._meta || {};
  if (!meta.lastChecked || meta.dataStatus === 'failed') {
    return true;
  }

  const lastChecked = new Date(meta.lastChecked);
  const now = new Date();
  const hoursDiff = (now.getTime() - lastChecked.getTime()) / (1000 * 60 * 60);

  return hoursDiff > maxAgeHours;
}

/**
 * 从 frontmatter 提取降级用的竞品数据映射
 */
export function extractFallbackCompetitors(frontmatter: Record<string, any>): Record<string, CompetitorProfile> {
  const competitors: Record<string, CompetitorProfile> = {};

  const analysis = frontmatter.competitorAnalysis;
  if (!analysis || !analysis.topCompetitors) {
    return competitors;
  }

  for (const comp of analysis.topCompetitors) {
    if (comp.domain) {
      competitors[comp.domain] = {
        domain: comp.domain,
        name: comp.name,
        keyFeatures: comp.keyFeatures || [],
        pricingTiers: comp.pricingTiers || [],
        weaknesses: comp.weaknesses || [],
      };
    }
  }

  return competitors;
}

/**
 * 获取所有已注册的竞品域名
 */
export async function getAllRegisteredDomains(): Promise<string[]> {
  // 硬编码已知域名列表（可扩展为从目录读取）
  return [
    'aiva.ai',
    'boomy.com',
    'humbot.ai',
    'kickresume.com',
    'remini.ai',
    'restorephotos.io',
    'resumeworded.com',
    'runwayml.com',
    'soundraw.io',
    'suno.ai',
    'tealhq.com',
    'undetectable.ai',
  ];
}
