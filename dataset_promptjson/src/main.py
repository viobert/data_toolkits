import json
import os
from pathlib import Path
from collections import defaultdict
from typing import Optional
from tqdm import tqdm
from collections import defaultdict

from config import *
from utils import is_empty, number_lines, extract_placeholders
from data_models import mapping, FieldSpec
from data_toolkits import load_datasets, load_templates, prepare_output_path, DatasetDict


def validate_template_placeholders(template: str) -> None:
    """检查模板的占位符是否覆盖了映射中的所有字段"""
    need = extract_placeholders(template)
    miss = sorted(need - set(mapping.keys()))
    if miss:
        raise ValueError(f"Template placeholders not covered by mapping: {miss}")

def process_sample(sample: dict, templates: dict) -> Optional[dict[str, str]]:
    """处理单个样本并返回最终的prompt数据，根据ID选择模板"""
    sid = sample.get(ID_FIELD, None)
    if is_empty(sid):
        return None  # 丢弃样本

    # 根据ID判断选择模板
    template_name = 'cwe_code_generate'
    # if "bug" in sid:
    #     template_name = "dataquality_insepct_bug"
    # elif "good" in sid or "fix" in sid:
    #     template_name = "dataquality_inspect_good"
    # else:
    #     raise ValueError(f"Unknown type(bug/good/fix), sample ID: {sid}")

    # 获取对应的模板
    template = templates.get(template_name)
    if template is None:
        raise ValueError(f"Template {template_name} not found in templates")

    values = {}
    for ph, spec in mapping.items():
        raw = None
        has_key = (spec.key is not None and spec.key in sample)
        if has_key:
            raw = sample.get(spec.key)

        # required：缺失/None/空 -> 丢弃
        if spec.required and (not has_key or is_empty(raw)):
            return None

        # non-required：缺失/None/空 -> 用默认值
        if not spec.required and (not has_key or is_empty(raw)):
            raw = spec.default

        # 生成最终值
        values[ph] = number_lines(raw) if spec.number_lines and NUMBER_CODE_LINES else str(raw)

    prompt = template.format(**values)
    return {"id": sid, "prompt": prompt}

def process_dataset(dataset, template) -> tuple[int, int, defaultdict, defaultdict, list]:
    """处理整个数据集，生成输出"""
    written = 0
    drop_cnt = 0
    drop_reasons = defaultdict(int)
    nonreq_filled = defaultdict(int)
    valid_samples = []  # 用来存储处理后的有效样本

    # 使用 tqdm 来显示进度条
    for sample in tqdm(dataset, desc="Processing samples", unit="sample"):
        processed_sample = process_sample(sample, template)
        if processed_sample is None:
            drop_cnt += 1
            drop_reasons["required_missing"] += 1  # 记录丢弃原因
        else:
            for key in processed_sample:
                nonreq_filled[key] += 1  # 统计每个键的出现次数
            valid_samples.append(processed_sample)  # 添加有效样本
            written += 1

    return written, drop_cnt, drop_reasons, nonreq_filled, valid_samples

def write_output(output_path: str, samples: list) -> None:
    """将生成的样本写入输出文件"""
    with open(output_path, "w", encoding="utf-8") as f:
        # 使用 tqdm 包装 samples 列表，显示写入进度
        for sample in tqdm(samples, desc="Writing samples", unit="sample"):
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")


def main():
    # 加载数据集
    dataset = load_datasets()

    # 准备输出路径
    dataset_name = os.path.basename(os.path.normpath(DATASET_DIR))
    split_tag = SPLIT_NAME if isinstance(dataset, DatasetDict) else "all"
    output_path = prepare_output_path(dataset_name, split_tag)

    # 需要加载的模板列表
    template_names = TEMPLATE_NAME

    # 加载指定模板
    templates = load_templates(PROMPT_TEMPLATE_DIR, template_names)

    # 处理样本并统计
    written, drop_cnt, drop_reasons, nonreq_filled, valid_samples = process_dataset(dataset, templates)

    # 写入有效样本
    write_output(output_path, valid_samples)
    print(f"Saved {written} samples to {output_path}")

    # 打印统计信息
    if drop_cnt:
        print(f"[DROP] {drop_cnt} samples dropped (required missing/empty).")
        for k, v in sorted(drop_reasons.items(), key=lambda x: (-x[1], x[0])):
            print(f"  {k:<30} {v}")

    if nonreq_filled:
        print("[FILL] non-required defaults used:")
        for k, v in sorted(nonreq_filled.items(), key=lambda x: (-x[1], x[0])):
            print(f"  {k:<30} {v}")

if __name__ == "__main__":
    main()
