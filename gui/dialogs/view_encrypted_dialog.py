#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解密查看对话框
显示加密文件解密后的内容
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QGroupBox, QTabWidget, QWidget,
    QScrollArea, QGridLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from typing import Dict, Any
import json


class ViewEncryptedDialog(QDialog):
    """解密查看对话框"""
    
    def __init__(self, decrypted_data: Dict[str, Any], parent=None):
        """
        初始化对话框
        
        Args:
            decrypted_data: 解密后的数据
            parent: 父窗口
        """
        super().__init__(parent)
        
        self.decrypted_data = decrypted_data
        
        self.setWindowTitle(f"🔓 解密查看 - {decrypted_data.get('app', 'Unknown')}")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # 标题
        title_label = QLabel(f"📄 {self.decrypted_data.get('app', 'Unknown')}")
        title_label.setProperty("heading", True)
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # 元数据
        meta_layout = QHBoxLayout()
        meta_layout.addWidget(QLabel(f"版本: {self.decrypted_data.get('version', 'N/A')}"))
        meta_layout.addWidget(QLabel(f"导出日期: {self.decrypted_data.get('export_date', 'N/A')[:19]}"))
        meta_layout.addWidget(QLabel(f"账号数量: {self.decrypted_data.get('count', 0)}"))
        meta_layout.addWidget(QLabel(f"已解密: ✅"))
        meta_layout.addStretch()
        layout.addLayout(meta_layout)
        
        # 标签页
        self.tabs = QTabWidget()
        
        accounts = self.decrypted_data.get('accounts', [])
        for idx, account in enumerate(accounts):
            email = account.get('email', f'账号 {idx+1}')
            account_widget = self._create_account_tab(account)
            self.tabs.addTab(account_widget, f"📧 {email}")
        
        layout.addWidget(self.tabs)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("关闭")
        close_btn.setMinimumWidth(100)
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _create_account_tab(self, account: Dict[str, Any]) -> QWidget:
        """创建单个账号的标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        
        # === 基本信息 ===
        basic_group = QGroupBox("基本信息")
        basic_layout = QGridLayout(basic_group)
        basic_layout.setSpacing(10)
        
        row = 0
        self._add_info_row(basic_layout, row, "邮箱:", account.get('email', 'N/A'))
        row += 1
        self._add_info_row(basic_layout, row, "用户ID:", account.get('user_id', 'N/A'))
        row += 1
        self._add_info_row(basic_layout, row, "套餐类型:", account.get('membership_type', 'free').upper())
        row += 1
        self._add_info_row(basic_layout, row, "使用情况:", 
                          f"{account.get('used', 0)} / {account.get('limit_value', 1000)} ({account.get('usage_percent', 0)}%)")
        
        content_layout.addWidget(basic_group)
        
        # === Token 信息 ===
        token_group = QGroupBox("Token 信息")
        token_layout = QVBoxLayout(token_group)
        
        # AccessToken
        token_layout.addWidget(QLabel("AccessToken:"))
        access_token_text = QTextEdit()
        access_token_text.setMaximumHeight(100)
        access_token_text.setReadOnly(True)
        access_token_text.setPlainText(account.get('access_token', ''))
        access_token_text.setStyleSheet("font-family: 'Courier New'; font-size: 9pt;")
        token_layout.addWidget(access_token_text)
        
        # 复制按钮
        copy_token_layout = QHBoxLayout()
        copy_access_btn = QPushButton("📋 复制 AccessToken")
        copy_access_btn.clicked.connect(lambda: self._copy_to_clipboard(account.get('access_token', '')))
        copy_token_layout.addWidget(copy_access_btn)
        copy_token_layout.addStretch()
        token_layout.addLayout(copy_token_layout)
        
        # RefreshToken
        if account.get('refresh_token'):
            token_layout.addWidget(QLabel("RefreshToken:"))
            refresh_token_text = QTextEdit()
            refresh_token_text.setMaximumHeight(100)
            refresh_token_text.setReadOnly(True)
            refresh_token_text.setPlainText(account.get('refresh_token', ''))
            refresh_token_text.setStyleSheet("font-family: 'Courier New'; font-size: 9pt;")
            token_layout.addWidget(refresh_token_text)
            
            copy_refresh_btn = QPushButton("📋 复制 RefreshToken")
            copy_refresh_btn.clicked.connect(lambda: self._copy_to_clipboard(account.get('refresh_token', '')))
            copy_refresh_layout = QHBoxLayout()
            copy_refresh_layout.addWidget(copy_refresh_btn)
            copy_refresh_layout.addStretch()
            token_layout.addLayout(copy_refresh_layout)
        
        # SessionToken
        if account.get('session_token'):
            token_layout.addWidget(QLabel("SessionToken (用于API):"))
            session_token_text = QTextEdit()
            session_token_text.setMaximumHeight(100)
            session_token_text.setReadOnly(True)
            session_token_text.setPlainText(account.get('session_token', ''))
            session_token_text.setStyleSheet("font-family: 'Courier New'; font-size: 9pt;")
            token_layout.addWidget(session_token_text)
            
            copy_session_btn = QPushButton("📋 复制 SessionToken")
            copy_session_btn.clicked.connect(lambda: self._copy_to_clipboard(account.get('session_token', '')))
            copy_session_layout = QHBoxLayout()
            copy_session_layout.addWidget(copy_session_btn)
            copy_session_layout.addStretch()
            token_layout.addLayout(copy_session_layout)
        
        content_layout.addWidget(token_group)
        
        # === 机器码信息 ===
        if account.get('machine_info'):
            machine_group = QGroupBox("机器码信息")
            machine_layout = QVBoxLayout(machine_group)
            
            machine_info = account.get('machine_info')
            
            if isinstance(machine_info, dict):
                machine_grid = QGridLayout()
                machine_grid.setSpacing(10)
                
                fields = [
                    ("telemetry.machineId", "Machine ID"),
                    ("telemetry.macMachineId", "Mac Machine ID"),
                    ("telemetry.devDeviceId", "Dev Device ID"),
                    ("telemetry.sqmId", "SQM ID"),
                    ("system.machineGuid", "Machine GUID")
                ]
                
                for idx, (key, label) in enumerate(fields):
                    if key in machine_info:
                        label_widget = QLabel(f"{label}:")
                        value_widget = QLabel(machine_info[key])
                        value_widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                        value_widget.setStyleSheet("font-family: 'Courier New'; font-size: 9pt;")
                        value_widget.setWordWrap(True)
                        
                        machine_grid.addWidget(label_widget, idx, 0)
                        machine_grid.addWidget(value_widget, idx, 1)
                
                machine_layout.addLayout(machine_grid)
                
                # 复制机器码JSON
                copy_machine_btn = QPushButton("📋 复制机器码 JSON")
                copy_machine_btn.clicked.connect(
                    lambda: self._copy_to_clipboard(json.dumps(machine_info, indent=2, ensure_ascii=False))
                )
                copy_machine_layout = QHBoxLayout()
                copy_machine_layout.addWidget(copy_machine_btn)
                copy_machine_layout.addStretch()
                machine_layout.addLayout(copy_machine_layout)
            else:
                machine_text = QTextEdit()
                machine_text.setMaximumHeight(150)
                machine_text.setReadOnly(True)
                machine_text.setPlainText(str(machine_info))
                machine_layout.addWidget(machine_text)
            
            content_layout.addWidget(machine_group)
        
        content_layout.addStretch()
        
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        return widget
    
    def _add_info_row(self, layout: QGridLayout, row: int, label: str, value: str):
        """添加信息行"""
        label_widget = QLabel(label)
        label_widget.setStyleSheet("font-weight: bold;")
        
        value_widget = QLabel(str(value))
        value_widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        layout.addWidget(label_widget, row, 0)
        layout.addWidget(value_widget, row, 1)
    
    def _copy_to_clipboard(self, text: str):
        """复制文本到剪贴板"""
        from PyQt6.QtWidgets import QApplication
        
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        
        # 简单提示（可以改进）
        self.statusBar().showMessage("✅ 已复制到剪贴板", 2000) if hasattr(self, 'statusBar') else None

