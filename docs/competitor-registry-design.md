# 竞品数据独立数据源 & 增强自动化方案

> **文档状态**：部分已实现（2026-04-12 更新）
>
> ✅ 已实现：竞品 Registry 存储（54个 profiles）、竞品爬取自动化（`competitor-crawl.yml`）、`trigger_competitor_crawl()` 入队链路、`extract_community_pains` 和 `extract_competitor_gaps` 模块。
>
> ⏳ 未实现：前端 `src/data/competitors/` 动态加载、painClusters 新格式（`source`/`evidence`）落地、`PainClusterItem` 前端组件。

## 目标

1. **竞品数据独立存储**：从 Markdown frontmatter 分离，支持独立更新
2. **竞品发现自动化**：SERP 发现新域名后自动触发爬取
3. **数据热更新**：更新竞品数据后无需重新生成文章

---

## 一、整体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Discovery Pipeline                            │
│  run_pipeline.py                                                        │
│    ├── step1_trend_discovery     → 趋势关键词                            │
│    ├── step2_community_scan      → 社区信号                               │
│    └── step3_serp_analysis      → SERP 竞品域名                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Competitor Profiles (已实现 ✅)                        │
│  pipeline/competitor_analysis/cache/competitor_profiles/                  │
│    └── {domain}.json          ← 竞品数据存储（54个 profiles）             │
│                                                                         
│  字段：                                                                 │
│    - domain: 域名                                                         │
│    - name: 双语名称                                                      │
│    - pricingTiers: 定价方案                                              │
│    - keyFeatures: 核心功能                                               │
│    - weaknesses: 弱点                                                    │
│    - lastChecked: 上次爬取时间                                           │
│    - dataStatus: fresh | stale | failed                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              Publishing Pipeline (已实现 ✅)                              │
│  generate_idea.py                                                        │
│    ├── 调用 extract_community_pains.py 提取社区痛点                       │
│    ├── 调用 extract_competitor_gaps.py 提取竞品弱点                       │
│    └── frontmatter 仍内嵌 topCompetitors（待分离为引用）                  │
│                                                                         
│  改动：competitorAnalysis 变为引用而非嵌入                               │
│    competitorAnalysis:                                                  │
│      domains: [suno.ai, boomy.com, ...]  ← 只存域名                     │
│      _registry: true                  ← 标记使用独立数据源               │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      Frontend Components                                 │
│  CompetitorAnalysisSection.astro                                         │
│    ├── 读取 frontmatter.domains                                         │
│    ├── 动态加载 src/data/competitors/{domain}.json                      │
│    └── 渲染时直接读取最新数据                                            │
│                                                                         
│  优势：刷新页面即可看到最新竞品数据，无需重新构建                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 二、核心改动

### 2.0 痛点聚类与市场空白区分优化

> **状态**：模块已实现（`extract_community_pains.py`、`extract_competitor_gaps.py`），但前端渲染尚未切换为新格式。painClusters 仍输出 `{en, zh}` 结构，新格式（`source`/`evidence`）待前端组件适配后落地。

**现状问题**：
```
painClusters 和 competitorGaps 高度重复
     │
     ├─ painClusters: 【竞品名】+ weakness（带前缀）
     │
     └─ competitorGaps: weakness（不带前缀）
     
本质：两者都是从 competitor.weaknesses 提取的同一数据
```

**优化后数据来源区分**：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         痛点聚类 (painClusters)                          │
│                                                                         │
│  数据来源优先级：                                                       │
│  1️⃣ 社区真实讨论提取（新增独立来源）                                     │
│     └── LLM 分析 HN/Reddit 帖子，提取带引用的用户原话                    │
│                                                                         │
│  2️⃣ 竞品弱点推断                                                       │
│     └── 竞品 Registry 中的 weaknesses，标注来源竞品                       │
│                                                                         │
│  3️⃣ 关键词匹配回退                                                     │
│     └── 基于标题关键词的规则匹配（现有逻辑）                              │
│                                                                         │
│  格式：                                                                 │
│  {                                                                   │
│    source: "community" | "competitor" | "keyword",                    │
│    sourceDomain: "boomy.com",  // 仅 competitor 类型                   │
│    evidence: [{ url, quote }],  // community 类型含引用                │
│    text: { en, zh }                                                   │
│  }                                                                   │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         市场空白 (competitorGaps)                        │
│                                                                         │
│  数据来源：                                                             │
│  纯粹从竞品 Registry 中的 weaknesses 提取                               │
│  不从社区讨论获取                                                       │
│                                                                         │
│  格式：                                                                 │
│  {                                                                   │
│    domain: "boomy.com",           // 来源竞品                          │
│    text: { en, zh }                                                   │
│  }                                                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

**LLM 社区痛点提取示例**：

```python
# 新增函数：extract_pain_from_community
def extract_pain_from_community(community_items: list[dict]) -> list[dict]:
    """
    从社区讨论中提取真实用户痛点
    
    输入：HN/Reddit 帖子列表
    输出：带引用的痛点列表
    
    格式：
    {
        "text": {"en": "...", "zh": "..."},
        "source": "community",
        "evidence": [
            {
                "url": "https://news.ycombinator.com/...",
                "quote": {"en": "原话引用", "zh": "原话引用"}
            }
        ]
    }
    """
```

---

### 2.1 竞品数据 Registry

**新目录**：`src/data/competitors/`

**文件结构**（每个竞品一个 JSON）：

```json
{
  "domain": "suno.ai",
  "name": {
    "en": "Suno",
    "zh": "Suno"
  },
  "pricingTiers": [
    {
      "name": {"en": "Free", "zh": "免费版"},
      "price": 0,
      "description": {
        "en": "50 credits/month, personal use only",
        "zh": "每月50积分，仅限个人使用"
      },
      "limits": {
        "monthlyCredits": {"en": "50", "zh": "50"},
        "commercialUse": {"en": "Not allowed", "zh": "不允许"}
      }
    },
    {
      "name": {"en": "Pro", "zh": "专业版"},
      "price": 10,
      "description": {
        "en": "Unlimited credits, commercial use",
        "zh": "无限积分，商用授权"
      },
      "limits": {
        "monthlyCredits": {"en": "Unlimited", "zh": "无限"},
        "commercialUse": {"en": "Allowed", "zh": "允许"}
      }
    }
  ],
  "keyFeatures": [
    {"en": "AI music generation from text", "zh": "文本生成音乐"},
    {"en": "Various music styles", "zh": "多种音乐风格"},
    {"en": "Remix and extend tracks", "zh": "混音和扩展音轨"}
  ],
  "weaknesses": [
    {"en": "Long generation times (5-10 minutes)", "zh": "生成时间长（5-10分钟）"},
    {"en": "Limited control over output", "zh": "对输出控制有限"},
    {"en": "Credit system can be expensive", "zh": "积分系统可能较贵"}
  ],
  "targetAudience": {
    "en": "Content creators, musicians, marketers",
    "zh": "内容创作者、音乐人、营销人员"
  },
  "positioning": {
    "en": "Consumer AI music creation platform",
    "zh": "消费级AI音乐创作平台"
  },
  "lastChecked": "2026-04-08T12:00:00Z",
  "dataStatus": "fresh",
  "dataSources": {
    "landingPage": "https://suno.ai/",
    "pricingPage": "https://suno.ai/pricing",
    "llmModel": "siliconflow-qwen-plus"
  }
}
```

### 2.2 frontmatter 简化与 painClusters 格式升级

**现状**（full embedded）：
```yaml
competitorAnalysis:
  topCompetitors:
    - domain: suno.ai
      name: {en: "Suno", zh: "Suno"}
      pricingTiers: [...]
      keyFeatures: [...]
      weaknesses: [...]

painClusters:
  - en: "【Boomy】Limited control over..."
    zh: "【Boomy】对AI生成的音乐质量..."

competitorGaps:
  - en: "Limited control over..."
    zh: "对AI生成的音乐质量..."
```

**改动后**（分离 + 增强格式）：

```yaml
# frontmatter 只存储引用和元数据
competitorAnalysis:
  domains:
    - suno.ai
    - boomy.com
    - soundraw.io
  _registry: true
  _version: 2

# painClusters 增强格式 - 区分来源
painClusters:
  # 来源 1: 社区真实讨论（带引用）
  - source: community
    text:
      en: "Soundraw outputs sound same-y after a while"
      zh: "Soundraw 听久了感觉千篇一律"
    evidence:
      - url: "https://news.ycombinator.com/item?id=xxx"
        source: hackernews
        quote:
          en: "Using Soundraw for a month, all tracks sound the same"
          zh: "用了 Soundraw 一个月，所有曲目听起来都一样"
  
  # 来源 2: 竞品弱点推断
  - source: competitor
    sourceDomain: boomy.com
    text:
      en: "Limited control over AI-generated music quality"
      zh: "对AI生成的音乐质量控制有限"
  
  # 来源 3: 关键词匹配（回退）
  - source: keyword
    text:
      en: "Speed & performance issues"
      zh: "速度和性能问题"

# competitorGaps - 纯粹从竞品弱点提取
competitorGaps:
  - domain: boomy.com
    text:
      en: "Limited control over AI-generated music quality"
      zh: "对AI生成的音乐质量控制有限"
  - domain: soundraw.io
    text:
      en: "Potential lack of originality in AI-generated tracks"
      zh: "AI生成的曲目可能缺乏原创性"
```

### 2.3 前端动态加载

**CompetitorAnalysisSection.astro** 改动：

```astro
---
// 改为动态加载竞品数据
import { getCompetitorRegistry } from '../lib/competitor-registry';

const { analysis, lang } = Astro.props;

// 获取域名列表
const domains = analysis.domains || [];

// 动态加载每个竞品的最新数据
const competitors = await getCompetitorRegistry(domains);
---

{/* 渲染竞品卡片，使用最新加载的数据 */}
{competitors.map(comp => (
  <CompetitorCard competitor={comp} lang={lang} />
))}
```

### 2.4 PainClusters 组件增强

**新增 PainClusterItem.astro**：

```astro
---
interface Props {
  cluster: {
    source: "community" | "competitor" | "keyword";
    sourceDomain?: string;  // 仅 competitor 类型
    text: { en: string; zh: string };
    evidence?: Array<{     // 仅 community 类型
      url: string;
      source: string;
      quote: { en: string; zh: string };
    }>;
  };
  lang: "en" | "zh";
}

const { cluster, lang } = Astro.props;
const text = cluster.text[lang];
---

<div class="pain-cluster">
  {cluster.source === "community" && cluster.evidence && (
    <div class="evidence-quote">
      <!-- 显示引用来源和原话 -->
      {cluster.evidence.map(e => (
        <cite>
          <a href={e.url} target="_blank" rel="noopener">
            [{e.source}] "{e.quote[lang]}"
          </a>
        </cite>
      ))}
    </div>
  )}
  
  {cluster.source === "competitor" && cluster.sourceDomain && (
    <span class="source-tag">【{cluster.sourceDomain}】</span>
  )}
  
  <span class="pain-text">{text}</span>
</div>
```

**样式区分**：
- `community` 来源：带引用链接，带引号样式
- `competitor` 来源：带竞品域名标签
- `keyword` 来源：纯文本，无特殊标记

### 2.5 Competitor Registry 工具函数（增强版）

**src/lib/competitor-registry.ts**：

```typescript
import type { CompetitorProfile } from './competitor';

const COMPETITOR_DATA_DIR = '/src/data/competitors/';

/**
 * 加载竞品 Registry 数据
 * 支持：
 * 1. 从 src/data/competitors/ 加载（独立数据源）
 * 2. 降级到 frontmatter 内嵌数据（兼容旧格式）
 */
export async function getCompetitorRegistry(
  domains: string[],
  fallback?: CompetitorProfile[]  // frontmatter 内嵌数据
): Promise<CompetitorProfile[]> {
  if (!domains || domains.length === 0) {
    return fallback || [];
  }

  const competitors = await Promise.all(
    domains.map(async (domain) => {
      try {
        // 尝试从独立数据源加载
        const safeDomain = domain.replace(/\./g, '_');
        const response = await fetch(`${COMPETITOR_DATA_DIR}${safeDomain}.json`);
        if (response.ok) {
          return await response.json();
        }
      } catch (e) {
        // 静默失败，使用降级数据
      }
      return null;
    })
  );

  const loaded = competitors.filter(Boolean);
  
  // 如果独立数据源数据不足，使用降级数据补充
  if (loaded.length < domains.length && fallback) {
    const loadedDomains = new Set(loaded.map(c => c.domain));
    const fallback补充 = fallback
      .filter(c => !loadedDomains.has(c.domain))
      .slice(0, domains.length - loaded.length);
    return [...loaded, ...fallback补充];
  }

  return loaded;
}

/**
 * 加载竞品 Registry 元数据
 * 返回 dataStatus, lastChecked 等信息
 */
export async function getCompetitorMetadata(domains: string[]): Promise<Map<string, {
  lastChecked: string;
  dataStatus: "fresh" | "stale" | "failed";
}>> {
  const metadata = new Map();
  
  for (const domain of domains) {
    try {
      const safeDomain = domain.replace(/\./g, '_');
      const response = await fetch(`${COMPETITOR_DATA_DIR}${safeDomain}.json`);
      if (response.ok) {
        const data = await response.json();
        metadata.set(domain, {
          lastChecked: data.lastChecked,
          dataStatus: data.dataStatus || "unknown"
        });
      }
    } catch (e) {
      // ignore
    }
  }
  
  return metadata;
}
```
```

---

## 三、增强竞品发现自动化

### 3.1 自动发现 → 自动爬取流程

**改动 run_pipeline.py**：

```python
# 在 build_keyword_profiles 后添加
def trigger_competitor_crawl(ideas: list[dict], min_score: int = 20):
    """
    发现新域名后自动触发爬取
    
    1. 收集所有 SERP 域名
    2. 对比已有缓存，找出新增域名
    3. 触发异步爬取任务
    """
    # 收集所有域名
    all_domains = set()
    for idea in ideas:
        if idea.get('score', 0) >= min_score:
            all_domains.update(idea.get('serp_niche_sites', []))
            all_domains.update(idea.get('serp_big_sites', []))
    
    # 检查已有缓存
    existing = get_cached_domains()
    new_domains = all_domains - existing
    
    if new_domains:
        print(f"[竞品] 发现 {len(new_domains)} 个新域名，触发爬取...")
        for domain in new_domains:
            queue_competitor_crawl(domain)
```

### 3.2 社区痛点提取模块（新增）

**新增文件**：`pipeline/discovery/extract_community_pains.py`

```python
"""
从社区讨论中提取真实用户痛点

使用 LLM 分析 HN/Reddit 帖子，提取：
1. 用户抱怨的具体问题
2. 原话引用作为证据
3. 严重程度评估
"""
from dataclasses import dataclass
from typing import List, Optional
import json

@dataclass
class CommunityPain:
    """社区提取的痛点"""
    text_zh: str
    text_en: str
    severity: str  # high | medium | low
    source_url: str
    source_name: str  # hackernews | reddit
    quote_zh: str
    quote_en: str

COMMUNITY_PAIN_PROMPT = """Analyze the following community discussions about {keyword} and extract user pain points.

Extract ONLY genuine complaints and frustrations expressed by users. DO NOT extract:
- Feature requests
- Neutral observations
- Praise or positive comments

For each pain point found, provide:
1. The specific pain point in both English and Chinese
2. The severity (high/medium/low)
3. A direct quote from the discussion as evidence

Return as JSON:
{{
  "painPoints": [
    {{
      "pain_en": "Specific pain point in English",
      "pain_zh": "中文具体痛点",
      "severity": "high|medium|low",
      "quote_en": "Direct quote from discussion in English",
      "quote_zh": "中文引用（翻译）"
    }}
  ]
}}

Community Discussions:
{discussions}
"""

def extract_pain_from_community(community_items: List[dict], keyword: str) -> List[dict]:
    """
    从社区讨论中提取痛点
    
    Args:
        community_items: 社区帖子列表 [{title, url, source, ...}]
        keyword: 关键词
        
    Returns:
        [{text: {en, zh}, source: "community", evidence: [{url, quote}]}]
    """
    if not community_items:
        return []
    
    # 格式化讨论内容
    discussions_text = "\n\n".join([
        f"Source: {item.get('source', 'unknown')}\n"
        f"Title: {item.get('title', '')}\n"
        f"URL: {item.get('url', '')}\n"
        f"Content: {item.get('content', item.get('text', ''))[:500]}"
        for item in community_items[:10]  # 限制数量避免 token 溢出
    ])
    
    prompt = COMMUNITY_PAIN_PROMPT.format(
        keyword=keyword,
        discussions=discussions_text
    )
    
    # 调用 LLM
    result = call_llm(prompt)
    if not result:
        return []
    
    pains = []
    for item in result.get("painPoints", []):
        # 找到对应的原始帖子
        matching_item = next(
            (ci for ci in community_items if item.get("quote_en", "") in ci.get("content", "")),
            community_items[0] if community_items else {}
        )
        
        pains.append({
            "text": {
                "en": item.get("pain_en", ""),
                "zh": item.get("pain_zh", "")
            },
            "source": "community",
            "severity": item.get("severity", "medium"),
            "evidence": [{
                "url": matching_item.get("url", ""),
                "source": matching_item.get("source", "community"),
                "quote": {
                    "en": item.get("quote_en", ""),
                    "zh": item.get("quote_zh", "")
                }
            }]
        })
    
    return pains


def derive_pain_clusters_enhanced(
    idea: dict,
    competitor_data: dict,
    community_items: list[dict]
) -> list[dict]:
    """
    增强版痛点聚类生成
    
    数据来源优先级：
    1. 社区真实讨论提取（带引用）
    2. 竞品弱点推断
    3. 关键词匹配回退
    """
    pains = []
    seen_en = set()
    
    # 1. 社区真实讨论提取
    community_pains = extract_pain_from_community(community_items, idea.get("keyword", ""))
    for pain in community_pains:
        key = pain["text"]["en"].lower()
        if key and key not in seen_en and len(key) > 10:
            pains.append(pain)
            seen_en.add(key)
    
    # 2. 竞品弱点推断
    if competitor_data.get("has_data"):
        pain_hints = competitor_data.get("pain_hints", [])
        for hint in pain_hints[:3]:  # 限制数量
            key = hint.get("en", "").lower()
            if key and key not in seen_en and len(key) > 10:
                pains.append({
                    "text": {"en": hint.get("en", ""), "zh": hint.get("zh", "")},
                    "source": "competitor",
                    "sourceDomain": extract_domain_from_hint(hint)
                })
                seen_en.add(key)
    
    # 3. 关键词匹配回退（仅填充到 4 条）
    if len(pains) < 4:
        keyword_pains = derive_pain_clusters_keyword_fallback(idea)
        for pain in keyword_pains:
            if len(pains) >= 4:
                break
            key = pain["text"]["en"].lower()
            if key and key not in seen_en:
                pains.append({**pain, "source": "keyword"})
                seen_en.add(key)
    
    return pains[:4]
```

### 3.3 竞品弱点独立提取（增强 competitorGaps）

**新增函数**：`pipeline/publishing/extract_competitor_gaps.py`

```python
"""
竞品弱点独立提取模块

专门用于生成 competitorGaps，与 painClusters 完全分离：
- painClusters: 社区真实讨论 + 竞品弱点 + 关键词匹配
- competitorGaps: 纯粹从竞品 Registry 的 weaknesses 提取
"""

def extract_competitor_gaps(profiles: list[CompetitorProfile]) -> list[dict]:
    """
    从竞品 profiles 纯粹提取弱点作为 market gaps
    
    与 extract_competitor_weaknesses 的区别：
    - 保留来源域名信息
    - 不做去重（同一弱点不同竞品可重复）
    - 纯粹提取，不添加任何推断
    
    Returns:
        [{
            "domain": "boomy.com",
            "text": {"en": "...", "zh": "..."}
        }]
    """
    gaps = []
    
    for profile in profiles:
        domain = profile.domain
        for weakness in profile.weaknesses:
            gaps.append({
                "domain": domain,
                "text": {
                    "en": weakness.en,
                    "zh": weakness.zh
                }
            })
    
    return gaps
```

### 3.4 竞品爬取优先级队列

**新增文件**：`pipeline/competitor_analysis/queue.py`

```python
"""
竞品爬取任务队列
支持：
- 优先级队列（SERP 出现频率高的优先）
- 重试机制
- 失败告警
"""
from dataclasses import dataclass
from typing import Optional
import json
from pathlib import Path
from datetime import datetime

@dataclass
class CrawlTask:
    domain: str
    priority: int  # 1-10, 越高越优先
    source_keyword: str  # 发现该域名的关键词
    created_at: str
    retry_count: int = 0
    status: str = "pending"  # pending | running | done | failed

class CompetitorCrawlQueue:
    def __init__(self, queue_file: str = "data/competitor_crawl_queue.json"):
        self.queue_file = Path(queue_file)
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)
    
    def add(self, domain: str, priority: int = 5, source_keyword: str = ""):
        """添加爬取任务"""
        tasks = self._load()
        
        # 去重，已存在的提升优先级
        existing = next((t for t in tasks if t['domain'] == domain), None)
        if existing:
            existing['priority'] = max(existing['priority'], priority)
            existing['retry_count'] = 0
        else:
            tasks.append(CrawlTask(
                domain=domain,
                priority=priority,
                source_keyword=source_keyword,
                created_at=datetime.now().isoformat()
            ).__dict__)
        
        self._save(tasks)
    
    def get_next(self) -> Optional[CrawlTask]:
        """获取下一个待处理任务"""
        tasks = self._load()
        if not tasks:
            return None
        
        # 按优先级排序
        tasks.sort(key=lambda t: (-t['priority'], t['created_at']))
        
        task = tasks[0]
        task['status'] = 'running'
        self._save(tasks)
        
        return CrawlTask(**task)
    
    def complete(self, domain: str, success: bool = True):
        """标记任务完成"""
        tasks = self._load()
        for task in tasks:
            if task['domain'] == domain:
                if success:
                    tasks.remove(task)
                else:
                    task['retry_count'] += 1
                    task['status'] = 'pending' if task['retry_count'] < 3 else 'failed'
        self._save(tasks)
```

### 3.3 竞品发现权重计算

```python
def calculate_competitor_priority(domain: str, ideas: list[dict]) -> int:
    """
    计算竞品爬取优先级
    
    因素：
    1. SERP 出现次数（越多越重要）
    2. 相关 idea 的评分（高分 idea 中的竞品更重要）
    3. 距离上次爬取时间（越久越优先）
    """
    appearances = 0
    total_score = 0
    
    for idea in ideas:
        sites = idea.get('serp_niche_sites', []) + idea.get('serp_big_sites', [])
        if domain in sites:
            appearances += 1
            total_score += idea.get('score', 0)
    
    # 基础分：出现次数 × 10
    base = appearances * 10
    
    # 加权分：平均 idea 评分 × 5
    weighted = (total_score / appearances * 5) if appearances else 0
    
    # 上次爬取时间惩罚
    last_crawl = get_last_crawl_time(domain)
    if last_crawl:
        days_since = (datetime.now() - last_crawl).days
        time_bonus = min(days_since * 2, 20)  # 最多加20分
    else:
        time_bonus = 30  # 新发现的+30分
    
    return min(int(base + weighted + time_bonus), 100)
```

---

## 四、数据迁移计划

### 4.1 现有数据迁移

```python
def migrate_existing_competitor_data():
    """
    将现有 competitor_profiles 缓存迁移到 src/data/competitors/
    """
    source_dir = Path("pipeline/competitor_analysis/cache/competitor_profiles")
    target_dir = Path("src/data/competitors")
    
    for json_file in source_dir.glob("*.json"):
        data = json.load(json_file.open())
        
        # 转换格式
        target_data = {
            "domain": data.get("domain"),
            "name": data.get("name"),
            "pricingTiers": data.get("pricingTiers", []),
            "keyFeatures": data.get("keyFeatures", []),
            "weaknesses": data.get("weaknesses", []),
            "targetAudience": data.get("targetAudience"),
            "positioning": data.get("positioning"),
            "lastChecked": data.get("analyzedAt"),
            "dataStatus": "fresh"
        }
        
        # 写入目标位置
        target_file = target_dir / f"{data['domain']}.json"
        json.dump(target_data, target_file.open("w"), ensure_ascii=False, indent=2)
```

### 4.2 迁移脚本

```bash
#!/bin/bash
# scripts/migrate_competitor_registry.sh

echo "Migrating competitor data to registry..."

python3 -c "
from migrate_competitor_data import migrate_existing_competitor_data
migrate_existing_competitor_data()
"

echo "Migration complete!"
echo "Found $(ls src/data/competitors/*.json | wc -l) competitors"
```

---

## 五、实施步骤

### Phase 1: 基础设施（1天）

- [ ] 创建 `src/data/competitors/` 目录结构
- [ ] 迁移现有 12 个竞品数据到 registry
- [ ] 创建 `competitor-registry.ts` 工具函数（含降级逻辑）
- [ ] 更新 `getCompetitorRegistry()` 加载逻辑

### Phase 2: 前端改造（1天）

- [ ] 修改 `CompetitorAnalysisSection.astro` 使用动态加载
- [ ] 修改 `IdeaDetailPage.astro` frontmatter 解析
- [ ] 更新 frontmatter schema（`src/content/config.ts`）
- [ ] 测试双语渲染

### Phase 3: 痛点来源区分（1天）⚠️ 新增

- [x] 创建 `extract_community_pains.py` 社区痛点提取模块
- [x] 创建 `derive_pain_clusters_enhanced()` 增强函数
- [x] 创建 `extract_competitor_gaps()` 纯粹弱点提取函数
- [x] 修改 `generate_idea.py` 中的 `derive_pain_clusters()` 和 `derive_competitor_gaps()`
- [ ] 更新 frontmatter schema 支持新格式
- [ ] 前端组件适配新格式（`PainClusterItem`）

### Phase 4: 自动化增强（1天）✅ 已实现

- [x] 创建竞品爬取队列（`data/competitor_crawl_queue.json`）
- [x] 创建竞品爬取 workflow（`competitor-crawl.yml`）
- [x] 修改 `run_pipeline.py` 添加 `trigger_competitor_crawl()` 入队逻辑
- [x] `daily-publish.yml` 末尾追加竞品爬取 step
- [ ] 添加失败告警机制（已接入 webhook，UI 展示待做）

### Phase 5: 收尾（0.5天）

- [ ] 更新文档
- [ ] 运行迁移脚本
- [ ] 全量测试（检查 painClusters 来源区分）
- [ ] 部署

---

## 六、预期效果

| 指标 | 现状 | 改动后 |
|------|------|--------|
| 竞品数据更新延迟 | ~2min（需重建+部署） | ~0（刷新页面即可见） |
| 新竞品发现到入库 | 手动操作 | 自动发现后24h内 |
| 竞品数据覆盖率 | ~30%（只有手动爬取的） | ~80%（自动发现优先爬取） |
| 价格数据准确性 | 低（过期难以及时更新） | 高（独立源易更新） |
| **痛点来源区分** | painClusters 和 competitorGaps 混用 | 完全区分，可追溯 |
| **社区痛点证据** | 无原话引用 | 带 HN/Reddit 原话引用 |
| **竞品弱点纯度** | 与痛点混用 | 纯粹弱点，不含推断 |

---

## 七、文件清单

### 新增文件

| 文件 | 状态 | 作用 |
|------|------|------|
| `pipeline/competitor_analysis/cache/competitor_profiles/*.json` | ✅ 已实现 | 竞品数据存储（54个 profiles） |
| `pipeline/discovery/extract_community_pains.py` | ✅ 已实现 | 社区痛点提取模块（LLM 分析） |
| `pipeline/publishing/extract_competitor_gaps.py` | ✅ 已实现 | 竞品弱点独立提取模块 |
| `.github/workflows/competitor-crawl.yml` | ✅ 已实现 | 竞品爬取定时 workflow |
| `data/competitor_crawl_queue.json` | ✅ 已实现 | 竞品爬取任务队列 |
| `src/data/competitors/*.json` | ⏳ 待实现 | 前端动态加载（与 pipeline 合并前需迁移） |
| `src/lib/competitor-registry.ts` | ⏳ 待实现 | 竞品数据加载工具（含降级逻辑） |
| `src/components/PainClusterItem.astro` | ⏳ 待实现 | 痛点聚类项组件（支持 evidence 展示） |

### 修改文件

| 文件 | 状态 | 改动 |
|------|------|------|
| `pipeline/publishing/generate_idea.py` | ✅ 已实现 | 调用 extract_community_pains 和 extract_competitor_gaps |
| `.github/workflows/daily-publish.yml` | ✅ 已实现 | 追加竞品爬取 step |
| `src/views/IdeaDetailPage.astro` | ⏳ 待实现 | 使用动态加载 |
| `src/components/CompetitorAnalysisSection.astro` | ⏳ 待实现 | 适配新数据源 |
| `src/content/config.ts` | ⏳ 待实现 | 更新 schema（支持 painClusters 新格式） |
| `pipeline/publishing/competitor_integration.py` | 增强版数据提取函数 |
| `pipeline/discovery/run_pipeline.py` | 添加竞品触发逻辑 |

---

## 八、数据流全景图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Discovery Pipeline                                │
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                 │
│  │   趋势数据    │    │   社区讨论    │    │   SERP 竞品   │                 │
│  │  (Trends)    │    │ (Community)  │    │  (Domains)   │                 │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                 │
│         │                   │                   │                          │
│         └───────────────────┼───────────────────┘                          │
│                             ▼                                               │
│                    ┌─────────────────┐                                       │
│                    │  Idea Profile   │                                       │
│                    └────────┬────────┘                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  痛点聚类        │ │  市场空白        │ │  竞品分析        │
│ (painClusters)  │ │ (competitorGaps)│ │  (Competitors)  │
├─────────────────┤ ├─────────────────┤ ├─────────────────┤
│ 1️⃣ 社区提取     │ │ 竞品弱点纯粹提取 │ │ 竞品 Registry   │
│   (新数据源)     │ │ (仅弱点)         │ │ (动态加载)      │
│                 │ │                 │ │                 │
│ 2️⃣ 竞品弱点推断 │ │ 来源: Registry  │ │ 来源:          │
│   (带竞品名)    │ │ (weaknesses)    │ │ - Landing Page │
│                 │ │                 │ │ - Pricing Page │
│ 3️⃣ 关键词匹配   │ │                 │ │ - LLM 分析     │
│   (回退)        │ │                 │ │                │
│                 │ │                 │ │                 │
│ 展示: 带来源标签 │ │ 展示: 带域名标签 │ │ 展示: 完整卡片  │
│ 社区: 带引用链接 │ │                 │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   Frontmatter    │
                    │   (Markdown)     │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │     Frontend     │
                    │  (动态数据加载)   │
                    └─────────────────┘
```

### 数据来源对比

| 字段 | 数据来源 | 是否去重 | 是否带证据 | 来源标注 |
|------|----------|----------|-----------|----------|
| painClusters | 社区 + 竞品 + 关键词 | 是 | 社区类型带引用 | ✅ |
| competitorGaps | 竞品弱点 | 否（保留域名） | ❌ | ✅ 域名 |
| topCompetitors | 竞品 Registry | N/A | ❌ | ✅ 元数据 |

