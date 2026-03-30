"""
Normalize C/C++ code strings in a HuggingFace dataset.

Supports Dataset/DatasetDict and multiprocessing via `dataset.map(...)`.
Adds one normalized code column and one boolean column indicating whether the
code changed after normalization.

"""

from __future__ import annotations

import argparse
import warnings

from datasets import Dataset, DatasetDict, load_from_disk


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _remove_c_cpp_comments(text: str) -> str:
    result = []
    i = 0
    n = len(text)

    in_line_comment = False
    in_block_comment = False
    in_string = False
    in_char = False
    in_raw_string = False
    escape = False

    raw_end_seq = ""

    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
                result.append("\n")
            i += 1
            continue

        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
            if ch == "\n":
                result.append("\n")
            i += 1
            continue

        if in_raw_string:
            if raw_end_seq and text.startswith(raw_end_seq, i):
                result.append(raw_end_seq)
                i += len(raw_end_seq)
                in_raw_string = False
                raw_end_seq = ""
                continue

            result.append(ch)
            i += 1
            continue

        if in_string:
            result.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            i += 1
            continue

        if in_char:
            result.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == "'":
                in_char = False
            i += 1
            continue

        if ch == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue

        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue

        # C++ raw string literal:
        # R"( ... )"
        # R"delim( ... )delim"
        if ch == "R" and nxt == '"':
            j = i + 2
            while j < n and text[j] != "(":
                j += 1

            if j < n:
                delim = text[i + 2 : j]
                raw_end_seq = ")" + delim + '"'
                literal_prefix = text[i : j + 1]  # include '('
                result.append(literal_prefix)
                i = j + 1
                in_raw_string = True
                continue

        if ch == '"':
            in_string = True
            result.append(ch)
            i += 1
            continue

        if ch == "'":
            in_char = True
            result.append(ch)
            i += 1
            continue

        result.append(ch)
        i += 1

    return "".join(result)


def _rstrip_trailing_whitespace_per_line(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.split("\n"))


def _collapse_blank_lines(text: str, max_consecutive_blank_lines: int = 1) -> str:
    lines = text.split("\n")
    new_lines = []
    blank_count = 0

    for line in lines:
        if line.strip() == "":
            blank_count += 1
            if blank_count <= max_consecutive_blank_lines:
                new_lines.append("")
        else:
            blank_count = 0
            new_lines.append(line)

    return "\n".join(new_lines)


def _trim_leading_trailing_blank_lines(text: str) -> str:
    lines = text.split("\n")

    start = 0
    end = len(lines)

    while start < end and lines[start].strip() == "":
        start += 1
    while end > start and lines[end - 1].strip() == "":
        end -= 1

    return "\n".join(lines[start:end])


def normalize_c_cpp_code(
    text: str,
    remove_comments: bool = True,
    strip_trailing_whitespace: bool = True,
    collapse_blank_lines: bool = True,
    max_consecutive_blank_lines: int = 1,
    trim_leading_trailing_blank_lines: bool = True,
) -> str:
    if not isinstance(text, str):
        raise TypeError(f"Expected a string, got {type(text).__name__}.")

    text = _normalize_newlines(text)

    if remove_comments:
        text = _remove_c_cpp_comments(text)

    if strip_trailing_whitespace:
        text = _rstrip_trailing_whitespace_per_line(text)

    if collapse_blank_lines:
        text = _collapse_blank_lines(text, max_consecutive_blank_lines)

    if trim_leading_trailing_blank_lines:
        text = _trim_leading_trailing_blank_lines(text)

    return text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize a C/C++ code column in a HuggingFace dataset."
    )
    parser.add_argument("--dataset_path", type=str, required=True)
    parser.add_argument("--input_field", type=str, required=True)
    parser.add_argument("--output_field", type=str, default="code")
    parser.add_argument("--output_path", type=str, required=True)
    parser.add_argument("--split", type=str, default=None)
    parser.add_argument("--num_proc", type=int, default=None)
    parser.add_argument("--batch_size", type=int, default=1000)

    parser.add_argument("--keep_comments", action="store_true")
    parser.add_argument("--no_strip_trailing_whitespace", action="store_true")
    parser.add_argument("--no_collapse_blank_lines", action="store_true")
    parser.add_argument("--max_consecutive_blank_lines", type=int, default=1)
    parser.add_argument("--no_trim_leading_trailing_blank_lines", action="store_true")

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    obj = load_from_disk(args.dataset_path)

    if isinstance(obj, DatasetDict):
        if args.split is None:
            split_names = list(obj.keys())
            if not split_names:
                raise ValueError("The DatasetDict is empty.")
            args.split = split_names[0]
            warnings.warn(
                f"Input is a DatasetDict. No split was specified, so the first "
                f"split '{args.split}' will be used.",
                stacklevel=2,
            )
        if args.split not in obj:
            raise ValueError(
                f"Split '{args.split}' not found. Available splits: {list(obj.keys())}"
            )
        dataset = obj[args.split]
    elif isinstance(obj, Dataset):
        dataset = obj
        if args.split is not None:
            warnings.warn(
                "A split was specified, but the loaded object is a Dataset. "
                "The split argument will be ignored.",
                stacklevel=2,
            )
    else:
        raise TypeError("Loaded object is neither Dataset nor DatasetDict.")

    if args.input_field not in dataset.column_names:
        raise ValueError(
            f"Column '{args.input_field}' not found. "
            f"Available columns: {dataset.column_names}"
        )

    def map_fn(batch):
        normalized_codes = []
        changed_flags = []

        for value in batch[args.input_field]:
            if not isinstance(value, str):
                raise TypeError(
                    f"Field '{args.input_field}' contains non-string values."
                )

            normalized = normalize_c_cpp_code(
                value,
                remove_comments=not args.keep_comments,
                strip_trailing_whitespace=not args.no_strip_trailing_whitespace,
                collapse_blank_lines=not args.no_collapse_blank_lines,
                max_consecutive_blank_lines=args.max_consecutive_blank_lines,
                trim_leading_trailing_blank_lines=(
                    not args.no_trim_leading_trailing_blank_lines
                ),
            )
            normalized_codes.append(normalized)
            changed_flags.append(normalized != value)

        return {
            args.output_field: normalized_codes,
            "changed": changed_flags,
        }

    dataset = dataset.map(
        map_fn,
        batched=True,
        batch_size=args.batch_size,
        num_proc=args.num_proc,
        desc=f"Normalizing code from '{args.input_field}'",
    )

    total = len(dataset)
    changed = sum(dataset["changed"])

    print(f"Total samples: {total}")
    print(f"Changed samples: {changed}")
    print(f"Unchanged samples: {total - changed}")
    print(f"Changed ratio: {(changed / total if total > 0 else 0.0):.6f}")

    dataset.save_to_disk(args.output_path)
    print(f"Saved to: {args.output_path}")


def test_normalize_c_cpp_code_comment_and_literal_cases():
    # 字符串中含 '//' 不应被删除
    code = 'const char* url = "http://example.com";'
    assert normalize_c_cpp_code(code) == code

    # 字符串中含 '/* */' 不应被删除
    code = 'const char* s = "a /* not a comment */ b";'
    assert normalize_c_cpp_code(code) == code

    # 字符串内有转义引号，后面紧跟真实注释
    code = 'const char* s = "say \\"hi\\""; // real comment\nint x = 1;'
    expected = 'const char* s = "say \\"hi\\"";\nint x = 1;'
    assert normalize_c_cpp_code(code) == expected

    # 字符字面量 '/' 不应干扰后续注释解析
    code = "char c = '/'; // real comment\nint x = 1;"
    expected = "char c = '/';\nint x = 1;"
    assert normalize_c_cpp_code(code) == expected

    # 字符串同时含有 '//' 和 '/*' 均不应被删除
    code = 'printf("Usage: a /* or */ b // c\\n");'
    assert normalize_c_cpp_code(code) == code

    # --------------------------------------------------
    # 暴露 BUG 的测试（这里按“当前实际行为”写）
    # --------------------------------------------------

    # C 标准下块注释等价于一个空格，但当前实现会输出 intx
    code = "int/**/x = 1;"
    result = normalize_c_cpp_code(code)
    assert result == "intx = 1;"

    # 同上，关键字与标识符之间也会被错误拼接
    code = "return/*value*/0;"
    result = normalize_c_cpp_code(code)
    assert result == "return0;"

    # C++11 raw string literal 中的内容不应被当成普通字符串结束
    code = 'const char* s = R"(He said " // still raw)";'
    result = normalize_c_cpp_code(code)
    assert result == code

    # raw string 内部 " 后接 /* 也不应触发块注释
    code = 'const char* s = R"(x" /* eat everything)";'
    result = normalize_c_cpp_code(code)
    assert result == code

if __name__ == "__main__":
    main()
    # test_normalize_c_cpp_code_comment_and_literal_cases()