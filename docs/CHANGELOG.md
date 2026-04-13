# Daily Micro SaaS - 变更日志

本文档记录项目的重大变更，方便快速了解各阶段的能力边界和实现状态。

---

## 2026-04-12

### 重大更新

- **竞品分析链路全面升级**：从"拍脑袋弱点"升级为真实竞品 profiles 存储 + 定时爬取
  - 竞品 profiles 存储于 `pipeline/competitor_analysis/cache/competitor_profiles/`（54 个 profiles）
  - 新增 `competitor-crawl.yml`：定时爬取（每4小时）+ 手动触发
  - 新增 `trigger_competitor_crawl()` 入队逻辑，自动发现新域名后加入爬取队列
  - `daily-publish.yml` 末尾追加竞品爬取 step，每次最多10个域名

- **社区痛点提取模块上线**：
  - `pipeline/discovery/extract_community_pains.py`：LLM 分析 HN/Reddit 帖子，提取带引用的用户原话
  - `pipeline/publishing/extract_competitor_gaps.py`：纯粹从竞品 weaknesses 提取，不含推断

- **历史文章全面重生成**：8篇历史文章基于真实竞品 profiles 重新生成

- **项目文档全面核查**：
  - `docs/competitor-registry-design.md`：标注已实现/待实现部分
  - `docs/idea-detail-fields.md`：更新字段实际状态和生成脚本清单
  - `docs/detail-page-redesign-v2.md`：标记已实现功能
  - `README.md`：补充竞品链路说明
  - `TODO.md`：同步最新优先级和完成项

### 新增文件

- `.github/workflows/competitor-crawl.yml`
- `data/competitor_crawl_queue.json`
- `pipeline/discovery/extract_community_pains.py`
- `pipeline/publishing/extract_competitor_gaps.py`
- `scripts/supplement_serp.py`
- `scripts/run_serp_for_history.py`
- `docs/CHANGELOG.md`

---

## 2026-04-09

### 重大更新

- **竞品分析独立链路确立**：采用方案 B，竞品发现 → 爬取 → 存储与内容生成分离
- **`fresh_data` 参数删除**：`skip_xxx` 系列替代，跳过即读缓存，不跳过即强制刷新
- **中文路由全面升级**：英文走根路径，中文统一走 `/zh/...`；旧 `?lang=zh` 仅保留兼容跳转
- **双语完整性硬门禁**：`scripts/check_i18n.mjs` 在 `npm run build`、deploy workflow 和发布流程前执行
- **Idea 详情页双语展示**：优先走 `src/lib/idea.ts` 结构化双语 helper 输出，避免英文模式残留中文

### 相关文件

- `pipeline/publishing/run_daily_publish.py`：竞品链路接入
- `src/lib/i18n.ts`：双语路由方案
- `scripts/check_i18n.mjs`：双语完整性校验

---

## 2026-04-07

### 重大更新

- **discovery pipeline 的 HN 社区扫描策略调整**：demand-first，优先前20个 seed 关键词 + Ask HN / alternative / looking for / problem / workflow / automate 查询组合
- **RSS 订阅入口接入**：英文 feed `/rss.xml`，中文 feed `/rss-zh.xml`
- **邮件订阅入口预留**：`PUBLIC_EMAIL_SUBSCRIBE_URL` 环境变量

---

## 2026-04-05

### 重大更新

- **GitHub Actions 自动发布链路打通**
  - `.github/workflows/daily-publish.yml`：每天北京时间 08:05 自动生成并发布
  - `.github/workflows/deploy.yml`：手动兜底部署入口
  - Cloudflare Pages Git 集成作为主部署链路
- **首次真实日跑完成**，验证端到端链路可用
