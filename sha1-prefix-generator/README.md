# generate_file_with_checksum

> 生成一个文件，使其内容以指定的 2 位十六进制前缀开头，并且文件内容的 SHA-1 校验和（hex）也以相同的前缀开头。

## 目录结构

. 
  ├── generate_file.py # 主脚本 
  └── README.md # 本说明文件

## 特性

- **前缀校验**：仅接受长度为 2 的十六进制字符（0–9, a–f）。  
- **前缀匹配**：通过穷举后缀，使文件内容的 SHA-1 校验和真正以指定前缀开头。  
- **易于使用**：提供清晰的命令行接口和帮助信息。

## 环境要求

- Python 3.6 及以上

## 安装

1. 克隆仓库：
   ```bash
   git clone https://github.com/你的用户名/你的仓库名.git
   cd 你的仓库名
   ```
2. （可选）创建并激活虚拟环境：
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```
## 用法
```
python3 generate_file.py <PREFIX>
```
> \<PREFIX\>：2 位十六进制字符，用作内容和校验和的前缀（例如 0f、a1）。


## 示例
```
$ python3 generate_file.py a1
✔ 生成文件：file_with_a1.txt
✔ SHA-1 checksum：a1f3b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2
```

# 参数校验
如果未传入或传入参数格式不正确，程序会输出错误并退出：
```
$ python3 generate_file.py zz
参数错误：参数 prefix 必须是 2 个十六进制字符（0-9, a-f）。
```







