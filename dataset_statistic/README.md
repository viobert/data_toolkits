# dataset_statistic

## 项目目录结构
```
dataset_statistic/
	src/
		dataset_statistic_distribution.py
		dataset_statistic_cwe_id.py
		plot_utils.py
	outputs/
	scripts/
		run_dataset_statistic_distribution.sh
		run_dataset_statistic_cwe_id.sh
	README.md
```

## 项目主体
### dataset_statistic_distribution.py
用于统计 HuggingFace 数据集某个字段分布，并导出：
- 饼状图（同时显示数量与百分比，包含图例）
- CSV 分布表

支持 `Dataset` 与 `DatasetDict`：
- 输入为 `DatasetDict` 且未指定 `--split` 时，默认使用第一个 split，并输出 warning。

统计模式（简化为两种）：
- `--mode value`：直接统计原值
- `--mode prefix`：按分隔符统计前缀（默认分隔符 `-`，可用 `--prefix_sep` 修改）

### dataset_statistic_cwe_id.py
用于 `cwe_id` 的专用统计规则：
- `cwe_id` 是单值 list（如 `['CWE-123']`）：按该类统计
- `cwe_id` 是多值 list（如 `['CWE-79', 'CWE-89']`）：统一统计为 `<MULTI_CWE>`
- 这样可直接得到类似 “`CWE-123` 有多少，`<MULTI_CWE>` 有多少，占比分别多少”

### plot_utils.py
通用绘图和导表工具，供两个主脚本复用：
- `counter_to_rows`
- `save_distribution_csv`
- `save_pie_chart`

#### 输入输出参数说明
- `dataset_statistic_distribution.py`
	- 必填：`--dataset_path`、`--column`、`--output_dir`
	- 可选：`--split`、`--output_prefix`、`--batch_size`、`--keep_empty`、`--dpi`
	- 模式：`--mode {value,prefix}`、`--prefix_sep`
- `dataset_statistic_cwe_id.py`
	- 必填：`--dataset_path`、`--output_dir`
	- 可选：`--column`、`--split`、`--output_prefix`、`--batch_size`、`--keep_empty`、`--dpi`
- 输出文件
	- `{prefix}_distribution.csv`
	- `{prefix}_distribution_pie.png`

#### 流程模块与关键函数
- `load_hf_dataset`：加载 Dataset/DatasetDict，并处理 split 逻辑。
- `compute_distribution`：普通字段值/前缀统计。
- `compute_cwe_distribution`：`cwe_id` 专用统计。
- `plot_utils.py`：统一实现 CSV 与饼图输出。

## 项目工具类
### scripts/run_dataset_statistic_distribution.sh
普通字段统计示例：
`python toolkit/dataset_statistic/src/dataset_statistic_distribution.py ...`

### scripts/run_dataset_statistic_cwe_id.sh
`cwe_id` 专用统计示例：
`python toolkit/dataset_statistic/src/dataset_statistic_cwe_id.py ...`
