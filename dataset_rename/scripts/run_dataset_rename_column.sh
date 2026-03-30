#!/usr/bin/env bash
set -euo pipefail

# Usage migrated from src/dataset_rename_column.py
# Example 1
python toolkit/dataset_rename/src/dataset_rename_column.py \
  --dataset_path /home/skl/mkx/data/defect_detection_bench/defect_detector/vulnerability_normalized \
  --output_path outputs/vulnerability_normalized_renamed \
  --old_names changed \
  --new_names normalization

# Example 2
python toolkit/dataset_rename/src/dataset_rename_column.py \
  --dataset_path /path/to/dataset \
  --output_path outputs/renamed_dataset \
  --old_names cwe_id source \
  --new_names cwe dataset_source
