"""
Replace specified values in a column of a HuggingFace dataset.

Supports both `Dataset` and `DatasetDict`. If the loaded object is a
`DatasetDict`, the script will use the first split by default and print a
warning. The target column can contain scalar values or lists. When the
column value matches any value in the given replacement set, it will be
replaced with the new value.

Matching rules:
- Scalar column:
    old value in target_values -> replace with new_value
- List column:
    if the entire list equals any target value -> replace with new_value
"""

import argparse
import json
import sys
from typing import Any, List, Tuple

from datasets import Dataset, DatasetDict, load_from_disk


def parse_flexible_value(text: str) -> Any:
    """
    Parse a command-line value with JSON-first behavior, while also supporting
    common non-JSON shorthand such as an empty string.

    Supported examples:
    - 'null' -> None
    - '[]' -> []
    - '["N/A"]' -> ["N/A"]
    - '"N/A"' -> "N/A"
    - '' -> ''
    """
    if text == "":
        return ""

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        lowered = text.lower()

        if lowered == "null":
            return None
        if lowered == "none":
            return None

        return text


def normalize_old_values(old_values: Any) -> List[Any]:
    """
    Normalize old_values into a list.

    Supported inputs:
    - JSON list: '["N/A", null]'
    - single scalar after flexible parsing: ''
    """
    if isinstance(old_values, list):
        return old_values
    return [old_values]

def load_dataset_auto(dataset_path: str) -> Tuple[Dataset, str]:
    ds = load_from_disk(dataset_path)

    if isinstance(ds, Dataset):
        return ds, "single_dataset"

    if isinstance(ds, DatasetDict):
        if len(ds) == 0:
            raise ValueError("The loaded DatasetDict is empty.")
        first_split = next(iter(ds.keys()))
        print(
            f"[Warning] Loaded object is a DatasetDict. "
            f"Using the first split by default: '{first_split}'.",
            file=sys.stderr,
        )
        return ds[first_split], first_split

    raise TypeError(f"Unsupported dataset type: {type(ds)}")


def values_equal(a: Any, b: Any) -> bool:
    return a == b


def should_replace(current_value: Any, target_values: List[Any]) -> bool:
    for target in target_values:
        if values_equal(current_value, target):
            return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replace specified values in a column of a HuggingFace dataset."
    )
    parser.add_argument(
        "--dataset_path",
        type=str,
        required=True,
        help="Path to the HuggingFace dataset saved by load_from_disk/save_to_disk.",
    )
    parser.add_argument(
        "--column",
        type=str,
        required=True,
        help="Target column name to modify.",
    )
    parser.add_argument(
        "--old_values",
        type=str,
        required=True,
        help=(
            "A JSON list of values to match. "
            "Examples: '[\"N/A\", null]' or '[[], [\"N/A\"], null]'"
        ),
    )
    parser.add_argument(
        "--new_value",
        type=str,
        required=True,
        help=(
            "The replacement value in JSON format. "
            "Examples: 'null', '[]', '[\"CWE-79\"]', '\"N/A\"'"
        ),
    )
    parser.add_argument(
        "--output_path",
        type=str,
        required=True,
        help="Output path for the modified dataset.",
    )
    parser.add_argument(
        "--num_proc",
        type=int,
        default=None,
        help="Number of processes for dataset.map(). Default: None",
    )

    args = parser.parse_args()

    target_values = normalize_old_values(parse_flexible_value(args.old_values))
    new_value = parse_flexible_value(args.new_value)

    dataset, used_split = load_dataset_auto(args.dataset_path)

    if args.column not in dataset.column_names:
        raise ValueError(
            f"Column '{args.column}' not found. Available columns: {dataset.column_names}"
        )

    print(f"[Info] Loaded dataset from: {args.dataset_path}")
    print(f"[Info] Active split: {used_split}")
    print(f"[Info] Target column: {args.column}")
    print(f"[Info] Old values to replace: {target_values}")
    print(f"[Info] New value: {new_value}")
    print(f"[Info] Number of samples: {len(dataset)}")

    replacement_counter = {"count": 0}

    def replace_fn(example: dict) -> dict:
        current_value = example[args.column]
        if should_replace(current_value, target_values):
            example[args.column] = new_value
            replacement_counter["count"] += 1
        return example

    updated_dataset = dataset.map(
        replace_fn,
        num_proc=args.num_proc,
        desc=f"Replacing values in column '{args.column}'",
    )

    updated_dataset.save_to_disk(args.output_path)

    print(f"[Info] Replacement finished.")
    print(f"[Info] Output saved to: {args.output_path}")
    print(
        "[Note] When num_proc > 1, the replacement counter printed here may be "
        "inaccurate because each process has its own memory space."
    )
    print(
        f"[Info] Approximate replaced sample count (accurate when num_proc is None or 1): "
        f"{replacement_counter['count']}"
    )


if __name__ == "__main__":
    main()