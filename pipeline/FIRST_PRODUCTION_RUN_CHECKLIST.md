# 首次真实日跑 Checklist

这份文档只解决一件事：

- 把 `dailymicrosaas` 第一次真实 `daily-publish` 日跑前需要补齐的配置、最低成本验证路径、正式发布顺序一次说清楚

别盲开定时任务。先把这份清单走完，不然第二天早上只会收到一堆噪音。

---

## 1. 先搞清楚哪些配置是必须的

### 1.1 GitHub Actions Secrets（真正阻塞发布 / 部署）

| 名称 | 是否必须 | 用途 | 不配会怎样 |
| --- | --- | --- | --- |
| `REDDIT_CLIENT_ID` | 必须 | Reddit OAuth client id | 社区扫描会回退公开 JSON 端点，稳定性差 |
| `REDDIT_CLIENT_SECRET` | 必须 | Reddit OAuth client secret | 同上，无法稳定拿 token |
| `REDDIT_USER_AGENT` | 强烈建议 | Reddit API 请求标识 | 不是硬阻塞，但不建议长期空着 |
| `CLOUDFLARE_API_TOKEN` | 仅手动兜底部署时必须 | `.github/workflows/deploy.yml` 手动上传到 Cloudflare Pages | 无法走 GitHub 手动 fallback |
| `CLOUDFLARE_ACCOUNT_ID` | 仅手动兜底部署时必须 | 目标 Cloudflare 账户 ID | 无法走 GitHub 手动 fallback |
| `PUBLISH_FAILURE_WEBHOOK_URL` | 可选 | 失败时发 webhook 告警 | 失败只能靠人盯 Actions |

### 1.2 GitHub Actions Variables（公开构建变量）

| 名称 | 是否必须 | 用途 | 配置位置 |
| --- | --- | --- | --- |
| `PUBLIC_EMAIL_SUBSCRIBE_URL` | 可选 | 控制 `/subscribe` 页面和订阅 CTA 是否展示邮件入口 | Cloudflare Pages 项目环境变量（主路径）；GitHub Actions Variables 仅供手动 fallback 使用 |

关键点：

- 这个值是公开 URL，不该塞进 secret。
- 当前正式线上构建默认发生在 Cloudflare Pages Git 集成，而不是 GitHub Actions。
- 所以你如果想让线上页面真的显示邮件订阅按钮，主路径下必须把这个值配在 **Cloudflare Pages 环境变量**；只有在手动运行 `.github/workflows/deploy.yml` 兜底部署时，GitHub Actions Variables 才会生效。

### 1.3 本地 `.env`（可选但建议和线上保持一致）

仓库根目录建议保留：

```bash
GITHUB_TOKEN=ghp_xxx
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=DailyMicroSaaS/0.1 by your_reddit_username
PUBLIC_EMAIL_SUBSCRIBE_URL=https://example.com/newsletter
```

用途：

- 本地复现 discovery / publish
- 本地预览 `/subscribe` 页面显示是否正确
- 出线上问题时能快速在本地复现，不用盲猜

---

## 2. 外部前置条件，不补齐别往下走

### 2.1 Reddit App

必须确认：

- 已在 `https://www.reddit.com/prefs/apps` 创建应用
- 类型选的是 `script`（不要选 `installed app`）
- 已拿到 `client id` 和 `client secret`

参考文档：`pipeline/REDDIT_OAUTH_SETUP.md`

### 2.2 Cloudflare Pages

必须确认：

- Cloudflare Pages 项目名就是 `dailymicrosaas`
- 仓库已经通过 Cloudflare Git 集成连接到该 Pages 项目
- 当前线上地址 `https://dailymicrosaas.pages.dev` 可正常打开
- 如需邮件订阅入口，Cloudflare Pages 项目环境变量里已配置 `PUBLIC_EMAIL_SUBSCRIBE_URL`

只有在你想保留 GitHub 手动兜底部署时，才额外确认：

- `CLOUDFLARE_API_TOKEN` 有 Pages 部署权限
- `CLOUDFLARE_ACCOUNT_ID` 对应的是实际部署账户

### 2.3 GitHub Actions 权限

必须确认：

- `daily-publish.yml` 还保留 `contents: write`
- 仓库没有额外 branch protection 把 bot push 卡死
- 如果你决定保留 GitHub 手动兜底部署，再确认 `deploy.yml` 仍保留 `deployments: write`

---

## 3. 推荐的首次上线顺序：先便宜验证，再正式推送

### 阶段 A：先跑一次最低成本 dry run

路径：

- `Actions -> Daily Content Publish -> Run workflow`

第一次建议参数：

- `dry_run = true`
- `skip_trends = false`
- `skip_community = false`
- `skip_serp = true`
- `fresh_data = true`
- `min_score = 25`

为什么这样配：

- 不提交、不推送，不会污染站点
- 还能真实验证 Google Trends + 社区扫描
- 跳过 SERP，先降低一个外部不稳定源
- `fresh_data = true`，确保不是吃旧缓存假装成功

### 阶段 A 的通过标准

满足下面几条再进入下一步：

1. Job Summary 里 `status = dry_run`
2. 没有新的阻断错误
3. Reddit 日志里出现 `使用 OAuth token`，而不是回退到公开 JSON
4. `summary.json` 里 `report_summary.worth_it > 0`
5. `candidate.score >= min_score`

如果阶段 A 过不了，先修配置或数据问题，别急着做真实发布。

---

## 4. 阶段 B：做一次真实发布，但尽量减少变量

阶段 A 成功后，建议 **同一天立刻手动再跑一次正式发布**，不要傻等第二天定时任务。

第一次真实发布建议参数：

- `dry_run = false`
- `skip_trends = true`
- `skip_community = true`
- `skip_serp = true`
- `fresh_data = false`
- `min_score = 25`

为什么这么做：

- 直接复用刚才已经验证过的 discovery 结果
- 把风险集中在 generate / validate / build / git push / deploy
- 第一次真实发布先求链路闭环，不求每个外部源都同时在线上首秀

### 阶段 B 的通过标准

满足下面几条，才算第一次真实发布跑通：

1. `daily-publish` 的 `summary.json.status = success`
2. `git_commit` 和 `git_push` 都是 `completed`
3. 新提交在 GitHub 上出现 `Cloudflare Pages` 成功 check run，或在 Cloudflare Pages 后台看到对应 deployment 成功
4. 线上首页 / 归档页 / 详情页能看到新内容
5. 如果配置了 `PUBLIC_EMAIL_SUBSCRIBE_URL`，`/subscribe` 页面应显示邮件入口按钮

---

## 5. 线上验收，不要只看绿勾

第一次真实发布后，至少检查这 5 件事：

1. `https://dailymicrosaas.pages.dev` 首页出现新卡片
2. `https://dailymicrosaas.pages.dev/archive` 能看到新条目
3. 新文章详情页能正常打开
4. `https://dailymicrosaas.pages.dev/subscribe` 的 RSS / 邮件入口文案符合预期
5. 如配了双语入口，`?lang=zh` 页面和 `rss-zh.xml` 没被新构建带坏

只看 GitHub Actions 绿了，不算验收完成。

---

## 6. 常见卡点，对应怎么处理

### 6.1 Reddit 仍然回退公开 JSON

看见这类日志就说明没配对：

- `未配置 Reddit OAuth，回退到公开 JSON 端点`
- `OAuth 取 token 失败，改用公开 JSON 端点`

处理：

- 回头核对 `REDDIT_CLIENT_ID`
- 回头核对 `REDDIT_CLIENT_SECRET`
- 检查 Reddit app 类型是不是 `script`
- 检查 `REDDIT_USER_AGENT` 是否明显可识别

### 6.2 `daily-publish` 成功，但站点没更新

优先检查：

1. 新提交在 GitHub 上有没有出现 `Cloudflare Pages` check run
2. Cloudflare Pages 后台是否出现了对应 commit 的 deployment 记录
3. 是否真的 push 到了 `main`
4. Cloudflare Pages 项目名是否仍然是 `dailymicrosaas`
5. 如果你走的是手动兜底部署，再检查 `CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_ACCOUNT_ID` 是否存在

### 6.3 `/subscribe` 没显示邮件入口

优先检查：

1. Cloudflare Pages 项目环境变量里有没有 `PUBLIC_EMAIL_SUBSCRIBE_URL`
2. 最近一次正式部署是不是在加这个变量之前构建的
3. 如果你跑过 GitHub 手动兜底部署，再补查仓库 Variables 里是否也配置了同名值
4. 变量值是不是空字符串或非法 URL

这不是页面组件的锅。问题通常出在你把变量配错了位置。

### 6.4 发布了错误内容，怎么回滚

别用 `reset --hard` 这种蠢办法。

正确顺序：

1. 找到本次自动发布产生的 commit
2. 用 `git revert <commit_sha>` 生成回滚提交
3. 推回 `main`
4. 等 Cloudflare 对回滚后的新提交重新部署
5. 再修生成逻辑或阈值，不要直接重跑碰运气

---

## 7. 最终完成标准

满足下面这些，才算这条链路真正能值班：

- Reddit OAuth 已经在 Actions 中稳定生效
- 第一次 dry run 跑通
- 第一次真实发布跑通
- Cloudflare Git 集成自动部署跑通
- 线上页面已人工验收
- 可选告警（webhook）已接好，后续失败不会无声无息
- 团队里任何人再接手时，只看这份清单 + `pipeline/DAILY_PUBLISH_SOP.md` 就能继续处理

---

## 8. 相关文档入口

- Reddit OAuth 配置：`pipeline/REDDIT_OAUTH_SETUP.md`
- daily publish 排障：`pipeline/DAILY_PUBLISH_SOP.md`
- pipeline 总说明：`pipeline/README.md`
- 项目总说明：`README.md`
- 本地变量模板：`.env.example`
