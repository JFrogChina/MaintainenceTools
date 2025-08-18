# JFrog Support Bundle 日志提取工具

## 功能描述

从JFrog Support Bundle中提取日志文件，支持多层zip解压，保留原始时间戳和权限。

## 使用方法

```bash
python3 bundle2logs.py
```

## 输出结构

- **Xray Bundle**: `./xray/` 目录
- **Artifactory Bundle**: `./artifactory/` 目录
- 每个节点创建独立子目录
- 保留 `service_manifest.json`

## 目录命名逻辑

### Bundle类型识别
- 读取 `service_manifest.json` 中的 `service_type` 字段
- `jfxr` → `./xray/` 目录
- `jfrt` → `./artifactory/` 目录

### 节点目录命名
- 从 `service_manifest.json` 的 `microservices` 部分提取节点名
- 例如：`artifactory-0`, `xray-0`
- 每个节点创建独立子目录，所有服务日志合并存放

### 文件组织方式
```
./artifactory/
├── service_manifest.json
├── artifactory-0/           # 节点目录
│   ├── artifactory-access.log
│   ├── artifactory-service.log
│   └── access-audit.log
└── artifactory-1/           # 另一个节点
    ├── artifactory-request.log
    └── frontend-metrics.log
```

## 特性

- 自动识别Bundle类型
- 并行处理提升速度
- 保留文件时间戳和权限
