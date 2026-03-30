# dataset_sampling

## 项目目录结构
```
dataset_sampling/
	src/
		data_random_sampling_hf.py
	outputs/
	scripts/
		run_data_random_sampling_hf.sh
	README.md
```

## 项目主体
### data_random_sampling_hf.py
用于对 HuggingFace 数据集做可复现随机抽样，并输出子集数据。该脚本偏向快速构造小规模调试集或评估子集。

#### 输入输出参数说明
- 输入参数（CLI）：
	- `--sample`：抽样数量。
	- `--seed`：随机种子。
	- `--input_path`：输入数据集。
	- `--output_path`：输出路径。
- 输出：
	- 抽样后数据集（`save_to_disk`）。
	- 控制台输出原始大小、抽样大小、保存路径。

#### 流程模块与关键函数
- `load_dataset_safely`：加载 Dataset / DatasetDict（DatasetDict 默认取首 split 并警告）。
- `sample_dataset`：
	- 校验 `sample_size <= total_size`。
	- 基于 `random.seed(seed)` 洗牌索引。
	- `dataset.select(selected_indices)` 生成子集。
- `main()`：参数解析、加载数据、抽样、保存。

## 项目工具类
### scripts/run_data_random_sampling_hf.sh
示例命令统一为：
`python toolkit/dataset_sampling/src/data_random_sampling_hf.py ...`

