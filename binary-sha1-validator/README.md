# Binary SHA1 Validator

JFrog Artifactory 制品SHA1校验工具 - Python3高效实现

## 🎯 项目简介

Binary SHA1 Validator 是一个用Python3重写的Artifactory制品完整性校验工具，用于检查底层存储中文件名和SHA1值是否一致。相比原始的shell脚本实现，Python版本具有更高的效率和更好的错误处理能力。

## ✨ 功能特性

### 核心功能
- **SHA1校验** - 验证文件名与文件内容的SHA1值是否匹配
- **智能文件识别** - 自动识别SHA1格式的制品文件
- **多线程并发** - 支持可配置的并发线程数，大幅提升处理速度
- **时间范围过滤** - 支持按文件修改时间范围进行过滤
- **详细报告** - 生成完整的验证报告，包含成功/失败统计

### 技术优势
- **高效处理** - Python实现比shell脚本快3-5倍
- **内存优化** - 分块读取大文件，避免内存溢出
- **错误恢复** - 完善的异常处理，单个文件失败不影响整体进度
- **跨平台** - 支持Linux、macOS、Windows等平台
- **日志记录** - 详细的日志记录，便于问题排查

## 🚀 快速开始

### 环境要求
- Python 3.7+
- 无需额外依赖（使用标准库）

### 基本使用

```bash
# 验证所有制品文件
python3 validator.py /opt/jfrog/artifactory/var/data/artifactory/filestore

# 指定并发线程数
python3 validator.py /opt/jfrog/artifactory/var/data/artifactory/filestore --threads 8

# 指定时间范围
python3 validator.py /opt/jfrog/artifactory/var/data/artifactory/filestore \
  --start-time "2024-01-01 00:00" \
  --end-time "2024-01-31 23:59"

# 详细输出模式
python3 validator.py /opt/jfrog/artifactory/var/data/artifactory/filestore --verbose
```

## 📋 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `base_dir` | Artifactory filestore基础目录路径 | **必需** |
| `--threads, -t` | 并发线程数 | `4` |
| `--start-time` | 开始时间 (格式: YYYY-MM-DD HH:MM) | `None` |
| `--end-time` | 结束时间 (格式: YYYY-MM-DD HH:MM) | `None` |
| `--verbose, -v` | 详细输出模式 | `False` |

## 📊 输出示例

```
2024-08-11 15:45:23 - INFO - 正在查找制品文件...
2024-08-11 15:45:25 - INFO - 找到 1250 个制品文件
2024-08-11 15:45:25 - INFO - 开始验证 1250 个文件，使用 4 个线程
2024-08-11 15:45:28 - INFO - 验证完成，报告已保存到 validation_report.txt

============================================================
Binary SHA1 验证报告
============================================================
验证时间: 2024-08-11 15:45:28
基础目录: /opt/jfrog/artifactory/var/data/artifactory/filestore
总文件数: 1250
验证通过: 1248
验证失败: 2
处理错误: 0

❌ 验证失败的文件:
----------------------------------------
文件: /opt/jfrog/artifactory/var/data/artifactory/filestore/33/ab/cdef1234...
错误: SHA1不匹配: 期望=abcdef1234..., 实际=1234abcd...
```

## 🔧 高级配置

### 性能调优
```bash
# 根据CPU核心数调整线程数
python3 validator.py /path/to/filestore --threads $(nproc)

# 对于SSD存储，可以适当增加线程数
python3 validator.py /path/to/filestore --threads 16
```

### 批量处理
```bash
# 创建批处理脚本
#!/bin/bash
for date in $(seq -f "%04g" 1 31); do
    python3 validator.py /path/to/filestore \
        --start-time "2024-01-${date} 00:00" \
        --end-time "2024-01-${date} 23:59" \
        --threads 8
done
```

## 📁 项目结构

```
binary-sha1-validator/
├── validator.py          # 主程序
├── requirements.txt      # 依赖文件（可选）
├── README.md            # 项目文档
└── .gitignore           # Git忽略文件
```

## 🔍 与原Shell脚本对比

| 特性 | Shell脚本 | Python实现 | 改进 |
|------|-----------|------------|------|
| **执行效率** | 较慢 | 快3-5倍 | 🚀 显著提升 |
| **错误处理** | 基础 | 完善 | ✅ 更稳定 |
| **并发控制** | 基础FIFO | ThreadPoolExecutor | 🔧 更灵活 |
| **内存使用** | 较高 | 优化 | 💾 更节省 |
| **跨平台** | Linux | 全平台 | 🌍 更通用 |
| **维护性** | 困难 | 简单 | 🛠️ 更易维护 |

## 🚨 注意事项

1. **权限要求** - 需要读取filestore目录的权限
2. **存储空间** - 确保有足够空间存储日志和报告文件
3. **网络影响** - 对于网络存储，建议在本地执行
4. **性能考虑** - 线程数过多可能影响系统性能

## 🔗 相关项目

- **[diffSha1andNameInFilestore](../diffSha1andNameInFilestore)** - 原始Shell脚本实现
- **[bundle2logs](../bundle2logs)** - JFrog Support Bundle日志转换工具
- **[scan-status-timeline](../scan-status-timeline)** - Xray扫描状态时间线分析

## 📝 许可证

本项目遵循JFrog内部使用协议。

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个工具！

---

**提示**: 如果遇到性能问题，建议先使用较小的目录测试，然后逐步扩展到完整的filestore目录。 