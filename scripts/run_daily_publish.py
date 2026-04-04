#!/usr/bin/env python3
"""便捷入口：运行自动发布编排脚本。"""

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pipeline.publishing.run_daily_publish import main


if __name__ == "__main__":
    main()
