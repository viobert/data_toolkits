# dataset_promptjson

把 HuggingFace Dataset 转成 prompt JSONL 的小工具。

当前版本已经移除 `config.py`，全部参数通过：
- `scripts/run_main.sh` 里的变量
- 或者直接 `python src/main.py --xxx ...` 传参

支持两类能力：
- 挂外部字典（CWE 索引）
- 不挂字典，只使用数据集本身字段

## 目录结构
```text
dataset_promptjson/
	src/
		main.py
		data_models.py
		data_toolkits.py
		utils.py
	templates/
	outputs/
	scripts/
		run_main.sh
	README.md
```

## 快速开始
在仓库根目录执行：

```bash
bash toolkit/dataset_promptjson/scripts/run_main.sh
```

默认参数都在 `run_main.sh` 顶部，改变量即可。

## 参数说明（main.py）

```bash
python toolkit/dataset_promptjson/src/main.py \
	--dataset-dir <hf_dataset_dir> \
	--split-name <train|test|validation> \
	--prompt-template-dir <template_dir> \
	--template-name <name1[,name2,...]> \
	--id-field <id_field> \
	--cwe-field <cwe_field> \
	--output-dir <output_dir> \
	[--drop-debug-sample-count <int>] \
	[--number-code-lines] \
	[--use-cwe-dict --cwe-index-path <cwe_json_path>]
```

关键点：
- `--template-name` 使用逗号分隔多个模板名。
- `--number-code-lines` 是 action 开关，不传就是关闭。
- `--use-cwe-dict` 是 action 开关，传了才启用外挂字典。
- 启用 `--use-cwe-dict` 后，必须同时传 `--cwe-index-path`。

## 四种常见模式

### 1) 挂字典 + 单模板
```bash
python toolkit/dataset_promptjson/src/main.py \
	--dataset-dir /home/skl/mkx/data/defect_detection_bench/datasets/vulnerability_filter_v1 \
	--split-name train \
	--prompt-template-dir /home/skl/mkx/data/toolkit/dataset_promptjson/templates \
	--template-name detect_with_cwedict \
	--id-field id \
	--cwe-field cwe_id \
	--output-dir /home/skl/mkx/data/toolkit/dataset_promptjson/outputs \
	--number-code-lines \
	--use-cwe-dict \
	--cwe-index-path /home/skl/mkx/data/cwe_dict/cwe_index_4.19.1.json
```

### 2) 挂字典 + 多模板（逗号分隔）
```bash
python toolkit/dataset_promptjson/src/main.py \
	--dataset-dir /home/skl/mkx/data/defect_detection_bench/datasets/vulnerability_filter_v1 \
	--split-name train \
	--prompt-template-dir /home/skl/mkx/data/toolkit/dataset_promptjson/templates \
	--template-name dataquality_bug_v2,dataquality_good_v2,detect_with_cwedict \
	--id-field id \
	--cwe-field cwe_id \
	--output-dir /home/skl/mkx/data/toolkit/dataset_promptjson/outputs \
	--use-cwe-dict \
	--cwe-index-path /home/skl/mkx/data/cwe_dict/cwe_index_4.19.1.json
```

### 3) 不挂字典 + 单模板
```bash
python toolkit/dataset_promptjson/src/main.py \
	--dataset-dir /home/skl/mkx/data/defect_detection_bench/datasets/vulnerability_filter_v1 \
	--split-name train \
	--prompt-template-dir /home/skl/mkx/data/toolkit/dataset_promptjson/templates \
	--template-name cwe_code_generate \
	--id-field id \
	--cwe-field cwe_id \
	--output-dir /home/skl/mkx/data/toolkit/dataset_promptjson/outputs
```

### 4) 不挂字典 + 多模板（逗号分隔）
```bash
python toolkit/dataset_promptjson/src/main.py \
	--dataset-dir /home/skl/mkx/data/defect_detection_bench/datasets/vulnerability_filter_v1 \
	--split-name train \
	--prompt-template-dir /home/skl/mkx/data/toolkit/dataset_promptjson/templates \
	--template-name dataquality_bug,dataquality_good \
	--id-field id \
	--cwe-field cwe_id \
	--output-dir /home/skl/mkx/data/toolkit/dataset_promptjson/outputs
```

## 使用 run_main.sh 的方式

`run_main.sh` 中已经提供了常用变量：
- `TEMPLATE_NAME` 用逗号写多模板
- `USE_CWE_DICT=true/false` 控制是否挂字典
- `CWE_INDEX_PATH` 在 `USE_CWE_DICT=true` 时必须非空

示例：
- 单模板：`TEMPLATE_NAME="detect_with_cwedict"`
- 多模板：`TEMPLATE_NAME="dataquality_bug,dataquality_good"`
- 挂字典：`USE_CWE_DICT=true` 且填写 `CWE_INDEX_PATH`
- 不挂字典：`USE_CWE_DICT=false`

## 处理流程简述
- 加载数据集（支持 Dataset 或 DatasetDict+split）
- 加载一个或多个模板
- 每条样本按占位符映射填充并生成 prompt
- 必填字段缺失会丢弃并统计原因
- 输出 JSONL：每行结构 `{ "id": ..., "prompt": ... }`

