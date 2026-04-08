# Idea 详情页内容优化方案

> 目标：结合当前数据源现状 + 后续要补充的真实竞品分析能力，从**产品定位**和**核心价值**出发，制定可直接落地执行的优化方案。

---

## 一、现状诊断

### 1.1 当前数据结构

| 数据源 | 采集方式 | 原始数据 | 当前问题 |
|--------|---------|---------|---------|
| **Google Trends** | pytrends API | 热度值、斜率、峰值、时间序列 | 仅展示趋势图，未深度解读 |
| **社区信号 (HN/GitHub/Reddit)** | API 抓取 | 帖子标题、upvotes、评论数 | 仅列标题，未做语义分析 |
| **SERP 竞争格局** | DDG HTML 抓取 | 域名列表 | **只有域名，没有页面内容** |
| **竞品弱点** | 规则推断 | `competitorGaps` frontmatter | **拍脑袋生成，无真实依据** |
| **痛点聚类** | 关键词匹配 | `painClusters` frontmatter | **纯关键词匹配，非真实痛点** |

### 1.2 当前详情页问题

1. **竞品分析是空的**：SERP 只采集了域名，没有抓取任何页面内容，导致"竞品弱点"是拍脑袋生成的
2. **痛点是猜的**：从社区标题关键词匹配推断痛点，而非真实语义分析
3. **差异化建议模板化**：按 category 套模板，不是基于真实市场分析
4. **变现建议通用**：按 category 给通用建议，没有结合具体竞品的定价策略

---

## 二、产品定位与核心价值

### 2.1 产品定位

**Daily Micro SaaS** 是一个**数据驱动的创业机会发现平台**，核心价值是：

> 帮助独立开发者/小团队**快速识别**有真实需求的 Micro SaaS 机会，并提供**可执行的切入路径**。

### 2.2 核心价值主张

| 维度 | 当前状态 | 理想状态 |
|------|---------|---------|
| **需求验证** | 有趋势数据 + 社区信号计数 | 真实用户讨论语义分析 |
| **竞争分析** | 域名列表 + 拍脑袋弱点 | 真实竞品功能/定价/体验对比 |
| **切入建议** | category 模板 | 基于真实市场空白的定制化建议 |
| **变现策略** | category 通用模板 | 基于竞品定价策略的差异化定价建议 |

---

## 三、优化方案（分阶段落地）

### Phase 1: 数据层增强（2-3 周）

#### 3.1.1 竞品页面深度抓取

**目标**：从 SERP 域名扩展到真实页面内容分析

**技术方案**：

```python
# 新增: pipeline/discovery/competitor_analyzer.py

class CompetitorAnalyzer:
    """竞品深度分析器 - 抓取并分析竞品页面内容"""
    
    def __init__(self):
        self.scraper = None  # 使用 scrapling 或 playwright
        self.llm_client = None  # OpenAI/Claude API
    
    async def analyze_competitor(self, domain: str, keyword: str) -> CompetitorProfile:
        """
        分析单个竞品站点，返回结构化数据
        """
        # 1. 抓取首页 + 定价页
        homepage = await self._fetch_page(f"https://{domain}")
        pricing_page = await self._fetch_page(f"https://{domain}/pricing")
        
        # 2. 提取关键信息
        return CompetitorProfile(
            domain=domain,
            # 核心功能（从首页提取）
            key_features=self._extract_features(homepage),
            # 定价策略（从定价页提取）
            pricing_tiers=self._extract_pricing(pricing_page),
            # 免费层限制
            free_tier_limits=self._extract_free_limits(pricing_page),
            # 目标用户描述
            target_audience=self._extract_audience(homepage),
            # 差异化定位
            positioning=self._extract_positioning(homepage),
        )
    
    def _extract_features(self, html: str) -> List[str]:
        """使用 LLM 提取页面描述的核心功能"""
        prompt = f"""
        从以下网页 HTML 中提取该产品的主要功能特点，返回 3-5 个要点：
        {html[:8000]}  # 截断避免 token 超限
        """
        return self.llm_client.extract_list(prompt)
    
    def _extract_pricing(self, html: str) -> List[PricingTier]:
        """提取定价层级信息"""
        # 使用结构化提取或 LLM
        pass
    
    def _extract_free_limits(self, html: str) -> Dict[str, Any]:
        """提取免费层具体限制"""
        # 例如: {"monthly_credits": 10, "max_file_size": "5MB", "watermark": True}
        pass
```

**数据存储扩展**（`serp_data_*.json` → `competitor_profiles_*.json`）：

```json
{
  "ai-music-generator": {
    "keyword": "ai music generator",
    "serp_results": [...],
    "competitor_profiles": [
      {
        "domain": "suno.ai",
        "analyzed_at": "2026-04-07T10:00:00Z",
        "key_features": [
          "Text-to-music generation",
          "Multiple genre support",
          "Lyrics generation"
        ],
        "pricing_tiers": [
          {"name": "Free", "price": 0, "credits": 50},
          {"name": "Pro", "price": 10, "credits": 2000}
        ],
        "free_tier_limits": {
          "daily_generations": 10,
          "max_duration_seconds": 120,
          "commercial_use": false
        },
        "target_audience": "Content creators, musicians",
        "positioning": "Professional AI music creation",
        "weaknesses_detected": [
          "Free tier very limited",
          "No batch processing",
          "No API access on lower tiers"
        ]
      }
    ]
  }
}
```

#### 3.1.2 社区信号语义分析

**目标**：从"标题关键词匹配"升级为"真实痛点语义提取"

**技术方案**：

```python
# 新增: pipeline/discovery/community_analyzer.py

class CommunityAnalyzer:
    """社区信号深度分析器 - 语义提取真实痛点"""
    
    async def analyze_discussions(self, signals: List[CommunitySignal]) -> PainAnalysis:
        """
        分析社区讨论，提取真实痛点
        """
        # 1. 获取帖子详情（如果有 API 支持）
        detailed_posts = await self._fetch_post_details(signals)
        
        # 2. 使用 LLM 做语义聚类
        prompt = f"""
        分析以下社区讨论，提取用户反复提到的痛点和未满足的需求。
        返回结构化结果：
        - pain_points: 痛点列表（每个包含描述、严重程度、提及次数）
        - desired_features: 用户期望的功能
        - complaints: 对现有方案的具体抱怨
        
        讨论数据：
        {json.dumps(detailed_posts, ensure_ascii=False)}
        """
        
        return self.llm_client.extract_structured(prompt)
```

**数据存储扩展**：

```json
{
  "ai-music-generator": {
    "raw_signals": [...],
    "pain_analysis": {
      "extracted_at": "2026-04-07T10:00:00Z",
      "pain_points": [
        {
          "description": "现有工具生成的音乐风格单一",
          "severity": "high",
          "mentions": 5,
          "source_posts": [...]
        },
        {
          "description": "免费额度太少，无法完整测试",
          "severity": "medium", 
          "mentions": 3,
          "source_posts": [...]
        }
      ],
      "desired_features": [
        "更细粒度的风格控制",
        "批量生成能力",
        "更长时长支持"
      ]
    }
  }
}
```

#### 3.1.3 生成逻辑重构

**目标**：`generate_idea.py` 使用真实分析数据，而非规则推断

**关键改动**：

```python
# pipeline/publishing/generate_idea.py

def build_competition_section(profile: CompetitorProfile, pain_analysis: PainAnalysis) -> str:
    """
    基于真实竞品分析生成竞争章节
    """
    # 之前：拍脑袋推断
    # gaps = derive_competitor_gaps_serp_only(serp_data)  # ❌
    
    # 现在：基于真实数据
    gaps = []
    for competitor in profile.competitor_profiles:
        gaps.extend(competitor.weaknesses_detected)
    
    # 结合用户痛点，找出市场空白
    market_gaps = find_market_gaps(pain_analysis, profile.competitor_profiles)
    
    return render_competition_template(
        competitors=profile.competitor_profiles,
        gaps=market_gaps,
        pain_points=pain_analysis.pain_points
    )
```

---

### Phase 2: 详情页内容重构（1-2 周）

#### 3.2.1 新增数据字段（Frontmatter）

```yaml
---
# 现有字段保持不变
title: { en: "...", zh: "..." }
category: "AI 工具"

# 新增：竞品深度分析
competitorAnalysis:
  analyzedAt: "2026-04-07"
  topCompetitors:
    - domain: "suno.ai"
      name: "Suno"
      pricing:
        freeTier: { en: "50 credits/month", zh: "每月 50 积分" }
        paidTier: { en: "$10/month for 2000 credits", zh: "$10/月，2000 积分" }
      keyFeatures:
        - { en: "Text-to-music", zh: "文本生成音乐" }
        - { en: "Lyrics generation", zh: "歌词生成" }
      weaknesses:
        - { en: "Very limited free tier", zh: "免费层限制严格" }
        - { en: "No batch processing", zh: "不支持批量处理" }
  
  marketGaps:
    - { en: "Cheaper alternative for casual users", zh: "面向 casual 用户的更便宜选择" }
    - { en: "Better batch processing workflow", zh: "更好的批量处理工作流" }

# 新增：痛点深度分析
painAnalysis:
  extractedAt: "2026-04-07"
  topPains:
    - description: 
        en: "Current tools produce generic-sounding music"
        zh: "现有工具生成的音乐风格过于单一"
      severity: "high"
      evidenceCount: 5
    - description:
        en: "Free tiers are too restrictive to properly evaluate"
        zh: "免费层限制太多，无法充分评估"
      severity: "medium"
      evidenceCount: 3

# 新增：差异化建议（基于真实分析）
differentiationStrategy:
  en: "Focus on batch processing and lower per-generation cost"
  zh: "专注批量处理和更低的单次生成成本"
  rationale:
    en: "Top competitors charge $0.005 per generation; there's room for $0.002 with simpler UI"
    zh: "头部竞品单次生成约 $0.005；简化 UI 后可以做到 $0.002 仍有利润"
---
```

#### 3.2.2 详情页组件重构

**新增组件**：

```astro
<!-- src/components/CompetitorAnalysisCard.astro -->
---
interface Props {
  competitors: CompetitorProfile[];
  marketGaps: LocalizedPair[];
  lang: Lang;
}

const { competitors, marketGaps, lang } = Astro.props;
---

<section class="competitor-analysis">
  <h2>{t['detail.competitors.title']}</h2>
  
  <!-- 竞品对比表格 -->
  <div class="competitor-grid">
    {competitors.map(comp => (
      <CompetitorCard 
        name={comp.name}
        pricing={comp.pricing}
        features={comp.keyFeatures}
        weaknesses={comp.weaknesses}
      />
    ))}
  </div>
  
  <!-- 市场空白分析 -->
  <div class="market-gaps">
    <h3>{t['detail.gaps.title']}</h3>
    <ul>
      {marketGaps.map(gap => (
        <li>{getLocalizedPairText(gap, lang)}</li>
      ))}
    </ul>
  </div>
</section>
```

**重构后的详情页结构**：

```
IdeaDetailPage
├── Hero Section（保持不变）
├── Trend Chart（保持不变）
├── Pain Points（重构：使用语义分析结果）
├── Competitor Analysis（新增：真实竞品对比）
├── Market Gaps（新增：基于真实分析的市场空白）
├── Source Signals（保持不变）
├── Full Breakdown（重构：使用增强数据）
└── Sidebar（保持不变）
```

---

### Phase 3: 自动化 Pipeline（2 周）

#### 3.3.1 完整 Pipeline 流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    Discovery Pipeline (Daily)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Step 1: Trend Discovery                                         │
│  └── Google Trends API → trend_data_*.json                      │
│                                                                  │
│  Step 2: Community Scan                                          │
│  └── HN/GitHub/Reddit API → community_signals_*.json            │
│                                                                  │
│  Step 3: SERP Collection                                         │
│  └── DDG HTML → serp_data_*.json                                │
│                                                                  │
│  Step 4: Competitor Analysis (NEW)                               │
│  └── scrapling/playwright + LLM → competitor_profiles_*.json    │
│                                                                  │
│  Step 5: Community Analysis (NEW)                                │
│  └── LLM semantic analysis → pain_analysis_*.json               │
│                                                                  │
│  Step 6: Opportunity Scoring                                     │
│  └── Combine all data → opportunity_report_*.json               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Publishing Pipeline (Manual)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Step 7: Generate Idea Markdown                                  │
│  └── generate_idea.py → src/content/ideas/*.md                  │
│      (使用真实竞品分析和痛点数据)                                │
│                                                                  │
│  Step 8: Human Review                                            │
│  └── 人工审核关键结论                                            │
│                                                                  │
│  Step 9: Deploy                                                  │
│  └── npm run build && deploy                                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.3.2 技术选型

| 组件 | 推荐方案 | 理由 |
|------|---------|------|
| **页面抓取** | `scrapling` | 轻量、异步、支持 JS 渲染 |
| **浏览器自动化** | `playwright` (备选) | 需要复杂交互时使用 |
| **LLM API** | OpenAI GPT-4o-mini / Claude 3 Haiku | 成本低、速度快、支持结构化输出 |
| **数据存储** | JSON files (保持现状) | 简单、版本控制友好 |
| **缓存策略** | 域名级缓存，7 天过期 | 避免频繁抓取被封 |

---

## 四、文案生成规则重构

### 4.1 竞品弱点文案（从拍脑袋 → 真实分析）

**之前（拍脑袋）**：

```python
def derive_competitor_gaps(serp_data):
    gaps = []
    if serp_data['tool_big_count'] >= 3:
        gaps.append("头部产品把关键功能放在付费墙后")  # ❌ 没看过定价页
    if serp_data['tool_big_count'] >= 2:
        gaps.append("大站要求先注册账号")  # ❌ 没看过注册流程
    return gaps
```

**之后（真实分析）**：

```python
def derive_competitor_gaps(competitor_profiles: List[CompetitorProfile]):
    gaps = []
    
    # 分析免费层限制
    free_limits = [c.free_tier_limits for c in competitor_profiles if c.free_tier_limits]
    if all(l.get('daily_generations', 999) < 20 for l in free_limits):
        gaps.append({
            "en": "All major competitors limit free tier to <20 generations/day",
            "zh": "主要竞品的免费层都限制在每日 20 次以内"
        })
    
    # 分析定价策略
    prices = [c.pricing_tiers[1]['price'] for c in competitor_profiles 
              if len(c.pricing_tiers) > 1]
    if prices and min(prices) > 8:
        gaps.append({
            "en": f"Lowest paid tier starts at ${min(prices)}/month — room for a cheaper option",
            "zh": f"最低付费档 ${min(prices)}/月起——有空间做更便宜的选择"
        })
    
    return gaps
```

### 4.2 痛点文案（从关键词匹配 → 语义分析）

**之前（关键词匹配）**：

```python
def derive_pain_clusters(signals):
    pains = []
    titles = [s['title'].lower() for s in signals]
    if any('slow' in t or 'speed' in t for t in titles):
        pains.append("速度和性能问题")  # ❌ 可能只是标题里有这个词
    return pains
```

**之后（语义分析）**：

```python
def derive_pain_clusters(pain_analysis: PainAnalysis):
    """使用 LLM 语义分析结果"""
    return [
        {
            "en": pain.description,
            "zh": pain.description_zh,  # LLM 翻译或原文
            "severity": pain.severity,
            "evidence_count": pain.mentions
        }
        for pain in pain_analysis.top_pains[:4]
    ]
```

### 4.3 差异化建议（从 category 模板 → 基于真实市场空白）

**之前（category 模板）**：

```python
def build_differentiation(category):
    templates = {
        "AI 工具": ["成本", "上手速度", "垂直场景"],  # ❌ 所有 AI 工具都一样
        "文档处理": ["格式保真度", "批量处理", "速度"]
    }
    return templates.get(category, ["通用建议"])
```

**之后（基于真实分析）**：

```python
def build_differentiation(
    competitor_profiles: List[CompetitorProfile],
    pain_analysis: PainAnalysis
) -> LocalizedPair:
    """
    基于竞品弱点和用户痛点的交叉分析，生成差异化建议
    """
    # 找出竞品共同弱点
    common_weaknesses = find_common_weaknesses(competitor_profiles)
    
    # 找出高频用户痛点
    top_pains = pain_analysis.top_pains[:3]
    
    # 使用 LLM 生成分差异化策略
    prompt = f"""
    基于以下信息，生成一个具体的差异化切入建议：
    
    竞品共同弱点：{common_weaknesses}
    用户高频痛点：{top_pains}
    
    要求：
    1. 具体、可执行
    2. 基于真实数据，不泛泛而谈
    3. 说明为什么这个切角有机会
    
    返回格式：{{"en": "...", "zh": "...", "rationale": "..."}}
    """
    
    return llm_client.generate_structured(prompt)
```

---

## 五、实施路线图

### Week 1-2: 基础设施

- [ ] 搭建 `scrapling` 抓取环境
- [ ] 实现 `CompetitorAnalyzer` 基础版（抓取 + 简单提取）
- [ ] 实现 `CommunityAnalyzer` 基础版（LLM 语义分析）
- [ ] 扩展数据存储格式（`competitor_profiles_*.json`, `pain_analysis_*.json`）

### Week 3: 生成逻辑重构

- [ ] 重构 `generate_idea.py` 使用真实分析数据
- [ ] 更新 frontmatter schema（新增 `competitorAnalysis`, `painAnalysis` 等字段）
- [ ] 更新 `template.md`
- [ ] 跑通完整 pipeline 测试

### Week 4: 前端重构

- [ ] 新增 `CompetitorAnalysisCard` 组件
- [ ] 重构 `IdeaDetailPage` 展示新数据
- [ ] 更新 `idea.ts` helper 函数
- [ ] 样式调整

### Week 5: 验证与优化

- [ ] 人工审核 5-10 个生成的 idea，验证竞品分析准确性
- [ ] 调整 LLM prompt 提升提取质量
- [ ] 优化抓取策略（避免被封）
- [ ] 文档更新

---

## 六、关键决策点

### 6.1 是否值得做？

| 维度 | 评估 |
|------|------|
| **成本** | 中等（主要是 LLM API 费用和开发时间） |
| **收益** | 高（大幅提升内容可信度，形成差异化） |
| **风险** | 竞品抓取可能被封，需要限速和缓存策略 |
| **ROI** | 高（这是产品的核心竞争力） |

### 6.2 替代方案

| 方案 | 优点 | 缺点 |
|------|------|------|
| **A. 全自动化（推荐）** | 可扩展、成本低 | 开发周期长 |
| **B. 半自动化** | 快速上线 | 人工成本高，难扩展 |
| **C. 保持现状** | 无额外成本 | 内容可信度低，难形成壁垒 |

### 6.3 技术风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| 竞品站点反爬 | 使用 `scrapling` 的 stealth 模式，限速 2-4s/请求 |
| LLM API 成本 | 使用 GPT-4o-mini，缓存常见站点的分析结果 |
| 分析质量不稳定 | 人工审核 + prompt 迭代 |
| 数据一致性 | 版本控制 + 数据校验脚本 |

---

## 七、预期效果

### 7.1 数据质量提升

| 指标 | 当前 | 目标 |
|------|------|------|
| 竞品分析依据 | 域名列表 | 完整的功能/定价/弱点分析 |
| 痛点来源 | 关键词匹配 | 语义分析 + 真实讨论引用 |
| 差异化建议 | category 模板 | 基于真实市场空白的定制建议 |
| 变现策略 | 通用模板 | 基于竞品定价的差异化建议 |

### 7.2 用户感知提升

- **可信度**：从"看起来是模板填充" → "看起来做了真实调研"
- **价值感**：从"泛泛而谈" → "有具体数据支撑"
- **差异化**：形成"真实竞品分析"的产品壁垒

---

## 八、附录

### 8.1 新增文件清单

```
pipeline/
├── discovery/
│   ├── competitor_analyzer.py      # 竞品深度分析器
│   ├── community_analyzer.py       # 社区信号语义分析器
│   └── cache/                      # 抓取缓存目录
│       └── competitor_cache.json
├── data/
│   ├── competitor_profiles_*.json  # 竞品分析数据
│   └── pain_analysis_*.json        # 痛点分析数据
└── publishing/
    └── generate_idea.py            # 重构：使用真实数据

src/
├── components/
│   ├── CompetitorCard.astro        # 单个竞品卡片
│   ├── CompetitorComparison.astro  # 竞品对比组件
│   └── MarketGaps.astro            # 市场空白分析
└── lib/
    └── idea.ts                     # 扩展：支持新数据字段
```

### 8.2 依赖安装

```bash
# Python 依赖
pip install scrapling playwright openai

# Playwright 浏览器
playwright install chromium
```

---

## 九、中英文切换实现方案

### 9.1 数据层双语规范

所有新增数据结构必须遵循 `{ en: string, zh: string }` 格式：

```typescript
// 竞品分析数据结构（双语）
interface LocalizedCompetitorProfile {
  domain: string;
  name: string;
  // 所有可展示字段必须双语
  keyFeatures: LocalizedPair[];        // [{ en: "...", zh: "..." }]
  pricingTiers: LocalizedPricingTier[];
  weaknesses: LocalizedPair[];
  targetAudience: LocalizedPair;
  positioning: LocalizedPair;
}

interface LocalizedPricingTier {
  name: LocalizedPair;                 // 套餐名称
  price: number;
  description: LocalizedPair;          // 套餐描述
  limits: LocalizedLimits;
}

interface LocalizedLimits {
  monthlyCredits: LocalizedPair;       // "2,000 credits/month" / "每月 2,000 积分"
  maxFileSize: LocalizedPair;          // "Up to 100MB" / "最大 100MB"
  features: LocalizedPair[];           // 包含功能列表
}

// 痛点分析数据结构（双语）
interface LocalizedPainPoint {
  description: LocalizedPair;          // 痛点描述
  severity: "high" | "medium" | "low";
  mentions: number;
  sourcePosts: LocalizedSourcePost[];
}

interface LocalizedSourcePost {
  title: LocalizedPair;                // 帖子标题（原文 + 翻译）
  url: string;
  source: string;
  quote?: LocalizedPair;               // 关键引用（原文 + 翻译）
}
```

### 9.2 Pipeline 生成逻辑双语处理

**Step 1: LLM Prompt 设计（双语输出）**

```python
# pipeline/discovery/competitor_analyzer.py

COMPETITOR_ANALYSIS_PROMPT = """
分析以下竞品网站内容，提取关键信息并以双语格式返回。

页面内容：
{html_content}

返回 JSON 格式：
{{
  "keyFeatures": [
    {{"en": "Feature in English", "zh": "中文功能描述"}}
  ],
  "pricingTiers": [
    {{
      "name": {{"en": "Free", "zh": "免费版"}},
      "price": 0,
      "description": {{"en": "...", "zh": "..."}},
      "limits": {{
        "monthlyCredits": {{"en": "50 credits/month", "zh": "每月 50 积分"}},
        "maxFileSize": {{"en": "Up to 10MB", "zh": "最大 10MB"}}
      }}
    }}
  ],
  "weaknesses": [
    {{"en": "Weakness description", "zh": "弱点描述"}}
  ],
  "targetAudience": {{"en": "...", "zh": "..."}},
  "positioning": {{"en": "...", "zh": "..."}}
}}

注意：
1. 所有用户可见文本必须提供 en 和 zh 两个版本
2. 英文保持专业术语准确
3. 中文自然流畅，符合国内用户表达习惯
4. 数字、单位、价格保持格式一致
"""

# 痛点分析双语 Prompt
PAIN_ANALYSIS_PROMPT = """
分析以下社区讨论，提取用户痛点并以双语格式返回。

讨论内容：
{discussions}

返回 JSON 格式：
{{
  "painPoints": [
    {{
      "description": {{
        "en": "Pain point description in English",
        "zh": "中文痛点描述"
      }},
      "severity": "high|medium|low",
      "mentions": 5,
      "evidence": [
        {{
          "title": {{"en": "Original title", "zh": "中文标题"}},
          "quote": {{"en": "Key quote", "zh": "中文引用"}}
        }}
      ]
    }}
  ]
}}
"""
```

**Step 2: 差异化建议双语生成**

```python
# pipeline/publishing/generate_idea.py

def build_differentiation_strategy(
    competitor_profiles: List[CompetitorProfile],
    pain_analysis: PainAnalysis,
    lang: str = "en"  # 新增语言参数
) -> LocalizedPair:
    """
    生成双语差异化建议
    """
    prompt = f"""
    基于以下竞品分析和用户痛点，生成差异化切入建议。
    
    竞品弱点：
    {format_weaknesses(competitor_profiles)}
    
    用户痛点：
    {format_pains(pain_analysis)}
    
    要求：
    1. 建议必须具体、可执行，不泛泛而谈
    2. 同时提供英文和中文版本
    3. 解释为什么这个切角有机会（双语）
    
    返回格式：
    {{
      "strategy": {{
        "en": "Differentiation strategy in English (1-2 sentences)",
        "zh": "中文差异化策略（1-2句话）"
      }},
      "rationale": {{
        "en": "Explanation of why this wedge works",
        "zh": "解释为什么这个切角有机会"
      }}
    }}
    """
    
    result = llm_client.generate_structured(prompt)
    return LocalizedPair(
        en=result["strategy"]["en"],
        zh=result["strategy"]["zh"]
    )
```

### 9.3 Frontmatter 双语 Schema

```yaml
---
# 基础信息（已有字段，保持双语）
title:
  en: "Ai Music Generator — Where an AI-first wedge still exists"
  zh: "Ai Music Generator — 这个 AI 方向还能怎么切"
description:
  en: "A deep dive into the ai music generator opportunity..."
  zh: "对 ai music generator 这个方向的一次深度拆解..."
bestWedge:
  en: "Cheaper & focused — do one thing, charge less than the generalists"
  zh: "更便宜、更聚焦：只做好一件事，价格打过通用型产品"

# 竞品深度分析（新增，必须双语）
competitorAnalysis:
  analyzedAt: "2026-04-07"
  topCompetitors:
    - domain: "suno.ai"
      name: "Suno"
      keyFeatures:
        - en: "Text-to-music generation with multiple genres"
          zh: "支持多种风格的文本生成音乐"
        - en: "AI-powered lyrics generation"
          zh: "AI 驱动的歌词生成"
        - en: "Commercial usage rights on paid tiers"
          zh: "付费档包含商业使用授权"
      pricingTiers:
        - name:
            en: "Free"
            zh: "免费版"
          price: 0
          description:
            en: "50 credits per month, non-commercial use only"
            zh: "每月 50 积分，仅限非商业用途"
          limits:
            monthlyCredits:
              en: "50 credits/month"
              zh: "每月 50 积分"
            maxDuration:
              en: "Up to 2 minutes per track"
              zh: "每首最长 2 分钟"
            commercialUse:
              en: "Not allowed"
              zh: "不允许"
        - name:
            en: "Pro"
            zh: "专业版"
          price: 10
          description:
            en: "2,000 credits per month with commercial rights"
            zh: "每月 2,000 积分，包含商业授权"
      weaknesses:
        - en: "Free tier is extremely limited (only 50 credits)"
          zh: "免费层限制非常严格（仅 50 积分）"
        - en: "No batch processing or API access on lower tiers"
          zh: "低档套餐不支持批量处理或 API 访问"
        - en: "Pricing jumps significantly for higher usage"
          zh: "用量增加时价格跳跃较大"
      targetAudience:
        en: "Content creators, musicians, and video producers"
        zh: "内容创作者、音乐人和视频制作人"
      positioning:
        en: "Professional-grade AI music creation tool"
        zh: "专业级 AI 音乐创作工具"
  
  marketGaps:
    - en: "Cheaper alternative for casual users who don't need 2,000 credits"
      zh: "面向不需要 2,000 积分的 casual 用户的更便宜选择"
    - en: "Better batch processing workflow for power users"
      zh: "面向重度用户的更好批量处理工作流"
    - en: "Mid-tier pricing between free and $10/month"
      zh: "免费版和 $10/月之间的中间价位"

# 痛点深度分析（新增，必须双语）
painAnalysis:
  extractedAt: "2026-04-07"
  topPains:
    - description:
        en: "Current tools produce generic-sounding music lacking unique style"
        zh: "现有工具生成的音乐风格过于单一，缺乏独特性"
      severity: "high"
      evidenceCount: 5
      evidence:
        - title:
            en: "Show HN: I built an AI music generator that doesn't sound generic"
            zh: "Show HN: 我做了个不会生成千篇一律音乐的 AI 音乐生成器"
          source: "hackernews"
          url: "https://news.ycombinator.com/item?id=..."
          quote:
            en: "Every other tool I've tried sounds like elevator music"
            zh: "我试过的其他工具听起来都像电梯音乐"
    - description:
        en: "Free tiers are too restrictive to properly evaluate before paying"
        zh: "免费层限制太多，无法在付费前充分评估产品"
      severity: "medium"
      evidenceCount: 3
      evidence:
        - title:
            en: "Ask HN: Best AI music generator with generous free tier?"
            zh: "Ask HN: 哪款 AI 音乐生成器的免费版比较大方？"
          source: "hackernews"
          url: "https://news.ycombinator.com/item?id=..."

# 差异化策略（新增，必须双语）
differentiationStrategy:
  strategy:
    en: "Focus on batch processing and lower per-generation cost for casual creators"
    zh: "专注批量处理和更低的单次生成成本，面向 casual 创作者"
  rationale:
    en: "Top competitors charge $0.005 per generation with complex UI. A simpler tool at $0.002/generation with batch workflow can capture price-sensitive casual users."
    zh: "头部竞品单次生成约 $0.005 且界面复杂。简化 UI 后做到 $0.002/次，配合批量工作流，可以吸引对价格敏感的 casual 用户。"
  targetUser:
    en: "Casual content creators who need 200-500 generations/month"
    zh: "每月需要 200-500 次生成的 casual 内容创作者"
  keyDifferentiators:
    - en: "50% lower cost per generation than competitors"
      zh: "单次生成成本比竞品低 50%"
    - en: "Simple batch upload and download workflow"
      zh: "简单的批量上传下载工作流"
    - en: "No complex features casual users don't need"
      zh: "去掉 casual 用户不需要的复杂功能"
---
```

### 9.4 前端组件双语实现

**新增 i18n Keys**：

```typescript
// src/lib/i18n.ts

export const ui = {
  en: {
    // 竞品分析相关
    'detail.competitors.title': 'Competitor Analysis',
    'detail.competitors.pricing': 'Pricing',
    'detail.competitors.features': 'Key Features',
    'detail.competitors.weaknesses': 'Weaknesses',
    'detail.competitors.targetAudience': 'Target Audience',
    'detail.competitors.positioning': 'Positioning',
    
    // 市场空白相关
    'detail.gaps.title': 'Market Gaps',
    'detail.gaps.description': 'Opportunities identified from competitor weaknesses and user pain points',
    
    // 痛点分析相关
    'detail.pain.title': 'User Pain Points',
    'detail.pain.severity.high': 'High Impact',
    'detail.pain.severity.medium': 'Medium Impact',
    'detail.pain.severity.low': 'Low Impact',
    'detail.pain.evidence': 'Evidence from {count} discussions',
    
    // 差异化策略相关
    'detail.strategy.title': 'Differentiation Strategy',
    'detail.strategy.rationale': 'Why this wedge works',
    'detail.strategy.targetUser': 'Target User',
    'detail.strategy.keyDifferentiators': 'Key Differentiators',
    
    // 定价对比相关
    'detail.pricing.freeTier': 'Free Tier',
    'detail.pricing.paidTier': 'Paid Tier',
    'detail.pricing.perMonth': '/month',
    'detail.pricing.credits': 'credits',
    'detail.pricing.commercialUse': 'Commercial Use',
    'detail.pricing.allowed': 'Allowed',
    'detail.pricing.notAllowed': 'Not Allowed',
  },
  zh: {
    // 竞品分析相关
    'detail.competitors.title': '竞品分析',
    'detail.competitors.pricing': '定价策略',
    'detail.competitors.features': '核心功能',
    'detail.competitors.weaknesses': '产品弱点',
    'detail.competitors.targetAudience': '目标用户',
    'detail.competitors.positioning': '产品定位',
    
    // 市场空白相关
    'detail.gaps.title': '市场空白',
    'detail.gaps.description': '从竞品弱点和用户痛点中识别出的机会',
    
    // 痛点分析相关
    'detail.pain.title': '用户痛点',
    'detail.pain.severity.high': '高影响',
    'detail.pain.severity.medium': '中影响',
    'detail.pain.severity.low': '低影响',
    'detail.pain.evidence': '来自 {count} 条讨论的证据',
    
    // 差异化策略相关
    'detail.strategy.title': '差异化策略',
    'detail.strategy.rationale': '为什么这个切角有机会',
    'detail.strategy.targetUser': '目标用户',
    'detail.strategy.keyDifferentiators': '核心差异点',
    
    // 定价对比相关
    'detail.pricing.freeTier': '免费版',
    'detail.pricing.paidTier': '付费版',
    'detail.pricing.perMonth': '/月',
    'detail.pricing.credits': '积分',
    'detail.pricing.commercialUse': '商业使用',
    'detail.pricing.allowed': '允许',
    'detail.pricing.notAllowed': '不允许',
  }
};
```

**竞品卡片组件（双语）**：

```astro
---
// src/components/CompetitorCard.astro
import { getLocalizedPairText } from '../lib/idea';
import type { Lang, LocalizedPair } from '../lib/i18n';

interface Props {
  competitor: {
    domain: string;
    name: string;
    keyFeatures: LocalizedPair[];
    pricingTiers: LocalizedPricingTier[];
    weaknesses: LocalizedPair[];
    targetAudience: LocalizedPair;
    positioning: LocalizedPair;
  };
  lang: Lang;
}

const { competitor, lang } = Astro.props;
const t = ui[lang];
---

<div class="competitor-card">
  <!-- 头部：名称和定位 -->
  <div class="competitor-header">
    <h3 class="competitor-name">{competitor.name}</h3>
    <span class="competitor-domain">{competitor.domain}</span>
    <p class="competitor-positioning">
      {getLocalizedPairText(competitor.positioning, lang)}
    </p>
  </div>
  
  <!-- 定价对比 -->
  <div class="pricing-section">
    <h4>{t['detail.competitors.pricing']}</h4>
    <div class="pricing-tiers">
      {competitor.pricingTiers.map(tier => (
        <div class={`pricing-tier ${tier.price === 0 ? 'free' : 'paid'}`}>
          <span class="tier-name">{getLocalizedPairText(tier.name, lang)}</span>
          <span class="tier-price">
            {tier.price === 0 ? 'Free' : `$${tier.price}`}
            {tier.price > 0 && <span class="per-month">{t['detail.pricing.perMonth']}</span>}
          </span>
          <p class="tier-description">
            {getLocalizedPairText(tier.description, lang)}
          </p>
          {tier.limits && (
            <ul class="tier-limits">
              {tier.limits.monthlyCredits && (
                <li>{getLocalizedPairText(tier.limits.monthlyCredits, lang)}</li>
              )}
              {tier.limits.maxDuration && (
                <li>{getLocalizedPairText(tier.limits.maxDuration, lang)}</li>
              )}
              {tier.limits.commercialUse && (
                <li>
                  {t['detail.pricing.commercialUse']}: 
                  {tier.limits.commercialUse.en === 'Allowed' 
                    ? t['detail.pricing.allowed']
                    : t['detail.pricing.notAllowed']}
                </li>
              )}
            </ul>
          )}
        </div>
      ))}
    </div>
  </div>
  
  <!-- 核心功能 -->
  <div class="features-section">
    <h4>{t['detail.competitors.features']}</h4>
    <ul class="feature-list">
      {competitor.keyFeatures.map(feature => (
        <li>{getLocalizedPairText(feature, lang)}</li>
      ))}
    </ul>
  </div>
  
  <!-- 弱点分析 -->
  <div class="weaknesses-section">
    <h4>{t['detail.competitors.weaknesses']}</h4>
    <ul class="weakness-list">
      {competitor.weaknesses.map(weakness => (
        <li class="weakness-item">
          <span class="weakness-icon">⚠️</span>
          {getLocalizedPairText(weakness, lang)}
        </li>
      ))}
    </ul>
  </div>
  
  <!-- 目标用户 -->
  <div class="audience-section">
    <h4>{t['detail.competitors.targetAudience']}</h4>
    <p>{getLocalizedPairText(competitor.targetAudience, lang)}</p>
  </div>
</div>
```

**痛点卡片组件（双语）**：

```astro
---
// src/components/PainPointCard.astro
import { getLocalizedPairText } from '../lib/idea';
import type { Lang, LocalizedPair } from '../lib/i18n';

interface Props {
  pain: {
    description: LocalizedPair;
    severity: 'high' | 'medium' | 'low';
    mentions: number;
    evidence: LocalizedSourcePost[];
  };
  lang: Lang;
}

const { pain, lang } = Astro.props;
const t = ui[lang];

const severityConfig = {
  high: { label: t['detail.pain.severity.high'], color: 'rose' },
  medium: { label: t['detail.pain.severity.medium'], color: 'amber' },
  low: { label: t['detail.pain.severity.low'], color: 'slate' },
};

const severity = severityConfig[pain.severity];
---

<div class={`pain-card severity-${pain.severity}`}>
  <div class="pain-header">
    <span class={`severity-badge bg-${severity.color}-100 text-${severity.color}-700`}>
      {severity.label}
    </span>
    <span class="mentions-count">
      {t['detail.pain.evidence'].replace('{count}', String(pain.mentions))}
    </span>
  </div>
  
  <p class="pain-description">
    {getLocalizedPairText(pain.description, lang)}
  </p>
  
  {pain.evidence.length > 0 && (
    <div class="pain-evidence">
      <p class="evidence-title">Evidence:</p>
      {pain.evidence.map(item => (
        <a href={item.url} target="_blank" rel="noopener" class="evidence-link">
          {getLocalizedPairText(item.title, lang)}
        </a>
      ))}
    </div>
  )}
</div>
```

### 9.5 双语内容校验机制

**Pipeline 校验脚本**：

```python
# scripts/check_i18n.mjs（已有，需扩展）

// 新增校验规则：竞品分析和痛点分析字段必须双语
function validateCompetitorAnalysis(frontmatter, errors) {
  const analysis = frontmatter.competitorAnalysis;
  if (!analysis) return;
  
  // 校验 topCompetitors
  if (analysis.topCompetitors) {
    for (const comp of analysis.topCompetitors) {
      // keyFeatures 必须双语
      if (comp.keyFeatures) {
        for (const feature of comp.keyFeatures) {
          if (!feature.en || !feature.zh) {
            errors.push(`竞品 ${comp.name} 的 keyFeatures 必须包含 en 和 zh`);
          }
        }
      }
      
      // weaknesses 必须双语
      if (comp.weaknesses) {
        for (const weakness of comp.weaknesses) {
          if (!weakness.en || !weakness.zh) {
            errors.push(`竞品 ${comp.name} 的 weaknesses 必须包含 en 和 zh`);
          }
        }
      }
    }
  }
  
  // 校验 marketGaps
  if (analysis.marketGaps) {
    for (const gap of analysis.marketGaps) {
      if (!gap.en || !gap.zh) {
        errors.push('marketGaps 每项必须包含 en 和 zh');
      }
    }
  }
}

function validatePainAnalysis(frontmatter, errors) {
  const analysis = frontmatter.painAnalysis;
  if (!analysis) return;
  
  if (analysis.topPains) {
    for (const pain of analysis.topPains) {
      if (!pain.description?.en || !pain.description?.zh) {
        errors.push('painAnalysis.topPains 每项 description 必须包含 en 和 zh');
      }
    }
  }
}

function validateDifferentiationStrategy(frontmatter, errors) {
  const strategy = frontmatter.differentiationStrategy;
  if (!strategy) return;
  
  if (!strategy.strategy?.en || !strategy.strategy?.zh) {
    errors.push('differentiationStrategy.strategy 必须包含 en 和 zh');
  }
  
  if (!strategy.rationale?.en || !strategy.rationale?.zh) {
    errors.push('differentiationStrategy.rationale 必须包含 en 和 zh');
  }
}
```

### 9.6 实施检查清单

**数据层**：
- [ ] `CompetitorProfile` 所有可展示字段使用 `LocalizedPair`
- [ ] `PainPoint` description 和 evidence 使用 `LocalizedPair`
- [ ] `DifferentiationStrategy` 所有字段使用 `LocalizedPair`
- [ ] LLM Prompt 要求双语输出
- [ ] 生成脚本校验双语完整性

**Frontmatter**：
- [ ] `competitorAnalysis.topCompetitors[].keyFeatures` 双语
- [ ] `competitorAnalysis.topCompetitors[].weaknesses` 双语
- [ ] `competitorAnalysis.topCompetitors[].targetAudience` 双语
- [ ] `competitorAnalysis.topCompetitors[].positioning` 双语
- [ ] `competitorAnalysis.marketGaps` 双语
- [ ] `painAnalysis.topPains[].description` 双语
- [ ] `painAnalysis.topPains[].evidence[].title` 双语
- [ ] `differentiationStrategy.strategy` 双语
- [ ] `differentiationStrategy.rationale` 双语
- [ ] `differentiationStrategy.targetUser` 双语
- [ ] `differentiationStrategy.keyDifferentiators` 双语

**前端组件**：
- [ ] 新增 i18n keys 覆盖所有新增 UI 元素
- [ ] `CompetitorCard` 使用 `getLocalizedPairText`
- [ ] `PainPointCard` 使用 `getLocalizedPairText`
- [ ] `MarketGaps` 使用 `getLocalizedPairText`
- [ ] `DifferentiationStrategy` 使用 `getLocalizedPairText`

**校验脚本**：
- [ ] `check_i18n.mjs` 扩展校验新字段
- [ ] CI 流程集成双语校验
- [ ] 构建失败时提示缺失的翻译

---

*文档版本: 1.1*
*更新日期: 2026-04-07*
*更新内容: 补充中英文切换实现方案（第9章）*
