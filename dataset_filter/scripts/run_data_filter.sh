#!/usr/bin/env bash
set -euo pipefail

# Usage migrated from src/data_filter.py
# Example 1: 按字段值过滤
python toolkit/dataset_filter/src/data_filter.py \
  --dataset_path /path/to/dataset \
  --field label \
  --value 1 \
  --num_proc 8 \
  --output_path outputs/filtered_by_label

# Example 2: 按字段存在性过滤
python toolkit/dataset_filter/src/data_filter.py \
  --dataset_path /home/skl/mkx/data/defect_detection_bench/defect_detector/vulnerability_merge \
  --field cwe_id \
  --exists \
  --keep_nonempty \
  --num_proc 8 \
  --output_path outputs/filtered_exists_cwe_id

# Example 3: 通用模板
python toolkit/dataset_filter/src/data_filter.py \
  --dataset_path /path/to/dataset \
  --field summary \
  --exists \
  --keep_nonempty \
  --num_proc 8 \
  --output_path outputs/filtered_summary_nonempty
