#!/usr/bin/env python3
"""
图标管理器
处理应用图标的加载和设置
"""

import os
import sys
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import Qt

class IconManager:
    """图标管理器类"""
    
    def __init__(self):
        self.icons_dir = "icons"
        self.ensure_icons_dir()
    
    def ensure_icons_dir(self):
        """确保icons目录存在"""
        if not os.path.exists(self.icons_dir):
            os.makedirs(self.icons_dir)
    
    def get_app_icon(self):
        """获取应用主图标"""
        # 按优先级尝试不同的图标文件
        icon_files = [
            "jfrog_icon.png",
            "license_decomposer.png", 
            "app_icon.png",
            "icon.png"
        ]
        
        for icon_file in icon_files:
            icon_path = os.path.join(self.icons_dir, icon_file)
            if os.path.exists(icon_path):
                try:
                    icon = QIcon(icon_path)
                    if not icon.isNull():
                        print(f"✅ 使用图标: {icon_file}")
                        return icon
                except Exception as e:
                    print(f"⚠️ 加载图标失败 {icon_file}: {e}")
                    continue
        
        # 如果没有找到自定义图标，创建一个简单的默认图标
        return self.create_default_icon()
    
    def create_default_icon(self):
        """创建默认图标"""
        try:
            from PyQt6.QtGui import QPainter, QColor, QBrush, QPen
            
            # 创建一个简单的默认图标
            pixmap = QPixmap(64, 64)
            pixmap.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # 绘制简单的文档图标
            painter.setBrush(QBrush(QColor("#3498DB")))
            painter.setPen(QPen(QColor("#2980B9"), 2))
            painter.drawRoundedRect(10, 8, 44, 48, 6, 6)
            
            # 绘制文档内容线
            painter.setPen(QPen(QColor("#FFFFFF"), 2))
            for i in range(3):
                y = 20 + i * 8
                painter.drawLine(16, y, 48, y)
            
            painter.end()
            
            icon = QIcon(pixmap)
            print("🔧 使用默认生成的图标")
            return icon
            
        except Exception as e:
            print(f"❌ 创建默认图标失败: {e}")
            return QIcon()  # 返回空图标
    
    def get_status_icon(self):
        """获取状态栏图标"""
        status_files = [
            "jfrog_status.png",
            "status_icon_22.png",
            "status_icon_16.png"
        ]
        
        for icon_file in status_files:
            icon_path = os.path.join(self.icons_dir, icon_file)
            if os.path.exists(icon_path):
                try:
                    icon = QIcon(icon_path)
                    if not icon.isNull():
                        return icon
                except:
                    continue
        
        # 使用主图标作为状态图标
        return self.get_app_icon()
    
    def list_available_icons(self):
        """列出可用的图标文件"""
        try:
            icon_extensions = ['.png', '.jpg', '.jpeg', '.ico', '.svg']
            available_icons = []
            
            for filename in os.listdir(self.icons_dir):
                if any(filename.lower().endswith(ext) for ext in icon_extensions):
                    file_path = os.path.join(self.icons_dir, filename)
                    file_size = os.path.getsize(file_path)
                    available_icons.append((filename, file_size))
            
            if available_icons:
                print("📁 可用的图标文件:")
                for filename, size in available_icons:
                    print(f"  - {filename} ({size} bytes)")
            else:
                print("📁 icons目录中没有找到图标文件")
                
            return available_icons
            
        except Exception as e:
            print(f"❌ 列出图标文件失败: {e}")
            return []
    
    def save_jfrog_instructions(self):
        """保存JFrog图标使用说明"""
        instructions = """
# JFrog 图标使用说明

## 📥 如何添加JFrog图标:

1. 将JFrog图标保存为以下任一文件名:
   - `jfrog_icon.png` (推荐)
   - `license_decomposer.png`
   - `app_icon.png`

2. 将图标文件放入 `icons/` 目录

3. 重启应用即可看到新图标

## 📐 推荐的图标规格:
- 格式: PNG (推荐) 或 ICO
- 尺寸: 64x64 到 256x256 像素
- 背景: 透明背景最佳

## 🔄 图标优先级:
1. jfrog_icon.png (最高优先级)
2. license_decomposer.png
3. app_icon.png
4. icon.png
5. 自动生成的默认图标

## 💡 提示:
- macOS Dock图标最佳尺寸: 512x512 或 1024x1024
- Windows ICO文件支持多尺寸
- 状态栏图标推荐: 16x16 或 22x22
"""
        
        try:
            with open(os.path.join(self.icons_dir, "README.md"), "w", encoding="utf-8") as f:
                f.write(instructions)
            print("📝 图标使用说明已保存到 icons/README.md")
        except Exception as e:
            print(f"⚠️ 保存说明文件失败: {e}")


def main():
    """测试图标管理器"""
    from PyQt6.QtWidgets import QApplication
    
    print("🎨 License Decomposer - 图标管理器")
    print("=" * 50)
    
    # 创建QApplication实例
    app = QApplication(sys.argv)
    
    icon_manager = IconManager()
    
    # 列出可用图标
    icon_manager.list_available_icons()
    
    # 生成使用说明
    icon_manager.save_jfrog_instructions()
    
    # 测试图标加载
    app_icon = icon_manager.get_app_icon()
    if not app_icon.isNull():
        print("✅ 应用图标加载成功")
    else:
        print("❌ 应用图标加载失败")
    
    print("\n💡 下一步:")
    print("1. 将JFrog图标保存为 'icons/jfrog_icon.png'")
    print("2. 重启应用查看效果")

if __name__ == "__main__":
    main()
