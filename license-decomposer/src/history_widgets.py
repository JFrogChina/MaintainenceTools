from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
                             QScrollArea, QWidget, QPushButton, QMenu, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QAction
from datetime import datetime
import os


class HistoryItem(QFrame):
    """单个历史记录项Widget"""
    
    # 定义信号
    single_clicked = pyqtSignal(dict)  # 单击信号
    double_clicked = pyqtSignal(dict)  # 双击信号
    copy_all_requested = pyqtSignal(dict)  # 复制全部信号
    delete_requested = pyqtSignal(dict)  # 删除信号
    
    def __init__(self, record):
        super().__init__()
        self.record = record
        self.click_timer = QTimer()
        self.click_timer.timeout.connect(self.handle_single_click)
        self.click_timer.setSingleShot(True)
        
        self.setup_ui()
        self.setup_styles()
    
    def setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        
        # 格式化显示文本
        display_text = self.format_display_text()
        self.label = QLabel(display_text)
        
        # 设置字体
        font = QFont()
        font.setPointSize(11)
        self.label.setFont(font)
        
        layout.addWidget(self.label)
        layout.addStretch()
    
    def format_display_text(self):
        """格式化显示文本"""
        timestamp = datetime.fromisoformat(self.record['timestamp'])
        date_str = timestamp.strftime('%Y-%m-%d %H:%M')
        
        # 获取许可证数量
        count = self.record.get('license_count', 0)
        
        # 只显示文件名，不显示完整路径
        filename = os.path.basename(self.record['filename'])
        
        return f"{date_str} ({count}) {filename}"
    
    def setup_styles(self):
        """设置样式"""
        self.setStyleSheet("""
            HistoryItem {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 4px;
                margin: 1px;
            }
            HistoryItem:hover {
                background-color: #e7f3ff;
                border-color: #007AFF;
            }
            QLabel {
                color: #333333;
                background-color: transparent;
                padding: 0px;
            }
        """)
        
        # 设置高度
        self.setFixedHeight(40)
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 启动单击计时器
            self.click_timer.start(300)  # 300ms后触发单击
        elif event.button() == Qt.MouseButton.RightButton:
            # 右键点击显示上下文菜单
            self.show_context_menu(event.globalPosition().toPoint())
        
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        """鼠标双击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 停止单击计时器
            self.click_timer.stop()
            # 发送双击信号
            self.double_clicked.emit(self.record)
        
        super().mouseDoubleClickEvent(event)
    
    def handle_single_click(self):
        """处理单击事件"""
        self.single_clicked.emit(self.record)
    
    def show_context_menu(self, position):
        """显示右键上下文菜单"""
        try:
            context_menu = QMenu(self)
            
            # 复制全部动作
            copy_action = QAction("复制全部", self)
            copy_action.triggered.connect(lambda: self.copy_all_requested.emit(self.record))
            context_menu.addAction(copy_action)
            
            # 删除动作
            delete_action = QAction("删除此条", self)
            delete_action.triggered.connect(self.confirm_delete)
            context_menu.addAction(delete_action)
            
            context_menu.exec(position)
        except Exception as e:
            # 右键菜单出错时静默处理
            pass
    
    def confirm_delete(self):
        """确认删除对话框"""
        try:
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Question)
            msg_box.setWindowTitle("确认删除")
            msg_box.setText(f"确定要删除历史记录 '{self.record['filename']}' 吗？\n此操作不可恢复。")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg_box.setDefaultButton(QMessageBox.StandardButton.No)
            
            # Apply explicit styling for better visibility
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                    color: black;
                }
                QMessageBox QPushButton {
                    background-color: #007AFF;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                    min-width: 60px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #0051D5;
                }
                QMessageBox QPushButton:pressed {
                    background-color: #003F99;
                }
                QMessageBox QLabel {
                    color: black;
                    background-color: transparent;
                }
            """)
            
            reply = msg_box.exec()
            
            if reply == QMessageBox.StandardButton.Yes:
                self.delete_requested.emit(self.record)
        except Exception as e:
            # 如果确认对话框出错，直接发送删除信号
            self.delete_requested.emit(self.record)


class HistoryListWidget(QScrollArea):
    """历史记录列表Widget"""
    
    # 定义信号 - 这些是主程序期望的信号
    item_single_clicked = pyqtSignal(dict)
    item_double_clicked = pyqtSignal(dict)
    item_copy_all_requested = pyqtSignal(dict)
    item_delete_requested = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.history_items = []
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        # 创建容器widget
        self.container_widget = QWidget()
        self.container_layout = QVBoxLayout(self.container_widget)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(2)
        
        # 设置滚动区域
        self.setWidget(self.container_widget)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        
        # 设置样式
        self.setStyleSheet("""
            QScrollArea {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)
        
        # 设置初始高度
        self.setMinimumHeight(4 * 42 + 10)
        self.setMaximumHeight(4 * 42 + 10)
    
    def set_history_records(self, history_records):
        """设置历史记录 - 主程序调用的方法名"""
        self.update_history(history_records)
    
    def update_history(self, history_records):
        """更新历史记录显示"""
        # 清除现有的项目
        self.clear_items()
        
        # 添加新的历史记录项
        for record in history_records:
            self.add_history_item(record)
        
        # 更新布局
        self.container_layout.addStretch()
        
        # 根据项目数量调整高度
        item_count = len(history_records)
        if item_count > 4:
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        else:
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    
    def add_history_item(self, record):
        """添加历史记录项"""
        item = HistoryItem(record)
        self.history_items.append(item)
        
        # 连接信号 - 将子项的信号转发到自己的信号
        item.single_clicked.connect(self.item_single_clicked.emit)
        item.double_clicked.connect(self.item_double_clicked.emit)
        item.copy_all_requested.connect(self.item_copy_all_requested.emit)
        item.delete_requested.connect(self.item_delete_requested.emit)
        
        # 插入到最后一个位置（在stretch之前）
        self.container_layout.insertWidget(self.container_layout.count() - 1, item)
        
        return item
    
    def clear_items(self):
        """清除所有历史记录项"""
        # 清除layout中的所有项目（除了最后的stretch）
        while self.container_layout.count() > 1:
            child = self.container_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # 清空历史项目列表
        self.history_items.clear()
    
    def get_history_items(self):
        """获取所有历史记录项"""
        return self.history_items


# 兼容性：HistoryControlPanel 类已被移除，但为了向下兼容，提供一个空类
class HistoryControlPanel:
    """已弃用的 HistoryControlPanel 类，为了向下兼容而保留"""
    def __init__(self, *args, **kwargs):
        pass
