# dataset_token_len

## 项目目录结构
```
dataset_token_len/
	src/
		token_len_statis.py
	outputs/
	scripts/
		run_token_len_statis.sh
	README.md
```

## 项目主体
### token_len_statis.py
用于统计文本字段 token 长度分布，输出均值、分位点、直方图和长短尾比例。适合用于上下文窗口规划与样本长度治理。

#### 输入输出参数说明
- 输入参数（CLI）：
	- `--tokenizer_path`、`--dataset_path`、`--fields`。
	- 可选：`--split`、`--max_samples`、`--num_proc`、`--batch_size`。
- 输出：
	- 控制台统计结果（通常通过 shell 重定向保存到 `outputs/*.txt`）。

#### 流程模块与关键函数
- `build_texts_from_batch`：把多个字段拼接成待分词文本。
- `compute_token_lengths_map`：`dataset.map` 批量计算 token 长度，返回长度数组与可选 `id`。
- `summarize`：计算 count/mean/std/min/max 及 p1~p99.9。
- `print_histogram`、`print_trimmed_histogram`、`print_tail_statistics`：输出全局与截尾直方图、长短尾统计。
- `analyze_split`：对一个 split 执行完整统计。
- `main()`：加载 tokenizer 和 dataset，支持 DatasetDict 多 split 处理。

## 项目工具类
### scripts/run_token_len_statis.sh
包含多组示例命令，统一为：
`python toolkit/dataset_token_len/src/token_len_statis.py ...`

