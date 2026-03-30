"""
Attach paired fix code to bug samples in a HuggingFace dataset.

Supports Dataset and DatasetDict loaded from disk. If the input is a
DatasetDict, the first split is used by default with a clear warning.
All `fix-*` samples are removed from the final dataset. A new column
`code_fix` is added to remaining samples and filled with the paired fix
code when available. The `pair` column is removed before saving.
"""

from __future__ import annotations

import argparse
import os
import shutil
import warnings
from typing import Dict, Optional

from datasets import Dataset, DatasetDict, Value, load_from_disk
from tqdm import tqdm


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Remove fix samples from a HuggingFace dataset, attach paired fix "
            "code as `code_fix`, and save the processed dataset."
        )
    )
    parser.add_argument(
        "--dataset_path",
        type=str,
        required=True,
        help="Path to the input HuggingFace Dataset or DatasetDict.",
    )
    parser.add_argument(
        "--output_path",
        type=str,
        required=True,
        help="Path to save the processed HuggingFace Dataset.",
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
        "--id_column",
        type=str,
        default="id",
        help="Name of the id column. Default: id",
    )
    parser.add_argument(
        "--pair_column",
        type=str,
        default="pair",
        help="Name of the pair column. Default: pair",
    )
    parser.add_argument(
        "--code_column",
        type=str,
        default="code",
        help="Name of the code column. Default: code",
    )
    parser.add_argument(
        "--code_fix_column",
        type=str,
        default="code_fix",
        help="Name of the output fix-code column. Default: code_fix",
    )
    parser.add_argument(
        "--num_proc",
        type=int,
        default=None,
        help="Number of processes for datasets.filter/map. Default: None",
    )
    parser.add_argument(
        "--overwrite_output",
        action="store_true",
        help="Overwrite output path if it already exists.",
    )
    return parser.parse_args()


def load_hf_dataset(dataset_path: str, split: Optional[str]) -> Dataset:
    obj = load_from_disk(dataset_path)

    if isinstance(obj, Dataset):
        return obj

    if isinstance(obj, DatasetDict):
        if len(obj) == 0:
            raise ValueError("The input DatasetDict is empty.")

        if split is not None:
            if split not in obj:
                raise ValueError(
                    f"Split '{split}' not found in DatasetDict. "
                    f"Available splits: {list(obj.keys())}"
                )
            return obj[split]

        first_split = next(iter(obj.keys()))
        warnings.warn(
            f"Input is a DatasetDict. No --split was provided, so the first split "
            f"'{first_split}' will be used by default.",
            UserWarning,
        )
        return obj[first_split]

    raise TypeError(
        f"Unsupported object loaded from disk: {type(obj).__name__}. "
        "Expected Dataset or DatasetDict."
    )


def validate_columns(
    dataset: Dataset,
    id_column: str,
    pair_column: str,
    code_column: str,
    code_fix_column: str,
) -> None:
    required_columns = [id_column, pair_column, code_column]
    missing_columns = [col for col in required_columns if col not in dataset.column_names]
    if missing_columns:
        raise ValueError(f"Missing required column(s): {missing_columns}")

    if code_fix_column in dataset.column_names:
        raise ValueError(
            f"Output column '{code_fix_column}' already exists. "
            "Please change --code_fix_column or remove the existing column first."
        )


def safe_remove_output_dir(output_path: str, overwrite_output: bool) -> None:
    if not os.path.exists(output_path):
        return

    if not overwrite_output:
        raise FileExistsError(
            f"Output path already exists: {output_path}\n"
            "Use --overwrite_output if you want to remove it first."
        )

    shutil.rmtree(output_path)


def build_fix_code_map(
    dataset: Dataset,
    id_column: str,
    code_column: str,
    num_proc: Optional[int],
) -> Dict[str, Optional[str]]:
    print("Step 1/4: Filtering fix samples...")

    fix_dataset = dataset.filter(
        lambda x: isinstance(x[id_column], str) and x[id_column].startswith("fix-"),
        num_proc=num_proc,
        desc="Filtering fix samples",
    )

    print(f"Found {len(fix_dataset)} fix samples.")
    print("Step 2/4: Building fix_id -> fix_code mapping...")

    fix_code_map: Dict[str, Optional[str]] = {}
    for sample in tqdm(fix_dataset, desc="Building fix map"):
        fix_id = sample[id_column]
        fix_code = sample[code_column]
        fix_code_map[fix_id] = fix_code

    return fix_code_map


def attach_fix_code(
    dataset: Dataset,
    fix_code_map: Dict[str, Optional[str]],
    id_column: str,
    pair_column: str,
    code_fix_column: str,
    num_proc: Optional[int],
) -> Dataset:
    print("Step 3/4: Removing fix samples from final dataset...")

    non_fix_dataset = dataset.filter(
        lambda x: not (
            isinstance(x[id_column], str) and x[id_column].startswith("fix-")
        ),
        num_proc=num_proc,
        desc="Filtering non-fix samples",
    )

    print(f"Remaining samples after removing fix rows: {len(non_fix_dataset)}")
    print("Step 4/4: Attaching paired fix code...")

    def map_fn(example: dict) -> dict:
        pair_id = example.get(pair_column)
        example[code_fix_column] = fix_code_map.get(pair_id, None)
        return example

    new_features = non_fix_dataset.features.copy()
    new_features[code_fix_column] = Value("string")

    processed = non_fix_dataset.map(
        map_fn,
        num_proc=num_proc,
        desc="Attaching code_fix",
        features=new_features,
    )

    if pair_column in processed.column_names:
        processed = processed.remove_columns(pair_column)

    return processed


def print_summary(
    original_dataset: Dataset,
    processed_dataset: Dataset,
    id_column: str,
    code_fix_column: str,
) -> None:
    total_rows = len(original_dataset)
    final_rows = len(processed_dataset)

    bug_rows = 0
    good_rows = 0
    matched_bug_rows = 0

    for sample in tqdm(processed_dataset, desc="Summarizing output"):
        sample_id = sample[id_column]
        code_fix = sample[code_fix_column]

        if isinstance(sample_id, str) and sample_id.startswith("bug-"):
            bug_rows += 1
            if code_fix is not None:
                matched_bug_rows += 1
        elif isinstance(sample_id, str) and sample_id.startswith("good-"):
            good_rows += 1

    print("\nSummary:")
    print(f"  Original rows: {total_rows}")
    print(f"  Final rows: {final_rows}")
    print(f"  Bug rows kept: {bug_rows}")
    print(f"  Good rows kept: {good_rows}")
    print(f"  Bug rows with matched code_fix: {matched_bug_rows}")
    print(f"  Final columns: {processed_dataset.column_names}")


def main() -> None:
    args = parse_args()

    dataset = load_hf_dataset(args.dataset_path, args.split)

    validate_columns(
        dataset=dataset,
        id_column=args.id_column,
        pair_column=args.pair_column,
        code_column=args.code_column,
        code_fix_column=args.code_fix_column,
    )

    print(f"Loaded dataset with {len(dataset)} rows.")
    print(f"Columns: {dataset.column_names}")

    fix_code_map = build_fix_code_map(
        dataset=dataset,
        id_column=args.id_column,
        code_column=args.code_column,
        num_proc=args.num_proc,
    )

    processed = attach_fix_code(
        dataset=dataset,
        fix_code_map=fix_code_map,
        id_column=args.id_column,
        pair_column=args.pair_column,
        code_fix_column=args.code_fix_column,
        num_proc=args.num_proc,
    )

    safe_remove_output_dir(args.output_path, args.overwrite_output)

    print("Saving processed dataset...")
    processed.save_to_disk(args.output_path)

    print_summary(
        original_dataset=dataset,
        processed_dataset=processed,
        id_column=args.id_column,
        code_fix_column=args.code_fix_column,
    )

    print(f"\nSaved processed dataset to: {args.output_path}")


if __name__ == "__main__":
    main()