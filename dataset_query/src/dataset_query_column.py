"""
Compute value distribution statistics for a field in a HuggingFace dataset.

Supports both Dataset and DatasetDict. If a DatasetDict is provided, the script
uses the first split by default and prints a clear warning message.

The target field can contain normal values, missing values, None, or empty
strings. All of them will be counted and exported to a CSV file.

Usage Example:
python toolkit/dataset_query/src/dataset_query_column.py \
    --dataset_path /home/skl/mkx/data/defect_detection_bench/defect_detector/vulnerability_merge \
    --field cwe_id \
    --output_csv toolkit/dataset_query/outputs/cwe_id_distribution.csv

python toolkit/dataset_query/src/field_distribution.py \
    --dataset_path /path/to/hf_dataset \
    --field cwe_id \
    --split train \
    --keep_empty \
    --output_csv toolkit/dataset_query/outputs/cwe_id_distribution_train.csv
"""

from __future__ import annotations

import argparse
import csv
import os
from collections import Counter
from typing import Any, Tuple

from datasets import Dataset, DatasetDict, load_from_disk


MISSING_TOKEN = "__MISSING__"
NONE_TOKEN = "__NONE__"
EMPTY_STRING_TOKEN = "__EMPTY_STRING__"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute value distribution statistics for a field in a HuggingFace dataset."
    )
    parser.add_argument(
        "--dataset_path",
        type=str,
        required=True,
        help="Path to a HuggingFace dataset saved by load_from_disk().",
    )
    parser.add_argument(
        "--field",
        type=str,
        required=True,
        help="Target field name to analyze, e.g. cwe_id.",
    )
    parser.add_argument(
        "--split",
        type=str,
        default=None,
        help="Split name to use if the dataset is a DatasetDict. "
             "If not provided, the first split will be used.",
    )
    parser.add_argument(
        "--output_csv",
        type=str,
        required=True,
        help="Output CSV file path.",
    )
    parser.add_argument(
        "--keep_empty",
        action="store_true",
        help="Keep empty strings as a separate category. "
             "By default, empty strings are still counted separately.",
    )
    parser.add_argument(
        "--sort_by",
        type=str,
        default="count",
        choices=["count", "value"],
        help="Sort output by count or by field value.",
    )
    parser.add_argument(
        "--descending",
        action="store_true",
        help="Sort in descending order. Default is ascending for value, descending for count.",
    )
    return parser.parse_args()


def load_hf_dataset(dataset_path: str, split: str | None) -> Tuple[Dataset, str | None]:
    data = load_from_disk(dataset_path)

    if isinstance(data, Dataset):
        print("[Info] Loaded a HuggingFace Dataset.")
        return data, None

    if isinstance(data, DatasetDict):
        split_names = list(data.keys())
        if not split_names:
            raise ValueError("The DatasetDict is empty and contains no splits.")

        if split is not None:
            if split not in data:
                raise ValueError(
                    f"Requested split '{split}' not found in DatasetDict. "
                    f"Available splits: {split_names}"
                )
            print(f"[Info] Loaded a HuggingFace DatasetDict. Using split: {split}")
            return data[split], split

        default_split = split_names[0]
        print(
            "[Warning] Input dataset is a DatasetDict, but --split was not provided. "
            f"Defaulting to the first split: '{default_split}'. "
            f"Available splits: {split_names}"
        )
        return data[default_split], default_split

    raise TypeError(
        f"Unsupported dataset type: {type(data)}. Expected Dataset or DatasetDict."
    )


def normalize_value(value: Any) -> str:
    if value is None:
        return NONE_TOKEN

    if isinstance(value, str):
        if value == "":
            return EMPTY_STRING_TOKEN
        return value

    return str(value)


def compute_distribution(dataset: Dataset, field: str) -> tuple[list[dict[str, Any]], int]:
    if field not in dataset.column_names:
        raise ValueError(
            f"Field '{field}' not found in dataset columns: {dataset.column_names}"
        )

    total_count = len(dataset)

    try:
        values = dataset[field]
    except Exception as exc:
        raise RuntimeError(f"Failed to access field '{field}' from dataset: {exc}") from exc

    counter = Counter()
    observed_count = 0

    for value in values:
        counter[normalize_value(value)] += 1
        observed_count += 1

    missing_count = total_count - observed_count
    if missing_count > 0:
        counter[MISSING_TOKEN] += missing_count

    rows = []
    for value, count in counter.items():
        ratio = count / total_count if total_count > 0 else 0.0
        rows.append(
            {
                "field_value": value,
                "count": count,
                "ratio": f"{ratio:.8f}",
            }
        )

    return rows, total_count


def sort_rows(
    rows: list[dict[str, Any]],
    sort_by: str,
    descending: bool,
) -> list[dict[str, Any]]:
    if sort_by == "count":
        reverse = True if not descending else True
        return sorted(
            rows,
            key=lambda x: (-int(x["count"]), str(x["field_value"]))
            if reverse
            else (int(x["count"]), str(x["field_value"]))
        )

    reverse = descending
    return sorted(rows, key=lambda x: str(x["field_value"]), reverse=reverse)


def save_csv(rows: list[dict[str, Any]], output_csv: str) -> None:
    output_dir = os.path.dirname(os.path.abspath(output_csv))
    os.makedirs(output_dir, exist_ok=True)

    with open(output_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["field_value", "count", "ratio"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()

    dataset, used_split = load_hf_dataset(args.dataset_path, args.split)
    rows, total_count = compute_distribution(dataset, args.field)
    rows = sort_rows(rows, args.sort_by, args.descending)
    save_csv(rows, args.output_csv)

    print("=" * 80)
    print("[Done] Field distribution statistics completed.")
    print(f"[Info] Dataset path: {args.dataset_path}")
    if used_split is not None:
        print(f"[Info] Used split: {used_split}")
    print(f"[Info] Field: {args.field}")
    print(f"[Info] Total samples: {total_count}")
    print(f"[Info] Number of unique values: {len(rows)}")
    print(f"[Info] Output CSV: {args.output_csv}")
    print("=" * 80)

    preview_size = min(10, len(rows))
    if preview_size > 0:
        print("[Preview] Top rows:")
        for row in rows[:preview_size]:
            print(
                f"  field_value={row['field_value']!r}, "
                f"count={row['count']}, ratio={row['ratio']}"
            )


if __name__ == "__main__":
    main()