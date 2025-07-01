# xray-indexer-request-trace.py 使用说明

## 脚本用途

本脚本用于扫描 Xray 日志目录，统计和提取各种类型的索引请求（如普通索引、build、release-bundle、forceReindex），并按分类分组输出到日志文件，便于分析和排查。

## 支持的请求类型
- 普通索引（created）
- build 索引（build）
- release-bundle 索引（release-bundle）
- 强制重新索引（forceReindex）

## 使用方法

```bash
python3 xray-indexer-request-trace.py <日志目录> [--head N] [--output 文件名]
```

### 参数说明
- `<日志目录>`：需要扫描的日志主目录（如 xray/）
- `--head N`：每个分类在控制台显示前 N 条（默认 20，脚本默认2，建议自定义）
- `--output 文件名`：输出日志文件名（默认 requests.log）

### 示例

```bash
python3 xray-indexer-request-trace.py /path/to/xray-logs/ --head 10 --output my_requests.log
```

## 输出说明

1. **控制台输出**：
   - 显示每类请求的统计摘要
   - 每类显示前 N 条最新请求（按时间倒序）
   - 如有更多条目，提示如何查看更多

2. **日志文件输出**：
   - 文件头部为统计摘要
   - 按 forceReindex、release-bundle、build、created 分类分组，最新在前
   - 每条带编号，便于查阅

### 日志文件样例
```
# Xray Index 请求统计摘要
# 生成时间: 2025-07-01 12:46:33
# 日志目录: xray/
# 总请求数: 1248
# EVENT 请求总数: 1150 条
#   - created: 1116 条
#   - build: 30 条
#   - release-bundle: 4 条
# forceReindex 请求: 88 条
# ================================================================================

# ==== forceReindex (88 条) ====
   1. 2025-07-01T03:14:25.038Z ...
   2. ...

# ==== release-bundle (4 条) ====
   1. 2025-07-01T03:14:25.038Z ...

# ==== build (30 条) ====
   1. 2025-07-01T03:14:25.038Z ...

# ==== created (1116 条) ====
   1. 2025-07-01T03:14:25.038Z ...
```

## 注意事项
- 仅扫描 xray-server-service.log 及其归档（xray-server-service-*.log），自动排除 metrics、error、stack、request、traefik 等无关日志。
- 日志行自动去重，避免重复统计。
- 按时间倒序输出，优先展示最新请求。
- forceReindex 匹配需同时包含 forceReindex 和 Scan status record updated for。
- 支持大批量日志目录分析，适合日常巡检和问题定位。

---
如有问题或建议，请联系脚本维护者。 