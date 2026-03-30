# utils.py
import re
from typing import Any

def is_empty(v: Any) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "")

def number_lines(code: Any) -> str:
    code = "" if code is None else str(code)
    return "\n".join(f"{i}| {line}" for i, line in enumerate(code.splitlines()))

def extract_placeholders(fmt: str) -> set:
    return set(re.findall(r"{([a-zA-Z_][a-zA-Z0-9_]*)}", fmt))
