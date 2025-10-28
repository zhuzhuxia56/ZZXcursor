#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aug账号编辑对话框
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QTextEdit, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from utils.logger import get_logger

logger = get_logger("aug_account_edit")


class AugAccountEditDialog(QDialog):
    """Aug账号编辑对话框"""
    
    def __init__(self, account_data, parent=None):
        super().__init__(parent)
        self.account_data = account_data.copy()
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("编辑Aug账号")
        self.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel("✏️ 编辑Aug账号信息")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # API URL
        api_group = QGroupBox("API地址")
        api_layout = QVBoxLayout(api_group)
        
        self.api_url_input = QLineEdit()
        self.api_url_input.setPlaceholderText("例如: d14.api.augmentcode.com")
        api_layout.addWidget(self.api_url_input)
        
        layout.addWidget(api_group)
        
        # 邮箱
        email_group = QGroupBox("注册邮箱")
        email_layout = QVBoxLayout(email_group)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("例如: abc****xyz@domain.com")
        email_layout.addWidget(self.email_input)
        
        layout.addWidget(email_group)
        
        # 授权Code
        code_group = QGroupBox("授权Code（JSON格式）")
        code_layout = QVBoxLayout(code_group)
        
        self.code_text = QTextEdit()
        self.code_text.setPlaceholderText('例如: {"code":"_fba4083f5fac69f0781abc17dcf5"}')
        self.code_text.setMaximumHeight(100)
        self.code_text.setStyleSheet("font-family: Consolas; font-size: 11px;")
        code_layout.addWidget(self.code_text)
        
        # 复制code按钮
        copy_code_btn = QPushButton("📋 复制Code")
        copy_code_btn.setProperty("secondary", True)
        copy_code_btn.clicked.connect(self._on_copy_code)
        code_layout.addWidget(copy_code_btn)
        
        layout.addWidget(code_group)
        
        # AccessToken（可选）
        token_group = QGroupBox("AccessToken（可选）")
        token_layout = QVBoxLayout(token_group)
        
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("如果有，可以填写...")
        token_layout.addWidget(self.token_input)
        
        layout.addWidget(token_group)
        
        # 备注
        notes_group = QGroupBox("备注")
        notes_layout = QVBoxLayout(notes_group)
        
        self.notes_text = QTextEdit()
        self.notes_text.setPlaceholderText("可以添加备注信息...")
        self.notes_text.setMaximumHeight(80)
        notes_layout.addWidget(self.notes_text)
        
        layout.addWidget(notes_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 保存")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 8px 20px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        save_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def load_data(self):
        """加载数据到界面"""
        self.api_url_input.setText(self.account_data.get('api_url', ''))
        self.email_input.setText(self.account_data.get('email', ''))
        self.code_text.setPlainText(self.account_data.get('auth_code', ''))
        self.token_input.setText(self.account_data.get('access_token', ''))
        self.notes_text.setPlainText(self.account_data.get('notes', ''))
    
    def get_data(self):
        """获取编辑后的数据"""
        self.account_data['api_url'] = self.api_url_input.text().strip()
        self.account_data['email'] = self.email_input.text().strip()
        self.account_data['auth_code'] = self.code_text.toPlainText().strip()
        self.account_data['access_token'] = self.token_input.text().strip()
        self.account_data['notes'] = self.notes_text.toPlainText().strip()
        
        return self.account_data
    
    def _on_copy_code(self):
        """复制code到剪贴板"""
        from PyQt6.QtWidgets import QApplication
        
        code = self.code_text.toPlainText().strip()
        if code:
            clipboard = QApplication.clipboard()
            clipboard.setText(code)
            QMessageBox.information(self, "成功", "Code已复制到剪贴板！")
        else:
            QMessageBox.warning(self, "提示", "Code为空，无法复制！")

