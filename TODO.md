# Daily Micro SaaS - TODO

## 当前阶段：MVP 已上线，自动发布链路已打通

- 线上状态：已部署到 Cloudflare Pages，当前使用 `pages.dev` 默认域名
- 内容生产：`discover -> generate -> validate -> build` 已可本地完整跑通
- 当前重点：把 GitHub 定时日跑跑稳，并持续积累高质量内容

---

## P0 - 当前优先级

- [ ] 在 GitHub Actions 上补齐生产环境 secrets / variables，并按 `pipeline/FIRST_PRODUCTION_RUN_CHECKLIST.md` 完成首次真实定时日跑
- [x] 收敛 `daily-publish` 工作流参数与失败告警，确保问题可追踪
- [x] 把 discovery / publish 运行摘要沉淀成固定排障 SOP
- [ ] 检查首页、归档页、详情页在真实内容增多后的展示与可读性

## P1 - 近期迭代

- [ ] 累积至少 30 篇有效 idea 内容
- [ ] 优化关键词评分与 SERP 竞争判断，减少低价值候选
- [ ] 增加 RSS / 邮件订阅入口
- [ ] 补强首页与 About 页文案，提升站点定位与 SEO 表达
- [ ] 评估并接入正式自定义域名

## P2 - 商业化准备

- [ ] 设计免费摘要 / 深度完整版的内容分层
- [ ] 增加邮箱收集与用户反馈闭环
- [ ] 设计可售卖的衍生产品形态（模板、报告、数据库或会员）
- [ ] 评估登录、支付与权限控制的最小实现方案

---

## 已完成

- [x] Astro 站点基础结构与 Tailwind 视觉体系
- [x] 首页、归档页、关于页、404、详情页等核心页面
- [x] Markdown 内容模型与 `src/content/ideas/` 发布链路
- [x] discovery / generate / validate / daily publish Python pipeline
- [x] Cloudflare Pages 基础部署与 GitHub Actions 部署流程
- [x] 本地真实数据端到端日跑验证，并修复 DDG redirect / 空 SERP 缓存锁死问题
- [x] 中英双语基础文案与站点展示

---

## 常用命令

```bash
cd /Users/lymanli/WorkBuddy/Claw/dailymicrosaas

npm run dev
npm run build
npm run content:discover
npm run content:generate -- --date YYYY-MM-DD
npm run content:publish -- --date YYYY-MM-DD
```

## 备注

- 当前正式内容目录是 `src/content/ideas/`。
- `dist/`、`.astro/`、`node_modules/` 属于构建产物、缓存或依赖目录，按需本地重建即可，不作为仓库结构中的业务目录。 
