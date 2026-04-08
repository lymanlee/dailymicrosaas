# 详情页字段文档

> 本文档维护 DailyMicrosaas 详情页展示的所有字段定义，包括字段名、数据来源、生成规则、中文描述。
> 随着产品能力升级，持续更新此文档。

---

## 一、基本信息字段

| 字段路径 | 中文描述 | 数据来源 | 生成规则 | 示例 |
|---------|---------|---------|---------|------|
| `title.en` | 英文标题 | 用户输入 / AI 生成 | 双语结构，英文优先 | "AI Music Generator SaaS" |
| `title.zh` | 中文标题 | AI 翻译 | 保持与英文语义一致 | "AI 音乐生成 SaaS" |
| `description.en` | 英文简短描述 | AI 生成 | 1-2 句话，概述核心价值 | "Generate royalty-free music with AI" |
| `description.zh` | 中文简短描述 | AI 翻译 | 与英文描述语义对应 | "用 AI 生成免版税音乐" |
| `tagline.en` | 英文口号 | AI 生成 | 更具吸引力的短句，用于 Hero 区 | "Turn ideas into tracks in seconds" |
| `tagline.zh` | 中文口号 | AI 翻译 | 中文语境下的吸引力表达 | "创意秒变音轨" |
| `keyword` | 核心关键词 | SERP 分析 | 从趋势数据中提取主关键词 | "ai music generator" |
| `buildWindow.en` | 英文构建时机 | 趋势 + 竞争分析 | 包含时机判断和理由 | "Now — low competition, rising demand" |
| `buildWindow.zh` | 中文构建时机 | AI 翻译 | 中文语境下的时机表达 | "现在 — 竞争低，需求上升" |
| `createdAt` | 创建时间 | 自动生成 | ISO 8601 格式 | "2026-04-08T12:00:00Z" |
| `ideaType` | Idea 类型 | AI 分类 | 可选值: `saas`, `tool`, `content`, `api`, `marketplace` | `saas` |

---

## 二、评分与元数据

| 字段路径 | 中文描述 | 数据来源 | 生成规则 | 示例 |
|---------|---------|---------|---------|------|
| `score` | 综合评分 | Discovery Pipeline | 0-100 分，基于趋势、竞争、需求多维度 | `75` |
| `difficulty` | 实施难度 | AI 评估 | 可选值: `low`, `medium`, `high` | `medium` |
| `trend` | 趋势方向 | 关键词趋势数据 | 可选值: `rising`, `stable`, `declining` | `rising` |
| `coverImage` | 封面图片 | AI 生成 / 用户上传 | 可选，16:9 比例 | "https://..." |
| `status` | 发布状态 | 用户控制 | 可选值: `draft`, `published`, `archived` | `published` |

---

## 三、痛点聚类 (painClusters)

> 描述目标用户面临的核心问题。
>
> **核心原则**：来源多元化、可追溯、带证据。

### 3.1 字段结构

```typescript
interface PainCluster {
  // 痛点内容
  text: {
    en: string;  // 英文痛点
    zh: string;  // 中文痛点
  };

  // 来源类型（必填，用于展示样式区分）
  source: "community" | "competitor" | "keyword";

  // 来源竞品（仅 source === "competitor" 时填写）
  sourceDomain?: string;

  // 原话引用（仅 source === "community" 时填写）
  evidence?: Array<{
    url: string;      // 来源帖子 URL
    source: string;   // 来源平台: "hackernews" | "reddit" | "twitter"
    quote: {
      en: string;      // 原文引用（英文）
      zh: string;      // 原文引用（中文翻译）
    };
  }>;
}
```

### 3.2 数据来源优先级

| 优先级 | 来源 | source 值 | 展示样式 | 证据 |
|--------|------|-----------|---------|------|
| 1️⃣ | 社区真实讨论 | `community` | 带引号 + 来源链接 | ✅ 带原话引用 |
| 2️⃣ | 竞品弱点推断 | `competitor` | 带竞品域名标签 `【域名】` | ❌ |
| 3️⃣ | 关键词匹配回退 | `keyword` | 纯文本，无特殊标记 | ❌ |

### 3.3 各来源详细说明

#### 来源 1：社区真实讨论 (community)

**数据来源**：
- Hacker News 帖子及评论
- Reddit 相关 subreddit 讨论
- Twitter/X 用户抱怨

**生成方式**：
1. 收集与 keyword 相关的社区讨论（最多 10 条）
2. 使用 LLM 分析提取用户抱怨和挫折
3. 保留原始评论引用作为证据

**生成模块**：`extract_community_pains.py` → `derive_pain_clusters_enhanced()`

**示例**：
```yaml
- source: community
  text:
    en: "Existing AI music tools all sound generic and repetitive"
    zh: "现有 AI 音乐工具听起来都很雷同且重复"
  evidence:
    - url: "https://news.ycombinator.com/item?id=xxx"
      source: hackernews
      quote:
        en: "Using Soundraw for a month, all tracks sound the same"
        zh: "用了 Soundraw 一个月，所有曲目听起来都一样"
```

#### 来源 2：竞品弱点推断 (competitor)

**数据来源**：
- 竞品 Registry 中的 `weaknesses` 字段
- 竞品分析模块生成的功能缺失列表

**生成方式**：
1. 从竞品 Registry 读取 weaknesses
2. 标注来源竞品域名
3. 去重后保留最多 3 条

**示例**：
```yaml
- source: competitor
  sourceDomain: boomy.com
  text:
    en: "Limited control over AI-generated music quality"
    zh: "对 AI 生成的音乐质量控制有限"
```

#### 来源 3：关键词匹配 (keyword)

**数据来源**：
- 标题关键词的规则匹配
- 作为前两种来源不足时的回退

**生成方式**：
1. 检查 painClusters 是否达到 4 条
2. 使用预定义痛点模板匹配
3. 不带特殊标记

**示例**：
```yaml
- source: keyword
  text:
    en: "Speed & performance issues"
    zh: "速度和性能问题"
```

### 3.4 数量限制

- **最少**：2 条
- **最多**：4 条
- 优先级：社区 > 竞品 > 关键词

---

## 四、市场空白 (competitorGaps)

> 描述竞品尚未解决或解决不好的问题，即潜在的产品机会。
>
> **核心原则**：纯粹从竞品弱点提取，与 painClusters 完全分离。

### 4.1 字段结构

```typescript
interface CompetitorGap {
  // 来源竞品域名（必填）
  domain: string;

  // 空白描述
  text: {
    en: string;  // 英文描述
    zh: string;  // 中文描述
  };
}
```

### 4.2 数据来源

| 来源 | 说明 |
|------|------|
| 竞品 Registry | `src/data/competitors/{domain}.json` → `weaknesses` |
| **不包含** | 社区讨论、用户评论、LLM 推断 |

### 4.3 与 painClusters 的区别

| 维度 | painClusters | competitorGaps |
|------|-------------|----------------|
| 数据来源 | 社区 + 竞品 + 关键词 | 仅竞品弱点 |
| 展示目的 | 用户痛点（情感层面） | 市场机会（商业层面） |
| 来源标注 | source + sourceDomain | 仅 domain |
| 去重 | 是（避免重复） | 否（保留域名来源） |
| 证据 | community 类型带引用 | 无 |

### 4.4 生成模块

`extract_competitor_gaps.py`

### 4.5 示例

```yaml
competitorGaps:
  - domain: boomy.com
    text:
      en: "Limited control over AI-generated music quality"
      zh: "对 AI 生成的音乐质量控制有限"
  - domain: soundraw.io
    text:
      en: "Outputs can sound repetitive after extended use"
      zh: "长期使用后输出可能显得千篇一律"
```

---

## 五、竞品分析 (CompetitorAnalysis)

> 展示直接竞争对手的详细信息。
>
> **核心原则**：动态加载，数据与 frontmatter 分离。

### 5.1 frontmatter 存储结构

```yaml
competitorAnalysis:
  # 只存储域名列表（引用方式）
  domains:
    - suno.ai
    - boomy.com
    - soundraw.io

  # 标记使用独立数据源
  _registry: true

  # 版本号（用于迁移校验）
  _version: 2
```

### 5.2 竞品 Registry 数据结构

**文件位置**：`src/data/competitors/{domain}.json`

```typescript
interface CompetitorProfile {
  // 基础信息
  domain: string;           // 域名
  name: {
    en: string;              // 英文名称
    zh: string;               // 中文名称
  };

  // 定价方案
  pricingTiers: Array<{
    name: {
      en: string;             // 方案名称
      zh: string;             // 方案名称（中文）
    };
    price: number;            // 月费价格（美元）
    billing?: string;         // 计费周期: "monthly" | "yearly"
    description: {
      en: string;             // 方案描述
      zh: string;             // 方案描述（中文）
    };
    limits?: {
      monthlyCredits?: { en: string; zh: string };
      commercialUse?: { en: string; zh: string };
      exportFormats?: { en: string; zh: string };
      [key: string]: { en: string; zh: string } | undefined;
    };
  }>;

  // 核心功能
  keyFeatures: Array<{
    en: string;               // 功能名称（英文）
    zh: string;               // 功能名称（中文）
  }>;

  // 弱点
  weaknesses: Array<{
    en: string;               // 弱点描述（英文）
    zh: string;               // 弱点描述（中文）
  }>;

  // 目标用户
  targetAudience: {
    en: string;              // 英文描述
    zh: string;              // 中文描述
  };

  // 市场定位
  positioning: {
    en: string;              // 英文描述
    zh: string;              // 中文描述
  };

  // 元数据
  lastChecked: string;       // 上次爬取时间 (ISO 8601)
  dataStatus: "fresh" | "stale" | "failed";  // 数据状态

  // 数据来源
  dataSources?: {
    landingPage?: string;
    pricingPage?: string;
    llmModel?: string;
  };
}
```

### 5.3 各字段详细说明

| 字段路径 | 中文描述 | 数据来源 | 生成规则 |
|---------|---------|---------|---------|
| `domain` | 竞品域名 | SERP 分析 | 从竞品发现模块提取 |
| `name.en` | 英文名称 | Landing Page 解析 | 从页面标题或 Logo 提取 |
| `name.zh` | 中文名称 | LLM 翻译 | 中文语境下的通用译名 |
| `pricingTiers[].name` | 方案名称 | Pricing Page 爬取 | 原文保留 |
| `pricingTiers[].price` | 月费价格 | Pricing Page 爬取 | 数值（美元），免费为 0 |
| `pricingTiers[].description` | 方案描述 | LLM 生成 | 概括方案差异点 |
| `pricingTiers[].limits` | 限制说明 | 解析 + LLM | 积分限制、商用权限等 |
| `keyFeatures` | 核心功能 | Landing Page 解析 | 列举 3-5 个主要功能 |
| `weaknesses` | 竞品弱点 | LLM 分析 | 基于页面内容和用户评价推断 |
| `targetAudience` | 目标用户 | Landing Page + LLM | 描述主要用户群体 |
| `positioning` | 市场定位 | Landing Page + LLM | 描述产品定位和差异化 |
| `lastChecked` | 上次爬取时间 | 自动记录 | ISO 8601 格式 |
| `dataStatus` | 数据状态 | 自动标注 | 见下方状态说明 |

### 5.4 数据状态说明

| 状态值 | 中文描述 | 触发条件 | 展示处理 |
|--------|---------|---------|---------|
| `fresh` | 数据新鲜 | 24 小时内爬取 | 正常展示 |
| `stale` | 数据可能过期 | 24 小时 - 7 天未更新 | 显示警告提示 |
| `failed` | 爬取失败 | 连续 3 次爬取失败 | 显示 "数据获取失败" |

### 5.5 动态加载机制

**加载函数**：`getCompetitorRegistry(domains, fallback?)`

**加载逻辑**：
1. 尝试从 `src/data/competitors/{domain}.json` 加载
2. 如果加载失败，使用 frontmatter 中的 fallback 数据
3. 合并结果返回

**降级策略**：
- 独立数据源不可用时，降级到 frontmatter 内嵌数据
- 确保详情页始终能正常展示

---

## 六、社区讨论 (CommunitySignals)

> 展示相关社区的用户讨论和反馈。
>
> **用途**：为 painClusters 提供证据，为用户提供社区热度参考。

### 6.1 字段结构

```typescript
interface CommunitySignals {
  // Hacker News
  hackernews?: Array<{
    id: string;
    title: string;
    url: string;
    score: number;
    commentCount: number;
    postedAt: string;
  }>;

  // Reddit
  reddit?: Array<{
    id: string;
    subreddit: string;
    title: string;
    url: string;
    score: number;
    commentCount: number;
    postedAt: string;
  }>;

  // 聚合热度分数
  totalSignals: number;
  sentiment: "positive" | "neutral" | "negative";
}
```

### 6.2 数据来源

| 平台 | 搜索关键词 | 数量限制 |
|------|-----------|---------|
| Hacker News | `keyword` + "Ask HN" | 最多 5 条 |
| Reddit | keyword + 相关 subreddit | 最多 5 条 |

---

## 七、数据来源全景图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Discovery Pipeline                                │
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │   趋势数据    │    │   社区讨论    │    │   SERP 竞品   │                   │
│  │  (Trends)    │    │ (Community)  │    │  (Domains)   │                   │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                   │
│         │                   │                   │                          │
│         │                   │                   │                          │
│         └───────────────────┼───────────────────┘                          │
│                             ▼                                              │
│                    ┌─────────────────┐                                     │
│                    │  Idea Profile   │                                     │
│                    └────────┬────────┘                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  痛点聚类        │ │  市场空白        │ │  竞品分析        │
│ (painClusters)  │ │ (competitorGaps)│ │  (Competitors)  │
├─────────────────┤ ├─────────────────┤ ├─────────────────┤
│ 1️⃣ 社区提取     │ │ 竞品弱点纯粹提取 │ │ 竞品 Registry   │
│   (新数据源)     │ │ (仅 weaknesses) │ │ (动态加载)      │
│                 │ │                 │ │                 │
│ 2️⃣ 竞品弱点推断 │ │ 来源:           │ │ 来源:          │
│   (带竞品名)    │ │ Registry        │ │ - Landing Page │
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

---

## 八、字段变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|---------|--------|
| 2026-04-08 | v1.0 | 初始文档，创建字段清单 | - |
| 2026-04-08 | v1.1 | 增加 painClusters 来源区分 (community/competitor/keyword) | - |
| 2026-04-08 | v1.2 | 增加 competitorGaps 纯粹提取规则，与 painClusters 分离 | - |
| 2026-04-08 | v1.3 | 增加竞品 Registry 动态加载机制说明 | - |

---

## 九、前端组件映射

| 字段组 | 组件文件 | 渲染说明 |
|--------|---------|---------|
| 基本信息 | `IdeaHero.astro` | 展示 title, tagline, buildWindow |
| 评分元数据 | `IdeaScoreBadge.astro` | 展示 score, difficulty, trend |
| 痛点聚类 | `PainClusterList.astro` + `PainClusterItem.astro` | 按 source 区分样式 |
| 市场空白 | `CompetitorGapList.astro` | 带 domain 标签 |
| 竞品分析 | `CompetitorAnalysisSection.astro` + `CompetitorCard.astro` | 动态加载 Registry |
| 社区讨论 | `CommunitySignals.astro` | 展示 HN/Reddit 信号 |

---

## 十、生成脚本清单

| 模块 | 文件路径 | 说明 |
|------|---------|------|
| 痛点聚类生成 | `pipeline/discovery/extract_community_pains.py` | 社区痛点提取 (LLM) |
| 痛点聚类增强 | `pipeline/publishing/derive_pain_clusters_enhanced()` | 多来源聚合 |
| 市场空白提取 | `pipeline/publishing/extract_competitor_gaps.py` | 纯粹弱点提取 |
| 竞品数据 Registry | `src/data/competitors/*.json` | 独立数据源 |
| 竞品动态加载 | `src/lib/competitor-registry.ts` | 加载工具函数 |

---

*文档版本：v1.3*
*最后更新：2026-04-08*
