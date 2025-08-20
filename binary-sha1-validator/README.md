# Binary SHA1 Validator

JFrog Artifactory 制品SHA1校验工具

## 功能

验证 Artifactory 底层存储中文件名和SHA1值是否一致

## 使用方法

```sh
#定线程数和批次大小
python3 validator.py /opt/jfrog/artifactory/var/data/artifactory/filestore --resume --threads 8 --batch-size 20000

# 指定时间范围
python3 validator.py /path/to/filestore --start-time "2024-01-01 00:00" --end-time "2024-01-31 23:59"

# 生成测试数据 （正确值）
python3 generate_test_files.py /opt/jfrog/artifactory/var/data/artifactory/filestore/ --count 10000  --min-size 10 --max-size 100
# 生成测试数据 （错误值）
python3 generate_test_files.py /opt/jfrog/artifactory/var/data/artifactory/filestore/ --count 1  --min-size 10 --max-size 100 --false
```

## 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `base_dir` | filestore目录路径 | **必需** |
| `--threads` | 并发线程数 | `4` |
| `--batch-size` | 批次大小 | `10000` |
| `--start-time` | 开始时间 | 无 |
| `--end-time` | 结束时间 | 无 |
| `--verbose` | 详细输出 | 无 |

## 特性

- 流式处理，支持大量文件
- 断点记录，中断后可继续，自动进度保存
- 多线程并发验证

## 输出

```
✅ 批次 1 | 文件: 10000 | 通过: 10000 | 失败: 0 | 错误: 0
📊 总计: 10000 文件 | 通过: 10000 | 失败: 0 | 错误: 0
```

## 环境要求

Python 3.6+，标准库模块 