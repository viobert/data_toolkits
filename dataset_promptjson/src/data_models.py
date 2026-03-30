# data.py
from dataclasses import dataclass
from typing import Optional, Any, Dict

@dataclass
class FieldSpec:
    key: Optional[str]
    default: Any = ""
    required: bool = False
    number_lines: bool = False   # 对该字段是否做行号化（受总开关 NUMBER_CODE_LINES 影响）

# 数据字段映射
# mapping: Dict[str, FieldSpec], 其中key表示template中的占位符，value表示数据字段

mapping: Dict[str, FieldSpec] = {
    "code": FieldSpec("code", default="", required=True, number_lines=True),
    "cwe_id": FieldSpec("cwe_id", default="", required=True),
    "cwe_name": FieldSpec("cwe_name", default="", required=True),
    "cwe_description": FieldSpec("cwe_description", default="", required=True),
}
# mapping: Dict[str, FieldSpec] = {
#     "language": FieldSpec("language", default="C/C++", required=False),
#     "cwe_id": FieldSpec("cwe_id", default="", required=True),
#     "cwe_name": FieldSpec("cwe_name", default="", required=True),
#     "cwe_description": FieldSpec("cwe_description", default="", required=True),
#     "bug_code": FieldSpec("bug_code", default="", required=True, number_lines=True),
#     "fix_code": FieldSpec("fix_code", default="", required=True, number_lines=True),
# }
# mapping: Dict[str, FieldSpec] = {
#     "cwe_id": FieldSpec("cwe_id", default="", required=True),
#     "code": FieldSpec("code", default="", required=True, number_lines=True),
# }
