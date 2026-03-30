# DATA-TOOLKITs

> This project focuses on fine-grained / routine data processing. It involves a relatively high degree of customization and does not guarantee general applicability.
> This directory is a tool repository for processing HuggingFace datasets, covering common workflows such as data cleaning, difference comparison, field fixing, field renaming, sampling, statistical analysis, and prompt construction.
> 🚀 Continuously being updated...

**注意**该项目旨在数据的细节性/日常性处理，客制化程度较高，不保证通用性。

本目录是一个面向 HuggingFace 数据集处理的工具仓库，覆盖清洗、差异比较、字段修复、字段重命名、抽样、统计分析、Prompt 构造等常见流程。

🚀持续更新ing...

## 目录概览
- `dataset_clean`：规则化清洗与清洗报告。
- `dataset_diff`：两份数据集结构和内容差异分析。
- `dataset_feature`：代码归一化与 bug-fix 对应关系合并。
- `dataset_filter`：按字段值/存在性过滤。
- `dataset_promptjson`：模板化生成 JSONL prompt。
- `dataset_query`：字段分布与缺失值模式分析。
- `dataset_rename`：字段改名。
- `dataset_repair`：按值替换修复字段。
- `dataset_sampling`：随机抽样子集。
- `dataset_token_len`：token 长度统计与分布分析。

## 统一约定
- 每个工具目录包含：`src/`、`outputs/`、`scripts/`、`README.md`。
- `scripts/` 提供可直接执行的启动命令，均使用 `python toolkit/<tool>/src/<file>.py ...` 形式。
- 详细代码级说明请查看各子目录 `README.md`。

