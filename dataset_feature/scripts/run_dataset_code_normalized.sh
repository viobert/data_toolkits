#!/usr/bin/env bash
set -euo pipefail

# Usage migrated from src/dataset_code_normalized.py
# Example 1
python toolkit/dataset_feature/src/dataset_code_normalized.py \
  --dataset_path /home/skl/mkx/data/defect_detection_bench/defect_detector/vulnerability_pair \
  --input_field raw_code \
  --output_field code \
  --output_path outputs/vulnerability_normalized \
  --num_proc 8 \
  --batch_size 10000

# Example 2
python toolkit/dataset_feature/src/dataset_code_normalized.py \
  --dataset_path /path/to/hf_dataset \
  --split train \
  --input_field code \
  --output_field code_normalized \
  --output_path outputs/normalized_train \
  --num_proc 4 \
  --batch_size 1000
