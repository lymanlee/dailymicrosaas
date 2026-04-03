# Daily Micro SaaS

每天发现一个小而美的创业机会。

## 简介

Daily Micro SaaS 是一个专注于发现 Web 工具/Micro SaaS 创业方向的内容平台。
我们通过分析搜索趋势、社区讨论和竞争情况，筛选出「可复制、可落地、可赚钱」的产品机会。

## 技术栈

- **框架**: [Astro](https://astro.build)
- **样式**: Tailwind CSS
- **托管**: Cloudflare Pages
- **内容**: Markdown

## 本地开发

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建
npm run build
```

## 内容生成

```bash
# 从 pipeline 结果生成今日内容
python3 scripts/generate_idea.py --date 2025-04-03

# 手动创建内容
cp content/ideas/template.md content/ideas/2025-04-04-your-idea.md
```

## 发布流程

```bash
# 1. 生成内容
python3 scripts/generate_idea.py

# 2. 编辑完善
vim content/ideas/2025-04-03-xxx.md

# 3. 提交部署
git add .
git commit -m "add: 2025-04-03 idea"
git push
```

## 项目结构

```
dailymicrosaas/
├── src/
│   ├── pages/          # 页面路由
│   ├── components/     # 组件
│   ├── layouts/        # 布局
│   └── content/        # 内容集合
├── content/
│   └── ideas/          # Markdown 内容
├── scripts/
│   └── generate_idea.py # 内容生成脚本
└── public/             # 静态资源
```

## 内容格式

见 `content/ideas/template.md`

## License

MIT