# 内容自动化发布链路

这套 pipeline 现在已经并入 `dailymicrosaas` 仓库，不再依赖仓库外的 `demand-discovery` 目录。

## 目录结构

```text
pipeline/
├── data/
│   └── seed_roots.json          # 种子词与黑名单配置
├── discovery/
│   ├── pipeline_common.py       # 公共配置、评分、目录定位
│   ├── step1_trend_discovery.py # Google Trends 抓取
│   ├── step2_community_scan.py  # HN + GitHub 社区信号
│   ├── step3_serp_analysis.py   # 可选 SERP 解析
│   └── run_pipeline.py          # 结构化机会报告生成
├── publishing/
│   ├── generate_idea.py         # 把报告转成 Markdown 内容
│   ├── validate_idea.py         # 生成内容结构校验
│   └── run_daily_publish.py     # 完整自动发布编排
├── reports/                     # 运行时生成，默认忽略提交
└── logs/                        # 运行时日志，默认忽略提交
```

## 运行前准备

```bash
npm install
python3 -m pip install -r requirements.txt
```

可选环境变量：

- `GITHUB_TOKEN`: 提高 GitHub API 限额，也可供自动发布工作流提交/推送时复用。

`.env` 放在仓库根目录即可，例如：

```bash
GITHUB_TOKEN=ghp_xxx
```

## 常用命令

### 1. 只跑机会发现

```bash
python3 scripts/run_discovery.py --date 2026-04-04
```

输出：

- `pipeline/reports/opportunity_report_YYYY-MM-DD.json`
- `pipeline/reports/opportunity_report_YYYY-MM-DD.txt`

### 2. 基于报告生成站点内容

```bash
python3 scripts/generate_idea.py --date 2026-04-04 --mode overwrite
```

默认输出到 `src/content/ideas/`。

关键参数：

- `--report`: 显式指定报告路径
- `--min-score`: 最低分数阈值
- `--allow-repeat`: 允许重复发布历史上已经出现过的关键词
- `--mode skip|overwrite|fail`: 文件已存在时的处理方式
- `--dry-run`: 只选题，不写文件

### 3. 跑完整自动发布链路

```bash
python3 scripts/run_daily_publish.py --mode overwrite --commit --push
```

它会依次执行：

1. discovery pipeline
2. 选题并生成 `src/content/ideas/*.md`
3. 校验 Markdown 结构
4. `npm run build`
5. `git commit`
6. `git push origin main`

推送后由 Cloudflare Pages 自动部署。

## GitHub Actions

仓库内新增了 `.github/workflows/daily-publish.yml`：

- 每天北京时间 **08:05** 自动运行（UTC `00:05`）
- 也支持手动触发，可选择 `skip_trends / skip_community / skip_serp / dry_run`
- 工作流只有在 discovery 门槛、内容校验、构建校验全部通过后才会提交并推送到 `main`
- 运行日志、报告文件、运行摘要（JSON/Markdown）会作为 artifact 保留，失败时便于直接排查
- 若配置仓库 Secret `PUBLISH_FAILURE_WEBHOOK_URL`，失败时会向该 webhook 发送一份 JSON 告警负载
- `main` 上的推送会继续走原有 Cloudflare Pages 部署流程

## 当前默认策略

- 输出目录固定为 `src/content/ideas`
- 自动跳过已发布过的 `sourceKeyword`，避免每天重复同一个题目
- 报告和缓存产物不进 Git
- SERP 主动采集会自动把 DuckDuckGo redirect 链接还原成真实目标 URL；若某次抓取拿到空结果，下次同日期重跑仍会自动重试，不会被空缓存锁死
- 发布前必须先过 Markdown 结构校验 + Astro 构建校验
