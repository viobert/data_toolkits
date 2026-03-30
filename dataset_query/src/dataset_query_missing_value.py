"""
Inspect missing-value and placeholder-value patterns in a HuggingFace dataset.

This script supports both `datasets.Dataset` and `datasets.DatasetDict`.
If a `DatasetDict` is provided, the first split is used by default and a warning
is printed unless `--split` is explicitly specified.

For each analyzed field, the script reports counts of:
- None values
- empty strings
- whitespace-only strings
- empty lists
- empty dicts
- placeholder strings (e.g. "N/A", "None", "unknown")
- placeholder containers (e.g. ["N/A"], ["", "NA"])
- normal values

It also exports top-value distributions for selected focus fields.

Usage Example:
python toolkit/data_missing_inspect/src/inspect_missing_patterns.py \
    --dataset_path /path/to/hf_dataset \
    --fields cwe_id summary label_text \
    --top_fields cwe_id summary \
    --sample_size 50000 \
    --batch_size 5000 \
    --output_dir toolkit/data_missing_inspect/output

python toolkit/dataset_query/src/dataset_query_missing_value.py \
    --dataset_path /home/skl/mkx/data/defect_detection_bench/defect_detector/vulnerability_repaired \
    --batch_size 10000 \
    --output_dir toolkit/dataset_query/outputs

python toolkit/data_missing_inspect/src/inspect_missing_patterns.py \
    --dataset_path /path/to/hf_dataset \
    --fields cwe_id \
    --top_fields cwe_id \
    --placeholder_values N/A NA None null unknown "-" TBD \
    --output_dir toolkit/data_missing_inspect/output
"""

from __future__ import annotations

import argparse
import csv
import math
import warnings
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

from datasets import Dataset, DatasetDict, Features, load_from_disk
from tqdm import tqdm


DEFAULT_PLACEHOLDERS = [
    "n/a",
    "na",
    "none",
    "null",
    "unknown",
    "-",
    "tbd",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect missing-value and placeholder-value patterns in a HuggingFace dataset."
    )
    parser.add_argument(
        "--dataset_path",
        type=str,
        required=True,
        help="Path to a HuggingFace dataset saved by `datasets.save_to_disk`.",
    )
    parser.add_argument(
        "--split",
        type=str,
        default=None,
        help="Split name to use when the input is a DatasetDict.",
    )
    parser.add_argument(
        "--fields",
        nargs="+",
        default=None,
        help="Fields to analyze. If omitted, all columns are analyzed.",
    )
    parser.add_argument(
        "--top_fields",
        nargs="+",
        default=None,
        help=(
            "Fields for which top-value distributions will be exported. "
            "If omitted, suspicious analyzed fields are selected automatically."
        ),
    )
    parser.add_argument(
        "--top_k",
        type=int,
        default=20,
        help="Number of most frequent values to export per top field.",
    )
    parser.add_argument(
        "--sample_size",
        type=int,
        default=None,
        help=(
            "Optional number of rows to inspect from the beginning of the dataset. "
            "Useful for fast diagnosis on large datasets."
        ),
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=5000,
        help="Batch size used during iteration.",
    )
    parser.add_argument(
        "--placeholder_values",
        nargs="+",
        default=DEFAULT_PLACEHOLDERS,
        help=(
            "Placeholder strings to treat as missing-like values. "
            "Comparison is case-insensitive after stripping whitespace."
        ),
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        required=True,
        help="Directory for output CSV files.",
    )
    return parser.parse_args()


def load_hf_dataset(dataset_path: str, split: str | None) -> tuple[Dataset, str | None]:
    obj = load_from_disk(dataset_path)

    if isinstance(obj, Dataset):
        return obj, None

    if isinstance(obj, DatasetDict):
        if len(obj) == 0:
            raise ValueError("The DatasetDict is empty.")

        if split is not None:
            if split not in obj:
                raise ValueError(
                    f"Requested split '{split}' was not found. Available splits: {list(obj.keys())}"
                )
            return obj[split], split

        first_split = next(iter(obj.keys()))
        warnings.warn(
            f"Input dataset is a DatasetDict. No `--split` was provided, so the first split "
            f"'{first_split}' will be used by default.",
            stacklevel=2,
        )
        return obj[first_split], first_split

    raise TypeError(
        f"Unsupported object returned by load_from_disk: {type(obj).__name__}. "
        "Expected Dataset or DatasetDict."
    )


def normalize_placeholder_set(values: Sequence[str]) -> set[str]:
    normalized = set()
    for value in values:
        normalized.add(value.strip().lower())
    return normalized


def safe_repr(value: Any, max_len: int = 500) -> str:
    text = repr(value)
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def is_placeholder_string(value: str, placeholder_set: set[str]) -> bool:
    return value.strip().lower() in placeholder_set


def is_placeholder_container(value: Any, placeholder_set: set[str]) -> bool:
    """
    Treat containers like ["N/A"], ["", "NA"], ("None",), {"N/A"} as placeholder-like
    when all contained elements are strings and each string is either:
    - empty after stripping, or
    - a placeholder string
    """
    if isinstance(value, (list, tuple, set)):
        items = list(value)
        if len(items) == 0:
            return False

        saw_meaningful_string = False
        for item in items:
            if not isinstance(item, str):
                return False
            stripped = item.strip()
            if stripped == "":
                continue
            saw_meaningful_string = True
            if stripped.lower() not in placeholder_set:
                return False
        return True if saw_meaningful_string or len(items) > 0 else False

    return False


def classify_value(value: Any, placeholder_set: set[str]) -> str:
    if value is None:
        return "none"

    if isinstance(value, str):
        if value == "":
            return "empty_string"
        if value.strip() == "":
            return "whitespace_string"
        if is_placeholder_string(value, placeholder_set):
            return "placeholder_string"
        return "normal"

    if isinstance(value, list):
        if len(value) == 0:
            return "empty_list"
        if is_placeholder_container(value, placeholder_set):
            return "placeholder_container"
        return "normal"

    if isinstance(value, dict):
        if len(value) == 0:
            return "empty_dict"
        return "normal"

    if isinstance(value, tuple) or isinstance(value, set):
        if len(value) == 0:
            return "empty_container"
        if is_placeholder_container(value, placeholder_set):
            return "placeholder_container"
        return "normal"

    return "normal"


def validate_fields(dataset: Dataset, fields: Sequence[str] | None) -> list[str]:
    available = list(dataset.column_names)
    if fields is None:
        return available

    missing = [field for field in fields if field not in available]
    if missing:
        raise ValueError(
            f"Some requested fields were not found: {missing}. Available columns: {available}"
        )
    return list(fields)


def get_field_feature_repr(features: Features, field: str) -> str:
    try:
        return str(features[field])
    except Exception:
        return "UNKNOWN"


def batched_row_iterator(dataset: Dataset, batch_size: int) -> Iterable[dict[str, list[Any]]]:
    total = len(dataset)
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        yield dataset[start:end]


def inspect_dataset(
    dataset: Dataset,
    fields: Sequence[str],
    top_fields: Sequence[str],
    placeholder_set: set[str],
    batch_size: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    total_rows = len(dataset)

    stats: dict[str, Counter] = {field: Counter() for field in fields}
    top_value_counters: dict[str, Counter] = {field: Counter() for field in top_fields}

    progress = tqdm(
        batched_row_iterator(dataset, batch_size=batch_size),
        total=math.ceil(total_rows / batch_size),
        desc="Inspecting dataset",
    )

    for batch in progress:
        current_batch_size = len(next(iter(batch.values()))) if batch else 0

        for field in fields:
            values = batch[field]
            field_counter = stats[field]

            for value in values:
                label = classify_value(value, placeholder_set)
                field_counter["total"] += 1
                field_counter[label] += 1

        for field in top_fields:
            values = batch[field]
            counter = top_value_counters[field]
            for value in values:
                counter[safe_repr(value)] += 1

        progress.set_postfix(rows_processed=sum(stats[fields[0]].values()) if fields else 0)

        if current_batch_size == 0:
            continue

    summary_rows: list[dict[str, Any]] = []
    for field in fields:
        field_counter = stats[field]
        total = field_counter["total"]
        missing_like = (
            field_counter["none"]
            + field_counter["empty_string"]
            + field_counter["whitespace_string"]
            + field_counter["empty_list"]
            + field_counter["empty_dict"]
            + field_counter["empty_container"]
            + field_counter["placeholder_string"]
            + field_counter["placeholder_container"]
        )
        normal = field_counter["normal"]

        summary_rows.append(
            {
                "field": field,
                "feature_type": get_field_feature_repr(dataset.features, field),
                "total": total,
                "none": field_counter["none"],
                "empty_string": field_counter["empty_string"],
                "whitespace_string": field_counter["whitespace_string"],
                "empty_list": field_counter["empty_list"],
                "empty_dict": field_counter["empty_dict"],
                "empty_container": field_counter["empty_container"],
                "placeholder_string": field_counter["placeholder_string"],
                "placeholder_container": field_counter["placeholder_container"],
                "missing_like_total": missing_like,
                "missing_like_ratio": round(missing_like / total, 8) if total > 0 else 0.0,
                "normal": normal,
                "normal_ratio": round(normal / total, 8) if total > 0 else 0.0,
            }
        )

    top_rows: list[dict[str, Any]] = []
    for field in top_fields:
        counter = top_value_counters[field]
        total = stats[field]["total"]

        for rank, (value_repr, count) in enumerate(counter.most_common(), start=1):
            top_rows.append(
                {
                    "field": field,
                    "rank": rank,
                    "value_repr": value_repr,
                    "count": count,
                    "ratio": round(count / total, 8) if total > 0 else 0.0,
                }
            )

    return summary_rows, top_rows


def select_top_fields(
    summary_rows: Sequence[dict[str, Any]],
    requested_top_fields: Sequence[str] | None,
    analyzed_fields: Sequence[str],
    max_auto_fields: int = 10,
) -> list[str]:
    if requested_top_fields is not None:
        invalid = [field for field in requested_top_fields if field not in analyzed_fields]
        if invalid:
            raise ValueError(
                f"Some `--top_fields` were not found in analyzed fields: {invalid}"
            )
        return list(requested_top_fields)

    suspicious = []
    for row in summary_rows:
        if row["missing_like_total"] > 0:
            suspicious.append((row["field"], row["missing_like_total"]))

    suspicious.sort(key=lambda x: x[1], reverse=True)
    return [field for field, _ in suspicious[:max_auto_fields]]


def write_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        with path.open("w", newline="", encoding="utf-8") as f:
            f.write("")
        return

    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()

    placeholder_set = normalize_placeholder_set(args.placeholder_values)

    dataset, used_split = load_hf_dataset(args.dataset_path, args.split)

    if args.sample_size is not None:
        if args.sample_size <= 0:
            raise ValueError("`--sample_size` must be a positive integer.")
        actual_size = min(args.sample_size, len(dataset))
        dataset = dataset.select(range(actual_size))
        print(f"[INFO] Sample mode enabled: using the first {actual_size} rows.")
    else:
        print(f"[INFO] Full dataset mode: using all {len(dataset)} rows.")

    fields = validate_fields(dataset, args.fields)

    print(f"[INFO] Dataset path: {args.dataset_path}")
    print(f"[INFO] Dataset type: {type(dataset).__name__}")
    print(f"[INFO] Used split: {used_split if used_split is not None else 'N/A (single Dataset)'}")
    print(f"[INFO] Number of rows: {len(dataset)}")
    print(f"[INFO] Number of analyzed fields: {len(fields)}")
    print(f"[INFO] Fields: {fields}")

    preliminary_summary_rows, _ = inspect_dataset(
        dataset=dataset,
        fields=fields,
        top_fields=[],
        placeholder_set=placeholder_set,
        batch_size=args.batch_size,
    )

    top_fields = select_top_fields(
        summary_rows=preliminary_summary_rows,
        requested_top_fields=args.top_fields,
        analyzed_fields=fields,
    )

    if top_fields:
        print(f"[INFO] Top-value analysis fields: {top_fields}")
    else:
        print("[INFO] No suspicious fields detected. Top-value CSV will be empty unless `--top_fields` is provided.")

    summary_rows, top_rows = inspect_dataset(
        dataset=dataset,
        fields=fields,
        top_fields=top_fields,
        placeholder_set=placeholder_set,
        batch_size=args.batch_size,
    )

    if top_fields:
        grouped_top_rows = defaultdict(list)
        for row in top_rows:
            grouped_top_rows[row["field"]].append(row)

        trimmed_top_rows = []
        for field in top_fields:
            trimmed_top_rows.extend(grouped_top_rows[field][: args.top_k])
        top_rows = trimmed_top_rows

    output_dir = Path(args.output_dir)
    summary_csv = output_dir / "field_missing_summary.csv"
    top_csv = output_dir / "field_top_values.csv"

    write_csv(summary_csv, summary_rows)
    write_csv(top_csv, top_rows)

    print(f"[INFO] Summary CSV written to: {summary_csv}")
    print(f"[INFO] Top-value CSV written to: {top_csv}")


if __name__ == "__main__":
    main()