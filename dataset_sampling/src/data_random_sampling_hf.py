"""
Random Sampling Script for HuggingFace Datasets

This script loads a dataset from disk (saved via HuggingFace `datasets`),
randomly samples a specified number of examples using a fixed seed,
and saves the resulting subset back to disk.

Features:
- Supports both `Dataset` and `DatasetDict` formats.
- If a `DatasetDict` is provided, the first split will be automatically selected.
  A clear warning will be printed to notify the user.
- Deterministic sampling via user-specified random seed.
- Output is saved in HuggingFace dataset format using `save_to_disk`.

Arguments:
- --sample (int): Number of samples to extract from the dataset.
- --seed (int): Random seed for reproducibility.
- --input_path (str): Path to the input dataset (loadable via `load_from_disk`).
- --output_path (str): Path where the sampled dataset will be saved.
"""
import argparse
import random
from datasets import load_from_disk, Dataset, DatasetDict


def load_dataset_safely(path):
    data = load_from_disk(path)

    if isinstance(data, DatasetDict):
        first_split = list(data.keys())[0]
        print("\n" + "=" * 50)
        print(f"⚠️  WARNING: Input is a DatasetDict!")
        print(f"⚠️  Automatically using the FIRST split: '{first_split}'")
        print("⚠️  If this is not what you want, please modify the script.")
        print("=" * 50 + "\n")
        return data[first_split]

    elif isinstance(data, Dataset):
        return data

    else:
        raise ValueError(f"Unsupported dataset type: {type(data)}")


def sample_dataset(dataset, sample_size, seed):
    total_size = len(dataset)

    if sample_size > total_size:
        raise ValueError(
            f"Sample size ({sample_size}) > dataset size ({total_size})"
        )

    random.seed(seed)
    indices = list(range(total_size))
    random.shuffle(indices)

    selected_indices = indices[:sample_size]
    sampled_dataset = dataset.select(selected_indices)

    return sampled_dataset


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, required=True, help="Number of samples to extract")
    parser.add_argument("--seed", type=int, required=True, help="Random seed")
    parser.add_argument("--input_path", type=str, required=True, help="Input dataset path")
    parser.add_argument("--output_path", type=str, required=True, help="Output dataset path")

    args = parser.parse_args()

    dataset = load_dataset_safely(args.input_path)

    print(f"Loaded dataset size: {len(dataset)}")

    sampled_dataset = sample_dataset(dataset, args.sample, args.seed)

    print(f"Sampled dataset size: {len(sampled_dataset)}")

    sampled_dataset.save_to_disk(args.output_path)

    print(f"✅ Saved sampled dataset to: {args.output_path}")


if __name__ == "__main__":
    main()