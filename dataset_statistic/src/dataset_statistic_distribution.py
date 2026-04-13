"""
Simple distribution statistics for one column in a HuggingFace dataset.

Only two statistic modes are supported:
- value: count original values directly
- prefix: for string values, count prefix by separator (default '-')
"""

from __future__ import annotations

import argparse
import re
import warnings
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING, Any

from plot_utils import counter_to_rows, save_distribution_csv, save_pie_chart

if TYPE_CHECKING:
    from datasets import Dataset
else:
    Dataset = Any


EMPTY_TOKEN = "<EMPTY>"
NONE_TOKEN = "<NONE>"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simple value/prefix distribution statistics with CSV and pie chart output."
    )
    parser.add_argument("--dataset_path", type=str, required=True, help="HF dataset path.")
    parser.add_argument("--column", type=str, required=True, help="Column name to analyze.")
    parser.add_argument(
        "--split",
        type=str,
        default=None,
        help="Split name for DatasetDict. If omitted, first split is used.",
    )
    parser.add_argument("--output_dir", type=str, required=True, help="Output directory.")
    parser.add_argument("--output_prefix", type=str, default=None, help="Output file prefix.")
    parser.add_argument("--batch_size", type=int, default=10000, help="Batch size.")
    parser.add_argument("--keep_empty", action="store_true", help="Keep empty/None values.")
    parser.add_argument("--dpi", type=int, default=160, help="Pie chart dpi.")
    parser.add_argument(
        "--mode",
        choices=["value", "prefix"],
        default="value",
        help="Statistics mode.",
    )
    parser.add_argument(
        "--prefix_sep",
        type=str,
        default="-",
        help="Separator used when mode=prefix.",
    )
    return parser.parse_args()


def load_hf_dataset(dataset_path: str, split: str | None) -> tuple[Dataset, str | None]:
    from datasets import Dataset, DatasetDict, load_from_disk

    obj = load_from_disk(dataset_path)

    if isinstance(obj, Dataset):
        return obj, None

    if isinstance(obj, DatasetDict):
        if len(obj) == 0:
            raise ValueError("The DatasetDict is empty.")

        if split is not None:
            if split not in obj:
                raise ValueError(
                    f"Requested split '{split}' not found. Available splits: {list(obj.keys())}"
                )
            return obj[split], split

        first_split = next(iter(obj.keys()))
        warnings.warn(
            f"Input is DatasetDict, --split is not set. Using first split: '{first_split}'.",
            stacklevel=2,
        )
        return obj[first_split], first_split

    raise TypeError(f"Unsupported dataset type: {type(obj).__name__}")


def sanitize_name(name: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip())
    return clean if clean else "distribution"


def normalize_value(raw_value: Any, mode: str, prefix_sep: str) -> str:
    if raw_value is None:
        return NONE_TOKEN
    if isinstance(raw_value, str) and raw_value == "":
        return EMPTY_TOKEN

    if mode == "prefix" and isinstance(raw_value, str):
        return raw_value.split(prefix_sep, 1)[0]

    return str(raw_value)


def compute_distribution(
    dataset: Dataset,
    column: str,
    mode: str,
    prefix_sep: str,
    keep_empty: bool,
    batch_size: int,
) -> tuple[Counter, int]:
    total_rows = len(dataset)
    counter: Counter = Counter()
    used_rows = 0

    for start in range(0, total_rows, batch_size):
        end = min(start + batch_size, total_rows)
        values = dataset[start:end][column]

        for value in values:
            key = normalize_value(value, mode=mode, prefix_sep=prefix_sep)
            if not keep_empty and key in {NONE_TOKEN, EMPTY_TOKEN}:
                continue
            counter[key] += 1
            used_rows += 1

    return counter, used_rows


def main() -> None:
    args = parse_args()

    dataset, used_split = load_hf_dataset(args.dataset_path, args.split)
    if args.column not in dataset.column_names:
        raise ValueError(
            f"Column '{args.column}' not found. Available columns: {dataset.column_names}"
        )

    counter, used_rows = compute_distribution(
        dataset=dataset,
        column=args.column,
        mode=args.mode,
        prefix_sep=args.prefix_sep,
        keep_empty=args.keep_empty,
        batch_size=args.batch_size,
    )
    rows = counter_to_rows(counter)
    if not rows:
        raise ValueError("Distribution is empty. Consider enabling --keep_empty.")

    output_dir = Path(args.output_dir)
    mode_tag = "prefix" if args.mode == "prefix" else "value"
    prefix = sanitize_name(args.output_prefix or f"{args.column}_{mode_tag}")
    output_csv = output_dir / f"{prefix}_distribution.csv"
    output_png = output_dir / f"{prefix}_distribution_pie.png"

    save_distribution_csv(rows, output_csv)

    split_info = f" | split={used_split}" if used_split is not None else ""
    title = f"Distribution({args.mode}): {args.column}{split_info} | n={used_rows}"
    save_pie_chart(rows, title=title, output_png=output_png, dpi=args.dpi)

    print("=" * 72)
    print("Dataset distribution finished")
    print(f"dataset_path : {args.dataset_path}")
    print(f"column       : {args.column}")
    print(f"mode         : {args.mode}")
    print(f"split_used   : {used_split}")
    print(f"rows_used    : {used_rows}")
    print(f"unique_value : {len(rows)}")
    print(f"csv_output   : {output_csv}")
    print(f"pie_output   : {output_png}")
    print("=" * 72)


if __name__ == "__main__":
    main()
