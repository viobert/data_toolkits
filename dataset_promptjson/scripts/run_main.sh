#!/usr/bin/env bash
set -euo pipefail

# src/main.py 顶部没有 Usage 段，当前脚本提供标准启动方式。
# 运行前请先检查 src/config.py 中 DATASET_DIR / SPLIT_NAME / TEMPLATE_NAME。
python toolkit/dataset_promptjson/src/main.py
