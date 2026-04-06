#!/usr/bin/env python3
"""
对自动生成的 idea Markdown 做结构和内容深度校验。

校验分两个层次：
1. 结构校验（必须通过，否则拒绝发布）：frontmatter 字段、必要章节
2. 内容质量校验（警告级别，不阻止发布，但会打印质量报告）：
   - 关键章节字数下限
   - 占位符文本检测（"暂无"、"待补充"、"TBD" 等）
   - 重复块检测（同一段话在不同章节出现）
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

REQUIRED_FIELDS = ["title", "date", "category", "difficulty", "description"]
REQUIRED_HEADINGS = [
    "一句话描述",
    "真实需求来源",
    "竞争情况",
    "技术难度",
    "变现方式",
    "参考案例",
    "最快实现路径",
    "SEO 关键词",
    "为什么值得做",
]

# 各章节的最低字数要求（字符数，中英文均计）
SECTION_MIN_CHARS = {
    "一句话描述": 50,
    "真实需求来源": 100,
    "竞争情况": 80,
    "技术难度": 100,
    "变现方式": 80,
    "参考案例": 30,
    "最快实现路径": 100,
    "为什么值得做": 80,
}

# 占位符模式（如果章节内容匹配这些，说明生成质量有问题）
PLACEHOLDER_PATTERNS = [
    r"待补充",
    r"TBD",
    r"TODO",
    r"暂无.*样本",
    r"暂无.*数据",
    r"当前.*未采集",
    r"建议.*人工补",
]

# 如果占位符出现次数超过此阈值，升级为错误（而不是警告）
PLACEHOLDER_ERROR_THRESHOLD = 3


def _extract_sections(text: str) -> dict[str, str]:
    """提取每个 ## 章节的内容。"""
    sections: dict[str, str] = {}
    # 找到正文部分（frontmatter 之后）
    body_match = re.match(r"^---\n.*?\n---\n(.*)", text, re.DOTALL)
    body = body_match.group(1) if body_match else text

    # 按 ## 分割章节
    parts = re.split(r"^## (.+)$", body, flags=re.MULTILINE)
    # parts[0] 是 ## 之前的内容（通常为空），然后交替出现 heading, content
    i = 1
    while i < len(parts) - 1:
        heading = parts[i].strip()
        content = parts[i + 1].strip()
        sections[heading] = content
        i += 2

    return sections


def validate_markdown(file_path: Path) -> list[str]:
    """
    执行结构校验，返回错误列表（空列表 = 通过）。
    这些错误会阻止发布。
    """
    text = file_path.read_text(encoding="utf-8")
    errors = []

    # 1. Frontmatter 存在性
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return ["缺少 frontmatter 区块"]

    frontmatter = match.group(1)

    # 2. 必要字段
    for field in REQUIRED_FIELDS:
        has_inline_value = re.search(rf"^{field}:\s*.+$", frontmatter, re.MULTILINE)
        has_nested_value = re.search(rf"^{field}:\s*$", frontmatter, re.MULTILINE)
        if not has_inline_value and not has_nested_value:
            errors.append(f"frontmatter 缺少字段: {field}")

    # 3. 必要章节
    for heading in REQUIRED_HEADINGS:
        if f"## {heading}" not in text:
            errors.append(f"缺少章节: {heading}")

    return errors


def audit_content_quality(file_path: Path) -> tuple[list[str], list[str]]:
    """
    执行内容质量审计，返回 (warnings, errors)。
    warnings 不阻止发布，errors 会阻止发布。
    """
    text = file_path.read_text(encoding="utf-8")
    warnings: list[str] = []
    errors: list[str] = []

    sections = _extract_sections(text)

    # 1. 章节字数检查
    for heading, min_chars in SECTION_MIN_CHARS.items():
        content = sections.get(heading, "")
        char_count = len(content.replace(" ", "").replace("\n", ""))
        if char_count < min_chars:
            warnings.append(
                f"章节「{heading}」内容偏少（{char_count} 字符，建议 ≥ {min_chars}）"
            )

    # 2. 占位符检测
    total_placeholder_count = 0
    for heading, content in sections.items():
        for pattern in PLACEHOLDER_PATTERNS:
            matches = re.findall(pattern, content)
            if matches:
                count = len(matches)
                total_placeholder_count += count
                warnings.append(
                    f"章节「{heading}」含 {count} 个占位符（匹配: {pattern}），"
                    f"说明此章节内容未被充分填充"
                )

    if total_placeholder_count >= PLACEHOLDER_ERROR_THRESHOLD:
        errors.append(
            f"占位符过多（共 {total_placeholder_count} 个），内容质量不达发布标准，"
            f"请检查 discovery 数据是否充足"
        )

    # 3. 重复内容检测（简单：检查是否有完全相同的长句子出现在多个章节）
    seen_sentences: dict[str, str] = {}
    for heading, content in sections.items():
        sentences = re.split(r"[。！？\.\!\?]", content)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 30:  # 只检查长句
                if sentence in seen_sentences:
                    warnings.append(
                        f"章节「{heading}」与「{seen_sentences[sentence]}」"
                        f"存在重复内容片段，可能是模板未被正确填充"
                    )
                else:
                    seen_sentences[sentence] = heading

    return warnings, errors


def main() -> None:
    parser = argparse.ArgumentParser(description="校验生成的 idea Markdown")
    parser.add_argument("file", help="目标 Markdown 文件路径")
    parser.add_argument("--strict", action="store_true", help="严格模式：质量警告也视为错误")
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    # 结构校验
    errors = validate_markdown(file_path)
    if errors:
        for error in errors:
            print(f"❌ [结构] {error}")
        raise SystemExit(1)

    print(f"✅ 结构校验通过: {file_path}")

    # 内容质量审计
    warnings, quality_errors = audit_content_quality(file_path)

    if warnings:
        print(f"\n⚠️  内容质量警告（{len(warnings)} 条）：")
        for warning in warnings:
            print(f"  ⚠️  {warning}")

    if quality_errors:
        print(f"\n❌ 内容质量错误（{len(quality_errors)} 条）：")
        for error in quality_errors:
            print(f"  ❌ {error}")
        raise SystemExit(1)

    if args.strict and warnings:
        print("\n❌ 严格模式：警告视为错误，发布被阻止")
        raise SystemExit(1)

    if not warnings and not quality_errors:
        print("✅ 内容质量通过（无警告）")
    else:
        print("\n✅ 结构通过，内容有警告但未达到阻止发布的阈值")


if __name__ == "__main__":
    main()
