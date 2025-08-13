# Binary SHA1 Validator

JFrog Artifactory 制品SHA1校验工具 - 提供Python和Shell两种实现

## 功能特性

- **SHA1校验** - 验证文件名与文件内容的SHA1值是否匹配
- **智能文件识别** - 自动识别SHA1格式的制品文件
- **多线程并发** - Python版本支持可配置的并发线程数
- **时间范围过滤** - 支持按文件修改时间范围进行过滤
- **详细报告** - 生成完整的验证报告

## 使用方法

### Python版本（推荐）
```bash
# 基本使用
python3 validator.py /opt/jfrog/artifactory/var/data/artifactory/filestore

# 指定并发线程数
python3 validator.py /path/to/filestore --threads 8

# 指定时间范围
python3 validator.py /path/to/filestore \
  --start-time "2024-01-01 00:00" \
  --end-time "2024-01-31 23:59"
```

### Shell版本
```bash
# 基本使用
bash checksum.sh /opt/jfrog/artifactory/var/data/artifactory/filestore

# 指定输出文件
bash checksum.sh /path/to/filestore > validation_report.txt
```

## 命令行参数

| 参数 | Python版本 | Shell版本 | 说明 |
|------|------------|-----------|------|
| `base_dir` | ✅ | ✅ | Artifactory filestore基础目录路径 |
| `--threads, -t` | ✅ | ❌ | 并发线程数（默认4） |
| `--start-time` | ✅ | ❌ | 开始时间过滤 |
| `--end-time` | ✅ | ❌ | 结束时间过滤 |
| `--verbose, -v` | ✅ | ❌ | 详细输出模式 |

## 输出示例

```
2024-08-11 15:45:23 - INFO - 正在查找制品文件...
2024-08-11 15:45:25 - INFO - 找到 1250 个制品文件
2024-08-11 15:45:28 - INFO - 验证完成

============================================================
Binary SHA1 验证报告
============================================================
总文件数: 1250
验证通过: 1248
验证失败: 2
```

## 性能对比

| 特性 | Shell版本 | Python版本 | 改进 |
|------|-----------|------------|------|
| **执行效率** | 基础 | 快3-5倍 | 🚀 显著提升 |
| **并发控制** | 基础FIFO | ThreadPoolExecutor | 🔧 更灵活 |
| **跨平台** | Linux | 全平台 | 🌍 更通用 |
| **维护性** | 困难 | 简单 | 🛠️ 更易维护 |

## 环境要求

- **Python版本**: Python 3.7+，无需额外依赖
- **Shell版本**: Linux/macOS，bash环境

## 注意事项

- 需要读取filestore目录的权限
- 建议在本地执行，避免网络存储性能影响
- Python版本线程数过多可能影响系统性能

## 项目结构

```
binary-sha1-validator/
├── validator.py          # Python主程序
├── checksum.sh           # Shell脚本
├── requirements.txt      # Python依赖（可选）
└── README.md            # 项目文档
``` 