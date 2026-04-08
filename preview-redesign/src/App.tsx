import { useState } from 'react';
import { 
  ArrowLeft, 
  TrendingUp, 
  Users, 
  Zap, 
  Target, 
  DollarSign, 
  AlertTriangle,
  Clock,
  ChevronDown,
  ChevronUp,
  Share2,
  Download,
  Copy,
  Mail,
  CheckCircle2,
  ExternalLink,
  BarChart3,
  Sparkles,
  Shield,
  Lightbulb
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Input } from '@/components/ui/input';

// 模拟数据
const ideaData = {
  title: 'AI Music Generator for Content Creators',
  titleZh: '面向内容创作者的 AI 音乐生成器',
  description: 'Generate royalty-free background music for videos, podcasts, and streams with AI.',
  descriptionZh: '为视频、播客和直播生成免版税的背景音乐。',
  category: 'AI Tools',
  verdict: 'Worth Building',
  confidence: 'High',
  score: 82,
  opportunityScore: {
    demand: 4,
    competition: 3,
    barrier: 2,
    monetization: 5
  },
  metrics: {
    trendChange: '+23%',
    competitorCount: 3,
    validationWeeks: '2-4',
    tamEstimate: '$50M+'
  },
  trendData: [
    { date: 'Jan', value: 45 },
    { date: 'Feb', value: 52 },
    { date: 'Mar', value: 48 },
    { date: 'Apr', value: 58 },
    { date: 'May', value: 65 },
    { date: 'Jun', value: 72 },
    { date: 'Jul', value: 78 }
  ]
};

function StarRating({ value, max = 5 }: { value: number; max?: number }) {
  return (
    <div className="flex gap-0.5">
      {Array.from({ length: max }).map((_, i) => (
        <Sparkles
          key={i}
          className={`w-4 h-4 ${i < value ? 'text-amber-400 fill-amber-400' : 'text-slate-200'}`}
        />
      ))}
    </div>
  );
}

function ScoreBar({ label, value, color }: { label: string; value: number; color: string }) {
  const colors: Record<string, string> = {
    emerald: 'bg-emerald-500',
    amber: 'bg-amber-500',
    rose: 'bg-rose-500',
    sky: 'bg-sky-500'
  };
  
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs">
        <span className="text-slate-600">{label}</span>
        <span className="font-medium text-slate-900">{value}/5</span>
      </div>
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
        <div 
          className={`h-full ${colors[color]} rounded-full transition-all duration-500`}
          style={{ width: `${(value / 5) * 100}%` }}
        />
      </div>
    </div>
  );
}

function TrendChart() {
  const maxValue = Math.max(...ideaData.trendData.map(d => d.value));
  const minValue = Math.min(...ideaData.trendData.map(d => d.value));
  const range = maxValue - minValue || 1;
  const dataCount = ideaData.trendData.length;
  
  // Fixed aspect ratio: 7 data points width, 100 height
  const viewBoxWidth = (dataCount - 1) * 20;
  const viewBoxHeight = 100;
  const paddingX = 10;
  
  const points = ideaData.trendData.map((d, i) => {
    const x = i * 20 + paddingX;
    const y = viewBoxHeight - ((d.value - minValue) / range) * 70 - 15;
    return `${x},${y}`;
  }).join(' ');
  
  const areaPoints = `${points} ${viewBoxWidth + paddingX},${viewBoxHeight} ${paddingX},${viewBoxHeight}`;
  
  return (
    <div className="h-32 w-full">
      <svg 
        viewBox={`0 0 ${viewBoxWidth + paddingX * 2} ${viewBoxHeight}`} 
        className="w-full h-full" 
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <linearGradient id="trendGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#0ea5e9" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#0ea5e9" stopOpacity="0" />
          </linearGradient>
        </defs>
        <polygon 
          points={areaPoints}
          fill="url(#trendGradient)"
        />
        <polyline
          points={points}
          fill="none"
          stroke="#0284c7"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* Data point dots */}
        {ideaData.trendData.map((d, i) => {
          const x = i * 20 + paddingX;
          const y = viewBoxHeight - ((d.value - minValue) / range) * 70 - 15;
          return (
            <circle
              key={i}
              cx={x}
              cy={y}
              r="3.5"
              fill="#0284c7"
              stroke="#fff"
              strokeWidth="2"
            />
          );
        })}
      </svg>
    </div>
  );
}

export default function App() {
  const [lang, setLang] = useState<'en' | 'zh'>('zh');
  const [breakdownOpen, setBreakdownOpen] = useState(false);
  const [email, setEmail] = useState('');
  const [subscribed, setSubscribed] = useState(false);

  const t = {
    en: {
      back: 'Back',
      verdict: 'Verdict',
      confidence: 'Confidence',
      opportunityScore: 'Opportunity Score',
      demand: 'Demand Strength',
      competition: 'Competition Space',
      barrier: 'Entry Barrier',
      monetizationPotential: 'Monetization Potential',
      evidence: 'Demand Evidence',
      painPoints: 'User Pain Points',
      marketLandscape: 'Market Landscape',
      entryStrategy: 'Entry Strategy',
      monetization: 'Monetization',
      risks: 'Risks & Considerations',
      deepDive: 'Deep Dive',
      keyMetrics: 'Key Metrics',
      quickActions: 'Quick Actions',
      subscribe: 'Subscribe',
      subscribers: '1,200+ subscribers',
      weeklyIdeas: '3 verified Micro SaaS ideas weekly',
      worthBuilding: 'Worth Building',
      watch: 'Watch',
      skip: 'Skip'
    },
    zh: {
      back: '返回',
      verdict: '核心结论',
      confidence: '置信度',
      opportunityScore: '机会评分',
      demand: '需求强度',
      competition: '竞争空间',
      barrier: '进入门槛',
      monetizationPotential: '变现潜力',
      evidence: '需求证据',
      painPoints: '用户痛点',
      marketLandscape: '市场格局',
      entryStrategy: '切入策略',
      monetization: '变现路径',
      risks: '风险与注意事项',
      deepDive: '深度拆解',
      keyMetrics: '关键数据',
      quickActions: '快速行动',
      subscribe: '订阅',
      subscribers: '1,200+ 订阅者',
      weeklyIdeas: '每周 3 个经过验证的 Micro SaaS 机会',
      worthBuilding: '值得构建',
      watch: '持续关注',
      skip: '建议跳过'
    }
  }[lang];

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <Button variant="ghost" size="sm" className="text-slate-600">
            <ArrowLeft className="w-4 h-4 mr-2" />
            {t.back}
          </Button>
          <div className="flex gap-2">
            <Button 
              variant={lang === 'en' ? 'default' : 'ghost'} 
              size="sm"
              onClick={() => setLang('en')}
            >
              EN
            </Button>
            <Button 
              variant={lang === 'zh' ? 'default' : 'ghost'} 
              size="sm"
              onClick={() => setLang('zh')}
            >
              中文
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="grid gap-8 lg:grid-cols-[1fr_340px] lg:items-start">
          {/* Main Column */}
          <div className="space-y-8">
            {/* Hero Section */}
            <section className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="p-8">
                <div className="flex flex-wrap gap-2 mb-4">
                  <Badge variant="secondary" className="bg-sky-50 text-sky-700 hover:bg-sky-100">
                    {ideaData.category}
                  </Badge>
                  <Badge className="bg-emerald-50 text-emerald-700 hover:bg-emerald-100">
                    ✅ {t.worthBuilding}
                  </Badge>
                </div>
                
                <h1 className="text-3xl sm:text-4xl font-black text-slate-900 tracking-tight">
                  {lang === 'zh' ? ideaData.titleZh : ideaData.title}
                </h1>
                <p className="mt-3 text-lg text-slate-600 leading-relaxed">
                  {lang === 'zh' ? ideaData.descriptionZh : ideaData.description}
                </p>

                {/* Opportunity Score Card */}
                <div className="mt-6 p-6 bg-slate-50 rounded-2xl border border-slate-100">
                  <div className="flex items-center gap-2 mb-4">
                    <Target className="w-5 h-5 text-slate-700" />
                    <h3 className="font-bold text-slate-900">{t.opportunityScore}</h3>
                    <span className="ml-auto text-2xl font-black text-slate-900">
                      {ideaData.score}
                      <span className="text-sm font-normal text-slate-400">/100</span>
                    </span>
                  </div>
                  <div className="grid sm:grid-cols-2 gap-4">
                    <ScoreBar label={t.demand} value={ideaData.opportunityScore.demand} color="emerald" />
                    <ScoreBar label={t.competition} value={ideaData.opportunityScore.competition} color="amber" />
                    <ScoreBar label={t.barrier} value={ideaData.opportunityScore.barrier} color="sky" />
                    <ScoreBar label={t.monetizationPotential} value={ideaData.opportunityScore.monetization} color="emerald" />
                  </div>
                </div>
              </div>
            </section>

            {/* Evidence Section */}
            <section className="bg-white rounded-3xl border border-slate-200 shadow-sm p-8">
              <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-sky-600" />
                {t.evidence}
              </h2>
              
              {/* Signal Cards */}
              <div className="grid sm:grid-cols-3 gap-4 mt-5">
                <Card className="border-sky-100 bg-sky-50/50">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2 text-sky-700">
                      <TrendingUp className="w-4 h-4" />
                      <span className="text-xs font-semibold uppercase tracking-wider">Search Trend</span>
                    </div>
                    <p className="mt-2 text-2xl font-black text-slate-900">{ideaData.metrics.trendChange}</p>
                    <p className="text-xs text-slate-500">Last 90 days</p>
                  </CardContent>
                </Card>
                <Card className="border-orange-100 bg-orange-50/50">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2 text-orange-700">
                      <Users className="w-4 h-4" />
                      <span className="text-xs font-semibold uppercase tracking-wider">Community</span>
                    </div>
                    <p className="mt-2 text-2xl font-black text-slate-900">High</p>
                    <p className="text-xs text-slate-500">Reddit + HN mentions</p>
                  </CardContent>
                </Card>
                <Card className="border-violet-100 bg-violet-50/50">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2 text-violet-700">
                      <Zap className="w-4 h-4" />
                      <span className="text-xs font-semibold uppercase tracking-wider">Gap Found</span>
                    </div>
                    <p className="mt-2 text-2xl font-black text-slate-900">3</p>
                    <p className="text-xs text-slate-500">Market gaps identified</p>
                  </CardContent>
                </Card>
              </div>

              {/* Trend Chart */}
              <div className="mt-6 p-4 bg-sky-50/50 rounded-2xl border border-sky-100">
                <TrendChart />
                <div className="flex justify-between mt-2 text-xs text-slate-500">
                  {ideaData.trendData.map(d => (
                    <span key={d.date}>{d.date}</span>
                  ))}
                </div>
              </div>
            </section>

            {/* Pain Points */}
            <section className="bg-white rounded-3xl border border-slate-200 shadow-sm p-8">
              <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-orange-500" />
                {t.painPoints}
              </h2>
              <div className="grid sm:grid-cols-2 gap-3 mt-5">
                {[
                  'Royalty-free music libraries are expensive and limited',
                  'Existing AI tools lack genre customization',
                  'Content creators need quick turnaround'
                ].map((pain, i) => (
                  <div key={i} className="flex items-start gap-3 p-4 bg-orange-50 rounded-2xl border border-orange-100">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-orange-500 text-white text-xs font-bold flex items-center justify-center">
                      {i + 1}
                    </span>
                    <p className="text-sm font-medium text-slate-800">{pain}</p>
                  </div>
                ))}
              </div>
            </section>

            {/* Market Landscape */}
            <section className="bg-white rounded-3xl border border-slate-200 shadow-sm p-8">
              <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                <Target className="w-5 h-5 text-violet-600" />
                {t.marketLandscape}
              </h2>
              
              {/* Competitor Cards */}
              <div className="grid sm:grid-cols-3 gap-4 mt-5">
                {[
                  { name: 'Soundraw', price: '$19.99/mo', weakness: 'Limited genres' },
                  { name: 'Boomy', price: '$9.99/mo', weakness: 'Quality inconsistent' },
                  { name: 'AIVA', price: '€15/mo', weakness: 'Complex UI' }
                ].map((comp) => (
                  <Card key={comp.name} className="border-slate-200 hover:border-slate-300 transition-colors">
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <h4 className="font-bold text-slate-900">{comp.name}</h4>
                        <ExternalLink className="w-4 h-4 text-slate-400" />
                      </div>
                      <p className="text-sm text-slate-500 mt-1">{comp.price}</p>
                      <div className="mt-3 flex items-center gap-1.5 text-xs text-amber-700">
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                        {comp.weakness}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>

              {/* Market Gaps */}
              <div className="mt-5 p-4 bg-violet-50 rounded-2xl border border-violet-100">
                <h4 className="font-semibold text-violet-900 flex items-center gap-2">
                  <Lightbulb className="w-4 h-4" />
                  Market Gaps
                </h4>
                <ul className="mt-3 space-y-2">
                  {[
                    'No affordable option for casual creators',
                    'Missing social media-optimized formats',
                    'No real-time collaboration features'
                  ].map((gap, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-violet-800">
                      <span className="flex-shrink-0 w-5 h-5 rounded-full bg-violet-200 text-violet-700 text-xs font-bold flex items-center justify-center">
                        {i + 1}
                      </span>
                      {gap}
                    </li>
                  ))}
                </ul>
              </div>
            </section>

            {/* Entry Strategy */}
            <section className="bg-white rounded-3xl border border-slate-200 shadow-sm p-8">
              <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                <Zap className="w-5 h-5 text-amber-500" />
                {t.entryStrategy}
              </h2>
              
              {/* Timeline */}
              <div className="mt-5 space-y-4">
                {[
                  { phase: 'Phase 1', title: 'MVP', weeks: 'Week 1-2', desc: 'Basic text-to-music, 3 genres' },
                  { phase: 'Phase 2', title: 'Validation', weeks: 'Week 3-4', desc: 'Beta with 50 creators, collect feedback' },
                  { phase: 'Phase 3', title: 'Launch', weeks: 'Month 2', desc: 'Product Hunt launch, pricing tiers' }
                ].map((item, i) => (
                  <div key={i} className="flex gap-4">
                    <div className="flex flex-col items-center">
                      <div className="w-8 h-8 rounded-full bg-slate-900 text-white text-xs font-bold flex items-center justify-center">
                        {i + 1}
                      </div>
                      {i < 2 && <div className="w-0.5 flex-1 bg-slate-200 my-2" />}
                    </div>
                    <div className="flex-1 pb-4">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-sky-600 uppercase">{item.phase}</span>
                        <span className="text-xs text-slate-400">·</span>
                        <span className="text-xs text-slate-500">{item.weeks}</span>
                      </div>
                      <h4 className="font-bold text-slate-900 mt-1">{item.title}</h4>
                      <p className="text-sm text-slate-600 mt-1">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* Monetization */}
            <section className="bg-white rounded-3xl border border-slate-200 shadow-sm p-8">
              <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                <DollarSign className="w-5 h-5 text-emerald-600" />
                {t.monetization}
              </h2>
              
              <div className="grid sm:grid-cols-3 gap-4 mt-5">
                {[
                  { tier: 'Free', price: '$0', features: '5 tracks/mo, basic genres' },
                  { tier: 'Pro', price: '$12/mo', features: 'Unlimited, all genres, commercial use' },
                  { tier: 'Team', price: '$29/mo', features: '5 seats, API access, priority support' }
                ].map((plan) => (
                  <Card key={plan.tier} className={`${plan.tier === 'Pro' ? 'border-emerald-200 bg-emerald-50/30' : 'border-slate-200'}`}>
                    <CardContent className="p-4">
                      <h4 className="font-bold text-slate-900">{plan.tier}</h4>
                      <p className="text-2xl font-black text-slate-900 mt-1">{plan.price}</p>
                      <p className="text-xs text-slate-500 mt-2">{plan.features}</p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </section>

            {/* Risks */}
            <section className="bg-white rounded-3xl border border-slate-200 shadow-sm p-8">
              <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                <Shield className="w-5 h-5 text-amber-600" />
                {t.risks}
              </h2>
              
              <div className="mt-5 space-y-3">
                {[
                  { risk: 'Copyright concerns with AI-generated music', mitigation: 'Clear TOS, watermarking, human-in-the-loop review' },
                  { risk: 'Big players (Adobe, Canva) may enter', mitigation: 'Focus on niche features, community building' },
                  { risk: 'Quality perception vs human composers', mitigation: 'A/B testing, user education, free trials' }
                ].map((item, i) => (
                  <div key={i} className="p-4 bg-amber-50/60 rounded-2xl border border-amber-100">
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 w-6 h-6 rounded-full bg-amber-100 flex items-center justify-center mt-0.5">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />
                      </div>
                      <div>
                        <p className="font-medium text-amber-900">{item.risk}</p>
                        <p className="text-sm text-amber-800/80 mt-1">
                          <span className="font-medium">Mitigation:</span> {item.mitigation}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-5 p-4 bg-slate-50 rounded-2xl border border-slate-100">
                <p className="text-sm text-slate-600">
                  <span className="font-medium text-slate-800">Not for:</span> Teams needing enterprise-grade compliance, classical music composers
                </p>
              </div>
            </section>

            {/* Deep Dive (Collapsible) */}
            <section className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
              <button
                onClick={() => setBreakdownOpen(!breakdownOpen)}
                className="w-full p-6 flex items-center justify-between hover:bg-slate-50 transition-colors"
              >
                <h2 className="text-xl font-bold text-slate-900">{t.deepDive}</h2>
                {breakdownOpen ? (
                  <ChevronUp className="w-5 h-5 text-slate-400" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-slate-400" />
                )}
              </button>
              {breakdownOpen && (
                <div className="px-6 pb-6 border-t border-slate-100">
                  <div className="pt-6 space-y-6">
                    <div>
                      <h3 className="font-bold text-slate-900">Technical Architecture</h3>
                      <p className="text-sm text-slate-600 mt-2">
                        Recommended stack: React + Web Audio API for frontend, Python + FastAPI backend, 
                        MusicGen/AudioLDM2 for generation. Deploy on Vercel + Railway.
                      </p>
                    </div>
                    <div>
                      <h3 className="font-bold text-slate-900">Go-to-Market Strategy</h3>
                      <p className="text-sm text-slate-600 mt-2">
                        Start with YouTube creator community, partner with video editing tool integrations,
                        leverage TikTok/Instagram Reels trend for short-form content music.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </section>

            {/* CTA Section */}
            <section className="bg-slate-900 rounded-3xl p-8 text-white">
              <div className="flex items-center gap-2 text-blue-200">
                <Mail className="w-5 h-5" />
                <span className="font-semibold">Weekly Micro SaaS Ideas</span>
              </div>
              <h2 className="text-2xl font-bold mt-3">{t.weeklyIdeas}</h2>
              <p className="text-slate-400 mt-2">Join {t.subscribers} getting verified opportunities every week.</p>
              
              <div className="mt-6 flex gap-3">
                <Input 
                  placeholder="your@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="bg-white/10 border-white/20 text-white placeholder:text-slate-500"
                />
                <Button 
                  onClick={() => setSubscribed(true)}
                  className="bg-white text-slate-900 hover:bg-slate-100"
                >
                  {subscribed ? (
                    <>
                      <CheckCircle2 className="w-4 h-4 mr-2" />
                      Subscribed
                    </>
                  ) : (
                    t.subscribe
                  )}
                </Button>
              </div>
            </section>
          </div>

          {/* Sidebar */}
          <aside className="space-y-6 lg:sticky lg:top-24">
            {/* Opportunity Overview */}
            <Card className="border-slate-200 shadow-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Target className="w-5 h-5 text-slate-700" />
                  {t.opportunityScore}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-600">{t.demand}</span>
                  <StarRating value={ideaData.opportunityScore.demand} />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-600">{t.competition}</span>
                  <Badge variant="outline" className="text-amber-600 border-amber-200 bg-amber-50">
                    Moderate
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-600">{t.barrier}</span>
                  <Badge variant="outline" className="text-emerald-600 border-emerald-200 bg-emerald-50">
                    Low
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-600">{t.monetizationPotential}</span>
                  <StarRating value={ideaData.opportunityScore.monetization} />
                </div>
                <Separator />
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-500">{t.confidence}</span>
                  <span className="font-medium text-emerald-600 flex items-center gap-1">
                    <CheckCircle2 className="w-4 h-4" />
                    High
                  </span>
                </div>
                <div className="text-xs text-slate-400">
                  Updated: April 8, 2026
                </div>
              </CardContent>
            </Card>

            {/* Key Metrics */}
            <Card className="border-slate-200 shadow-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg">{t.keyMetrics}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl">
                  <div className="flex items-center gap-2 text-slate-600">
                    <TrendingUp className="w-4 h-4" />
                    <span className="text-sm">Search Trend</span>
                  </div>
                  <span className="font-bold text-emerald-600">{ideaData.metrics.trendChange}</span>
                </div>
                <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl">
                  <div className="flex items-center gap-2 text-slate-600">
                    <Target className="w-4 h-4" />
                    <span className="text-sm">Competitors</span>
                  </div>
                  <span className="font-bold text-slate-900">{ideaData.metrics.competitorCount}</span>
                </div>
                <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl">
                  <div className="flex items-center gap-2 text-slate-600">
                    <Clock className="w-4 h-4" />
                    <span className="text-sm">Validation</span>
                  </div>
                  <span className="font-bold text-slate-900">{ideaData.metrics.validationWeeks}</span>
                </div>
                <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl">
                  <div className="flex items-center gap-2 text-slate-600">
                    <DollarSign className="w-4 h-4" />
                    <span className="text-sm">Est. TAM</span>
                  </div>
                  <span className="font-bold text-slate-900">{ideaData.metrics.tamEstimate}</span>
                </div>
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <Card className="border-slate-200 shadow-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg">{t.quickActions}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <Button variant="outline" className="w-full justify-start gap-2">
                  <Copy className="w-4 h-4" />
                  Copy Keywords
                </Button>
                <Button variant="outline" className="w-full justify-start gap-2">
                  <Download className="w-4 h-4" />
                  Download Report
                </Button>
                <Button variant="outline" className="w-full justify-start gap-2">
                  <Share2 className="w-4 h-4" />
                  Share
                </Button>
              </CardContent>
            </Card>

            {/* Subscribe Card */}
            <Card className="bg-slate-900 text-white border-slate-800">
              <CardContent className="p-6">
                <Mail className="w-8 h-8 text-blue-400 mb-3" />
                <h3 className="font-bold text-lg">Get More Ideas</h3>
                <p className="text-sm text-slate-400 mt-2">
                  {t.weeklyIdeas}
                </p>
                <div className="mt-4 space-y-2">
                  <Input 
                    placeholder="your@email.com"
                    className="bg-white/10 border-white/20 text-white placeholder:text-slate-500"
                  />
                  <Button className="w-full bg-white text-slate-900 hover:bg-slate-100">
                    {t.subscribe}
                  </Button>
                </div>
                <p className="text-xs text-slate-500 mt-3 text-center">
                  {t.subscribers}
                </p>
              </CardContent>
            </Card>
          </aside>
        </div>
      </main>
    </div>
  );
}
