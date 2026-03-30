#!/usr/bin/env bash
set -euo pipefail

# Usage migrated from src/token_len_statis.py
# Example 1
python toolkit/dataset_token_len/src/token_len_statis.py \
  --tokenizer_path /home/skl/mkx/model/Qwen2.5-7B-Instruct/ \
  --dataset_path /home/skl/mkx/proj/volc_engine_batchedprocess/dataset/ZERO/finetune \
  --fields input \
  --num_proc 8 \
  --batch_size 2000 \
  > outputs/token_len_statis.txt 2>&1

# Example 2
python toolkit/dataset_token_len/src/token_len_statis.py \
  --tokenizer_path /home/skl/mkx/model/Qwen2.5-7B-Instruct/ \
  --dataset_path /home/skl/mkx/data/defect_detection_bench/tasks/data/datasets/vulnerability_merge_sampled \
  --fields code \
  --num_proc 8 \
  --batch_size 2000 \
  > outputs/token_len_statis_vmsampled.txt 2>&1

# Example 3
python toolkit/dataset_token_len/src/token_len_statis.py \
  --tokenizer_path /home/skl/mkx/model/Qwen2.5-7B-Instruct/ \
  --dataset_path /home/skl/mkx/data/defect_detection_bench/defect_detector/vulnerability_repaired \
  --fields code \
  --num_proc 8 \
  --batch_size 10000 \
  > outputs/token_len_statis_vm.txt 2>&1
