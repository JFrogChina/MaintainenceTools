#!/usr/bin/env python3
"""
简化的构建脚本
支持用户描述的构建流程：
1. 创建venv
2. source venv
3. pip3 install -r requirements.txt
4. python3 build.py --dmg (自动跳过test)
"""

import os
import sys
import shutil
import subprocess
import argparse
import platform

# setuptools 导入（延迟到需要时）
def get_setuptools():
    try:
        from setuptools import setup
        return setup
    except ImportError:
        print("❌ 错误：setuptools 未安装")
        print("请运行：pip install setuptools")
        sys.exit(1)

# 项目路径配置
PROJECT_ROOT = os.path.dirname(__file__)
BUILD_DIR = os.path.join(PROJECT_ROOT, 'build')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output')
DIST_DIR = os.path.join(OUTPUT_DIR, 'dist')
VENV_DIR = os.path.join(OUTPUT_DIR, 'venv')

# 确保输出目录存在
os.makedirs(DIST_DIR, exist_ok=True)

# py2app 配置
APP = ['start_license_splitter.py']
DATA_FILES = [
    ('', ['jfrog_icon.icns']),
]
OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'jfrog_icon.icns',
    'plist': {
        'CFBundleName': 'License Splitter',
        'CFBundleDisplayName': 'License Splitter',
        'CFBundleIdentifier': 'com.jfrog.license-splitter',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.15',
        'LSApplicationCategoryType': 'public.app-category.developer-tools',
        'NSAppTransportSecurity': {
            'NSAllowsArbitraryLoads': True
        }
    },
    'packages': ['PyQt6', 'cryptography'],
    'includes': ['gui_app_pyqt', 'history_manager', 'history_widgets', 'icon_manager', 'license_decomposer', 'encodings', 'codecs', 'copyreg', 'encodings.utf_8', 'encodings.ascii', 'encodings.latin_1'],
    'excludes': ['PyQt6.Qt3D', 'PyQt6.QtQuick3D', 'PyQt6.QtWebEngine', 'PyQt6.QtWebView'],
    'resources': [],
    'optimize': 0,
    'strip': False,
    'semi_standalone': False,  # 改为False，使用完整的Python标准库
    'alias': False,
    'site_packages': True,
}

def clean_build():
    """清理旧的构建文件"""
    print("🧹 清理旧的构建文件...")
    
    # 清理项目根目录下的临时文件
    for item in ['build', 'dist', 'temp_build', '*.pyc', '__pycache__']:
        if os.path.exists(item):
            if os.path.isdir(item):
                # shutil.rmtree(item)  # 注释掉删除
                pass
            else:
                # os.remove(item)  # 注释掉删除
                pass
    
    # 清理 build 目录中的临时文件
    build_subdir = os.path.join(BUILD_DIR, 'build')
    dist_subdir = os.path.join(BUILD_DIR, 'dist')
    
    for dir_path in [build_subdir, dist_subdir]:
        if os.path.exists(dir_path):
            # shutil.rmtree(dir_path)  # 注释掉删除
            pass
    
    # 清理 output/dist 目录
    if os.path.exists(DIST_DIR):
        # shutil.rmtree(DIST_DIR)  # 注释掉删除
        # os.makedirs(DIST_DIR, exist_ok=True)  # 注释掉重新创建
        pass
    
    # 清理临时文件
    for pattern in ['*.app', '*.dmg']:
        for file in os.listdir(PROJECT_ROOT):
            if file.endswith('.app') or file.endswith('.dmg'):
                file_path = os.path.join(PROJECT_ROOT, file)
                if os.path.isdir(file_path):
                    # shutil.rmtree(file_path)  # 注释掉删除
                    pass
                else:
                    # os.remove(file_path)  # 注释掉删除
                    pass

def create_venv():
    """创建虚拟环境"""
    if not os.path.exists(VENV_DIR):
        print("🔧 创建虚拟环境...")
        subprocess.run([sys.executable, '-m', 'venv', VENV_DIR], check=True)
        print("✅ 虚拟环境创建成功！")
    else:
        print("✅ 虚拟环境已存在")
    
    return VENV_DIR

def install_dependencies(venv_dir):
    """安装项目依赖"""
    print("📦 安装项目依赖...")
    
    # 激活虚拟环境并安装依赖
    pip_path = os.path.join(venv_dir, 'bin', 'pip')
    requirements_file = os.path.join(PROJECT_ROOT, 'requirements.txt')
    
    if os.path.exists(requirements_file):
        subprocess.run([pip_path, 'install', '-r', requirements_file], check=True)
        print("✅ 依赖安装成功！")
    else:
        print("⚠️ 未找到 requirements.txt，跳过依赖安装")
    
    # 安装 py2app
    subprocess.run([pip_path, 'install', 'py2app'], check=True)
    print("✅ py2app 安装成功！")

def build_app():
    """构建应用程序包"""
    print("🔨 构建应用程序包...")
    
    # 创建临时构建目录
    temp_build_dir = "temp_build"
    if os.path.exists(temp_build_dir):
        shutil.rmtree(temp_build_dir)
    os.makedirs(temp_build_dir)
    
    # 复制必要的文件到临时目录
    shutil.copy2("jfrog_icon.icns", temp_build_dir)
    shutil.copy2("start_license_splitter.py", temp_build_dir)
    
    # 创建setup.py文件
    setup_content = f'''from setuptools import setup

APP = ['start_license_splitter.py']
OPTIONS = {{
    'argv_emulation': False,
    'iconfile': 'jfrog_icon.icns',
    'plist': {{
        'CFBundleName': 'License Splitter',
        'CFBundleDisplayName': 'License Splitter',
        'CFBundleIdentifier': 'com.jfrog.license-splitter',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.15',
        'LSApplicationCategoryType': 'public.app-category.developer-tools',
        'NSAppTransportSecurity': {{
            'NSAllowsArbitraryLoads': True
        }}
    }},
    'packages': ['PyQt6', 'cryptography'],
    'includes': ['gui_app_pyqt', 'history_manager', 'history_widgets', 'icon_manager', 'license_decomposer', 'encodings', 'codecs', 'copyreg', 'encodings.utf_8', 'encodings.ascii', 'encodings.latin_1'],
    'excludes': ['PyQt6.Qt3D', 'PyQt6.QtQuick3D', 'PyQt6.QtWebEngine', 'PyQt6.QtWebView'],
    'resources': [],
    'optimize': 0,
    'strip': False,
    'semi_standalone': False,
    'alias': False,
    'site_packages': True,
}}

setup(
    app=APP,
    options={{'py2app': OPTIONS}},
    setup_requires=['py2app'],
)
'''
    
    with open(os.path.join(temp_build_dir, "setup.py"), "w") as f:
        f.write(setup_content)
    
    # 设置环境变量
    env = os.environ.copy()
    env['PYTHONPATH'] = os.getcwd()  # 添加项目根目录到Python路径
    
    try:
        # 使用虚拟环境的Python运行py2app
        venv_python = os.path.join(os.getcwd(), "output", "venv", "bin", "python")
        result = subprocess.run([venv_python, "setup.py", "py2app"], 
                              cwd=temp_build_dir,
                              env=env,
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ 构建失败：{result.stderr}")
            return False
        
        print("✅ 应用程序构建成功！")
        
        # 复制构建的应用程序到输出目录
        dist_dir = os.path.join("output", "dist")
        if not os.path.exists(dist_dir):
            os.makedirs(dist_dir)
        
        source_app = os.path.join(temp_build_dir, "dist", "License Splitter.app")
        target_app = os.path.join(dist_dir, "License Splitter.app")
        
        if os.path.exists(target_app):
            shutil.rmtree(target_app)
        
        shutil.copytree(source_app, target_app)
        
        print("✅ 成功复制：License Splitter.app")
        return True
        
    except Exception as e:
        print(f"❌ 构建过程中出错：{e}")
        return False

def copy_app_to_output():
    """复制应用程序到输出目录"""
    print("📦 复制应用程序包到 output 目录...")
    
    # 查找构建的应用程序（在临时目录中）
    temp_dist_dir = os.path.join(PROJECT_ROOT, 'temp_build', 'dist')
    app_name = "License Splitter.app"
    source_app = os.path.join(temp_dist_dir, app_name)
    target_app = os.path.join(DIST_DIR, app_name)
    
    if os.path.exists(source_app):
        # 复制应用程序
        try:
            if os.path.exists(target_app):
                # shutil.rmtree(target_app)  # 注释掉删除
                print(f"⚠️ 目标应用程序已存在，跳过复制")
                return True
            
            # 使用ignore参数跳过可能不存在的文件
            shutil.copytree(source_app, target_app, ignore=shutil.ignore_patterns('*.pyc', '__pycache__', 'config-*'))
            print(f"✅ 应用程序包复制成功！")
            print(f"📁 输出位置：{target_app}")
            
            # 显示文件信息
            print("📊 应用程序包信息：")
            subprocess.run(['ls', '-la', target_app])
            
            return True
        except (OSError, IOError) as e:
            print(f"❌ 错误：复制应用程序包时出错：{e}")
            return False
    else:
        print(f"❌ 错误：找不到应用程序包 {source_app}")
        return False

def create_dmg():
    """创建 DMG 文件"""
    print("📦 创建 DMG 文件...")
    
    # 检查是否为 macOS
    if platform.system() != 'Darwin':
        print("❌ 错误：DMG 创建仅在 macOS 上支持")
        return False
    
    # 检查应用程序是否存在
    app_path = os.path.join(DIST_DIR, "License Splitter.app")
    if not os.path.exists(app_path):
        print("❌ 错误：应用程序包不存在，无法创建 DMG")
        return False
    
    # 创建临时目录用于 DMG 构建
    dmg_temp_dir = os.path.join(OUTPUT_DIR, 'dmg_temp')
    if os.path.exists(dmg_temp_dir):
        # shutil.rmtree(dmg_temp_dir)  # 注释掉删除
        pass
    os.makedirs(dmg_temp_dir, exist_ok=True)
    
    try:
        # 复制应用程序到临时目录
        shutil.copytree(app_path, os.path.join(dmg_temp_dir, "License Splitter.app"))
        
        # 创建 Applications 快捷方式
        os.symlink('/Applications', os.path.join(dmg_temp_dir, 'Applications'))
        
        # 创建 DMG 文件
        dmg_name = "License_Splitter_v1.0.dmg"
        dmg_path = os.path.join(PROJECT_ROOT, dmg_name)
        
        subprocess.run([
            'hdiutil', 'create', 
            '-volname', 'License Splitter', 
            '-srcfolder', dmg_temp_dir, 
            '-ov', '-format', 'UDZO', 
            dmg_path
        ], check=True)
        
        # 检查 DMG 是否创建成功
        if os.path.exists(dmg_path):
            print("✅ DMG 文件创建成功！")
            print(f"📁 DMG 位置：{dmg_path}")
            print("📊 DMG 文件信息：")
            subprocess.run(['ls', '-lh', dmg_path])
            
            # 移动 DMG 文件到 output 目录
            output_dmg_path = os.path.join(OUTPUT_DIR, dmg_name)
            shutil.move(dmg_path, output_dmg_path)
            print(f"📁 DMG 已移动到：{output_dmg_path}")
            return True
        else:
            print("❌ DMG 文件创建失败")
            return False
            
    except Exception as e:
        print(f"❌ DMG 创建失败：{e}")
        return False
    finally:
        # 清理临时目录
        if os.path.exists(dmg_temp_dir):
            # shutil.rmtree(dmg_temp_dir)  # 注释掉删除
            pass

def cleanup_build():
    """清理构建文件"""
    print("🧹 清理构建文件...")
    
    # 清理 build 目录中的临时文件
    build_dir = os.path.join(BUILD_DIR, 'build')
    dist_dir_build = os.path.join(BUILD_DIR, 'dist')
    
    if os.path.exists(build_dir):
        # shutil.rmtree(build_dir)  # 注释掉删除
        pass
    if os.path.exists(dist_dir_build):
        # shutil.rmtree(dist_dir_build)  # 注释掉删除
        pass
    
    # 清理临时构建目录
    temp_build_dir = os.path.join(PROJECT_ROOT, 'temp_build')
    if os.path.exists(temp_build_dir):
        # shutil.rmtree(temp_build_dir)  # 注释掉删除
        pass
    
    print("✅ 清理完成！")

def main():
    """主构建流程"""
    parser = argparse.ArgumentParser(description='License Splitter 构建脚本')
    parser.add_argument('--dmg', action='store_true', help='构建 .app 包并创建 DMG 文件')
    parser.add_argument('--no-cleanup', action='store_true', help='跳过构建文件清理')
    
    args = parser.parse_args()
    
    print("🔧 使用 py2app 创建 macOS 应用程序包...")
    
    try:
        # 1. 清理旧文件
        clean_build()
        
        # 2. 创建虚拟环境
        venv_dir = create_venv()
        
        # 3. 安装依赖
        install_dependencies(venv_dir)
        
        # 4. 构建应用程序
        build_app()
        
        # 5. 复制到输出目录
        copy_app_to_output()
        
        # 6. 如果指定了 --dmg 参数，创建 DMG 文件
        if args.dmg:
            create_dmg()
        
        # 7. 清理构建文件（除非指定跳过）
        if not args.no_cleanup:
            cleanup_build()
        
        print("🎉 构建完成！")
        print(f"📁 应用程序包位置：{os.path.join(DIST_DIR, 'License Splitter.app')}")
        if args.dmg:
            print(f"📁 DMG 文件位置：{os.path.join(OUTPUT_DIR, 'License_Splitter_v1.0.dmg')}")
        
    except Exception as e:
        print(f"❌ 构建失败：{e}")
        sys.exit(1)

# 为 setuptools 提供配置
if 'py2app' in sys.argv:
    setup = get_setuptools()
    setup(
        app=APP,
        data_files=DATA_FILES,
        options={'py2app': OPTIONS},
        setup_requires=['py2app'],
    )

if __name__ == '__main__':
    main() 