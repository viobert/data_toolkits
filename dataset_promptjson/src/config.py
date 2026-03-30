# config.py
from pathlib import Path

# ======================
# Config
# ======================
DATASET_DIR = "/home/skl/mkx/data/cwe_dict/cwe_index_4.19.1_dataset"
# DATASET_DIR = "/home/skl/mkx/data/defect_detection_bench/defect_detector/defect_merged"
SPLIT_NAME = "train"
PROMPT_TEMPLATE_DIR = "/home/skl/mkx/data/toolkit/dataset_promptjson/templates"
# TEMPLATE_NAME = ["dataquality_insepct_bug", "dataquality_inspect_good"]
TEMPLATE_NAME = ["cwe_code_generate"]


NUMBER_CODE_LINES = True  # ✅ 开关：是否把 code 转成 '0| code' 行号形式
# ID_FIELD = "id"
ID_FIELD = "cwe_id"
OUTPUT_DIR = "/home/skl/mkx/data/tmp"  # 输出目录
