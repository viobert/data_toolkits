# data_loader.py
import os
from datasets import load_from_disk, DatasetDict
from config import DATASET_DIR, SPLIT_NAME

def load_datasets() -> DatasetDict:
    """加载数据集并处理split"""
    ds = load_from_disk(DATASET_DIR)

    if isinstance(ds, DatasetDict):
        if SPLIT_NAME not in ds:
            raise ValueError(f"Split '{SPLIT_NAME}' not found in dataset")
        return ds[SPLIT_NAME]
    else:
        print(f"Warning: dataset is not a DatasetDict; using it directly")
        return ds
    

def load_templates(template_dir: str, template_names: list) -> dict:
    """根据模板名称列表，从指定目录加载相应的模板文件并返回字典"""
    templates = {}
    for template_name in template_names:
        template_path = os.path.join(template_dir, f"{template_name}.txt")
        if os.path.exists(template_path):
            with open(template_path, "r", encoding="utf-8") as f:
                templates[template_name] = f.read()
        else:
            # 如果模板文件不存在，报错
            raise FileNotFoundError(f"\033[1;31mWarning: Template {template_name} not found in {template_dir}\033[0m")
    return templates


def prepare_output_path(dataset_name: str, split_tag: str) -> str:
    """根据数据集和split名称准备输出路径"""
    return os.path.join("./tmp", f"{dataset_name}_{split_tag}.jsonl")
