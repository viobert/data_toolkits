# dataset_promptjson

## 项目目录结构
```
dataset_promptjson/
	src/
		main.py
		config.py
		data_models.py
		data_toolkits.py
		utils.py
	templates/
	outputs/
	scripts/
		run_main.sh
	README.md
```

## 项目主体
### main.py
主流程负责把数据样本转成 prompt JSONL。它按照模板占位符映射规则逐字段填充，并在必填字段缺失时丢弃样本，最后输出处理统计。

#### 输入输出参数说明
- 参数来源：`config.py` 常量（非 CLI）。
- 关键输入：`DATASET_DIR`、`SPLIT_NAME`、`PROMPT_TEMPLATE_DIR`、`TEMPLATE_NAME`、`ID_FIELD`、`NUMBER_CODE_LINES`。
- 输出：通过 `prepare_output_path` 得到 JSONL 路径，并写入 `{id, prompt}` 记录。

#### 流程模块与关键函数
- `validate_template_placeholders`：检查模板占位符是否能被 `mapping` 覆盖（当前未在 `main()` 里调用）。
- `process_sample`：
	- 读取样本 ID。
	- 按 `mapping` 处理 required/default/number_lines。
	- `template.format(**values)` 生成 prompt。
- `process_dataset`：遍历数据集，累计写入数、丢弃数、字段填充统计。
- `write_output`：把结果写成 JSONL。
- `main()`：加载数据、加载模板、处理样本、输出统计。

## 项目工具类
### config.py
集中配置输入数据、模板路径、模板名、ID 字段、行号化开关等。

### data_models.py
定义 `FieldSpec` 与 `mapping`，用于描述模板占位符和数据字段的映射关系。

### data_toolkits.py
提供数据加载、模板加载、输出路径生成函数：
- `load_datasets`
- `load_templates`
- `prepare_output_path`

### utils.py
提供通用函数：
- `is_empty`
- `number_lines`
- `extract_placeholders`

### templates/
存放 prompt 模板文本文件（`*.txt`），由 `TEMPLATE_NAME` 指定加载。

### scripts/run_main.sh
统一启动脚本，命令为：
`python toolkit/dataset_promptjson/src/main.py`

