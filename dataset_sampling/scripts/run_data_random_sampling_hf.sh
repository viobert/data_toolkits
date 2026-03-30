#!/usr/bin/env bash
set -euo pipefail

# Usage migrated from src/data_random_sampling_hf.py
python toolkit/dataset_sampling/src/data_random_sampling_hf.py \
  --sample 100 \
  --seed 42 \
  --input_path /home/skl/mkx/data/defect_detection_bench/defect_detector/vulnerability_merge \
  --output_path outputs/vulnerability_merge_sampled
