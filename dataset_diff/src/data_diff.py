"""
Description: Automatically compare two Hugging Face DatasetDict objects by reading splits and columns directly from the data, 
detecting a usable row identity strategy per split (single unique column, composite unique columns, 
or fallback occurrence-based alignment), and then reporting field-level differences with examples.
"""
import json
import hashlib
import itertools
from collections import Counter, defaultdict
from datasets import load_from_disk


DATASET_A_PATH = "/home/skl/mkx/proj/volc_engine_batchedprocess/dataset/ZERO/finetune"
DATASET_B_PATH = "/home/skl/mkx/proj/volc_engine_batchedprocess/dataset/ZERO/finetune2"

MAX_COMPOSITE_KEY_SIZE = 3
MAX_EXAMPLE_DIFFS_PER_SPLIT = 1
MAX_CHANGED_FIELDS_PRINT = 20


def normalize_value(v):
    if isinstance(v, dict):
        return {k: normalize_value(v[k]) for k in sorted(v)}
    if isinstance(v, list):
        return [normalize_value(x) for x in v]
    return v


def stable_json(v):
    return json.dumps(normalize_value(v), ensure_ascii=False, sort_keys=True)


def row_hash(sample, columns=None):
    if columns is None:
        columns = sorted(sample.keys())
    obj = {c: normalize_value(sample.get(c, "<MISSING>")) for c in columns}
    return hashlib.md5(stable_json(obj).encode("utf-8")).hexdigest()


def get_common_splits(ds_a, ds_b):
    splits_a = set(ds_a.keys())
    splits_b = set(ds_b.keys())
    return sorted(splits_a & splits_b), splits_a, splits_b


def get_common_columns(split_a, split_b):
    cols_a = list(split_a.column_names)
    cols_b = list(split_b.column_names)
    common = [c for c in cols_a if c in set(cols_b)]
    return cols_a, cols_b, common


def count_unique_values(ds_split, column):
    seen = set()
    for x in ds_split:
        seen.add(stable_json(x.get(column)))
    return len(seen)


def count_unique_tuples(ds_split, columns):
    seen = set()
    for x in ds_split:
        key = tuple(stable_json(x.get(c)) for c in columns)
        seen.add(key)
    return len(seen)


def detect_identity_columns(split_a, split_b, common_columns):
    n_a = len(split_a)
    n_b = len(split_b)

    # 1) try single-column unique key
    for col in common_columns:
        ua = count_unique_values(split_a, col)
        ub = count_unique_values(split_b, col)
        if ua == n_a and ub == n_b:
            return {
                "mode": "single_unique",
                "columns": [col],
                "description": f"single unique column: {col}",
            }

    # 2) try composite unique key
    max_k = min(MAX_COMPOSITE_KEY_SIZE, len(common_columns))
    for k in range(2, max_k + 1):
        for cols in itertools.combinations(common_columns, k):
            ua = count_unique_tuples(split_a, cols)
            ub = count_unique_tuples(split_b, cols)
            if ua == n_a and ub == n_b:
                return {
                    "mode": "composite_unique",
                    "columns": list(cols),
                    "description": f"composite unique columns: {list(cols)}",
                }

    # 3) fallback: prefer common id-like columns for grouped occurrence matching
    preferred = []
    lower_map = {c.lower(): c for c in common_columns}
    for cand in ["custom_id", "key", "id", "sample_id", "item_id", "uid"]:
        if cand in lower_map:
            preferred.append(lower_map[cand])

    if preferred:
        return {
            "mode": "group_occurrence",
            "columns": [preferred[0]],
            "description": f"group by non-unique column + occurrence index: {preferred[0]}",
        }

    # 4) final fallback: align by row index
    return {
        "mode": "row_index",
        "columns": [],
        "description": "row index alignment",
    }


def sample_diff_fields(a, b, compare_columns):
    changed = []
    for c in compare_columns:
        va = a.get(c, "<MISSING>")
        vb = b.get(c, "<MISSING>")
        if va != vb:
            changed.append(c)
    return changed


def index_by_unique_key(ds_split, key_columns):
    index = {}
    for row_idx, x in enumerate(ds_split):
        key = tuple(stable_json(x.get(c)) for c in key_columns)
        index[key] = (row_idx, x)
    return index


def group_by_key_with_occurrence(ds_split, key_columns):
    groups = defaultdict(list)
    for row_idx, x in enumerate(ds_split):
        key = tuple(stable_json(x.get(c)) for c in key_columns)
        groups[key].append((row_idx, x))
    return groups


def compare_by_unique_identity(split_name, split_a, split_b, identity, common_columns):
    key_columns = identity["columns"]

    idx_a = index_by_unique_key(split_a, key_columns)
    idx_b = index_by_unique_key(split_b, key_columns)

    keys_a = set(idx_a.keys())
    keys_b = set(idx_b.keys())

    only_a = keys_a - keys_b
    only_b = keys_b - keys_a
    common_keys = sorted(keys_a & keys_b)

    diff_counter = Counter()
    examples = []
    same_count = 0
    diff_count = 0

    for key in common_keys:
        _, a = idx_a[key]
        _, b = idx_b[key]

        changed = sample_diff_fields(a, b, common_columns)
        if not changed:
            same_count += 1
            continue

        diff_count += 1
        for f in changed:
            diff_counter[f] += 1

        if len(examples) < MAX_EXAMPLE_DIFFS_PER_SPLIT:
            examples.append(
                {
                    "identity_key": key,
                    "changed_fields": changed[:MAX_CHANGED_FIELDS_PRINT],
                    "sample_a": {f: a.get(f, "<MISSING>") for f in changed[:MAX_CHANGED_FIELDS_PRINT]},
                    "sample_b": {f: b.get(f, "<MISSING>") for f in changed[:MAX_CHANGED_FIELDS_PRINT]},
                }
            )

    return {
        "mode": identity["mode"],
        "identity_columns": key_columns,
        "keys_only_in_a": len(only_a),
        "keys_only_in_b": len(only_b),
        "same_rows": same_count,
        "different_rows": diff_count,
        "changed_field_counts": dict(diff_counter.most_common()),
        "examples": examples,
    }


def compare_by_group_occurrence(split_name, split_a, split_b, identity, common_columns):
    key_columns = identity["columns"]

    groups_a = group_by_key_with_occurrence(split_a, key_columns)
    groups_b = group_by_key_with_occurrence(split_b, key_columns)

    group_keys_a = set(groups_a.keys())
    group_keys_b = set(groups_b.keys())

    only_a = group_keys_a - group_keys_b
    only_b = group_keys_b - group_keys_a
    common_group_keys = sorted(group_keys_a & group_keys_b)

    diff_counter = Counter()
    examples = []
    same_count = 0
    diff_count = 0
    unmatched_rows_a = 0
    unmatched_rows_b = 0

    for gk in common_group_keys:
        rows_a = groups_a[gk]
        rows_b = groups_b[gk]

        min_len = min(len(rows_a), len(rows_b))
        unmatched_rows_a += max(0, len(rows_a) - len(rows_b))
        unmatched_rows_b += max(0, len(rows_b) - len(rows_a))

        for i in range(min_len):
            row_idx_a, a = rows_a[i]
            row_idx_b, b = rows_b[i]

            changed = sample_diff_fields(a, b, common_columns)
            if not changed:
                same_count += 1
                continue

            diff_count += 1
            for f in changed:
                diff_counter[f] += 1

            if len(examples) < MAX_EXAMPLE_DIFFS_PER_SPLIT:
                examples.append(
                    {
                        "group_key": gk,
                        "occurrence_index": i,
                        "row_idx_a": row_idx_a,
                        "row_idx_b": row_idx_b,
                        "changed_fields": changed[:MAX_CHANGED_FIELDS_PRINT],
                        "sample_a": {f: a.get(f, "<MISSING>") for f in changed[:MAX_CHANGED_FIELDS_PRINT]},
                        "sample_b": {f: b.get(f, "<MISSING>") for f in changed[:MAX_CHANGED_FIELDS_PRINT]},
                    }
                )

    unmatched_rows_a += sum(len(groups_a[k]) for k in only_a)
    unmatched_rows_b += sum(len(groups_b[k]) for k in only_b)

    return {
        "mode": identity["mode"],
        "identity_columns": key_columns,
        "group_keys_only_in_a": len(only_a),
        "group_keys_only_in_b": len(only_b),
        "unmatched_rows_a": unmatched_rows_a,
        "unmatched_rows_b": unmatched_rows_b,
        "same_rows": same_count,
        "different_rows": diff_count,
        "changed_field_counts": dict(diff_counter.most_common()),
        "examples": examples,
    }


def compare_by_row_index(split_name, split_a, split_b, common_columns):
    n = min(len(split_a), len(split_b))

    diff_counter = Counter()
    examples = []
    same_count = 0
    diff_count = 0

    for i in range(n):
        a = split_a[i]
        b = split_b[i]

        changed = sample_diff_fields(a, b, common_columns)
        if not changed:
            same_count += 1
            continue

        diff_count += 1
        for f in changed:
            diff_counter[f] += 1

        if len(examples) < MAX_EXAMPLE_DIFFS_PER_SPLIT:
            examples.append(
                {
                    "row_index": i,
                    "changed_fields": changed[:MAX_CHANGED_FIELDS_PRINT],
                    "sample_a": {f: a.get(f, "<MISSING>") for f in changed[:MAX_CHANGED_FIELDS_PRINT]},
                    "sample_b": {f: b.get(f, "<MISSING>") for f in changed[:MAX_CHANGED_FIELDS_PRINT]},
                }
            )

    return {
        "mode": "row_index",
        "same_rows": same_count,
        "different_rows": diff_count,
        "length_only_in_a": max(0, len(split_a) - len(split_b)),
        "length_only_in_b": max(0, len(split_b) - len(split_a)),
        "changed_field_counts": dict(diff_counter.most_common()),
        "examples": examples,
    }


def compare_row_multiset(split_a, split_b, common_columns):
    counter_a = Counter()
    counter_b = Counter()

    for x in split_a:
        counter_a[row_hash(x, common_columns)] += 1
    for x in split_b:
        counter_b[row_hash(x, common_columns)] += 1

    only_a = counter_a - counter_b
    only_b = counter_b - counter_a

    return {
        "same_row_multiset": (counter_a == counter_b),
        "rows_only_in_a": sum(only_a.values()),
        "rows_only_in_b": sum(only_b.values()),
    }


def main():
    ds_a = load_from_disk(DATASET_A_PATH)
    ds_b = load_from_disk(DATASET_B_PATH)

    common_splits, splits_a, splits_b = get_common_splits(ds_a, ds_b)

    print("========== SPLIT CHECK ==========")
    print("splits_a =", sorted(splits_a))
    print("splits_b =", sorted(splits_b))
    print("same_splits =", splits_a == splits_b)
    print("only_splits_in_a =", sorted(splits_a - splits_b))
    print("only_splits_in_b =", sorted(splits_b - splits_a))
    print()

    total_same = 0
    total_diff = 0

    for split in common_splits:
        print(f"========== SPLIT: {split} ==========")

        split_a = ds_a[split]
        split_b = ds_b[split]

        cols_a, cols_b, common_columns = get_common_columns(split_a, split_b)

        print(f"len(dataset_a[{split}]) = {len(split_a)}")
        print(f"len(dataset_b[{split}]) = {len(split_b)}")
        print("columns_a =", cols_a)
        print("columns_b =", cols_b)
        print("same_columns =", set(cols_a) == set(cols_b))
        print("common_columns =", common_columns)
        print()

        multiset_info = compare_row_multiset(split_a, split_b, common_columns)
        print("row_multiset_equal =", multiset_info["same_row_multiset"])
        print("rows_only_in_a_by_full_row =", multiset_info["rows_only_in_a"])
        print("rows_only_in_b_by_full_row =", multiset_info["rows_only_in_b"])

        identity = detect_identity_columns(split_a, split_b, common_columns)
        print("comparison_strategy =", identity["description"])
        print()

        if identity["mode"] in {"single_unique", "composite_unique"}:
            result = compare_by_unique_identity(split, split_a, split_b, identity, common_columns)
        elif identity["mode"] == "group_occurrence":
            result = compare_by_group_occurrence(split, split_a, split_b, identity, common_columns)
        else:
            result = compare_by_row_index(split, split_a, split_b, common_columns)

        print("result_mode =", result["mode"])
        print("same_rows =", result.get("same_rows"))
        print("different_rows =", result.get("different_rows"))

        for k in [
            "identity_columns",
            "keys_only_in_a",
            "keys_only_in_b",
            "group_keys_only_in_a",
            "group_keys_only_in_b",
            "unmatched_rows_a",
            "unmatched_rows_b",
            "length_only_in_a",
            "length_only_in_b",
        ]:
            if k in result:
                print(f"{k} =", result[k])

        print("changed_field_counts =", result.get("changed_field_counts", {}))
        print()

        examples = result.get("examples", [])
        if examples:
            print(f"----- Example diffs in split: {split} -----")
            for i, ex in enumerate(examples, 1):
                print(f"[Example {i}]")
                print(json.dumps(ex, ensure_ascii=False, indent=2))
                print("-" * 80)
        else:
            print(f"No aligned field-level differences found in split: {split}")

        print()

        total_same += result.get("same_rows", 0)
        total_diff += result.get("different_rows", 0)

    print("========== OVERALL SUMMARY ==========")
    print("total_same_rows =", total_same)
    print("total_different_rows =", total_diff)


if __name__ == "__main__":
    main()