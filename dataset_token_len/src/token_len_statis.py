"""
Compute token length statistics for a HuggingFace dataset.

Supports Dataset/DatasetDict, multiple text fields, and multiprocessing via
`dataset.map(...)`. Prints summary statistics and a histogram for each split.

"""

import argparse
import math
import numpy as np
from datasets import load_from_disk, DatasetDict
from transformers import AutoTokenizer


def build_texts_from_batch(batch, fields):
    batch_size = len(batch[fields[0]]) if fields else 0
    texts = []

    for i in range(batch_size):
        parts = []
        for f in fields:
            if f in batch:
                v = batch[f][i]
                if v is not None:
                    parts.append(str(v))
        texts.append("\n".join(parts))

    return texts


def compute_token_lengths_map(dataset, tokenizer, fields, max_samples=None, num_proc=1, batch_size=1000):
    if max_samples is not None:
        dataset = dataset.select(range(min(len(dataset), max_samples)))

    def token_len_fn(batch):
        texts = build_texts_from_batch(batch, fields)

        encodings = tokenizer(
            texts,
            add_special_tokens=False,
            truncation=False,
        )

        lengths = [len(ids) for ids in encodings["input_ids"]]
        return {"token_length": lengths}

    processed = dataset.map(
        token_len_fn,
        batched=True,
        batch_size=batch_size,
        num_proc=num_proc,
        desc="Computing token lengths",
    )

    lengths = np.array(processed["token_length"], dtype=np.int32)
    ids = list(processed["id"]) if "id" in processed.column_names else None
    return lengths, ids


def get_percentile_example_id(lengths, ids, percentile_value):
    if ids is None or len(ids) == 0 or len(lengths) == 0:
        return None

    target = int(math.ceil(percentile_value))
    for length, sample_id in zip(lengths, ids):
        if int(length) == target:
            return sample_id

    closest_index = int(np.argmin(np.abs(lengths - percentile_value)))
    return ids[closest_index]


def summarize(lengths, ids=None):
    if len(lengths) == 0:
        return {}

    percentile_keys = [
        ("p1", 1),
        ("p5", 5),
        ("p10", 10),
        ("p15", 15),
        ("p20", 20),
        ("p25", 25),
        ("p50", 50),
        ("p75", 75),
        ("p90", 90),
        ("p95", 95),
        ("p99", 99),
        ("p99.9", 99.9),
    ]

    stats = {
        "count": len(lengths),
        "mean": float(np.mean(lengths)),
        "std": float(np.std(lengths)),
        "min": int(np.min(lengths)),
        "max": int(np.max(lengths)),
    }

    for key, pct in percentile_keys:
        value = float(np.percentile(lengths, pct))
        example_id = get_percentile_example_id(lengths, ids, value)
        stats[key] = {"value": value, "id": example_id}

    return stats


def print_histogram(lengths, bins=20, width=50, title="Histogram"):
    hist, bin_edges = np.histogram(lengths, bins=bins)
    max_count = max(hist) if len(hist) > 0 else 1

    print(f"\n{title}:")
    for i in range(len(hist)):
        bar_len = int(width * hist[i] / max_count) if max_count > 0 else 0
        bar = "#" * bar_len
        print(f"[{int(bin_edges[i]):5d}, {int(bin_edges[i+1]):5d}): {bar} ({hist[i]})")


def print_trimmed_histogram(lengths, lower_pct=1, upper_pct=99, bins=20, width=50):
    lower = np.percentile(lengths, lower_pct)
    upper = np.percentile(lengths, upper_pct)

    trimmed = lengths[(lengths >= lower) & (lengths <= upper)]
    if len(trimmed) == 0:
        print(f"\nTrimmed Histogram (p{lower_pct} ~ p{upper_pct}): empty")
        return

    hist, bin_edges = np.histogram(trimmed, bins=bins)
    max_count = max(hist) if len(hist) > 0 else 1

    print(f"\nTrimmed Histogram (p{lower_pct} ~ p{upper_pct}, range: [{int(lower)}, {int(upper)}]):")
    for i in range(len(hist)):
        bar_len = int(width * hist[i] / max_count) if max_count > 0 else 0
        bar = "#" * bar_len
        print(f"[{int(bin_edges[i]):5d}, {int(bin_edges[i+1]):5d}): {bar} ({hist[i]})")


def print_tail_statistics(lengths):
    total = len(lengths)

    short_thresholds = [8, 16, 32, 64, 128, 256]
    long_thresholds = [512, 1024, 2048, 4096, 8192, 16384]

    print("\nShort-length statistics:")
    for t in short_thresholds:
        count = int(np.sum(lengths <= t))
        ratio = count / total * 100
        print(f"  <= {t:5d}: {count:10d} ({ratio:6.3f}%)")

    print("\nLong-length statistics:")
    for t in long_thresholds:
        count = int(np.sum(lengths >= t))
        ratio = count / total * 100
        print(f"  >= {t:5d}: {count:10d} ({ratio:6.3f}%)")


def analyze_split(dataset_name, split_name, dataset, tokenizer, fields, max_samples, num_proc, batch_size):
    print("=" * 80)
    print(f"Tokenizer: {tokenizer.__class__.__name__}")
    print(f"Dataset Name: {dataset_name}")
    print(f"Dataset: {dataset}")
    print(f"Split: {split_name}")
    print(f"Fields: {fields}")
    print(f"Num Proc: {num_proc}")
    print(f"Batch Size: {batch_size}")
    print("=" * 80)

    lengths, ids = compute_token_lengths_map(
        dataset=dataset,
        tokenizer=tokenizer,
        fields=fields,
        max_samples=max_samples,
        num_proc=num_proc,
        batch_size=batch_size,
    )

    if len(lengths) == 0:
        print("No valid samples found.")
        return

    stats = summarize(lengths, ids)

    print("\nSummary Statistics:")
    for k, v in stats.items():
        if isinstance(v, dict):
            sample_id = v["id"] if v["id"] is not None else "N/A"
            print(f"{k:>6}: {v['value']}  {sample_id}")
        else:
            print(f"{k:>6}: {v}")

    print_histogram(lengths, bins=20, width=50, title="Global Histogram")
    print_trimmed_histogram(lengths, lower_pct=1, upper_pct=99, bins=20, width=50)
    print_tail_statistics(lengths)
    print("\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tokenizer_path", type=str, required=True)
    parser.add_argument("--dataset_path", type=str, required=True)
    parser.add_argument("--split", type=str, default=None)
    parser.add_argument("--fields", type=str, nargs="+", required=True)
    parser.add_argument("--max_samples", type=int, default=None)
    parser.add_argument("--num_proc", type=int, default=1)
    parser.add_argument("--batch_size", type=int, default=1000)

    args = parser.parse_args()

    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer_path, use_fast=True)

    dataset_name = args.dataset_path.split("/")[-1]
    dataset = load_from_disk(args.dataset_path)

    if isinstance(dataset, DatasetDict):
        for split_name, split_dataset in dataset.items():
            if args.split is not None and split_name != args.split:
                continue
            analyze_split(
                dataset_name,
                split_name,
                split_dataset,
                tokenizer,
                args.fields,
                args.max_samples,
                args.num_proc,
                args.batch_size,
            )
    else:
        analyze_split(
            dataset_name,
            args.split or "dataset",
            dataset,
            tokenizer,
            args.fields,
            args.max_samples,
            args.num_proc,
            args.batch_size,
        )


if __name__ == "__main__":
    main()