#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aug账号管理面板
管理Augment Code账号
"""

import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.logger import get_logger

logger = get_logger("aug_account_panel")


class AugAccountPanel(QWidget):
    """Aug账号管理面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AugAccountPanel")
        
        self.accounts = []  # Aug账号列表
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 标题栏
        title_row = QHBoxLayout()
        
        title_label = QLabel("🔷 Aug账号管理")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_row.addWidget(title_label)
        
        title_row.addStretch()
        
        # 操作按钮
        add_btn = QPushButton("➕ 添加账号")
        add_btn.setProperty("primary", True)
        add_btn.clicked.connect(self._on_add_account)
        title_row.addWidget(add_btn)
        
        import_btn = QPushButton("📥 导入")
        import_btn.setProperty("secondary", True)
        import_btn.clicked.connect(self._on_import)
        title_row.addWidget(import_btn)
        
        export_btn = QPushButton("📤 导出")
        export_btn.setProperty("secondary", True)
        export_btn.clicked.connect(self._on_export)
        title_row.addWidget(export_btn)
        
        main_layout.addLayout(title_row)
        
        # 统计信息
        self.stats_label = QLabel("共 0 个Aug账号")
        self.stats_label.setStyleSheet("color: #7f8c8d; font-size: 13px; padding: 5px 0;")
        main_layout.addWidget(self.stats_label)
        
        # 账号列表区域
        list_group = QGroupBox("账号列表")
        list_layout = QVBoxLayout(list_group)
        
        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        
        # 账号列表容器
        self.account_list_widget = QWidget()
        account_list_layout = QVBoxLayout(self.account_list_widget)
        account_list_layout.setSpacing(10)
        account_list_layout.setContentsMargins(10, 10, 10, 10)
        
        # 占位符
        placeholder = QLabel("暂无Aug账号\n\n点击上方'添加账号'按钮添加")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("""
            color: #95a5a6;
            font-size: 14px;
            padding: 50px;
        """)
        account_list_layout.addWidget(placeholder)
        
        account_list_layout.addStretch()
        
        scroll_area.setWidget(self.account_list_widget)
        list_layout.addWidget(scroll_area)
        
        main_layout.addWidget(list_group)
        
        # 底部说明
        info_label = QLabel(
            "💡 Aug账号管理功能正在开发中\n"
            "即将支持：添加、导入、导出、刷新等功能"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("""
            color: #3498db;
            font-size: 12px;
            padding: 10px;
            background-color: rgba(52, 152, 219, 0.1);
            border-radius: 5px;
        """)
        main_layout.addWidget(info_label)
    
    def _on_add_account(self):
        """添加账号"""
        QMessageBox.information(
            self,
            "功能开发中",
            "Aug账号添加功能正在开发中...\n\n"
            "即将支持：\n"
            "• 手动添加Aug账号\n"
            "• 导入Aug账号列表\n"
            "• 账号验证和刷新"
        )
    
    def _on_import(self):
        """导入账号"""
        QMessageBox.information(
            self,
            "功能开发中",
            "Aug账号导入功能正在开发中..."
        )
    
    def _on_export(self):
        """导出账号"""
        QMessageBox.information(
            self,
            "功能开发中",
            "Aug账号导出功能正在开发中..."
        )

