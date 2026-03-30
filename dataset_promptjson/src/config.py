# config.py
from pathlib import Path

# ======================
# Config
# ======================
# DATASET_DIR = "/home/skl/mkx/data/cwe_dict/cwe_index_4.19.1_dataset"
# DATASET_DIR = "/home/skl/mkx/data/defect_detection_bench/defect_detector/defect_merged"
DATASET_DIR = "/home/skl/mkx/data/defect_detection_bench/defect_detector/vulnerability_cleaned"
SPLIT_NAME = "train"
PROMPT_TEMPLATE_DIR = "/home/skl/mkx/data/toolkit/dataset_promptjson/templates"
CWE_INDEX_PATH = "/home/skl/mkx/data/cwe_dict/cwe_index_4.19.1.json"
# TEMPLATE_NAME = ["dataquality_bug", "dataquality_good"]
TEMPLATE_NAME = ["dataquality_bug_v2", "dataquality_good_v2", "dataquality_bug_with_cwe"]
# TEMPLATE_NAME = ["cwe_code_generate"]


NUMBER_CODE_LINES = False  # ✅ 开关：是否把 code 转成 '0| code' 行号形式
ID_FIELD = "id"
# ID_FIELD = "cwe_id"
CWE_FIELD = "cwe_id"
OUTPUT_DIR = "/home/skl/mkx/data/toolkit/dataset_promptjson/outputs"  # 输出目录
DROP_DEBUG_SAMPLE_COUNT = 1  # 随机输出多少个被丢弃样本的具体情况；设为 0 可关闭
