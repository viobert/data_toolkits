#!/usr/bin/env bash
set -euo pipefail

# src/data_diff.py 顶部没有 Usage 段，且数据路径为源码常量。
# 使用前请先修改 src/data_diff.py 中 DATASET_A_PATH / DATASET_B_PATH。
python toolkit/dataset_diff/src/data_diff.py
