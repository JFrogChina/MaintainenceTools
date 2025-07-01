# Bundle2Logs

自动解包、归档和整理 JFrog Xray/Artifactory 多节点日志的实用工具。

## 项目简介

Bundle2Logs 能够自动递归解压多层嵌套的 JFrog 支持包（zip），并根据节点唯一标识将所有日志文件归档到对应目录，便于后续分析和处理。支持 `.log` 和 `.gz` 日志，自动解压缩，避免日志重名覆盖。

## 主要特性

- 支持多层嵌套 zip 包自动解包
- 按节点唯一标识归档日志，结构清晰
- 支持 `.log` 和 `.gz` 日志自动解压
- 兼容 Xray、Artifactory 等多种 bundle
- 操作简单，一键归档

## 使用方法

1. 将所有待处理的 zip 包放在同一目录下。
2. 运行脚本：

   ```bash
   python3 unzip_bundle_logs.py
   ```

3. 日志会自动整理到 `./xray/` 和 `./artifactory/` 目录下，每个节点一个子目录。

## 目录结构示例
```
xray/
├── node1/
│ ├── xray-analysis-service.log
│ ├── xray-server-service.log
│ └── ...
└── node2/
├── xray-analysis-service.log
└── ...
artifactory/
└── ...
```
## 适用场景

- JFrog/Xray/Artifactory 日志归档与分析
- 多节点日志自动整理

---
