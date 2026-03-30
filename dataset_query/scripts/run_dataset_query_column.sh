#!/usr/bin/env bash
set -euo pipefail

# Usage migrated from src/dataset_query_column.py
# Example 1
python toolkit/dataset_query/src/dataset_query_column.py \
  --dataset_path /home/skl/mkx/data/defect_detection_bench/defect_detector/vulnerability_merge \
  --field cwe_id \
  --output_csv outputs/cwe_id_distribution.csv

# Example 2
python toolkit/dataset_query/src/dataset_query_column.py \
  --dataset_path /path/to/hf_dataset \
  --field cwe_id \
  --split train \
  --keep_empty \
  --output_csv outputs/cwe_id_distribution_train.csv
