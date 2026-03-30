# dataset_query

## 项目目录结构
```
dataset_query/
	src/
		dataset_query_column.py
		dataset_query_missing_value.py
	outputs/
	scripts/
		run_dataset_query_column.sh
		run_dataset_query_missing_value.sh
	README.md
```

## 项目主体
### dataset_query_column.py
用于统计单字段值分布并导出 CSV，重点解决字段离散分布检查、空值比例检查、标签不平衡初筛等场景。

#### 输入输出参数说明
- 输入参数（CLI）：
	- `--dataset_path`、`--field`、`--output_csv`。
	- 可选：`--split`、`--keep_empty`、`--sort_by`、`--descending`。
- 输出：
	- CSV 列为 `field_value,count,ratio`。
	- 控制台输出总样本量、唯一值数量和前 10 条预览。

#### 流程模块与关键函数
- `load_hf_dataset`：加载 Dataset/DatasetDict。
- `normalize_value`：把 `None` 和空字符串映射为 token。
- `compute_distribution`：统计字段频次并计算比例。
- `sort_rows`：按 count 或 value 排序（当前 count 分支始终降序）。
- `save_csv`：写出 CSV。

### dataset_query_missing_value.py
用于系统化检查缺失值与占位值模式，支持字符串、容器、空白字符串等多类型异常的分类统计，并导出摘要与 top values。

#### 输入输出参数说明
- 输入参数（CLI）：
	- `--dataset_path`、`--output_dir`。
	- 可选：`--split`、`--fields`、`--top_fields`、`--top_k`、`--sample_size`、`--batch_size`、`--placeholder_values`。
- 输出：
	- `field_missing_summary.csv`
	- `field_top_values.csv`

#### 流程模块与关键函数
- `classify_value`：把值分类为 `none/empty_string/whitespace_string/placeholder_string/placeholder_container/normal` 等。
- `inspect_dataset`：按 batch 统计字段分布并累积 top 值计数。
- `select_top_fields`：自动选择可疑字段（也可由 `--top_fields` 指定）。
- `write_csv`：统一输出 CSV 文件。
- `main()`：先做预扫描，再做正式统计并输出结果。

## 项目工具类
### scripts/run_dataset_query_column.sh
包含多个示例命令，统一为：
`python toolkit/dataset_query/src/dataset_query_column.py ...`

### scripts/run_dataset_query_missing_value.sh
包含多个示例命令，统一为：
`python toolkit/dataset_query/src/dataset_query_missing_value.py ...`

