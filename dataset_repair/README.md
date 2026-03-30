# dataset_repair

## 项目目录结构
```
dataset_repair/
	src/
		dataset_value_repair.py
	outputs/
	scripts/
		run_dataset_value_repair.sh
	README.md
```

## 项目主体
### dataset_value_repair.py
用于按列值匹配进行数据修复。脚本支持把标量、列表、`null`、空字符串等“异常值”统一替换成目标值，便于后续训练和统计一致化。

#### 输入输出参数说明
- 输入参数（CLI）：
	- `--dataset_path`、`--column`、`--old_values`、`--new_value`、`--output_path`。
	- 可选：`--num_proc`。
- 输出：
	- 修复后的数据集（`save_to_disk`）。
	- 控制台输出替换摘要与近似替换计数。

#### 流程模块与关键函数
- `parse_flexible_value`：JSON 优先解析，兼容 `null/none/''` 等快捷输入。
- `normalize_old_values`：把 old_values 归一为列表。
- `load_dataset_auto`：DatasetDict 自动选择首个 split。
- `should_replace`：判断当前值是否命中替换集合。
- `main()`：
	- 解析参数并规范化 old/new 值。
	- 校验目标列存在。
	- `dataset.map` 执行替换。
	- 保存结果并打印统计。

## 项目工具类
### scripts/run_dataset_value_repair.sh
包含多组示例命令，统一为：
`python toolkit/dataset_repair/src/dataset_value_repair.py ...`

