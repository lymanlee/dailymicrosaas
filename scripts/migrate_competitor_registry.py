#!/usr/bin/env python3
"""
竞品数据迁移脚本

将 pipeline/competitor_analysis/cache/competitor_profiles/ 中的数据
迁移到 src/data/competitors/ 目录，添加必要的元数据字段。
"""
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone

# 路径配置
SOURCE_DIR = Path(__file__).parent.parent / "pipeline/competitor_analysis/cache/competitor_profiles"
TARGET_DIR = Path(__file__).parent.parent / "src/data/competitors"


def migrate_competitor(source_file: Path, target_dir: Path) -> dict:
    """迁移单个竞品文件"""
    with open(source_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 添加元数据字段
    domain = data.get('domain', source_file.stem.replace('_', '.'))

    # 确定 dataStatus
    analyzed_at = data.get('analyzedAt')
    if analyzed_at:
        try:
            analyzed_time = datetime.fromisoformat(analyzed_at.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            hours_diff = (now - analyzed_time).total_seconds() / 3600

            if hours_diff < 24:
                data['dataStatus'] = 'fresh'
            elif hours_diff < 168:  # 7 days
                data['dataStatus'] = 'stale'
            else:
                data['dataStatus'] = 'stale'
        except Exception:
            data['dataStatus'] = 'stale'
    else:
        data['dataStatus'] = 'stale'

    # 标准化 domain 格式
    data['domain'] = domain.replace('_', '.')

    # 添加 lastChecked
    data['lastChecked'] = analyzed_at or datetime.now(timezone.utc).isoformat()

    # 添加 dataSources
    if 'dataSources' not in data:
        data['dataSources'] = {
            'landingPage': f'https://{domain}',
            'pricingPage': f'https://{domain}/pricing',
        }

    # 移除旧字段
    if 'analyzedAt' in data:
        del data['analyzedAt']

    # 写入目标文件
    target_file = target_dir / f"{domain.replace('.', '_')}.json"
    with open(target_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {
        'domain': domain,
        'source': source_file.name,
        'target': target_file.name,
        'status': data['dataStatus']
    }


def main():
    """执行迁移"""
    # 路径配置
    script_dir = Path(__file__).parent.parent
    source_dir = script_dir / "pipeline/competitor_analysis/cache/competitor_profiles"
    registry_dir = script_dir / "src/data/competitors"
    public_dir = script_dir / "public/data/competitors"

    # 创建目标目录
    registry_dir.mkdir(parents=True, exist_ok=True)
    public_dir.mkdir(parents=True, exist_ok=True)

    # 收集所有源文件
    source_files = list(source_dir.glob("*.json"))

    if not source_files:
        print("No competitor data found to migrate.")
        return

    print(f"Found {len(source_files)} competitor files to migrate.")
    print(f"Source: {source_dir}")
    print(f"Registry: {registry_dir}")
    print(f"Public: {public_dir}")
    print("-" * 50)

    results = []
    for source_file in sorted(source_files):
        try:
            result = migrate_competitor(source_file, registry_dir)
            results.append(result)

            # 复制到 public 目录
            shutil.copy(
                registry_dir / result['target'],
                public_dir / result['target']
            )

            print(f"✓ {result['domain']:25} → {result['target']:30} [{result['status']}]")
        except Exception as e:
            print(f"✗ {source_file.name}: {e}")

    print("-" * 50)
    print(f"Migrated {len(results)} competitors successfully.")

    # 列出迁移后的文件
    registry_files = list(registry_dir.glob("*.json"))
    print(f"\nRegistry: {len(registry_files)} competitors")
    print(f"Public: {len(list(public_dir.glob('*.json')))} competitors")


if __name__ == "__main__":
    main()
