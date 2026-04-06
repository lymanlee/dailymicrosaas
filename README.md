# Daily Micro SaaS

每天拆解一个真实、有验证信号、适合快速做成 MVP 的 Micro SaaS 方向。

## 项目定位

`Daily Micro SaaS` 现在不只是一个 Astro 静态站，它已经把内容生产链路也并进来了：

- **展示层**：Astro + Tailwind，负责首页、归档页、详情页和 SEO
- **生产层**：Python pipeline，负责发现机会、生成报告、转成站点内容、自动发布
- **部署层**：GitHub + Cloudflare Pages，`main` 分支自动部署

## 技术栈

- **站点**: Astro 5 + Tailwind CSS
- **内容**: Markdown + Astro Content Collections
- **发现 pipeline**: Python
- **部署**: GitHub Actions + Cloudflare Pages

## 本地开发

```bash
npm install
npm run dev
npm run build
```

## 内容自动化链路

### 安装 Python 依赖

```bash
python3 -m pip install -r requirements.txt
```

### 只跑机会发现

```bash
npm run content:discover
# 或
python3 scripts/run_discovery.py --date 2026-04-04
```

输出会落到：

- `pipeline/reports/opportunity_report_YYYY-MM-DD.json`
- `pipeline/reports/opportunity_report_YYYY-MM-DD.txt`

### 基于报告生成内容

```bash
npm run content:generate
# 或
python3 scripts/generate_idea.py --date 2026-04-04 --mode overwrite
```

默认输出到：

- `src/content/ideas/*.md`

### 运行完整自动发布链路

```bash
npm run content:publish
# 或
python3 scripts/run_daily_publish.py --mode overwrite --commit --push
```

完整流程：

1. 生成结构化机会报告
2. 先做 discovery 质量门槛校验（没有 `worth_it` 或出现严重告警就中止）
3. 自动挑选一个未发布过的高分题目
4. 生成 `src/content/ideas/*.md`
5. 校验 Markdown 结构与内容质量
6. 执行 `npm run build`
7. 只有全部通过后才会自动 `git commit` + `git push`
8. 由 Cloudflare Pages 自动部署上线

## 自动发布工作流

仓库内已包含：

- `.github/workflows/daily-publish.yml`：每天北京时间 08:05 自动生成并发布内容；支持手动覆盖 `min_score`、`skip_*`、`dry_run` 等参数；失败时会保留日志、报告、运行摘要 artifact，并把关键 warnings/errors 直接转成 Actions 注释；如已配置 `PUBLISH_FAILURE_WEBHOOK_URL`，还会额外发送 webhook 告警
- `.github/workflows/deploy.yml`：`main` 分支更新后自动部署到 Cloudflare Pages；如需在线上打开邮件订阅入口，需额外配置仓库 Variable `PUBLIC_EMAIL_SUBSCRIBE_URL`
- 固定排障文档见：`pipeline/DAILY_PUBLISH_SOP.md`
- 首次生产配置与真实日跑 checklist 见：`pipeline/FIRST_PRODUCTION_RUN_CHECKLIST.md`

## 项目结构

```text
dailymicrosaas/
├── pipeline/                  # 内容发现与发布自动化
│   ├── data/
│   ├── discovery/
│   ├── publishing/
│   └── README.md
├── public/                    # 静态资源
├── scripts/                   # 兼容入口脚本
├── src/
│   ├── components/
│   ├── content/
│   │   └── ideas/             # 站点最终消费的内容
│   ├── layouts/
│   ├── lib/
│   ├── pages/
│   └── styles/
├── requirements.txt           # Python pipeline 依赖
└── package.json
```

## 配置说明

### 可选环境变量

仓库根目录支持本地 `.env`，`pipeline/discovery/step2_community_scan.py` 会优先读取它；Astro 本地构建也会读取同一个 `.env`。

```bash
cp .env.example .env
```

常用项：

- `GITHUB_TOKEN`: 提高 GitHub API 限额，也可用于自动发布时的提交/推送
- `REDDIT_CLIENT_ID`: Reddit app 的 client id，用于社区扫描走 OAuth
- `REDDIT_CLIENT_SECRET`: Reddit app 的 client secret
- `REDDIT_USER_AGENT`: 推荐显式设置，格式建议为 `<app_name>/<version> by <reddit_username>`
- `PUBLIC_EMAIL_SUBSCRIBE_URL`: 可选，供本地 Astro 构建/预览时打开邮件订阅入口

示例：

```bash
GITHUB_TOKEN=ghp_xxx
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=DailyMicroSaaS/0.1 by your_reddit_username
PUBLIC_EMAIL_SUBSCRIBE_URL=https://example.com/newsletter
```

如果不配 Reddit OAuth，程序仍会回退到公开 JSON 搜索端点，但稳定性和限流表现都更差，不适合作为长期默认方案。

### GitHub Actions Secrets / Variables

自动发布工作流 `.github/workflows/daily-publish.yml` 现在会读取以下仓库 Secrets：

- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `REDDIT_USER_AGENT`（建议配置）
- `PUBLISH_FAILURE_WEBHOOK_URL`（可选，失败告警）
- `CLOUDFLARE_API_TOKEN`（部署必需，由 `.github/workflows/deploy.yml` 使用）
- `CLOUDFLARE_ACCOUNT_ID`（部署必需，由 `.github/workflows/deploy.yml` 使用）

另外，部署工作流会在构建时读取仓库 Variable：

- `PUBLIC_EMAIL_SUBSCRIBE_URL`（可选，用于打开 `/subscribe` 页面和 CTA 组件中的邮件订阅入口）

这样 Actions 里的社区扫描会优先使用 Reddit OAuth，而不是匿名公开接口；部署时如果配置了 `PUBLIC_EMAIL_SUBSCRIBE_URL`，线上构建也会带上邮件订阅入口。

更细的 Reddit app 创建与 GitHub Secrets 配置步骤见：`pipeline/REDDIT_OAUTH_SETUP.md`

首次补齐生产配置并执行真实日跑，直接按：`pipeline/FIRST_PRODUCTION_RUN_CHECKLIST.md`

## 补充说明

- `src/content/ideas/template.md` 仍保留为人工写作模板
- 自动生成内容会带上 `sourceKeyword` / `sourceScore` / `sourceGrade`，方便后续去重和追踪来源
- `pipeline/reports`、`pipeline/logs`、趋势/社区缓存默认不进入 Git

更细的 pipeline 说明见：`pipeline/README.md`
