# HF Cache Validator

Hugging Face 模型和数据集缓存状态检查工具，用于验证 Artifactory 代理仓库的缓存完整性。

## 功能特性

- **缓存验证** - 检查模型/数据集文件在 Artifactory 代理中的缓存状态
- **批量处理** - 支持从文件批量检查多个仓库
- **并发检查** - 多进程和多线程并发处理，提升检查效率
- **实时输出** - 实时显示检查进度和结果
- **日志记录** - 自动保存检查日志到文件

## 使用方法

### 环境准备
```sh
# 设置 Hugging Face Token
export HF_TOKEN="your_token_here"
```

### 基本使用
```sh
# 检查单个模型(手动修改 #263 repo_id 和 #264 revision)
python3 check_on_remote_cache.py --registry https://demo.jfrogchina.com/artifactory/api/huggingfaceml/j-huggingfaceml-remote

# 并发模式
python3 check_on_remote_cache.py --file checklist.txt --workers 4 --registry https://demo.jfrogchina.com/artifactory/api/huggingfaceml/j-huggingfaceml-remote
```

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--file` | 模型/数据集列表文件路径 | `None` |
| `--timeout` | 每个模型检测超时时间（秒） | `15` |
| `--workers` | 并发进程数 | `1` |
| `--file-workers` | 每个模型内部文件并发数 | `10` |
| `--registry` | Artifactory 代理基础URL | `http://localhost:8082/artifactory/api/huggingfaceml/huggingfaceml-remote` |

## 输入文件格式

```txt
# 每行格式: model/dataset,repo_id,revision
model,LiheYoung/depth_anything_vitl14,973948530e4e4f4afd6d1913f670d9f96071dcaa
dataset,black-forest-labs/kontext-bench,main
```

## 输出示例

```
🔍 model: LiheYoung/depth_anything_vitl14@973948530e4e4f4afd6d1913f670d9f96071dcaa
------------------------------------------------------------
config.json                              | CACHED
pytorch_model.bin                        | CACHED
tokenizer.json                           | CACHED

统计: CACHED 4, NOT CACHED 0, ERROR 0
```


## 环境要求

- Python 3.6+
- `requests` 库
- Hugging Face Token 环境变量

## 注意事项

- 需要设置 `HF_TOKEN` 环境变量
- 确保 Artifactory 代理仓库可访问
- 大量文件检查时建议使用并发模式 