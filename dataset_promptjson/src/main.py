import argparse
import json
import os
import random
from collections import defaultdict
from typing import Any, Optional
from tqdm import tqdm

from utils import is_empty, number_lines, extract_placeholders
from data_models import mapping
from data_toolkits import (
    load_datasets,
    load_templates,
    load_cwe_lookup,
    enrich_sample_with_cwe,
    build_computed_placeholders,
    prepare_output_path,
    validate_template_placeholders,
    choose_template_name,
)

def process_sample(
    sample: dict,
    templates: dict,
    id_field: str,
    cwe_field: str,
    number_code_lines: bool,
    cwe_lookup: dict | None = None,
) -> tuple[Optional[dict[str, str]], Optional[dict[str, Any]]]:
    """处理单个样本并返回最终的prompt数据；丢弃时返回详细原因。"""
    sample = enrich_sample_with_cwe(sample, cwe_lookup or {}, cwe_field)
    sid = sample.get(id_field, None)
    if is_empty(sid):
        return None, {
            "reason": "missing_id",
            "sample_id": None,
            "template_name": None,
            "missing_placeholder": id_field,
            "missing_source_key": id_field,
            "raw_cwe_value": sample.get(cwe_field),
            "sample_keys": sorted(sample.keys()),
        }

    # 根据样本内容选择模板
    template_name = choose_template_name(sample, templates, id_field, cwe_field)

    # 获取对应的模板
    template = templates.get(template_name)
    if template is None:
        raise ValueError(f"Template {template_name} not found in templates")

    # 仅按当前模板占位符填充与校验字段，支持不同模板字段不一致。
    placeholders = extract_placeholders(template)
    computed_values = build_computed_placeholders(sample)
    values = {}
    for ph in placeholders:
        if ph in computed_values:
            values[ph] = computed_values[ph]
            continue

        spec = mapping.get(ph)
        if spec is None:
            raise ValueError(f"Placeholder '{ph}' not found in mapping")

        raw = None
        has_key = (spec.key is not None and spec.key in sample)
        if has_key:
            raw = sample.get(spec.key)

        # required：缺失/None/空 -> 丢弃
        if spec.required and (not has_key or is_empty(raw)):
            return None, {
                "reason": "required_missing",
                "sample_id": sid,
                "template_name": template_name,
                "missing_placeholder": ph,
                "missing_source_key": spec.key,
                "raw_cwe_value": sample.get(cwe_field),
                "sample_keys": sorted(sample.keys()),
                "sample_brief": {
                    "id": sample.get(id_field),
                    "cwe_id": sample.get("cwe_id"),
                    "cwe_name": sample.get("cwe_name"),
                    "cwe_description": sample.get("cwe_description"),
                    "code_present": not is_empty(sample.get("code")),
                },
            }

        # non-required：缺失/None/空 -> 用默认值
        if not spec.required and (not has_key or is_empty(raw)):
            raw = spec.default

        # 生成最终值
        values[ph] = number_lines(raw) if spec.number_lines and number_code_lines else str(raw)

    prompt = template.format(**values)
    return {"id": sid, "prompt": prompt}, None

def maybe_record_drop_case(
    drop_case_samples: list[dict[str, Any]],
    drop_case: dict[str, Any],
    drop_cnt: int,
    sample_limit: int,
) -> None:
    """用 reservoir sampling 保留随机的丢弃样本，避免占用过多内存。"""
    if sample_limit <= 0:
        return
    if len(drop_case_samples) < sample_limit:
        drop_case_samples.append(drop_case)
        return

    idx = random.randint(1, drop_cnt)
    if idx <= sample_limit:
        drop_case_samples[idx - 1] = drop_case

def process_dataset(
    dataset,
    templates,
    id_field: str,
    cwe_field: str,
    number_code_lines: bool,
    drop_debug_sample_count: int,
    cwe_lookup: dict | None = None,
) -> tuple[int, int, defaultdict, defaultdict, list, list]:
    """处理整个数据集，生成输出"""
    written = 0
    drop_cnt = 0
    drop_reasons = defaultdict(int)
    nonreq_filled = defaultdict(int)
    valid_samples = []  # 用来存储处理后的有效样本
    drop_case_samples = []

    # 使用 tqdm 来显示进度条
    for sample in tqdm(dataset, desc="Processing samples", unit="sample"):
        processed_sample, drop_case = process_sample(
            sample,
            templates,
            id_field=id_field,
            cwe_field=cwe_field,
            number_code_lines=number_code_lines,
            cwe_lookup=cwe_lookup,
        )
        if processed_sample is None:
            drop_cnt += 1
            reason = "required_missing" if drop_case is None else drop_case.get("reason", "required_missing")
            drop_reasons[reason] += 1
            if drop_case is not None:
                maybe_record_drop_case(drop_case_samples, drop_case, drop_cnt, drop_debug_sample_count)
        else:
            for key in processed_sample:
                nonreq_filled[key] += 1  # 统计每个键的出现次数
            valid_samples.append(processed_sample)  # 添加有效样本
            written += 1

    return written, drop_cnt, drop_reasons, nonreq_filled, valid_samples, drop_case_samples

def write_output(output_path: str, samples: list) -> None:
    """将生成的样本写入输出文件"""
    with open(output_path, "w", encoding="utf-8") as f:
        # 使用 tqdm 包装 samples 列表，显示写入进度
        for sample in tqdm(samples, desc="Writing samples", unit="sample"):
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate prompt jsonl from dataset and templates.")
    parser.add_argument("--dataset-dir", required=True, help="Dataset path used by datasets.load_from_disk")
    parser.add_argument("--split-name", required=True, help="Split name when dataset is DatasetDict")
    parser.add_argument("--prompt-template-dir", required=True, help="Directory containing template txt files")
    parser.add_argument(
        "--template-name",
        required=True,
        help="Comma-separated template names, e.g. detect_with_cwedict,dataquality_bug_v2",
    )
    parser.add_argument("--id-field", default="id", help="Field name used as sample id")
    parser.add_argument("--cwe-field", default="cwe_id", help="Field name used for CWE id lookup")
    parser.add_argument("--output-dir", required=True, help="Output directory for jsonl")
    parser.add_argument("--drop-debug-sample-count", type=int, default=1, help="Random drop sample count for debug")
    parser.add_argument("--number-code-lines", action="store_true", help="Enable line numbering for code fields")
    parser.add_argument("--use-cwe-dict", action="store_true", help="Enable external CWE dictionary")
    parser.add_argument("--cwe-index-path", default="", help="Path to external CWE dictionary json")

    args = parser.parse_args()

    template_names = [item.strip() for item in args.template_name.split(",") if item.strip()]
    if not template_names:
        parser.error("--template-name must contain at least one template")
    args.template_name = template_names

    if args.use_cwe_dict and not args.cwe_index_path:
        parser.error("--use-cwe-dict is enabled, so --cwe-index-path is required")

    if args.drop_debug_sample_count < 0:
        parser.error("--drop-debug-sample-count must be >= 0")

    return args


def main():
    args = parse_args()

    # 加载数据集
    dataset = load_datasets(args.dataset_dir, args.split_name)
    cwe_lookup = load_cwe_lookup(args.cwe_index_path if args.use_cwe_dict else None)

    # 准备输出路径
    dataset_name = os.path.basename(os.path.normpath(args.dataset_dir))
    split_tag = args.split_name
    output_path = prepare_output_path(dataset_name, split_tag, args.output_dir)

    # 需要加载的模板列表
    template_names = args.template_name

    # 加载指定模板
    templates = load_templates(args.prompt_template_dir, template_names)

    # 启动时校验模板占位符，尽早发现模板/映射不一致。
    for template in templates.values():
        validate_template_placeholders(template, mapping)

    # 处理样本并统计
    written, drop_cnt, drop_reasons, nonreq_filled, valid_samples, drop_case_samples = process_dataset(
        dataset,
        templates,
        id_field=args.id_field,
        cwe_field=args.cwe_field,
        number_code_lines=args.number_code_lines,
        drop_debug_sample_count=args.drop_debug_sample_count,
        cwe_lookup=cwe_lookup,
    )

    # 写入有效样本
    write_output(output_path, valid_samples)
    print(f"Saved {written} samples to {output_path}")

    # 打印统计信息
    if drop_cnt:
        print(f"[DROP] {drop_cnt} samples dropped (required missing/empty).")
        for k, v in sorted(drop_reasons.items(), key=lambda x: (-x[1], x[0])):
            print(f"  {k:<30} {v}")
        if drop_case_samples:
            print(f"[DROP_SAMPLE] random {len(drop_case_samples)} dropped sample(s):")
            for idx, drop_case in enumerate(drop_case_samples, start=1):
                print(f"  sample #{idx}:")
                print(json.dumps(drop_case, ensure_ascii=False, indent=2))

    if nonreq_filled:
        print("[FILL] non-required defaults used:")
        for k, v in sorted(nonreq_filled.items(), key=lambda x: (-x[1], x[0])):
            print(f"  {k:<30} {v}")

if __name__ == "__main__":
    main()
