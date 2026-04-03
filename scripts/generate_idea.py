#!/usr/bin/env python3
"""
从 demand-discovery pipeline 结果生成 Daily Micro SaaS 内容
用法: python3 scripts/generate_idea.py --date 2025-04-03
"""

import json
import argparse
from datetime import datetime
from pathlib import Path
import sys

# 添加 demand-discovery 到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "demand-discovery"))

def load_pipeline_results(date_str: str):
    """加载 pipeline 生成的报告"""
    report_path = Path(__file__).parent.parent.parent / "demand-discovery" / "reports" / f"opportunity_report_{date_str}.json"
    
    if not report_path.exists():
        # 尝试找最新的报告
        reports_dir = Path(__file__).parent.parent.parent / "demand-discovery" / "reports"
        reports = sorted(reports_dir.glob("opportunity_report_*.json"))
        if reports:
            report_path = reports[-1]
            print(f"使用最新报告: {report_path.name}")
        else:
            print("错误: 找不到 pipeline 报告")
            return None
    
    with open(report_path) as f:
        return json.load(f)

def generate_markdown(idea: dict, date_str: str) -> str:
    """生成 Markdown 内容"""
    
    # 根据评分确定难度
    score = idea.get("total_score", 0)
    if score >= 50:
        difficulty = "Easy"
    elif score >= 35:
        difficulty = "Medium"
    else:
        difficulty = "Hard"
    
    # 根据关键词确定分类
    keyword = idea["keyword"]
    category_map = {
        "pdf": "文档处理",
        "image": "图像处理",
        "video": "视频处理",
        "ai": "AI 工具",
        "code": "开发者工具",
        "timer": "效率工具",
        "productivity": "效率工具",
    }
    
    category = "效率工具"  # 默认
    for key, cat in category_map.items():
        if key in keyword.lower():
            category = cat
            break
    
    # 生成 slug
    slug = f"{date_str}-{keyword.replace(' ', '-')}"
    
    # 构建 Markdown
    md_content = f"""---
title: "{keyword.title()} - {idea.get('title_suffix', 'Web 工具')}"
date: "{date_str}"
category: "{category}"
difficulty: "{difficulty}"
description: "{idea.get('description', f'基于搜索趋势和社区讨论的 {keyword} 工具方向分析。')}"
status: "New"
---

## 一句话描述

{idea.get('one_liner', f'解决 {keyword} 相关痛点的 Web 工具/SaaS 方向。')}

## 真实需求来源

- **搜索趋势**: Google Trends 显示 "{keyword}" 近 3 个月热度稳定/上升
- **社区讨论**: 相关话题在 Reddit/HN 有持续讨论
- **评分**: {score}/100（趋势 {idea.get('trend_score', 0)} + 社区 {idea.get('community_score', 0)} + 竞争 {idea.get('serp_score', 0)}）

## 竞争情况

| 维度 | 评估 |
|------|------|
| **难度** | {difficulty} |
| **总评分** | {score}/100 |
| **趋势分** | {idea.get('trend_score', 0)}/45 |
| **社区分** | {idea.get('community_score', 0)}/25 |
| **竞争分** | {idea.get('serp_score', 0)}/30 |

## 技术难度

{idea.get('tech_difficulty', '**待补充** - 根据具体功能评估前端/后端/AI 需求')}

## 变现方式

- **免费**: 基础功能
- **付费**: 高级功能/无限使用
- **订阅**: $9-29/月

## 参考案例

{idea.get('references', '- 待补充相关案例')}

## 最快实现路径

1. **Week 1**: 搭建 MVP 核心功能
2. **Week 2**: 完善体验，集成支付
3. **Week 3**: 部署上线，开始推广

## SEO 关键词

- {keyword}
- {keyword} online
- {keyword} free
- best {keyword}

## 为什么值得做

{idea.get('why_worth', f'1. 搜索需求真实\\n2. 竞争评分 {idea.get(\"serp_score\", 0)}/30，有机会\\n3. 技术实现可行\\n4. 变现路径清晰')}
"""
    
    return slug, md_content

def main():
    parser = argparse.ArgumentParser(description="生成 Daily Micro SaaS 内容")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="日期 (YYYY-MM-DD)")
    parser.add_argument("--output", default="content/ideas", help="输出目录")
    args = parser.parse_args()
    
    # 加载 pipeline 结果
    data = load_pipeline_results(args.date)
    if not data:
        return
    
    # 获取 worth_it 和 watch 列表
    opportunities = data.get("opportunities", {})
    worth_it = opportunities.get("worth_it", [])
    watch = opportunities.get("watch", [])
    
    # 合并并按评分排序
    all_ideas = worth_it + watch
    all_ideas.sort(key=lambda x: x.get("total_score", 0), reverse=True)
    
    if not all_ideas:
        print("没有可用的 idea")
        return
    
    # 取评分最高的
    top_idea = all_ideas[0]
    
    print(f"\n选中: {top_idea['keyword']} (评分: {top_idea.get('total_score', 0)})")
    print(f"分类: {top_idea.get('classification', 'unknown')}")
    
    # 生成 Markdown
    slug, md_content = generate_markdown(top_idea, args.date)
    
    # 保存文件
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"{slug}.md"
    
    if output_file.exists():
        print(f"警告: 文件已存在 {output_file}")
        response = input("是否覆盖? (y/n): ")
        if response.lower() != 'y':
            print("已取消")
            return
    
    with open(output_file, 'w') as f:
        f.write(md_content)
    
    print(f"\n✅ 已生成: {output_file}")
    print(f"\n下一步:")
    print(f"  1. 编辑文件补充详细内容")
    print(f"  2. git add . && git commit -m 'add: {args.date} idea'")
    print(f"  3. git push 部署")

if __name__ == "__main__":
    main()