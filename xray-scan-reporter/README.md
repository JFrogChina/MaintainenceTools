# Scan Results Report

单独制品的 GUI、RestAPI 扫描结果批量汇总及对比。

## 功能

- 扫描结果汇总
- 批量对比分析
- 支持GUI和API两种方式

## 使用方法

```sh
$ cat file.list
j-maven-remote-cache/com/fasterxml/jackson/core/jackson-databind/2.4.1/jackson-databind-2.4.1.jar CVE-2022-42004 true
$ python3 report.py -f file.list --base_url=http://localhost:8082 --username=xx --password=xx
``` 