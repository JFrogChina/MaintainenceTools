# Artifactory Repository Indexer

## 概述

该项目是一个Python脚本，用于对JFrog Xray的 **Indexed Resources** 的数据进行解释。
支持并发API调用，结果可以保存为CSV、JSON或表格格式。

## 具体功能

### 核心功能模块

1. **仓库索引扫描** - 扫描Artifactory仓库中的制品索引状态
2. **扫描状态分析** - 分析每个制品的扫描状态（scanned、failed、not scanned等）
3. **并发API调用** - 支持多线程并发处理，提高扫描效率
4. **包类型支持检查** - 根据配置文件检查制品是否被Xray支持
5. **强制重新索引** - 可选择强制重新索引制品
6. **多格式输出** - 支持table、CSV、JSON三种输出格式

### 使用场景

- 运维人员检查仓库扫描状态
- 识别扫描失败的制品
- 批量分析仓库健康状态
- 生成扫描状态报告
- 强制重新索引相关制品

## 功能演示

### 对 index 数据的进度进行展开

问题展示：

<div style="text-align: center;">
    <img src="https://github.com/JFrogChina/MaintainenceTools/blob/main/artifactory-repo-index/resource/images/indexresource01.jpg?raw=true" alt="图一" />
</div>
![图一](./resource/images/indexresource01.jpg)

### 扫描结果解答

<div style="text-align: center;">
    <img src="https://github.com/JFrogChina/MaintainenceTools/blob/main/artifactory-repo-index/resource/images/indexresource02.jpg?raw=true" alt="图二" />
</div>

## 相关数值对应的定义和澄清

### 扫描状态
[官方说明](https://jfrog.com/help/r/xray-rest-apis/scan-status)中,有以下几种状态：
```shell
{
"status": "failed"/"not supported"/"in progress"/"not scanned"/"scanned"
}
```

> **注意**: 在Xray一些版本中可能存在其他的状态，如scan failed、或者接口返回500报错等情况。

**对几种状态的通俗解释:**
```json
"not supported": 此仓库不支持此制品,比如在nuget仓库中上传的dll文件;
"not scanned": 未扫描,通常出现在制品刚上传的阶段或扫描结果已经过期的阶段（默认保留90天）;
"in progress": 扫描过程中,如果长时间保持这个状态,需要具体排查原因;
"scanned": 扫描成功;
"failed/scan failed": 扫描失败,需要具体分析其原因;
```

### 图一说明

- **UI index 结果为 64/65**
- **65** 为Xray识别的应扫描的文件数量
- **64** 为减去扫描结果状态为 `not scanned | scan failed | not supported` 之后的制品数量

### 图二说明
```shell
[Repo ] - [xx-local] - Potential files: 65, Scan Status Counts: Counter({'scanned': 64, 'scan failed': 1})
```
- **xx-local**: 为仓库名
- **Potential files: 65** 表示共计有65个文件应该被扫描
- **scanned: 64** 表示有64个制品的扫描结果为此状态
- **scan failed: 1** 表示有1个制品的扫描结果为此状态

## 安装

### 环境准备

1. **克隆项目到本地**
    ```sh
    git clone https://github.com/jfrogchina/MaintainenceTools.git
    ```

2. **进入项目目录**
    ```sh
    cd MaintainenceTools/artifactory-repo-index
    ```

3. **准备Python3环境及依赖包**
    ```sh
    python3 -m venv repoindex
    source repoindex/bin/activate
    python3 -m pip install argparse requests tqdm wcwidth tabulate
    ```

## 项目结构

- **`indexer.py`** - 主脚本文件
- **`Xray_pkg_support.json`** - 文件类型的支持规则

## 使用方法

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `reponame` | 仓库的名称 | **必需** |
| `--base_url` | Artifactory实例的基本URL | `http://localhost:8082` |
| `--pkg_support` | 包支持规则文件 | `Xray_pkg_support.json` |
| `--username` | Artifactory用户名 | `admin` |
| `--password` | Artifactory密码 | `password` |
| `--scan_result_save` | 保存扫描结果的文件 | `scan_details.file` |
| `--print_lines` | 在控制台打印的行数 | `10` |
| `--format` | 数据格式: `table` \| `json` \| `csv` | `table` |
| `--clear_log` | 是否清空日志 | `True` |
| `--threads` | 并发API调用的线程数 | `50` |

### 运行示例

1. 运行脚本：
    ```python
    python3 indexer.py my-repo --base_url=https://myjfrogurl.com --username myuser --password mypass --scan_result_save results.csv --format csv
    ```

2. **参数说明**
    - **`my-repo`** - 要扫描的仓库名称
    - **`--base_url`** - JFrog 平台地址
    - **`--username`** - JFrog 用户名
    - **`--password`** - JFrog 密码
    - **`--scan_result_save`** - 保存扫描结果的文件，格式为CSV
    - **`--format`** - 结果格式，支持 `table`、`json` 和 `csv`

### 日志记录

日志记录保存在`scan_details.file`（默认）文件中,可以根据需要使用 --scan_result_save 参数更改文件名。


## 特殊情况
极少数情况下,可能会遇到脚本返回的数字与UI页面上展示的不一样的问题,通常可能是由于特殊包或垃圾数据导致的,具体情况需要具体分析;
再次声明,此脚本主要用于找到'失败的那个文件',其他的需要具体排查和解决。

## 贡献

欢迎贡献！请 fork 本仓库并提交 PR。

## 许可证


