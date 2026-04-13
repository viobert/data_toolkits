#!/usr/bin/env bash
set -euo pipefail

# # Example 1: value mode (direct counting)
# python toolkit/dataset_statistic/src/dataset_statistic_distribution.py \
#   --dataset_path /path/to/hf_dataset \
#   --column name \
#   --mode value \
#   --output_dir toolkit/dataset_statistic/outputs

# Example 2: prefix mode (split by '-')
python toolkit/dataset_statistic/src/dataset_statistic_distribution.py \
  --dataset_path  /home/skl/mkx/data/defect_detection_bench/datasets/vulnerability_filter_v2_fill\
  --column source \
  --mode prefix \
  --prefix_sep - \
  --output_dir toolkit/dataset_statistic/outputs
