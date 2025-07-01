# MaintainenceTools 项目说明

## 项目简介

MaintainenceTools 是一套面向 JFrog Artifactory/Xray 日常运维、日志分析、批量处理等场景的实用工具集合。涵盖索引追踪、日志提取、镜像列表、校验和比对、sha1前缀生成等多种常用功能，助力一线运维、支持和开发团队高效定位和解决问题。

---

## 目录结构与工具功能（及检索关键字）

- **artifactory-repo-index/**
  - `indexer.py`：Artifactory 仓库索引日志分析与可视化工具。
    - 关键字：index all、indexed resources、索引进度、未100%、Force Reindex 整个仓库
- **bundle2logs/**
  - `bundle2logs.py`：提取和处理 Artifactory/Xray 支持包中的日志。
    - 关键字：support bundle、日志提取
- **diffSha1andNameInFilestore/**
  - `checksum.sh`：对 filestore 目录下的文件名与 sha1 校验和进行批量比对。
    - 关键字：binarystore、filestore、sha1、校验和、checksum
- **dockerImageList/**
  - `dockerImageList.py`：批量获取 Artifactory 仓库中的 Docker 镜像列表。
    - 关键字：docker、镜像列表、仓库
- **repo-jas-configuration/**
  - `repo-jas-configuration-check.py`：JAS（JFrog Advanced Security）相关仓库配置检查脚本。
    - 关键字：JAS、仓库配置、设置高级索引
- **scan-results-report/**
  - `report.py`：单独制品的 GUI、RestAPI 扫描结果批量汇总及对比
    - 关键字：xray、scan result、扫描结果不同、CVE、JFrog CLI、Force Reindex status、单个制品
- **scan-status-timeline/**
  - `xray_scan_timeline_traceid.py`：根据 trace id/artifact，分析 Xray 扫描全流程各阶段耗时与状态，支持 debug 日志输出。
    - 关键字：trace id、timeline、scan status、阶段耗时
- **sha1-prefix-generator/**
  - `generate_file.py`：生成特定 checksum 值 的文件；支持两位数的入参
    - 关键字：sha1、生成特定文件、checksum
- **xray-indexer-request/**
  - `xray-indexer-request-trace.py`：批量分析 Xray 索引请求日志，支持多类型事件分类、分组、去重和统计。
    - 关键字：xray、index request、事件分类、日志去重

---

## 适用场景与注意事项
- 适用于 JFrog Artifactory/Xray 日常巡检、问题定位、批量数据处理、日志分析等场景。
- 日志分析类工具需指定正确的日志主目录，部分工具需 artifact/trace id 关键词。
- 建议在 Python 3.6+ 环境下运行，部分脚本依赖第三方库（如 pandas、requests）。
- 处理大批量日志时，建议先过滤无关日志文件，提升效率。

---

## 贡献与维护
- 欢迎团队成员补充新工具、优化现有脚本。
- 建议每个工具目录下附带 README 或注释说明用法。
- 如有问题或建议，请联系项目维护者。
