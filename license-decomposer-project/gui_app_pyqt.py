#!/usr/bin/env python3
"""
License Splitter - Advanced GUI Application (PyQt6) with Drag & Drop and License List Mode
A modern desktop application for splitting and extracting license keys from encrypted JSON files.
"""

import sys
import os
import threading
import json
import re
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QTextEdit, QFileDialog, 
    QMessageBox, QProgressBar, QCheckBox, QGroupBox, QFrame,
    QSplitter, QStatusBar, QMenuBar, QMenu, QDialog,
    QFormLayout, QSpinBox, QComboBox, QTabWidget, QScrollArea, QSizePolicy
)
from PyQt6.QtGui import QAction, QFont, QDragEnterEvent, QDropEvent
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSettings, QMimeData, QUrl
from PyQt6.QtGui import QIcon, QPalette, QColor, QPixmap
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Import our custom modules
from history_manager import HistoryManager
from history_widgets import HistoryListWidget, HistoryControlPanel
from icon_manager import IconManager

class DragDropLineEdit(QLineEdit):
    """QLineEdit with drag and drop support for files"""
    file_dropped = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setPlaceholderText("选择加密的JSON文件或拖拽文件到此处...")
        # 增加文件输入框的高度和点击区域
        self.setStyleSheet("""
            QLineEdit {
                padding: 12px 16px;
                border: 2px solid #DEE2E6;
                border-radius: 6px;
                font-size: 14px;
                background-color: #FFFFFF;
                color: #000000;
                min-height: 20px;
            }
            QLineEdit:focus {
                border: 2px solid #007AFF;
                background-color: #F8F9FA;
            }
            QLineEdit:hover {
                border: 2px solid #ADB5BD;
            }
        """)
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1 and urls[0].isLocalFile():
                file_path = urls[0].toLocalFile()
                if file_path.lower().endswith(('.json', '.enc')):
                    event.acceptProposedAction()
                    self.setStyleSheet("""
                        QLineEdit {
                            padding: 12px 16px;
                            border: 2px solid #34C759;
                            background-color: #D4EDDA;
                            border-radius: 6px;
                            font-size: 14px;
                            color: #000000;
                            min-height: 20px;
                        }
                    """)
                    return
        event.ignore()
        
    def dragLeaveEvent(self, event):
        """Handle drag leave events"""
        # 恢复正常样式而不是清空
        self.setStyleSheet("""
            QLineEdit {
                padding: 12px 16px;
                border: 2px solid #DEE2E6;
                border-radius: 6px;
                font-size: 14px;
                background-color: #FFFFFF;
                color: #000000;
                min-height: 20px;
            }
            QLineEdit:focus {
                border: 2px solid #007AFF;
                background-color: #F8F9FA;
            }
            QLineEdit:hover {
                border: 2px solid #ADB5BD;
            }
        """)
        
    def dropEvent(self, event: QDropEvent):
        """Handle drop events"""
        # 恢复正常样式
        self.setStyleSheet("""
            QLineEdit {
                padding: 12px 16px;
                border: 2px solid #DEE2E6;
                border-radius: 6px;
                font-size: 14px;
                background-color: #FFFFFF;
                color: #000000;
                min-height: 20px;
            }
            QLineEdit:focus {
                border: 2px solid #007AFF;
                background-color: #F8F9FA;
            }
            QLineEdit:hover {
                border: 2px solid #ADB5BD;
            }
        """)
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1 and urls[0].isLocalFile():
                file_path = urls[0].toLocalFile()
                if file_path.lower().endswith(('.json', '.enc')):
                    self.file_dropped.emit(file_path)
                    event.acceptProposedAction()
                    return
        event.ignore()

class LicenseItem(QFrame):
    """Compact single-line license item widget"""
    clicked = pyqtSignal(int)  # Emit index when clicked
    
    def __init__(self, license_text, index, parent=None):
        super().__init__(parent)
        self.license_text = license_text
        self.index = index
        self.copied = False
        self.copy_time = None
        
        self.setup_ui()
        self.update_appearance()
    
    def setup_ui(self):
        """Setup the compact license item UI"""
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(48)  # Slightly increased height
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)  # Restored margins for better spacing
        layout.setSpacing(2)  # Restored spacing
        
        # Main info line: Index + Status + Type + Content
        main_layout = QHBoxLayout()
        
        # Index number
        self.index_label = QLabel(f"{self.index + 1}")
        self.index_label.setFixedWidth(25)
        self.index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.index_label.setStyleSheet("font-weight: bold; color: #495057;")
        
        # Status icon
        self.status_label = QLabel("⏳")
        self.status_label.setFixedWidth(25)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Time
        self.time_label = QLabel("----")
        self.time_label.setFixedWidth(45)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet("font-family: monospace; font-size: 11px;")
        
        # Content preview (expanded to use more space)
        preview_text = self.license_text[:60] + "..." if len(self.license_text) > 60 else self.license_text
        self.content_label = QLabel(preview_text)
        self.content_label.setStyleSheet("color: #6C757D; font-family: monospace; font-size: 11px;")
        
        main_layout.addWidget(self.index_label)
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.time_label)
        main_layout.addWidget(self.content_label)
        main_layout.addStretch()
        
        layout.addLayout(main_layout)
    

    
    def mousePressEvent(self, event):
        """Handle click to copy license"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.index)
    
    def set_copied(self, copied=True):
        """Update the copied status"""
        self.copied = copied
        if copied:
            self.copy_time = datetime.now().strftime("%H:%M")
        self.update_appearance()
    
    def update_appearance(self):
        """Update visual appearance based on status"""
        if self.copied:
            # Copied state - green highlight
            self.setStyleSheet("""
                QFrame {
                    background-color: #D4EDDA;
                    border-left: 4px solid #28A745;
                }
                QFrame:hover {
                    background-color: #C3E6CB;
                }
            """)
            self.status_label.setText("✅")
            self.status_label.setStyleSheet("color: #28A745; font-size: 14px;")
            self.time_label.setText(self.copy_time)
            self.time_label.setStyleSheet("color: #28A745; font-family: monospace; font-size: 11px; font-weight: bold;")
        else:
            # Not copied state - neutral
            self.setStyleSheet("""
                QFrame {
                    background-color: #FFFFFF;
                    border-left: 4px solid #DEE2E6;
                }
                QFrame:hover {
                    background-color: #F8F9FA;
                    border-left: 4px solid #007AFF;
                }
            """)
            self.status_label.setText("⏳")
            self.status_label.setStyleSheet("color: #6C757D; font-size: 14px;")
            self.time_label.setText("----")
            self.time_label.setStyleSheet("color: #6C757D; font-family: monospace; font-size: 11px;")

class LicenseListWidget(QScrollArea):
    """Scrollable list of license items"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.licenses = []
        self.license_items = []
        self.parent_window = parent
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the scroll area and container"""
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Container widget for license items
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setSpacing(4)  # Reduced spacing
        self.container_layout.setContentsMargins(4, 4, 4, 20)  # Extra bottom margin for last item
        
        self.setWidget(self.container)
        
        # Set minimum height and ensure proper scrolling
        self.setMinimumHeight(300)  # Reasonable minimum height
        self.setMaximumHeight(400)  # Limited max height to force scrolling when needed
        self.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollArea::corner {
                background: transparent;
            }
        """)
    
    def set_licenses(self, licenses):
        """Set the list of licenses and create items"""
        self.licenses = licenses
        self.clear_items()
        
        for i, license_text in enumerate(licenses):
            item = LicenseItem(license_text, i, self.container)
            item.clicked.connect(self.on_license_clicked)
            
            self.license_items.append(item)
            self.container_layout.addWidget(item)
        
        # Add minimal stretch at the end to ensure proper spacing
        self.container_layout.addStretch(1)
        
        # Ensure container can accommodate all items with extra padding
        item_height = 48  # Updated to match new item height
        spacing_total = (len(licenses) - 1) * 4 if len(licenses) > 1 else 0
        margins = 24  # 4 top + 20 bottom
        extra_padding = 30  # Extra space to ensure last item is fully visible
        
        total_height = len(licenses) * item_height + spacing_total + margins + extra_padding
        self.container.setMinimumHeight(total_height)
        
        # Set scroll area height dynamically but ensure scrolling when needed
        if len(licenses) <= 4:
            # For 4 or fewer licenses, show all without scrolling
            required_height = total_height + 10
            self.setMinimumHeight(required_height)
            self.setMaximumHeight(required_height + 30)
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        else:
            # For more than 4 licenses, limit height to force scrolling
            max_display_height = 4 * item_height + 3 * 4 + margins + 20  # Height for 4 items + scrollbar space
            self.setMinimumHeight(max_display_height)
            self.setMaximumHeight(max_display_height)
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        
        # Force layout update
        self.container.updateGeometry()
        self.updateGeometry()
    
    def clear_items(self):
        """Clear all license items"""
        for item in self.license_items:
            item.deleteLater()
        self.license_items.clear()
    
    def on_license_clicked(self, index):
        """Handle license item click"""
        if 0 <= index < len(self.licenses):
            # Copy to clipboard
            clipboard = QApplication.clipboard()
            clipboard.setText(self.licenses[index])
            
            # Update item status
            self.license_items[index].set_copied(True)
            
            # Show temporary message
            if self.parent_window:
                self.parent_window.show_temporary_message(f"✅ 许可证 {index + 1} 已复制到剪贴板", 3000)
                self.parent_window.update_progress_display()
    
    def get_copy_status(self):
        """Get list of copy status for all licenses"""
        return [item.copied for item in self.license_items]
    
    def reset_all_status(self):
        """Reset all copy status"""
        for item in self.license_items:
            item.set_copied(False)
        if self.parent_window:
            self.parent_window.update_progress_display()
    
    def copy_all_licenses(self):
        """Mark all licenses as copied"""
        # Join licenses with double newlines, no extra formatting
        all_licenses = "\n\n".join(self.licenses)
        clipboard = QApplication.clipboard()
        clipboard.setText(all_licenses)
        
        for item in self.license_items:
            item.set_copied(True)
        
        if self.parent_window:
            self.parent_window.show_temporary_message(f"✅ 已复制全部 {len(self.licenses)} 个许可证", 3000)
            self.parent_window.update_progress_display()

class LicenseDecomposerGUI(QMainWindow):
    """License Splitter - Main GUI Application Window"""
    def __init__(self):
        super().__init__()
        self.settings = QSettings('LicenseSplitter', 'LicenseSplitter')
        self.processing = False
        
        # License navigation data
        self.licenses = []  # List of all license strings
        self.current_index = 0  # Current license index
        self.copied_status = []  # Track which licenses have been copied
        
        # Display mode management
        self.display_mode = "decompose"  # "decompose", "history", "history_result"
        
        # Initialize history manager
        self.history_manager = HistoryManager()
        
        # Initialize icon manager
        self.icon_manager = IconManager()
        
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("License Splitter")
        # 设置更合适的默认窗口大小 - 更紧凑
        self.setGeometry(100, 100, 750, 550)
        self.setMinimumSize(700, 500)
        
        # Set application icon
        app_icon = self.icon_manager.get_app_icon()
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)
            # 同时设置应用程序图标（在Dock/任务栏中显示）
            QApplication.instance().setWindowIcon(app_icon)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout with reduced margins for tighter layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)  # 减少间距从20到15
        main_layout.setContentsMargins(15, 15, 15, 15)  # 减少边距从20到15
        
        # Title removed for cleaner interface
        
        # Create input section
        self.create_input_section(main_layout)
        
        # Create main content area with left control panel and right results
        self.create_main_content_area(main_layout)
        
        # Create status bar
        self.create_status_bar()
        
        # Create menu bar
        self.create_menu_bar()
        
        # Apply modern styling
        self.apply_styles()
        
    def create_input_section(self, parent_layout):
        """Create the input section with file selection and password"""
        # File selection group with drag & drop
        file_group = QGroupBox("📁 选择加密文件")
        file_layout = QHBoxLayout(file_group)
        
        self.file_path_edit = DragDropLineEdit()
        self.file_path_edit.file_dropped.connect(self.on_file_dropped)
        
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_file)
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056CC;
            }
            QPushButton:pressed {
                background-color: #004499;
            }
        """)
        
        file_layout.addWidget(self.file_path_edit)
        file_layout.addWidget(browse_btn)
        
        # Password group
        password_group = QGroupBox("🔑 解密密码")
        password_layout = QHBoxLayout(password_group)
        
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("输入解密密码...")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        # 增加密码框的高度和点击区域
        self.password_edit.setStyleSheet("""
            QLineEdit {
                padding: 12px 16px;
                border: 2px solid #DEE2E6;
                border-radius: 6px;
                font-size: 14px;
                background-color: #FFFFFF;
                color: #000000;
                min-height: 20px;
            }
            QLineEdit:focus {
                border: 2px solid #007AFF;
                background-color: #F8F9FA;
            }
            QLineEdit:hover {
                border: 2px solid #ADB5BD;
            }
        """)
        
        self.show_password_btn = QPushButton("👁️ 显示密码")
        self.show_password_btn.setCheckable(True)
        self.show_password_btn.clicked.connect(self.toggle_password_visibility)
        self.show_password_btn.setStyleSheet("""
            QPushButton {
                background-color: #F8F9FA;
                color: #6C757D;
                border: 1px solid #DEE2E6;
                border-radius: 6px;
                padding: 8px 12px;
                font-weight: bold;
            }
            QPushButton:checked {
                background-color: #D4EDDA;
                color: #155724;
                border: 1px solid #C3E6CB;
            }
            QPushButton:hover {
                background-color: #E9ECEF;
            }
            QPushButton:checked:hover {
                background-color: #C3E6CB;
            }
        """)
        
        password_layout.addWidget(self.password_edit)
        password_layout.addWidget(self.show_password_btn)
        
        # Add groups to main layout
        parent_layout.addWidget(file_group)
        parent_layout.addWidget(password_group)

    def create_main_content_area(self, parent_layout):
        """Create main content area with left control panel and right results"""
        # Main horizontal layout for left-right split
        main_content_layout = QHBoxLayout()
        main_content_layout.setSpacing(12)  # 减少间距从20到12
        
        # Left control panel (30% width)
        self.create_control_panel(main_content_layout)
        
        # Right results area (70% width)
        self.create_results_section(main_content_layout)
        
        parent_layout.addLayout(main_content_layout)

    def create_control_panel(self, parent_layout):
        """Create left control panel with action buttons"""
        control_group = QGroupBox("        控制面板        ")
        control_layout = QVBoxLayout(control_group)
        control_layout.setSpacing(12)
        
        # Set custom style with proper centering using text-align
        control_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: #000000;
                border: 2px solid #DEE2E6;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
                text-align: center;
                background-color: transparent;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 8px 0 8px;
                background-color: #FFFFFF;
                text-align: center;
            }
        """)
        
        # Start button
        self.start_btn = QPushButton("🚀 开始分解")
        self.start_btn.clicked.connect(self.start_decomposition)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #34C759;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #28A745;
            }
            QPushButton:disabled {
                background-color: #A8E6CF;
                color: #6C757D;
            }
        """)
        
        # Copy all button
        copy_all_btn = QPushButton("📋 复制全部")
        copy_all_btn.clicked.connect(self.copy_all_licenses)
        copy_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #17A2B8;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
        """)
        
        # Save button
        save_btn = QPushButton("💾 保存结果")
        save_btn.clicked.connect(self.save_results)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #28A745;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #1E7E34;
            }
        """)
        
        # Reset button
        reset_btn = QPushButton("🔄 重置状态")
        reset_btn.clicked.connect(self.reset_copy_status)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFC107;
                color: #212529;
                border: none;
                padding: 8px 12px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #E0A800;
            }
        """)
        
        # History button
        self.history_btn = QPushButton("🕐 历史记录")
        self.history_btn.clicked.connect(self.show_history)
        self.history_btn.setStyleSheet("""
            QPushButton {
                background-color: #6F42C1;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #5A34A3;
            }
        """)
        
        # Exit button
        exit_btn = QPushButton("🚪 退出程序")
        exit_btn.clicked.connect(self.close)
        exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #DC3545;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #C82333;
            }
        """)
        
        # Add buttons to layout - remove stretch for compact design
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(copy_all_btn)
        control_layout.addWidget(save_btn)
        control_layout.addWidget(reset_btn)
        control_layout.addWidget(self.history_btn)
        control_layout.addWidget(exit_btn)  # Exit button directly after history
        
        # Set fixed width for control panel - wider to reduce middle gap
        control_group.setFixedWidth(260)
        parent_layout.addWidget(control_group)
        

        
    def create_results_section(self, parent_layout):
        """Create results display section with compact license list and history support"""
        self.results_group = QGroupBox("            分解结果            ")
        self.results_layout = QVBoxLayout(self.results_group)
        self.results_layout.setSpacing(10)
        
        # Set custom style with proper centering using text-align
        self.results_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: #000000;
                border: 2px solid #DEE2E6;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
                text-align: center;
                background-color: transparent;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 8px 0 8px;
                background-color: #FFFFFF;
                text-align: center;
            }
        """)
        
        # Progress and clear history button in the same row
        progress_row_layout = QHBoxLayout()
        
        # Progress label
        self.progress_label = QLabel("📋 分解结果 (0个许可证) ░░░░░░░░░░ 0/0 准备就绪")
        self.progress_label.setStyleSheet("""
            QLabel {
                color: #495057;
                font-weight: bold;
                font-family: monospace;
                padding: 8px 12px;
                background-color: #F8F9FA;
                border-radius: 6px;
                border: 1px solid #DEE2E6;
                font-size: 12px;
            }
        """)
        
        # Clear history button (initially hidden, shown only in history mode)
        self.clear_history_btn = QPushButton("🗑️ 清空历史")
        self.clear_history_btn.clicked.connect(self.clear_all_history)
        self.clear_history_btn.setStyleSheet("""
            QPushButton {
                background-color: #DC3545;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #C82333;
            }
        """)
        self.clear_history_btn.hide()  # Initially hidden
        
        # Add to horizontal layout
        progress_row_layout.addWidget(self.progress_label)
        progress_row_layout.addStretch()  # Push button to right
        progress_row_layout.addWidget(self.clear_history_btn)
        
        # Add the row to main layout
        self.results_layout.addLayout(progress_row_layout)
        
        # License list widget (scrollable, compact)
        self.license_list = LicenseListWidget(self)
        self.results_layout.addWidget(self.license_list)
        
        # History list widget (initially hidden)
        self.history_list = HistoryListWidget()
        self.history_list.item_single_clicked.connect(self.on_history_single_click)
        self.history_list.item_double_clicked.connect(self.on_history_double_click)
        self.history_list.item_copy_all_requested.connect(self.on_history_copy_all)
        self.history_list.item_delete_requested.connect(self.on_history_delete_item)
        self.history_list.hide()
        self.results_layout.addWidget(self.history_list)
        
        # Note: History control panel removed - clear button moved to title row
        
        parent_layout.addWidget(self.results_group)

    def on_file_dropped(self, file_path):
        """Handle file dropped into the input field"""
        self.file_path_edit.setText(file_path)
        self.show_temporary_message(f"📁 文件已加载: {os.path.basename(file_path)}", 3000)

    def copy_all_licenses(self):
        """Copy all licenses to clipboard"""
        self.license_list.copy_all_licenses()

    def reset_copy_status(self):
        """Reset all copy status"""
        self.license_list.reset_all_status()
        self.show_temporary_message("🔄 已重置所有复制状态", 2000)

    def show_history(self):
        """Show processing history"""
        if self.display_mode == "decompose":
            self.switch_to_history_mode()
        elif self.display_mode == "history":
            self.switch_to_decompose_mode()
        elif self.display_mode == "history_result":
            self.switch_to_history_mode()

    def update_progress_display(self):
        """Update the compact progress display based on copy status"""
        if not self.licenses:
            self.progress_label.setText("📋 分解结果 (0个许可证) ░░░░░░░░░░ 0/0 准备就绪")
            return
        
        copy_status = self.license_list.get_copy_status()
        copied_count = sum(copy_status)
        total_count = len(self.licenses)
        progress_percent = int((copied_count / total_count) * 100) if total_count > 0 else 0
        
        # Create compact progress bar
        progress_bar = "█" * (progress_percent // 10) + "░" * (10 - progress_percent // 10)
        
        # Status text
        if copied_count == total_count:
            status_text = "全部完成！"
        elif copied_count > 0:
            status_text = "复制中..."
        else:
            status_text = "开始复制"
        
        self.progress_label.setText(
            f"📋 分解结果 ({total_count}个许可证) {progress_bar} {copied_count}/{total_count} {status_text}"
        )
        
    def create_status_bar(self):
        """Create status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Status label
        self.status_label = QLabel("📊 状态: 就绪 | 文件: 0 | 许可证: 0")
        self.status_bar.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.status_bar.addPermanentWidget(self.progress_bar)
        
    def create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('文件')
        
        open_action = QAction('打开文件', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.browse_file)
        file_menu.addAction(open_action)
        
        save_action = QAction('保存结果', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_results)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu('编辑')
        
        copy_all_action = QAction('复制全部', self)
        copy_all_action.setShortcut('Ctrl+C')
        copy_all_action.triggered.connect(self.copy_all_licenses)
        edit_menu.addAction(copy_all_action)
        
        clear_action = QAction('清除输入', self)
        clear_action.setShortcut('Ctrl+Shift+C')
        clear_action.triggered.connect(self.clear_inputs)
        edit_menu.addAction(clear_action)
        
        # Tools menu
        tools_menu = menubar.addMenu('工具')
        
        settings_action = QAction('设置', self)
        settings_action.triggered.connect(self.open_settings)
        tools_menu.addAction(settings_action)
        
        # Help menu
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def apply_styles(self):
        """Apply modern styling to the application"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #FFFFFF;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #DEE2E6;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #DEE2E6;
                border-radius: 6px;
                background-color: #FFFFFF;
                color: #000000;
            }
            QLineEdit:focus {
                border: 2px solid #007AFF;
            }
            QCheckBox {
                spacing: 8px;
                color: #000000;
                font-weight: bold;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #007AFF;
                border-radius: 4px;
                background-color: #FFFFFF;
            }
            QCheckBox::indicator:checked {
                background-color: #007AFF;
                border: 2px solid #007AFF;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #0056CC;
                border: 2px solid #0056CC;
            }
            QCheckBox::indicator:hover {
                border: 2px solid #0056CC;
            }
            QGroupBox {
                color: #000000;
            }
            QLabel {
                color: #000000;
            }
        """)
        
    def browse_file(self):
        """Browse for input file"""
        import os
        downloads_path = os.path.expanduser("~/Downloads")
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "选择加密文件",
            downloads_path,
            "JSON files (*.json);;All files (*.*)"
        )
        if filename:
            self.file_path_edit.setText(filename)
            self.update_status()
            

    def clear_file(self):
        """Clear selected file"""
        self.file_path_edit.clear()
        self.update_status()
        
    def clear_inputs(self):
        """Clear all inputs and results"""
        self.file_path_edit.clear()
        self.password_edit.clear()
        
        # Reset license data
        self.licenses = []
        self.license_list.clear_items()
        self.update_progress_display()
        
        self.show_temporary_message("🧹 已清除所有输入和结果", 2000)
        
    def toggle_password_visibility(self, checked):
        """Toggle password visibility"""
        if checked:
            self.password_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_password_btn.setText("✅ 隐藏密码")
        else:
            self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_password_btn.setText("👁️ 显示密码")
            

    def start_decomposition(self):
        """Start the license decomposition process"""
        if not self.file_path_edit.text():
            self.show_styled_warning("警告", "请选择要处理的文件")
            return
        
        if not self.password_edit.text():
            self.show_styled_warning("警告", "请输入解密密码")
            return
            
        if self.processing:
            return
            
        # Start processing in background thread
        self.processing = True
        self.start_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.update_status("正在处理...")
        
        self.worker_thread = WorkerThread(
            self.file_path_edit.text(),
            self.password_edit.text()
        )
        self.worker_thread.result_ready.connect(self.handle_results)
        self.worker_thread.error_occurred.connect(self.handle_error)
        self.worker_thread.finished.connect(self.finish_processing)
        self.worker_thread.start()
        
    def handle_results(self, license_keys):
        """Handle processing results"""
        if license_keys:
            # Set licenses in the list widget
            self.licenses = license_keys
            self.license_list.set_licenses(license_keys)
            
            # Update progress display
            self.update_progress_display()
            
            # Save to history (only if successfully extracted licenses)
            try:
                filepath = self.file_path_edit.text().strip()
                password = self.password_edit.text()
                if filepath and password:
                    self.save_to_history(filepath, password, license_keys)
            except Exception as e:
                print(f"保存历史记录时出错: {e}")
            
            self.show_temporary_message(f"✅ 成功提取 {len(license_keys)} 个许可证", 3000)
            self.update_status(f"处理完成 | 文件: 1 | 许可证: {len(license_keys)}")
        else:
            # No licenses found
            self.licenses = []
            self.license_list.clear_items()
            self.progress_label.setText("未找到许可证")
            
            self.show_temporary_message("⚠️ 未找到许可证", 3000)
            self.update_status("处理完成 | 文件: 1 | 许可证: 0")
            
    def handle_error(self, error_msg):
        """Handle processing error with user-friendly messages"""
        # Parse common error patterns and provide friendly messages
        friendly_msg = self.get_friendly_error_message(error_msg)
        
        # Create custom styled message box for better visibility
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle("解密失败")
        msg_box.setText(friendly_msg)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        
        # Apply explicit styling to ensure button visibility
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
        
        msg_box.exec()
        self.show_temporary_message("❌ 解密失败，请检查文件和密码", 4000)
    
    def show_styled_warning(self, title, message):
        """Show a styled warning message box with proper button visibility"""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        
        # Apply explicit styling to ensure button visibility
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
        
        msg_box.exec()

    def get_friendly_error_message(self, error_msg):
        """Convert technical error messages to user-friendly ones"""
        error_lower = error_msg.lower()
        
        if "invalid json" in error_lower or "json" in error_lower:
            if "extra data" in error_lower:
                return ("🔐 密码可能不正确\n\n"
                       "解密后的内容不是有效的JSON格式。\n"
                       "请检查：\n"
                       "• 密码是否正确\n"
                       "• 文件是否被正确加密\n"
                       "• 文件是否完整无损坏")
            else:
                return ("🔐 JSON格式错误\n\n"
                       "文件内容不是有效的JSON格式。\n"
                       "请检查：\n"
                       "• 密码是否正确\n"
                       "• 文件是否为加密的许可证文件")
        
        elif "decryption failed" in error_lower or "decrypt" in error_lower:
            return ("🔑 解密失败\n\n"
                   "无法使用提供的密码解密文件。\n"
                   "请检查：\n"
                   "• 密码拼写是否正确\n"
                   "• 是否使用了正确的密码\n"
                   "• 文件格式是否支持")
        
        elif "file" in error_lower and ("not found" in error_lower or "exist" in error_lower):
            return ("📁 文件不存在\n\n"
                   "找不到指定的文件。\n"
                   "请检查文件路径是否正确。")
        
        elif "permission" in error_lower or "access" in error_lower:
            return ("🚫 文件访问被拒绝\n\n"
                   "没有权限访问该文件。\n"
                   "请检查文件权限设置。")
        
        else:
            # For other errors, provide a generic friendly message
            return ("❌ 处理过程中出现错误\n\n"
                   f"技术详情：{error_msg}\n\n"
                   "建议：\n"
                   "• 确认文件格式正确\n"
                   "• 检查密码是否正确\n"
                   "• 尝试重新选择文件")
        
    def finish_processing(self):
        """Finish processing and reset UI"""
        self.processing = False
        self.start_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        


        

            
    def save_results(self):
        """Save results to file"""
        if not self.licenses:
            self.show_temporary_message("⚠️ 没有可保存的内容", 3000)
            return
            
        import os
        downloads_path = os.path.expanduser("~/Downloads")
        default_filename = os.path.join(downloads_path, "license_results.txt")
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "保存结果",
            default_filename,
            "Text files (*.txt);;All files (*.*)"
        )
        
        if filename:
            try:
                copy_status = self.license_list.get_copy_status()
                
                with open(filename, 'w', encoding='utf-8') as f:
                    # Write pure license content, separated by double newlines
                    f.write("\n\n".join(self.licenses))
                
                filename_only = os.path.basename(filename)
                self.show_temporary_message(f"💾 结果已保存到: {filename_only}", 3000)
            except Exception as e:
                self.show_temporary_message(f"❌ 保存失败: {str(e)}", 4000)
                

    def open_settings(self):
        """Open settings dialog"""
        dialog = SettingsDialog(self)
        dialog.exec()
        
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "关于 License Decomposer",
            """
            <h3>License Decomposer</h3>
            <p>版本: 1.0.0</p>
            <p>一个用于从加密JSON文件中提取许可证密钥的桌面应用程序。</p>
            <p>支持AES-256-CBC加密格式，兼容OpenSSL。</p>
            """
        )
        
    def update_status(self, status_text=None):
        """Update status bar"""
        if status_text:
            self.status_label.setText(f"📊 {status_text}")
        else:
            self.status_label.setText("📊 状态: 就绪 | 文件: 0 | 许可证: 0")
            
    def show_temporary_message(self, message, timeout=3000):
        """Show temporary message in status bar"""
        # Store original message
        original_text = self.status_label.text()
        
        # Show temporary message
        self.status_label.setText(f"📊 {message}")
        
        # Set timer to restore original message
        QTimer.singleShot(timeout, lambda: self.status_label.setText(original_text))
            
    def load_settings(self):
        """Load application settings"""
        # 始终使用最佳默认尺寸，不保存窗口状态
        # geometry = self.settings.value('geometry')
        # if geometry:
        #     self.restoreGeometry(geometry)
        pass  # 不加载保存的几何形状，始终使用代码中的默认尺寸
            
    def save_settings(self):
        """Save application settings"""
        # 不保存窗口几何形状，始终使用默认尺寸
        # self.settings.setValue('geometry', self.saveGeometry())
        pass  # 不保存窗口状态
        
    def closeEvent(self, event):
        """Handle application close event"""
        self.save_settings()
        event.accept()

class WorkerThread(QThread):
    """Worker thread for processing files"""
    result_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, file_path, password):
        super().__init__()
        self.file_path = file_path
        self.password = password
        
    def run(self):
        """Run the processing in background"""
        try:
            # Import the license decomposer logic
            from license_decomposer import LicenseDecomposer
            
            decomposer = LicenseDecomposer()
            license_keys = decomposer.process_file(self.file_path, self.password)
            
            self.result_ready.emit(license_keys)
            
        except Exception as e:
            self.error_occurred.emit(str(e))

class SettingsDialog(QDialog):
    """Settings dialog"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setModal(True)
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # Create tabs
        tab_widget = QTabWidget()
        
        # General tab
        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)
        
        # Add settings controls
        self.auto_save_cb = QCheckBox("自动保存结果")
        general_layout.addRow("保存设置:", self.auto_save_cb)
        
        self.remember_path_cb = QCheckBox("记住最后使用的路径")
        general_layout.addRow("路径设置:", self.remember_path_cb)
        
        self.check_updates_cb = QCheckBox("启动时检查更新")
        general_layout.addRow("更新设置:", self.check_updates_cb)
        
        tab_widget.addTab(general_tab, "常规")
        
        # Security tab
        security_tab = QWidget()
        security_layout = QFormLayout(security_tab)
        
        self.clear_password_cb = QCheckBox("清除内存中的密码")
        security_layout.addRow("安全设置:", self.clear_password_cb)
        
        self.encrypt_temp_cb = QCheckBox("加密临时文件")
        security_layout.addRow("文件安全:", self.encrypt_temp_cb)
        
        tab_widget.addTab(security_tab, "安全")
        
        layout.addWidget(tab_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
        """)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6C757D;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
        """)
        
        button_layout.addStretch()
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)


# Add new methods to LicenseDecomposerGUI class
def add_history_methods():
    """Add history-related methods to LicenseDecomposerGUI class"""
    
    def switch_to_history_mode(self):
        """Switch to history mode"""
        self.display_mode = "history"
        self.update_display_for_mode()
        
        # Load and display history
        history_records = self.history_manager.get_sorted_history()
        self.history_list.set_history_records(history_records)
        
        self.show_temporary_message("📋 历史记录已加载", 2000)
    
    def switch_to_decompose_mode(self):
        """Switch to decompose mode"""
        self.display_mode = "decompose"
        self.update_display_for_mode()
        self.show_temporary_message("🔙 返回分解模式", 2000)
    
    def switch_to_history_result_mode(self, licenses, source_info):
        """Switch to history result mode"""
        self.display_mode = "history_result"
        self.licenses = licenses
        self.copied_status = [False] * len(licenses)
        
        # Update progress label for history result
        self.progress_label.setText(f"📋 历史记录 ({len(licenses)}个许可证) ████████████ {len(licenses)}/{len(licenses)} 已加载")
        
        # Display licenses
        self.license_list.set_licenses(licenses)
        self.update_display_for_mode()
        
        self.show_temporary_message(f"✅ 历史记录已展示: {source_info}", 3000)
    
    def update_display_for_mode(self):
        """Update UI elements based on current display mode"""
        if self.display_mode == "decompose":
            # Show decompose elements
            self.progress_label.show()
            self.license_list.show()
            
            # Hide history elements
            self.history_list.hide()
            self.clear_history_btn.hide()  # Hide clear button in decompose mode
            
            # Reset license list height constraints to allow proper scrolling
            self.license_list.setMinimumHeight(0)
            self.license_list.setMaximumHeight(16777215)  # Maximum widget height
            
            # Update group box title
            self.results_group.setTitle("            分解结果            ")
            
            # Update history button text
            self.history_btn.setText("🕐 历史记录")
            
        elif self.display_mode == "history":
            # Show progress bar but hide license list
            self.progress_label.show()
            self.license_list.hide()
            
            # Show history elements
            self.history_list.show()
            self.clear_history_btn.show()  # Show clear button in history mode
            
            # Update group box title
            self.results_group.setTitle("            历史记录            ")
            
            # Update history button text
            self.history_btn.setText("🔙 返回分解")
            
        elif self.display_mode == "history_result":
            # Show decompose elements for result display
            self.progress_label.show()
            self.license_list.show()
            
            # Hide history list and clear button
            self.history_list.hide()
            self.clear_history_btn.hide()
            
            # Update group box title
            self.results_group.setTitle("            历史详情            ")
            
            # Update history button text
            self.history_btn.setText("📋 返回历史")
    
    def on_history_single_click(self, record):
        """Handle single click on history item - fill inputs"""
        try:
            # Get file path from history
            filepath = self.history_manager.get_record_filepath(record)
            
            # Check if file exists
            if not os.path.exists(filepath):
                self.show_temporary_message("⚠️ 历史文件不存在", 3000)
                return
            
            # Fill inputs
            self.file_path_edit.setText(filepath)
            
            # Decode and fill password
            password = self.history_manager.decode_password(record)
            if password:
                self.password_edit.setText(password)
                self.show_temporary_message("📁 已填充文件和密码", 2000)
            else:
                self.show_temporary_message("📁 已填充文件路径", 2000)
                
        except Exception as e:
            self.show_temporary_message(f"❌ 填充失败: {str(e)}", 3000)
    
    def on_history_double_click(self, record):
        """Handle double click on history item - direct decomposition"""
        try:
            # Get file path from history
            filepath = self.history_manager.get_record_filepath(record)
            
            # Check if file exists
            if not os.path.exists(filepath):
                self.show_temporary_message("⚠️ 历史文件不存在", 3000)
                return
            
            # Decode password
            password = self.history_manager.decode_password(record)
            if not password:
                self.show_temporary_message("❌ 密码解码失败", 3000)
                return
            
            # Show loading message
            self.show_temporary_message("🔄 正在加载历史记录...", 2000)
            
            # Decompose and display
            self.auto_decompose_and_display(filepath, password, record['filename'])
            
        except Exception as e:
            self.show_temporary_message(f"❌ 加载失败: {str(e)}", 3000)
    
    def auto_decompose_and_display(self, filepath, password, source_filename):
        """Automatically decompose and display results"""
        try:
            from license_decomposer import LicenseDecomposer
            
            decomposer = LicenseDecomposer()
            licenses = decomposer.process_file(filepath, password)
            
            # Switch to history result mode
            self.switch_to_history_result_mode(licenses, source_filename)
            
        except Exception as e:
            self.show_temporary_message(f"❌ 分解失败: {str(e)}", 3000)
    
    def clear_all_history(self):
        """Clear all history records"""
        try:
            from PyQt6.QtWidgets import QMessageBox
            
            # 创建自定义样式的消息框
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Question)
            msg_box.setWindowTitle("确认清空")
            msg_box.setText("确定要清空所有历史记录吗？此操作不可恢复。")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg_box.setDefaultButton(QMessageBox.StandardButton.No)
            
            # 应用自定义样式
            msg_box.setStyleSheet("""
                QMessageBox { 
                    background-color: white; 
                    color: black; 
                    font-size: 14px;
                }
                QMessageBox QPushButton {
                    background-color: #007AFF; 
                    color: white; 
                    border: none;
                    padding: 10px 20px; 
                    border-radius: 6px; 
                    font-weight: bold; 
                    font-size: 14px;
                    min-width: 80px;
                    margin: 4px;
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
                    font-size: 14px;
                    padding: 10px;
                }
            """)
            
            reply = msg_box.exec()
            
            if reply == QMessageBox.StandardButton.Yes:
                success = self.history_manager.clear_history()
                if success:
                    # Refresh history display
                    self.history_list.set_history_records([])
                    self.show_temporary_message("🗑️ 历史记录已清空", 2000)
                else:
                    self.show_temporary_message("❌ 清空失败", 3000)
                    
        except Exception as e:
            self.show_temporary_message(f"❌ 操作失败: {str(e)}", 3000)
    
    def save_to_history(self, filepath, password, licenses):
        """Save successful decomposition to history"""
        try:
            result = self.history_manager.save_success_record(filepath, password, licenses)
            
            if result == "updated":
                self.show_temporary_message("📝 更新了现有历史记录", 2000)
            elif result == "created":
                self.show_temporary_message("💾 已保存到历史记录", 2000)
            elif result == "failed":
                self.show_temporary_message("⚠️ 历史记录保存失败", 2000)
                
        except Exception as e:
            print(f"保存历史记录失败: {e}")
    
    def on_history_copy_all(self, record):
        """从历史记录复制全部许可证"""
        try:
            # 先尝试自动分解获取许可证
            filepath = self.history_manager.get_record_filepath(record)
            
            if not os.path.exists(filepath):
                self.show_temporary_message("⚠️ 历史文件不存在", 3000)
                return
            
            password = self.history_manager.decode_password(record)
            if not password:
                self.show_temporary_message("❌ 密码解码失败", 3000)
                return
            
            # 分解文件获取许可证
            from license_decomposer import LicenseDecomposer
            decomposer = LicenseDecomposer()
            licenses = decomposer.process_file(filepath, password)
            
            if licenses:
                # 复制到剪贴板
                clipboard_text = '\n\n'.join(licenses)
                
                import sys
                app = QApplication.instance()
                if app:
                    clipboard = app.clipboard()
                    clipboard.setText(clipboard_text)
                
                self.show_temporary_message(f"📋 已复制 {len(licenses)} 个许可证到剪贴板", 3000)
            else:
                self.show_temporary_message("⚠️ 未找到许可证内容", 3000)
                
        except Exception as e:
            self.show_temporary_message(f"❌ 复制失败: {str(e)}", 3000)
    
    def on_history_delete_item(self, record):
        """删除单个历史记录项"""
        try:
            # 删除记录
            success = self.history_manager.delete_record(record['id'])
            
            if success:
                # 刷新历史显示
                updated_history = self.history_manager.get_sorted_history()
                self.history_list.set_history_records(updated_history)
                
                self.show_temporary_message(f"🗑️ 已删除记录: {record['filename']}", 2000)
            else:
                self.show_temporary_message("❌ 删除失败", 3000)
                
        except Exception as e:
            self.show_temporary_message(f"❌ 删除失败: {str(e)}", 3000)
    
    # Bind methods to class
    LicenseDecomposerGUI.switch_to_history_mode = switch_to_history_mode
    LicenseDecomposerGUI.switch_to_decompose_mode = switch_to_decompose_mode
    LicenseDecomposerGUI.switch_to_history_result_mode = switch_to_history_result_mode
    LicenseDecomposerGUI.update_display_for_mode = update_display_for_mode
    LicenseDecomposerGUI.on_history_single_click = on_history_single_click
    LicenseDecomposerGUI.on_history_double_click = on_history_double_click
    LicenseDecomposerGUI.auto_decompose_and_display = auto_decompose_and_display
    LicenseDecomposerGUI.clear_all_history = clear_all_history
    LicenseDecomposerGUI.save_to_history = save_to_history
    LicenseDecomposerGUI.on_history_copy_all = on_history_copy_all
    LicenseDecomposerGUI.on_history_delete_item = on_history_delete_item

# Call the function to add methods
add_history_methods()


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("License Splitter")
    app.setApplicationDisplayName("License Splitter")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("JFrog License Tools")
    app.setOrganizationDomain("jfrog.com")
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = LicenseDecomposerGUI()
    window.show()
    
    # Start application
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 