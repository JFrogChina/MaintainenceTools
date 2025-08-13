# Bundle2Logs

JFrog Support Bundle 日志提取工具，自动解析 bundle 文件并按节点分类组织日志。

## 功能特性

- **智能识别**: 基于 `service_manifest.json` 自动检测 Xray/Artifactory bundle
- **节点分类**: 按 manifest 中的节点信息自动创建目录结构
- **文件处理**: 自动解压 `.gz` 文件，保留时间戳和权限

## 使用方法

```bash
# 将 Support Bundle 文件放在当前目录
python3 bundle2logs.py
```

## 输出结构

```
xray/                           # Xray bundle 输出
├── service_manifest.json
└── jfrogxap02/
    ├── xray-analysis-*.log
    └── xray-indexer-*.log

artifactory/                    # Artifactory bundle 输出
├── service_manifest.json
└── sptwlvx00501.tw.fbl/
    ├── access-*.log
    └── artifactory-*.log
```

## 环境要求

- Python 3.6+
- 无需额外依赖

## 注意事项

- 确保 bundle 文件包含 `service_manifest.json`
- 支持任何命名格式的 bundle 文件 