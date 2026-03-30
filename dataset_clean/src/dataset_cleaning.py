"""
Run dataset cleaning with code-aware rules.

- Load dataset from disk
- Apply cleaning rules
- Print and save cleaning report
"""

import json
from pathlib import Path
from typing import Any

from datasets import load_from_disk, Dataset, DatasetDict

# import your cleaning pipeline
from clean_utils import (
    RequiredFieldsRule,
    FieldsNotEqualRule,
    clean_dataset,
    print_cleaning_report,
)


# =========================
# Code normalization logic
# =========================

def normalize_code(code: Any) -> Any:
    """
    Normalize code for strict equivalence comparison.

    Current behavior:
    - Remove single-line comments
    - Remove multi-line comments
    - Remove all whitespace (space, tab, newline)

    This makes the comparison *structural-textual*:
    if two code snippets differ only in formatting or comments,
    they will be treated as identical.
    """
    if not isinstance(code, str):
        return code

    import re

    # Remove single-line comments (// ...)
    code = re.sub(r"//.*", "", code)

    # Remove multi-line comments (/* ... */)
    code = re.sub(r"/\*[\s\S]*?\*/", "", code)

    # Remove Python-style comments (# ...)
    code = re.sub(r"#.*", "", code)

    # Remove all whitespace
    code = re.sub(r"\s+", "", code)

    return code


# =========================
# Main
# =========================

def main():
    dataset_path = "/home/skl/mkx/data/diverse_vul/datasets/diverse_vul"
    # dataset_path = "/home/skl/mkx/data/big_vul/datasets/big_vul"

    output_path = f"{dataset_path}_cleaned"
    report_path = f"{dataset_path}_cleaning_report.json"

    dataset_path = Path(dataset_path)

    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset path not found: {dataset_path}")

    print(f"Loading dataset from: {dataset_path}")
    dataset = load_from_disk(str(dataset_path))

    # -------------------------
    # Define cleaning rules
    # -------------------------

    rules = [
        # Rule 1: required fields must exist and be non-empty
        RequiredFieldsRule(
            required_keys=[
                "func",
                # "patched_code",
                # "label",
            ]
        ),

        # Rule 2: vulnerable_code and patched_code must not be identical
        # after code normalization
        # FieldsNotEqualRule(
        #     key_a="vulnerable_code",
        #     key_b="patched_code",
        #     normalize_fn=normalize_code,
        # ),
    ]

    # -------------------------
    # Run cleaning
    # -------------------------

    cleaned_dataset, report = clean_dataset(dataset, rules)

    # -------------------------
    # Report
    # -------------------------

    print_cleaning_report(report)

    print(f"\nSaving cleaning report to: {report_path}")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # -------------------------
    # Save cleaned dataset
    # -------------------------

    print(f"Saving cleaned dataset to: {output_path}")
    cleaned_dataset.save_to_disk(output_path)

    print("\nCleaning finished successfully.")


if __name__ == "__main__":
    main()
