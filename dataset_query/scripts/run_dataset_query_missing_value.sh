#!/usr/bin/env bash
set -euo pipefail

# Usage migrated from src/dataset_query_missing_value.py
# Example 1
python toolkit/dataset_query/src/dataset_query_missing_value.py \
  --dataset_path /home/skl/mkx/data/defect_detection_bench/defect_detector/vulnerability_repaired \
  --batch_size 10000 \
  --output_dir outputs

# Example 2
python toolkit/dataset_query/src/dataset_query_missing_value.py \
  --dataset_path /path/to/hf_dataset \
  --fields cwe_id summary label_text \
  --top_fields cwe_id summary \
  --sample_size 50000 \
  --batch_size 5000 \
  --output_dir outputs

# Example 3
python toolkit/dataset_query/src/dataset_query_missing_value.py \
  --dataset_path /path/to/hf_dataset \
  --fields cwe_id \
  --top_fields cwe_id \
  --placeholder_values N/A NA None null unknown - TBD \
  --output_dir outputs
