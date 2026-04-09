# Daily Publish 运行与排障 SOP

这份 SOP 只解决一件事：

- 让 `daily-publish.yml` 的日跑、手动重跑、失败排查有一套固定动作
- 避免每次出问题都重新猜“该先看哪里”

适用范围：

- GitHub Actions 工作流：`.github/workflows/daily-publish.yml`
- 本地编排脚本：`python3 scripts/run_daily_publish.py`

---

## 1. 先知道这条链路到底做了什么

`daily-publish.yml` 现在会按下面顺序执行：

1. 安装 Node / Python 依赖
2. 运行 `scripts/run_daily_publish.py`
3. 生成运行日志、JSON 摘要、Markdown 摘要
4. 上传 artifact
5. 把摘要里的关键信息转成 Actions 注释和诊断区块
6. 如果配置了 `PUBLISH_FAILURE_WEBHOOK_URL`，失败时再发 webhook 告警

只有下面几关都过了，才会真正提交并推送：

- discovery 门槛通过
- Markdown 结构校验通过
- 内容质量校验通过
- `npm run build` 通过

---

## 2. 先看哪里，不要乱翻

每次 workflow 跑完，优先按这个顺序看：

### A. Actions 页面里的 Job Summary

这里会直接看到：

- 最终状态（success / failed / dry_run）
- 候选关键词与分数
- worth_it 数量
- Top warnings
- Top errors
- 本次 artifact 名称
- 本次 log / summary 路径

如果这里已经把问题说清楚，就别先去翻整份日志。

### B. 下载 artifact

artifact 名称固定为：

```text
daily-publish-<run_id>
```

重点看 4 类文件：

- `pipeline/logs/daily_publish_*.log`
- `pipeline/logs/daily_publish_*.summary.json`
- `pipeline/logs/daily_publish_*.summary.md`
- `pipeline/reports/opportunity_report_*.json`

### C. 再看 summary.json

`summary.json` 是最适合机器和人一起读的诊断入口，重点字段：

- `status`
- `candidate`
- `report_summary`
- `steps`
- `warnings`
- `errors`
- `paths`

如果要判断“卡在哪一步”，先看 `steps`，不要先盯着整份原始日志。

---

## 3. 手动重跑时怎么选参数

### 场景 1：只想快速看 discovery / 社区扫描有没有炸

GitHub Actions 手动触发建议：

- `dry_run = true`
- `skip_serp = true`
- `min_score = 25`

目的：

- 不写内容
- 不构建
- 优先验证 discovery 本身是否还能产出可用候选

本地等价命令：

```bash
python3 scripts/run_daily_publish.py --date YYYY-MM-DD --dry-run --no-build --skip-serp --min-score 25
```

### 场景 2：怀疑是生成内容或站点构建炸了

GitHub Actions 手动触发建议：

- `dry_run = false`
- `skip_trends = true`
- `skip_community = true`
- `skip_serp = true`

目的：

- 尽量复用已有 discovery 结果
- 把注意力集中在 generate / validate / build

本地等价命令：

```bash
python3 scripts/run_daily_publish.py --date YYYY-MM-DD --skip-trends --skip-community --skip-serp --mode overwrite --min-score 25
```

### 场景 3：怀疑阈值太严，不是代码炸了

只改一个参数先试：

- `min_score` 从 `25` 暂时降到 `20`

如果这样能过，说明更像是候选质量或评分阈值问题，不是工作流本身坏了。

---

## 4. 常见失败类型，对应怎么处理

### 4.1 `worth_it` 为 0 / `top_pick` 分数低于 `min_score`

这不是系统崩了，通常是数据质量不够。

优先检查：

- 当天 discovery 报告里的 `worth_it` 数量
- `top_pick.score`
- 最近是否把评分规则调严了
- 当前 seed 关键词是不是过窄

处理顺序：

1. 先看 `summary.json -> report_summary`
2. 再看 `opportunity_report_*.json`
3. 必要时临时降低 `min_score`
4. 如果连续多天都低，回头调 discovery 评分或 seed 集

### 4.2 `所有 SERP 采集结果为空`

通常不是内容逻辑问题，而是外部抓取失败或被限。

先做：

1. 用 `dry_run=true + skip_serp=true` 重跑一次，确认是不是只有 SERP 在炸
2. 看 `step3_serp_analysis.py` 对应日志
3. 如果跳过 SERP 后能恢复，说明主要是搜索抓取稳定性问题

### 4.3 Reddit 回退到公开 JSON 端点

典型日志：

- `未配置 Reddit OAuth，回退到公开 JSON 端点`
- `OAuth 取 token 失败，改用公开 JSON 端点`

处理：

- 直接看 `pipeline/REDDIT_OAUTH_SETUP.md`
- 补齐 `REDDIT_CLIENT_ID`
- 补齐 `REDDIT_CLIENT_SECRET`
- 建议同时补 `REDDIT_USER_AGENT`

### 4.4 GitHub Search API rate limit

如果日志里仍出现 rate limit：

1. 先确认 Actions 环境是否有 `GITHUB_TOKEN`
2. 再确认是不是缓存命中率太低，导致短时间查询过多
3. 查看 summary / log 中 GitHub 扫描阶段的告警

当前代码已经做了匿名节流和缓存回退；如果还频繁撞墙，就别再盲目加查询量。

### 4.5 Markdown 校验或内容质量校验失败

先看：

- `summary.errors`
- 生成的 `src/content/ideas/*.md`

本地复现：

```bash
python3 scripts/run_daily_publish.py --date YYYY-MM-DD --skip-trends --skip-community --skip-serp --mode overwrite
npm run build
```

如果是内容结构问题，先修生成逻辑；如果是站点构建问题，直接修页面或 schema，不要反复重跑 workflow 碰运气。

### 4.6 `git_push` 被跳过

常见原因：

- 没开 `--push`
- 没产生新的 commit
- 目标文件内容和现有内容完全一致

先看 `steps` 里：

- `git_commit`
- `git_push`

不要看到“没推送”就先怀疑 GitHub 权限，很多时候只是没有新变更。

---

## 5. 推荐的排查顺序

固定按这 6 步来：

1. 看 Job Summary 的 `status / Top errors / Top warnings`
2. 下 artifact
3. 看 `summary.json -> steps / errors / warnings`
4. 判断问题属于 discovery、generate、validate、build 还是 git push
5. 只改一个变量重跑（例如先改 `skip_serp` 或 `min_score`）
6. 确认问题归因后，再决定是修代码、补 secret、还是调阈值

别一上来就全量重跑三遍。那只会把噪音变多。

---

## 6. 日常建议配置

### GitHub Actions Secrets

建议至少有：

- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `REDDIT_USER_AGENT`

可选但有用：

- `PUBLISH_FAILURE_WEBHOOK_URL`

### 手动触发时默认建议

如果只是做健康检查，优先：

- `dry_run = true`
- `skip_serp = true`
- `min_score = 25`

---

## 7. 什么时候算修好了

满足下面几条，才算真的恢复：

1. Job Summary 里没有新的阻断错误
2. `summary.json` 的 `status` 变成 `success` 或至少 `dry_run`
3. 关键外部源（尤其 Reddit / GitHub）没有再回退到明显不稳定路径
4. 如果是正式发布，`git_push` 已完成，且新提交在 GitHub 上出现 `Cloudflare Pages` 成功 check run（或能在 Cloudflare Pages 后台看到对应 deployment 成功）

如果只是“这次碰巧过了”，不算修好。
