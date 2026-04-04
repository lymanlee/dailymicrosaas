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

- `.github/workflows/daily-publish.yml`：每天北京时间 08:05 自动生成并发布内容；失败时会保留日志、报告、运行摘要 artifact，并支持通过 `PUBLISH_FAILURE_WEBHOOK_URL` 发送 webhook 告警
- `.github/workflows/deploy.yml`：`main` 分支更新后自动部署到 Cloudflare Pages

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

- `GITHUB_TOKEN`: 提高 GitHub API 限额，也可用于自动发布时的提交/推送

可放在仓库根目录 `.env` 中：

```bash
GITHUB_TOKEN=ghp_xxx
```

## 补充说明

- `src/content/ideas/template.md` 仍保留为人工写作模板
- 自动生成内容会带上 `sourceKeyword` / `sourceScore` / `sourceGrade`，方便后续去重和追踪来源
- `pipeline/reports`、`pipeline/logs`、趋势/社区缓存默认不进入 Git

更细的 pipeline 说明见：`pipeline/README.md`
