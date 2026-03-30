from typing import List, Dict, Callable, Tuple, Any, Union
from datasets import Dataset, DatasetDict
import copy


# =========================
# Base Filter Rule
# =========================

class FilterRule:
    """
    Base class for all filter rules.
    Each rule must implement apply(dataset) and return:
      - filtered dataset
      - report dict
    """

    name: str = "base_rule"
    description: str = ""

    def apply(self, dataset: Dataset) -> Tuple[Dataset, Dict[str, Any]]:
        raise NotImplementedError


# =========================
# Rule 1: Required fields non-empty
# =========================

class RequiredFieldsRule(FilterRule):
    """
    Drop samples where any required field is missing or empty.
    """

    def __init__(self, required_keys: List[str]):
        self.required_keys = required_keys
        self.name = "required_fields_non_empty"
        self.description = f"Required fields must exist and be non-empty: {required_keys}"

    def apply(self, dataset: Dataset) -> Tuple[Dataset, Dict[str, Any]]:
        before = len(dataset)

        def _filter_fn(example: Dict[str, Any]) -> bool:
            for key in self.required_keys:
                if key not in example:
                    return False
                value = example[key]
                if value is None:
                    return False
                if isinstance(value, str) and value.strip() == "":
                    return False
            return True

        filtered_dataset = dataset.filter(_filter_fn)
        after = len(filtered_dataset)

        report = {
            "rule": self.name,
            "description": self.description,
            "before": before,
            "after": after,
            "filtered": before - after,
        }
        return filtered_dataset, report


# =========================
# Rule 2: Two fields must not be identical
# =========================

class FieldsNotEqualRule(FilterRule):
    """
    Drop samples where two fields are considered identical.

    A normalize_fn hook is provided so that the comparison logic
    can be easily extended later (e.g. code normalization).
    """

    def __init__(
        self,
        key_a: str,
        key_b: str,
        normalize_fn: Callable[[Any], Any] = None,
    ):
        self.key_a = key_a
        self.key_b = key_b
        self.normalize_fn = normalize_fn or self._default_normalize

        self.name = "fields_not_equal"
        self.description = (
            f"Fields '{key_a}' and '{key_b}' must not be identical "
            "(after normalization)"
        )

    def _default_normalize(self, value: Any) -> Any:
        """
        Default normalization:
        - Only strip whitespace for strings
        - Leave other types unchanged

        You can later replace this with:
        - code normalization
        - comment removal
        - whitespace collapsing
        """
        if isinstance(value, str):
            return value.strip()
        return value

    def apply(self, dataset: Dataset) -> Tuple[Dataset, Dict[str, Any]]:
        before = len(dataset)

        def _filter_fn(example: Dict[str, Any]) -> bool:
            if self.key_a not in example or self.key_b not in example:
                # If either field is missing, keep it
                # (field existence should be handled by RequiredFieldsRule)
                return True

            a = self.normalize_fn(example[self.key_a])
            b = self.normalize_fn(example[self.key_b])

            return a != b

        filtered_dataset = dataset.filter(_filter_fn)
        after = len(filtered_dataset)

        report = {
            "rule": self.name,
            "description": self.description,
            "before": before,
            "after": after,
            "filtered": before - after,
            "fields": [self.key_a, self.key_b],
        }
        return filtered_dataset, report


# =========================
# Cleaning Pipeline
# =========================

def clean_dataset(
    dataset: Union[Dataset, DatasetDict],
    rules: List[FilterRule],
) -> Tuple[Union[Dataset, DatasetDict], Dict[str, List[Dict[str, Any]]]]:
    """
    Apply cleaning rules to a Dataset or DatasetDict.

    Returns:
      - cleaned dataset
      - cleaning report (per split)
    """

    reports: Dict[str, List[Dict[str, Any]]] = {}

    # Handle DatasetDict
    if isinstance(dataset, DatasetDict):
        cleaned_splits = {}
        for split_name, split_dataset in dataset.items():
            current_dataset = split_dataset
            reports[split_name] = []

            for rule in rules:
                current_dataset, report = rule.apply(current_dataset)
                reports[split_name].append(report)

            cleaned_splits[split_name] = current_dataset

        return DatasetDict(cleaned_splits), reports

    # Handle single Dataset
    else:
        current_dataset = dataset
        reports["__single__"] = []

        for rule in rules:
            current_dataset, report = rule.apply(current_dataset)
            reports["__single__"].append(report)

        return current_dataset, reports


# =========================
# Pretty print report
# =========================

def print_cleaning_report(report: Dict[str, List[Dict[str, Any]]]) -> None:
    print("=" * 80)
    print("DATASET CLEANING REPORT")
    print("=" * 80)

    for split, split_reports in report.items():
        print(f"\nSplit: {split}")
        for r in split_reports:
            print(
                f"  - Rule: {r['rule']}\n"
                f"    Description: {r['description']}\n"
                f"    Before: {r['before']}, After: {r['after']}, "
                f"Filtered: {r['filtered']}"
            )
    print("=" * 80)
