# Xray Indexer Request

JFrog Xray 索引器请求分析工具，用于分析 Xray 日志中的索引请求和统计信息。

## 功能特性

- **索引请求分析** - 识别和分析 Xray 索引器接收的各种请求类型
- **请求分类** - 按类型分类：created、build、release-bundle、forceReindex
- **统计报告** - 生成详细的请求统计摘要

## 使用方法

```sh
# 分析指定日志目录
python3 xray-indexer-request-trace.py /path/to/logs

# 指定输出文件
python3 xray-indexer-request-trace.py /path/to/logs --output analysis.log

# 显示前N条结果
python3 xray-indexer-request-trace.py /path/to/logs --head 10
```

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `log_dir` | Xray 日志目录路径 | **必需** |
| `--head` | 显示前N条结果 | `2` |
| `--output` | 输出日志文件名 | `requests.log` |

## 环境要求

- Python 3.6+
- 标准库模块（无需额外依赖） 