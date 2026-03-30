# data_loader.py
import json
import os
from datasets import load_from_disk, DatasetDict
from config import DATASET_DIR, SPLIT_NAME, OUTPUT_DIR
from utils import extract_placeholders, is_empty

COMPUTED_PLACEHOLDERS = {"claimed_cwe_json", "claimed_cwe_text"}

def load_datasets() -> DatasetDict:
    """加载数据集并处理split"""
    ds = load_from_disk(DATASET_DIR)

    if isinstance(ds, DatasetDict):
        if SPLIT_NAME not in ds:
            raise ValueError(f"Split '{SPLIT_NAME}' not found in dataset")
        return ds[SPLIT_NAME]
    else:
        print(f"Warning: dataset is not a DatasetDict; using it directly")
        return ds
    

def load_templates(template_dir: str, template_names: list) -> dict:
    """根据模板名称列表，从指定目录加载相应的模板文件并返回字典"""
    templates = {}
    for template_name in template_names:
        template_path = os.path.join(template_dir, f"{template_name}.txt")
        if os.path.exists(template_path):
            with open(template_path, "r", encoding="utf-8") as f:
                templates[template_name] = f.read()
        else:
            # 如果模板文件不存在，报错
            raise FileNotFoundError(f"\033[1;31mWarning: Template {template_name} not found in {template_dir}\033[0m")
    return templates


def normalize_cwe_id(cwe_id: object) -> str:
    """统一 CWE ID 形式，兼容 '787'、'CWE-787' 和 ['CWE-787']。"""
    if cwe_id is None:
        return ""

    if isinstance(cwe_id, (list, tuple, set)):
        for item in cwe_id:
            normalized = normalize_cwe_id(item)
            if normalized:
                return normalized
        return ""

    text = str(cwe_id).strip()
    if not text:
        return ""

    upper = text.upper()
    if upper.startswith("CWE-"):
        return upper
    if upper.isdigit():
        return f"CWE-{upper}"
    return upper


def normalize_cwe_ids(cwe_value: object) -> list[str]:
    """把单个或多个 CWE 值统一整理成规范化后的列表。"""
    if cwe_value is None:
        return []

    if isinstance(cwe_value, (list, tuple, set)):
        normalized_ids = []
        seen = set()
        for item in cwe_value:
            normalized = normalize_cwe_id(item)
            if normalized and normalized not in seen:
                normalized_ids.append(normalized)
                seen.add(normalized)
        return normalized_ids

    normalized = normalize_cwe_id(cwe_value)
    return [normalized] if normalized else []


def as_list(value: object) -> list:
    """把标量或序列统一成列表，便于按索引对齐 CWE 元数据。"""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, set):
        return list(value)
    return [value]


def build_claimed_cwe_json(sample: dict) -> str:
    """把样本中的 claimed CWE 渲染成可插入模板的 JSON 字面量。"""
    cwe_id = sample.get("cwe_id")
    if isinstance(cwe_id, (list, tuple, set)):
        return json.dumps(list(cwe_id), ensure_ascii=False)
    return json.dumps(cwe_id if cwe_id is not None else "", ensure_ascii=False)


def build_claimed_cwe_text(sample: dict) -> str:
    """把一个或多个 CWE 渲染成更适合阅读的文本块。"""
    ids = as_list(sample.get("cwe_id"))
    names = as_list(sample.get("cwe_name"))
    descriptions = as_list(sample.get("cwe_description"))
    size = max(len(ids), len(names), len(descriptions))

    if size == 0:
        return "None"

    lines = []
    for idx in range(size):
        cwe_id = str(ids[idx]) if idx < len(ids) and ids[idx] is not None else ""
        cwe_name = str(names[idx]) if idx < len(names) and names[idx] is not None else ""
        cwe_description = str(descriptions[idx]) if idx < len(descriptions) and descriptions[idx] is not None else ""

        head_parts = [part for part in [cwe_id, cwe_name] if part]
        head = " — ".join(head_parts) if head_parts else f"CWE #{idx + 1}"
        if cwe_description:
            lines.append(f"- {head}: {cwe_description}")
        else:
            lines.append(f"- {head}")

    return "\n".join(lines)


def build_computed_placeholders(sample: dict) -> dict[str, str]:
    """生成不直接来自数据集字段的模板占位符。"""
    return {
        "claimed_cwe_json": build_claimed_cwe_json(sample),
        "claimed_cwe_text": build_claimed_cwe_text(sample),
    }


def load_cwe_lookup(cwe_index_path: str | None) -> dict[str, dict[str, str]]:
    """加载 CWE 字典；未配置时返回空字典。"""
    if not cwe_index_path:
        return {}
    if not os.path.exists(cwe_index_path):
        raise FileNotFoundError(f"CWE index file not found: {cwe_index_path}")

    with open(cwe_index_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    lookup: dict[str, dict[str, str]] = {}

    if isinstance(raw, dict):
        items = raw.items()
    elif isinstance(raw, list):
        items = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            key = item.get("cwe_id") or item.get("id")
            if key is not None:
                items.append((key, item))
    else:
        raise ValueError("Unsupported CWE index format; expected dict or list")

    for key, value in items:
        if not isinstance(value, dict):
            continue

        normalized = normalize_cwe_id(key)
        if not normalized:
            continue

        name = value.get("name") or value.get("cwe_name") or ""
        description = value.get("description") or value.get("cwe_description") or ""
        lookup[normalized] = {
            "cwe_id": normalized,
            "cwe_name": str(name),
            "cwe_description": str(description),
        }

    return lookup


def enrich_sample_with_cwe(
    sample: dict,
    cwe_lookup: dict[str, dict[str, str]],
    cwe_field: str,
) -> dict:
    """用外挂 CWE 字典补全样本缺失的 cwe_name/cwe_description，不覆盖已有值。"""
    if not cwe_lookup:
        return sample

    raw_cwe_value = sample.get(cwe_field)
    normalized_ids = normalize_cwe_ids(raw_cwe_value)
    if not normalized_ids:
        return sample

    matched = []
    for normalized_id in normalized_ids:
        cwe_meta = cwe_lookup.get(normalized_id)
        if cwe_meta:
            matched.append(cwe_meta)

    if not matched:
        return sample

    updates = {}
    if isinstance(raw_cwe_value, (list, tuple, set)):
        if is_empty(sample.get("cwe_id")):
            updates["cwe_id"] = [item["cwe_id"] for item in matched]
        if is_empty(sample.get("cwe_name")):
            updates["cwe_name"] = [item["cwe_name"] for item in matched]
        if is_empty(sample.get("cwe_description")):
            updates["cwe_description"] = [item["cwe_description"] for item in matched]
    else:
        cwe_meta = matched[0]
        if is_empty(sample.get("cwe_id")):
            updates["cwe_id"] = cwe_meta["cwe_id"]
        if is_empty(sample.get("cwe_name")) and not is_empty(cwe_meta.get("cwe_name")):
            updates["cwe_name"] = cwe_meta["cwe_name"]
        if is_empty(sample.get("cwe_description")) and not is_empty(cwe_meta.get("cwe_description")):
            updates["cwe_description"] = cwe_meta["cwe_description"]

    if not updates:
        return sample

    enriched = dict(sample)
    enriched.update(updates)
    return enriched


def validate_template_placeholders(template: str, mapping: dict) -> None:
    """检查模板中的占位符是否都能在 mapping 中找到。"""
    need = extract_placeholders(template)
    miss = sorted(need - set(mapping.keys()) - COMPUTED_PLACEHOLDERS)
    if miss:
        raise ValueError(f"Template placeholders not covered by mapping: {miss}")


def choose_template_name(sample: dict, templates: dict, id_field: str, cwe_field: str) -> str:
    """根据样本内容选择模板，仅为带 CWE 的 bug 样本使用 CWE 模板。"""
    sid = sample.get(id_field)
    has_cwe = not is_empty(sample.get(cwe_field))

    if isinstance(sid, str) and "bug" in sid:
        if has_cwe and "dataquality_bug_with_cwe" in templates:
            return "dataquality_bug_with_cwe"
        return "dataquality_bug_v2"

    if isinstance(sid, str) and "good" in sid:
        return "dataquality_good_v2"

    raise ValueError(f"Unknown type(bug/good/fix), sample ID: {sid}")


def prepare_output_path(dataset_name: str, split_tag: str) -> str:
    """根据数据集和split名称准备输出路径"""
    output_dir = OUTPUT_DIR or "./tmp"
    os.makedirs(output_dir, exist_ok=True)
    return os.path.join(output_dir, f"{dataset_name}_{split_tag}.jsonl")
