# dataset_filter

## 项目目录结构
```
dataset_filter/
	src/
		data_filter.py
	outputs/
	scripts/
		run_data_filter.sh
	README.md
```

## 项目主体
### data_filter.py
这是一个通用数据过滤脚本，支持按“字段值等于目标值”或“字段存在且非空”两种模式筛选数据，兼容 Dataset 与 DatasetDict。

#### 输入输出参数说明
- 输入参数（CLI）：
	- 必填：`--dataset_path`、`--field`。
	- 过滤模式：`--value` 与 `--exists` 二选一。
	- 附加约束：`--keep_nonempty`（配合 `--exists` 使用）。
	- 其他：`--split`、`--num_proc`、`--output_path`、`--print_samples`。
- 输出：
	- 过滤后数据集对象。
	- 提供 `--output_path` 时落盘到指定目录。

#### 流程模块与关键函数
- `parse_value`：将 `--value` 尝试按 JSON 解析（支持数字、布尔、null、字符串）。
- `load_single_dataset`：DatasetDict 自动 split 选择并输出 warning。
- `validate_args`：确保参数模式合法。
- `build_filter_fn`：按模式生成过滤函数。
- `main()`：执行过滤、输出统计、按需打印样本、按需保存结果。

## 项目工具类
### scripts/run_data_filter.sh
包含多个示例命令，均使用：
`python toolkit/dataset_filter/src/data_filter.py ...`

