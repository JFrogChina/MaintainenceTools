# License Decomposer

JFrog许可证分解工具，用于分析和处理软件许可证信息。

## ✨ 功能特性

- 🖥️ 图形化用户界面（PyQt6）
- 📚 许可证历史管理
- 🎨 现代化图标和界面
- 📦 支持DMG打包分发

## 🚀 快速开始



### 构建应用程序
```bash
# 构建.app包和DMG文件
python3 build.py --dmg
```

### 开发环境运行
```bash
# 安装依赖
pip3 install -r requirements.txt

# 运行应用程序
python3 src/main.py
```

### 运行构建后的应用
```bash
# 直接运行.app包
"output/dist/License Splitter.app/Contents/MacOS/License Splitter"

# 或双击DMG文件安装后运行
open "output/License Splitter v1.0.dmg"
```

## 📁 项目结构

```
license-decomposer/
├── src/                    # 源代码
├── icons/                  # 图标资源
├── build.py               # 构建脚本
├── requirements.txt       # 依赖列表
└── output/                # 构建输出
```

## 📋 系统要求

- macOS 10.15+
- Python 3.8+
- PyQt6
- cryptography

## 🔧 构建说明

构建过程会自动：
1. 创建Python虚拟环境
2. 安装项目依赖
3. 使用py2app打包应用
4. 生成DMG安装包

## 📝 许可证
