# Artifactory 代理缓存检测工具


本工具用于批量检测 Hugging Face 等模型文件和数据集在 JFrog Artifactory 代理仓库中的缓存状态，支持单线程和并发检测，自动输出彩色结果并保存日志。

## 主要功能
- 检查模型文件和数据集在 Artifactory 代理中的缓存情况（CACHED/NOT CACHED/ERROR）
- 支持批量检测，自动并发（可配置）
- 检查结果彩色高亮（NOT CACHED 为紫色）
- 检查结果自动保存到 `head.log` 日志文件
- 支持超时控制、调试模式
- 输出美观，分组统计，进度清晰

## 使用方法

### 1. 准备清单文件
清单文件（如 `checklist.txt`），每行格式：
```
model,repo_id,revision
或
dataset,repo_id,revision
```
例如：
```
model,LiheYoung/depth_anything_vitl14,973948530e4e4f4afd6d1913f670d9f96071dcaa
model,Qwen/Qwen3-14B-FP8,b1929466a4961baa91177cad8896d3b057dea12b
dataset,black-forest-labs/kontext-bench,main
```

### 2. 运行脚本

#### 单线程检测（默认）
```bash
python check_on_remote_cache.py --models checklist.txt
```

#### 并发检测（如2进程）
```bash
python check_on_remote_cache.py --models checklist.txt --workers 2
```

#### 主要参数（已更新默认值）
- `--models`：清单文件路径（必需）
- `--workers`：并发进程数，默认1（单线程），大于1时并发
- `--file-workers`：每个模型/数据集内部文件并发数，默认10
- `--timeout`：每个模型/数据集检测最大超时（秒），默认15
- `--file-timeout`：每个文件 HEAD 检查超时（秒），默认5
- `--debug`：开启调试输出
- `--registry`：Artifactory 代理基础URL（如需自定义）

### 3. 输出示例
```
🔍 model: LiheYoung/depth_anything_vitl14@973948530e4e4f4afd6d1913f670d9f96071dcaa
------------------------------------------------------------
[LiheYoung/depth_anything_vitl14@973948530e4e4f4afd6d1913f670d9f96071dcaa] 共4个文件，将检测 Artifactory 代理缓存：
config.json                              | CACHED
README.md                                | CACHED
pytorch_model.bin                        | CACHED
.gitattributes                           | CACHED

统计: CACHED 4, NOT CACHED 0, ERROR 0
✅ model LiheYoung/depth_anything_vitl14@973948530e4e4f4afd6d1913f670d9f96071dcaa 处理完成 (3/8)
------
```

### 4. 日志说明
- 所有终端输出（含彩色高亮）会自动保存到 `head.log` 文件，便于后续查阅。

### 5. 注意事项
- 并发检测时建议合理设置 `--workers`，避免对 Artifactory 服务器造成过大压力。
- 如果模型文件未缓存，会触发 Artifactory 向外网拉取，可能导致响应变慢。
- 建议分批检测，监控服务器负载。

---

如有问题或需定制功能，请联系维护者。 