#!/usr/bin/env bash
set -euo pipefail

# ======================
# Config moved from src/config.py
# ======================
# DATASET_DIR="/home/skl/mkx/data/cwe_dict/cwe_index_4.19.1_dataset"
# DATASET_DIR="/home/skl/mkx/data/defect_detection_bench/defect_detector/defect_merged"
DATASET_DIR="/home/skl/mkx/data/defect_detection_bench/datasets/vulnerability_filter_v1"
SPLIT_NAME="train"
PROMPT_TEMPLATE_DIR="/home/skl/mkx/data/toolkit/dataset_promptjson/templates"

# TEMPLATE_NAME="dataquality_bug,dataquality_good"
# TEMPLATE_NAME="dataquality_bug_v2,dataquality_good_v2,dataquality_bug_with_cwe"
TEMPLATE_NAME="detect_with_cwedict"
# TEMPLATE_NAME="cwe_code_generate"

# NUMBER_CODE_LINES=False  # ✅ 开关：是否把 code 转成 '0| code' 行号形式
NUMBER_CODE_LINES=true
ID_FIELD="id"
# ID_FIELD="cwe_id"
CWE_FIELD="cwe_id"
OUTPUT_DIR="/home/skl/mkx/data/toolkit/dataset_promptjson/outputs"  # 输出目录
DROP_DEBUG_SAMPLE_COUNT=1  # 随机输出多少个被丢弃样本的具体情况；设为 0 可关闭

# action: 传递 --use-cwe-dict 即视为开启外挂字典；开启后必须有路径
USE_CWE_DICT=true
CWE_INDEX_PATH="/home/skl/mkx/data/cwe_dict/cwe_index_4.19.1.json"

ARGS=(
	--dataset-dir "$DATASET_DIR"
	--split-name "$SPLIT_NAME"
	--prompt-template-dir "$PROMPT_TEMPLATE_DIR"
	--template-name "$TEMPLATE_NAME"
	--id-field "$ID_FIELD"
	--cwe-field "$CWE_FIELD"
	--output-dir "$OUTPUT_DIR"
	--drop-debug-sample-count "$DROP_DEBUG_SAMPLE_COUNT"
)

if [[ "$NUMBER_CODE_LINES" == "true" ]]; then
	ARGS+=(--number-code-lines)
fi

if [[ "$USE_CWE_DICT" == "true" ]]; then
	if [[ -z "$CWE_INDEX_PATH" ]]; then
		echo "ERROR: USE_CWE_DICT=true 时，CWE_INDEX_PATH 不能为空" >&2
		exit 1
	fi
	ARGS+=(--use-cwe-dict --cwe-index-path "$CWE_INDEX_PATH")
fi

python toolkit/dataset_promptjson/src/main.py "${ARGS[@]}"
