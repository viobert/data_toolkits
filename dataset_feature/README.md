# dataset_feature

## 项目目录结构
```
dataset_feature/
	src/
		dataset_code_normalized.py
		dataset_pair_merge.py
	outputs/
	scripts/
		run_dataset_code_normalized.sh
		run_dataset_pair_merge.sh
	README.md
```

## 项目主体
### dataset_code_normalized.py
用于对 C/C++ 代码字段做文本标准化，并生成 `changed` 标记列。该脚本通过状态机方式处理注释删除，可避免误删字符串/字符字面量中的注释符号。

#### 输入输出参数说明
- 输入参数（CLI）：
	- `--dataset_path`、`--input_field`、`--output_path`。
	- `--output_field`（默认 `code`）、`--split`、`--num_proc`、`--batch_size`。
	- 归一化开关：`--keep_comments`、`--no_strip_trailing_whitespace`、`--no_collapse_blank_lines`、`--max_consecutive_blank_lines`、`--no_trim_leading_trailing_blank_lines`。
- 输出：
	- 处理后的数据集（`save_to_disk`）。
	- 新增/覆盖 `output_field`。
	- 新增 `changed` 布尔列。

#### 流程模块与关键函数
- `_remove_c_cpp_comments`：基于状态机处理行注释、块注释、普通字符串、字符字面量、raw string。
- `normalize_c_cpp_code`：串联换行统一、注释移除、行尾空白清理、空行压缩、首尾空行裁剪。
- `main()`：
	- 加载 Dataset / DatasetDict（自动 split 处理）。
	- 校验输入列存在。
	- `dataset.map` 批处理文本归一化。
	- 打印变更统计并保存输出。

### dataset_pair_merge.py
用于将 `fix-*` 样本代码回填到对应样本，生成 `code_fix` 列，同时从最终数据集中移除 `fix-*` 样本。

#### 输入输出参数说明
- 输入参数（CLI）：
	- 必填：`--dataset_path`、`--output_path`。
	- 可选：`--split`、`--id_column`、`--pair_column`、`--code_column`、`--code_fix_column`、`--num_proc`、`--overwrite_output`。
- 输出：
	- 新数据集写入 `--output_path`。
	- 输出中移除 `pair_column`，并新增 `code_fix_column`。

#### 流程模块与关键函数
- `load_hf_dataset`：统一加载 Dataset/DatasetDict。
- `validate_columns`：校验必需列及冲突列。
- `build_fix_code_map`：构建 `fix_id -> fix_code` 映射。
- `attach_fix_code`：过滤 `fix-*`、按 `pair_column` 回填 `code_fix`。
- `print_summary`：输出 bug/good 行统计与匹配命中情况。

## 项目工具类
### scripts/run_dataset_code_normalized.sh
包含多组启动命令，均使用：
`python toolkit/dataset_feature/src/dataset_code_normalized.py ...`

### scripts/run_dataset_pair_merge.sh
包含多组启动命令，均使用：
`python toolkit/dataset_feature/src/dataset_pair_merge.py ...`

