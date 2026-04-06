# Reddit App 创建说明 + GitHub Secrets 填写 SOP

这份 SOP 只解决一件事：

- 让本地运行和 GitHub Actions 都能稳定使用 Reddit OAuth
- 避免 `step2_community_scan.py` 回退到公开 JSON 搜索端点

当前项目使用的是 **server-side app-only OAuth**，代码里通过 `client_credentials` 换 token。
这意味着你的 Reddit app 必须是 **带 `client_secret` 的 confidential client**。

## 一、先搞清楚当前项目需要什么

当前代码实际读取这 3 个 Reddit 相关环境变量：

- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `REDDIT_USER_AGENT`

另外建议同时配置：

- `GITHUB_TOKEN`

> 不要选 `installed app`。它没有 `client_secret`，和当前项目代码不兼容。

## 二、创建 Reddit App

### 1. 登录 Reddit

先登录你自己的 Reddit 账号，然后打开：

`https://www.reddit.com/prefs/apps`

页面底部一般会有 `create app` 或 `create another app`。

### 2. 新建应用

创建时重点看这几个字段：

#### `name`

随便填一个能认出来的名字，比如：

- `DailyMicroSaaS Pipeline`
- `dailymicrosaas-discovery`

#### `type`

当前项目建议这样选：

- **优先选 `script`**：最贴近这种服务端自动化脚本场景
- 如果你界面上只有 `web app` 可选，也可以用，但它会要求填 `redirect uri`
- **不要选 `installed app`**：它没有 `client_secret`

#### `description`

可选，但建议写清楚用途，比如：

`Server-side pipeline for DailyMicroSaaS community discovery.`

#### `about url`

可选，不填也行。

#### `redirect uri`

- 如果你选的是 `script`，通常不需要这个字段参与当前流程
- 如果你选的是 `web app`，可以先填一个占位值：

`http://localhost:8080`

因为当前项目走的是 app-only token，不做用户登录跳转，这个值只是为了满足表单要求

### 3. 创建完成后，找到凭据

创建成功后，页面会显示两项关键值：

#### `client id`

通常显示在 app 名称下面的一小段字符串。

#### `client secret`

会显示在应用详情区域。

把它们分别记下来，对应到：

- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`

## 三、如何填写 `REDDIT_USER_AGENT`

Reddit API 不喜欢匿名、模糊的请求头。
`REDDIT_USER_AGENT` 最好写得明确一点。

建议格式：

`<app_name>/<version> by <reddit_username>`

例如：

`DailyMicroSaaS/0.1 by your_reddit_username`

如果你想写得更规范一点，也可以写成：

`python:dailymicrosaas:0.1 (by /u/your_reddit_username)`

当前项目里，两种写法都够用，关键是：

- 能看出是谁的应用
- 不是默认空值
- 后续排查限流时容易识别

## 四、本地 `.env` 填写 SOP

### 1. 复制示例文件

在仓库根目录执行：

```bash
cp .env.example .env
```

### 2. 填入真实值

把 `.env` 改成这样：

```bash
GITHUB_TOKEN=ghp_xxx
REDDIT_CLIENT_ID=your_real_client_id
REDDIT_CLIENT_SECRET=your_real_client_secret
REDDIT_USER_AGENT=DailyMicroSaaS/0.1 by your_reddit_username
```

### 3. 注意事项

- `.env` 已在 `.gitignore` 中，不要手动提交
- `REDDIT_CLIENT_SECRET` 不要贴到 issue、聊天记录、截图里
- 如果 `REDDIT_USER_AGENT` 不填，代码会用默认值，但不建议长期依赖默认值

## 五、GitHub Secrets 填写 SOP

### 1. 打开仓库 Secrets 页面

进入仓库后，点击：

`Settings -> Secrets and variables -> Actions`

### 2. 逐个新增以下 Secrets

#### Secret 1

- Name: `REDDIT_CLIENT_ID`
- Secret: 你的 Reddit app client id

#### Secret 2

- Name: `REDDIT_CLIENT_SECRET`
- Secret: 你的 Reddit app client secret

#### Secret 3

- Name: `REDDIT_USER_AGENT`
- Secret: 例如 `DailyMicroSaaS/0.1 by your_reddit_username`

### 3. 可选但建议保留的其他项

如果还没配，也建议一起检查：

- `PUBLISH_FAILURE_WEBHOOK_URL`：失败告警 webhook
- `CLOUDFLARE_API_TOKEN`：仅在需要运行 GitHub 手动兜底部署 `.github/workflows/deploy.yml` 时使用
- `CLOUDFLARE_ACCOUNT_ID`：仅在需要运行 GitHub 手动兜底部署 `.github/workflows/deploy.yml` 时使用

> `GITHUB_TOKEN` 不需要你手工创建同名仓库 Secret。
> GitHub Actions 运行时会自动提供内置的 `secrets.GITHUB_TOKEN`。

## 六、如何验证是不是已经走到 OAuth

最直接的办法：手动触发一次自动发布工作流。

路径：

`Actions -> Daily Content Publish -> Run workflow`

建议第一次这样跑：

- `skip_trends = false`
- `skip_community = false`
- `skip_serp = true`
- `dry_run = true`

这样成本最低，而且能专门看社区扫描日志。

### 你想看到的日志

如果 Reddit OAuth 配对了，日志里应该出现类似：

`[Reddit] ✅ 使用 OAuth token`

### 你不想看到的日志

如果还是这类日志，说明 secrets 没配对或拿 token 失败：

`[Reddit] ⚠️ 未配置 Reddit OAuth，回退到公开 JSON 端点（稳定性较差）`

或者：

`[Reddit] ⚠️ OAuth 取 token 失败，改用公开 JSON 端点`

## 七、常见坑

### 1. 选错 app 类型

最常见的坑就是选成 `installed app`。

结果：

- 没有 `client_secret`
- 当前项目没法按现有代码换 token

### 2. `client id` 复制错位置

Reddit 的 `client id` 不一定长得像普通平台那种明显的 key。
它常常是 app 名称下面的一小段字符串，容易漏看。

### 3. `REDDIT_USER_AGENT` 写得太敷衍

虽然很多时候能跑，但限流或风控时更容易吃亏。
别偷懒，写成能识别来源的格式。

### 4. 本地能跑，Actions 不能跑

通常是因为：

- 你只填了本地 `.env`
- 但没去 GitHub 仓库里补 `Actions Secrets`

本地 `.env` 不会自动同步到 GitHub Actions。

## 八、当前项目的推荐填写模板

### 本地 `.env`

```bash
GITHUB_TOKEN=ghp_xxx
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=DailyMicroSaaS/0.1 by your_reddit_username
```

### GitHub Actions Secrets

- `REDDIT_CLIENT_ID` = 同上
- `REDDIT_CLIENT_SECRET` = 同上
- `REDDIT_USER_AGENT` = 同上

## 九、做完后的完成标准

满足下面 4 条，就算配完：

1. 本地 `.env` 已填好
2. 仓库 Actions Secrets 已填好
3. 手动触发 workflow 后日志出现 `使用 OAuth token`
4. 日跑不再默认退回公开 Reddit JSON 端点
