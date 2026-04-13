#!/usr/bin/env bash
set -euo pipefail

# # Example 1: default cwe_id column
# python toolkit/dataset_statistic/src/dataset_statistic_cwe_id.py \
#   --dataset_path /path/to/hf_dataset \
#   --output_dir toolkit/dataset_statistic/outputs

# Example 2: custom split + keep empty 
# Add `keep_empty`: Empty values will also be included in the distribution, making it easier to identify data quality issues.
python toolkit/dataset_statistic/src/dataset_statistic_cwe_id.py \
  --dataset_path /home/skl/mkx/data/defect_detection_bench/datasets/vulnerability_filter_v2_fill \
  --keep_empty \
  --output_dir toolkit/dataset_statistic/outputs
