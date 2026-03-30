#!/usr/bin/env bash
set -euo pipefail

# Usage migrated from src/dataset_value_repair.py
# Example 1
python toolkit/dataset_repair/src/dataset_value_repair.py \
  --dataset_path /home/skl/mkx/data/defect_detection_bench/defect_detector/vulnerability_merge \
  --column cwe_id \
  --old_values '[[], ["N/A"]]' \
  --new_value 'null' \
  --output_path outputs/vulnerability_cwe \
  --num_proc 8

# Example 2
python toolkit/dataset_repair/src/dataset_value_repair.py \
  --dataset_path /home/skl/mkx/data/defect_detection_bench/defect_detector/vulnerability_cwe_lines \
  --column summary \
  --old_values '' \
  --new_value 'null' \
  --output_path outputs/vulnerability_repaired \
  --num_proc 8

# Example 3
python toolkit/dataset_repair/src/dataset_value_repair.py \
  --dataset_path /path/to/your/dataset \
  --column cwe_id \
  --old_values '["N/A", null]' \
  --new_value '[]' \
  --output_path outputs/repaired_dataset
