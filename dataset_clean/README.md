# dataset_clean

## 项目目录结构
```
dataset_clean/
	src/
		clean_utils.py
		dataset_cleaning.py
	outputs/
	scripts/
		run_dataset_cleaning.sh
	README.md
```

## 项目主体
### dataset_cleaning.py
用于执行一次完整的数据清洗任务：加载数据集、应用规则、输出清洗报告、保存清洗后数据集。当前脚本是“固定配置入口”，并未暴露命令行参数，适合先在单数据源上稳定跑通。

#### 输入输出参数说明
- 输入参数来源：源码内部变量（非 CLI）。
- 关键输入：`dataset_path`（`load_from_disk` 路径）。
- 关键输出：
	- `output_path = f"{dataset_path}_cleaned"`，保存清洗后数据集。
	- `report_path = f"{dataset_path}_cleaning_report.json"`，保存规则统计报告。

#### 流程模块与关键函数
- `normalize_code(code)`：可选代码归一化函数，支持去注释与去空白（当前默认规则未启用该函数）。
- `main()` 流程：
	- 校验输入路径存在。
	- 加载数据集（支持 Dataset / DatasetDict）。
	- 构造规则列表（当前启用 `RequiredFieldsRule(required_keys=["func"])`）。
	- 调用 `clean_dataset` 执行规则链。
	- 调用 `print_cleaning_report` 打印摘要。
	- 输出 JSON 报告与清洗数据集。

## 项目工具类
### clean_utils.py
定义了清洗规则抽象与规则执行框架，是本目录核心工具层。

- `FilterRule`：规则基类，约定 `apply(dataset) -> (filtered_dataset, report)`。
- `RequiredFieldsRule`：过滤缺字段、`None`、空字符串样本。
- `FieldsNotEqualRule`：过滤两个字段归一化后相等的样本，支持自定义 `normalize_fn`。
- `clean_dataset(dataset, rules)`：统一支持 `Dataset` 和 `DatasetDict`，按顺序执行规则并产出分 split 报告。
- `print_cleaning_report(report)`：格式化输出规则执行统计。

### scripts/run_dataset_cleaning.sh
统一启动脚本，命令为：
`python toolkit/dataset_clean/src/dataset_cleaning.py`

