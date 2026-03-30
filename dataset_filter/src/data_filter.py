"""
Filter samples from a HuggingFace dataset by field value or field existence.

Supports Dataset/DatasetDict loaded from disk. If the input is a DatasetDict,
the script uses the first split by default and prints a clear warning.

Filtering is performed with the official `datasets.Dataset.filter(...)` API.
It supports:
1. equality filtering: keep samples where `field == value`
2. existence filtering: keep samples where `field is not None`

Optionally, empty strings can also be excluded.
"""

from __future__ import annotations

import argparse
import json
import warnings
from typing import Any

from datasets import Dataset, DatasetDict, load_from_disk


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Filter a HuggingFace dataset by field value or field existence."
    )
    parser.add_argument(
        "--dataset_path",
        type=str,
        required=True,
        help="Path to a HuggingFace dataset saved by `save_to_disk`.",
    )
    parser.add_argument(
        "--field",
        type=str,
        required=True,
        help="Field name used for filtering.",
    )
    parser.add_argument(
        "--value",
        type=str,
        default=None,
        help=(
            "Target value for equality filtering. "
            "It will be parsed with json.loads when possible, "
            "so values like 1, true, null, \"text\" are supported."
        ),
    )
    parser.add_argument(
        "--exists",
        action="store_true",
        help="Keep samples where the given field exists and is not None.",
    )
    parser.add_argument(
        "--keep_nonempty",
        action="store_true",
        help="When used with --exists, also require the field to be non-empty if it is a string.",
    )
    parser.add_argument(
        "--split",
        type=str,
        default=None,
        help=(
            "Split name to use when the input is a DatasetDict. "
            "If not provided, the first split will be used with a warning."
        ),
    )
    parser.add_argument(
        "--num_proc",
        type=int,
        default=None,
        help="Number of processes for dataset.filter(...).",
    )
    parser.add_argument(
        "--output_path",
        type=str,
        default=None,
        help="Optional path to save the filtered dataset with `save_to_disk`.",
    )
    parser.add_argument(
        "--print_samples",
        type=int,
        default=2,
        help="Number of filtered samples to preview.",
    )
    return parser.parse_args()


def parse_value(raw_value: str | None) -> Any:
    if raw_value is None:
        return None
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError:
        return raw_value


def load_single_dataset(dataset_path: str, split: str | None) -> Dataset:
    dataset_obj = load_from_disk(dataset_path)

    if isinstance(dataset_obj, Dataset):
        print("[Info] Loaded a Dataset object.")
        return dataset_obj

    if isinstance(dataset_obj, DatasetDict):
        split_names = list(dataset_obj.keys())
        if not split_names:
            raise ValueError("The DatasetDict is empty.")

        if split is None:
            split = split_names[0]
            warnings.warn(
                f"Input is a DatasetDict. No --split was provided, so the first split "
                f"`{split}` will be used by default. Available splits: {split_names}",
                stacklevel=2,
            )
        elif split not in dataset_obj:
            raise ValueError(
                f"Split `{split}` not found in DatasetDict. Available splits: {split_names}"
            )

        print(f"[Info] Loaded a DatasetDict object. Using split: {split}")
        return dataset_obj[split]

    raise TypeError(
        f"Unsupported object type loaded from disk: {type(dataset_obj).__name__}"
    )


def validate_args(args: argparse.Namespace) -> None:
    if not args.exists and args.value is None:
        raise ValueError("You must provide either --value or --exists.")

    if args.exists and args.value is not None:
        raise ValueError("Please use only one mode: either --value or --exists.")


def build_filter_fn(field: str, target_value: Any, exists: bool, keep_nonempty: bool):
    if exists:
        def filter_fn(example: dict) -> bool:
            if field not in example:
                return False
            value = example[field]
            if value is None:
                return False
            if keep_nonempty and isinstance(value, str) and value == "":
                return False
            return True

        return filter_fn

    def filter_fn(example: dict) -> bool:
        return example.get(field, None) == target_value

    return filter_fn


def main() -> None:
    args = parse_args()
    validate_args(args)

    target_value = parse_value(args.value)
    dataset = load_single_dataset(args.dataset_path, args.split)

    print(f"[Info] Original dataset size: {len(dataset)}")
    print(f"[Info] Columns: {dataset.column_names}")

    if args.field not in dataset.column_names:
        warnings.warn(
            f"Field `{args.field}` is not in dataset columns: {dataset.column_names}. "
            f"The filtered result will be empty.",
            stacklevel=2,
        )

    filter_fn = build_filter_fn(
        field=args.field,
        target_value=target_value,
        exists=args.exists,
        keep_nonempty=args.keep_nonempty,
    )

    print("[Info] Start filtering...")
    filtered_dataset = dataset.filter(
        filter_fn,
        num_proc=args.num_proc,
        desc="Filtering dataset",
        load_from_cache_file=False
    )

    print(f"[Info] Filtered dataset size: {len(filtered_dataset)}")
    print(f"[Info] Removed samples: {len(dataset) - len(filtered_dataset)}")
    print(f"filtered_dataset: {filtered_dataset}")

    preview_count = min(args.print_samples, len(filtered_dataset))
    if preview_count > 0:
        print(f"[Info] Preview first {preview_count} sample(s):")
        for idx in range(preview_count):
            print(f"----- sample {idx} -----")
            print(filtered_dataset[idx])

    if args.output_path is not None:
        filtered_dataset.save_to_disk(args.output_path)
        print(f"[Info] Filtered dataset saved to: {args.output_path}")


if __name__ == "__main__":
    main()