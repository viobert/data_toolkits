# dataset_rename

## 项目目录结构
```
dataset_rename/
	src/
		dataset_rename_column.py
	outputs/
	scripts/
		run_dataset_rename_column.sh
	README.md
```

## 项目主体
### dataset_rename_column.py
这是一个轻量字段改名工具，适用于数据标准化阶段对列名做统一。支持单列和多列两种改名模式。

#### 输入输出参数说明
- 输入参数（CLI）：
	- `--dataset_path`：输入数据集路径。
	- `--output_path`：输出数据集路径。
	- `--old_names`：原字段名列表。
	- `--new_names`：新字段名列表。
- 输出：
	- 改名后的数据集（`save_to_disk`）。
	- 控制台打印数据集对象摘要。

#### 流程模块与关键函数
- `parse_args`：读取命令行参数。
- `main()`：
	- 校验 old/new 列表长度一致。
	- 加载数据集。
	- 单列场景用 `rename_column`，多列场景用 `rename_columns`。
	- 保存输出。

## 项目工具类
### scripts/run_dataset_rename_column.sh
包含多组示例命令，统一为：
`python toolkit/dataset_rename/src/dataset_rename_column.py ...`

