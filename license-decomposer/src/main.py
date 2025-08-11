#!/usr/bin/env python3
"""
License Splitter - 主启动脚本
使用相对导入，避免模块路径问题
"""

import sys
import os

def main():
    """主启动函数"""
    print("🚀 启动 License Splitter...")
    print("📄 Split a License Bucket")
    
    try:
        # 导入PyQt6
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        
        # 创建应用实例
        app = QApplication(sys.argv)
        
        # 设置应用信息
        app.setApplicationName("License Splitter")
        app.setApplicationDisplayName("License Splitter")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("JFrog License Tools")
        app.setOrganizationDomain("jfrog.com")
        
        # 设置应用样式
        app.setStyle('Fusion')
        
        # 应用全局样式表
        app.setStyleSheet("""
            QMainWindow {
                background-color: #FFFFFF;
            }
            QWidget {
                background-color: transparent;
            }
            QGroupBox {
                background-color: transparent;
            }
            QScrollArea {
                background-color: transparent;
                border: none;
            }
        """)
        
        # 设置应用图标
        try:
            from icon_manager import IconManager
            icon_manager = IconManager()
            app_icon = icon_manager.get_app_icon()
            if not app_icon.isNull():
                app.setWindowIcon(app_icon)
                print("✅ JFrog图标加载成功")
            else:
                print("⚠️ 使用默认图标")
        except Exception as e:
            print(f"⚠️ 图标加载失败: {e}")
        
        # 创建主窗口
        from gui_app_pyqt import LicenseDecomposerGUI
        window = LicenseDecomposerGUI()
        
        # 确保窗口样式正确
        window.setStyleSheet("""
            QMainWindow {
                background-color: #FFFFFF;
            }
        """)
        
        # 显示窗口
        window.show()
        
        print("✅ License Splitter 启动成功")
        
        # 运行应用
        sys.exit(app.exec())
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("请确保安装了PyQt6: pip install PyQt6")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 