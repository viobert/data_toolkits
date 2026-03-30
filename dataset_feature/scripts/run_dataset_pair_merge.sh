#!/usr/bin/env bash
set -euo pipefail

# Usage migrated from src/dataset_pair_merge.py
# Example 1
python toolkit/dataset_feature/src/dataset_pair_merge.py \
  --dataset_path /home/skl/mkx/data/defect_detection_bench/defect_detector/vulnerability_repaired \
  --output_path outputs/vulnerability_pair \
  --num_proc 8

# Example 2
python toolkit/dataset_feature/src/dataset_pair_merge.py \
  --dataset_path /path/to/dataset_or_datasetdict \
  --output_path outputs/pair_train \
  --split train \
  --num_proc 4 \
  --overwrite_output
