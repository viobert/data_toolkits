"""
Rename columns in a HuggingFace dataset.
"""

import argparse
from datasets import load_from_disk


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_path", required=True, type=str)
    parser.add_argument("--output_path", required=True, type=str)
    parser.add_argument("--old_names", nargs="+", required=True)
    parser.add_argument("--new_names", nargs="+", required=True)
    return parser.parse_args()


def main():
    args = parse_args()

    if len(args.old_names) != len(args.new_names):
        raise ValueError("`--old_names` and `--new_names` must have the same length.")

    dataset = load_from_disk(args.dataset_path)

    if len(args.old_names) == 1:
        dataset = dataset.rename_column(args.old_names[0], args.new_names[0])
    else:
        dataset = dataset.rename_columns(dict(zip(args.old_names, args.new_names)))

    print(dataset)
    dataset.save_to_disk(args.output_path)


if __name__ == "__main__":
    main()