# dataset_diff

## 项目目录结构
```
dataset_diff/
	src/
		data_diff.py
	outputs/
	scripts/
		run_data_diff.sh
	README.md
```

## 项目主体
### data_diff.py
该脚本用于比较两个 HuggingFace 数据集在 split、列、行以及字段值层面的差异。它的核心能力是“自动识别对齐策略”，避免仅靠行号比较导致误判。

#### 输入输出参数说明
- 输入参数来源：源码顶部常量（非 CLI）。
- 关键输入：
	- `DATASET_A_PATH`、`DATASET_B_PATH`。
	- `MAX_COMPOSITE_KEY_SIZE`、`MAX_EXAMPLE_DIFFS_PER_SPLIT`、`MAX_CHANGED_FIELDS_PRINT`。
- 输出：标准输出日志（可重定向到 `outputs/`）。

#### 流程模块与关键函数
- 值规范化：`normalize_value`、`stable_json`、`row_hash`。
- 结构比较：`get_common_splits`、`get_common_columns`、`compare_row_multiset`。
- 身份策略检测：`detect_identity_columns`，按如下顺序选择：
	- 单列唯一键。
	- 组合列唯一键（最多 `MAX_COMPOSITE_KEY_SIZE` 列）。
	- 类 ID 列分组 + 组内出现序号。
	- 行索引兜底。
- 差异执行：
	- `compare_by_unique_identity`
	- `compare_by_group_occurrence`
	- `compare_by_row_index`
- 主流程 `main()`：逐 split 输出 same/different 统计、字段变更计数、差异样例。

## 项目工具类
### scripts/run_data_diff.sh
统一启动脚本，命令为：
`python toolkit/dataset_diff/src/data_diff.py`

建议把执行日志保存到 `outputs/`，例如：
`python toolkit/dataset_diff/src/data_diff.py > toolkit/dataset_diff/outputs/report.txt 2>&1`

