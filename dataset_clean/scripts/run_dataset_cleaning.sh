#!/usr/bin/env bash
set -euo pipefail

# src/dataset_cleaning.py 顶部没有 Usage 段，当前脚本提供标准启动方式。
# 注意：输入路径与输出位置在 src/dataset_cleaning.py 内部硬编码，请先按需修改后再执行。
python toolkit/dataset_clean/src/dataset_cleaning.py
