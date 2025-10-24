#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
未保存警告对话框
带动图的提示对话框
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QMovie
from utils.resource_path import get_gui_resource
from pathlib import Path


class UnsavedWarningDialog(QDialog):
    """未保存警告对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("未保存的修改")
        self.setMinimumWidth(400)
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # 动图
        gif_label = QLabel()
        gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 加载动图
        gif_path = get_gui_resource("warning_save.gif")
        if gif_path.exists():
            movie = QMovie(str(gif_path))
            gif_label.setMovie(movie)
            movie.start()
            # 限制动图大小
            gif_label.setMaximumSize(200, 200)
            gif_label.setScaledContents(True)
        
        layout.addWidget(gif_label)
        
        # 警告文字
        warning_label = QLabel("⚠️ 你还没有保存，请保存！！！")
        warning_font = QFont()
        warning_font.setPointSize(16)
        warning_font.setBold(True)
        warning_label.setFont(warning_font)
        warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        warning_label.setStyleSheet("color: #e74c3c; padding: 10px;")
        layout.addWidget(warning_label)
        
        # 提示信息
        info_label = QLabel("是否保存修改？")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("font-size: 14px; color: #7f8c8d; padding: 10px;")
        layout.addWidget(info_label)
        
        # 选项说明
        options_label = QLabel(
            "• <b>是</b> - 保存并继续<br>"
            "• <b>否</b> - 放弃修改<br>"
            "• <b>取消</b> - 留在当前页面"
        )
        options_label.setTextFormat(Qt.TextFormat.RichText)
        options_label.setStyleSheet("font-size: 12px; color: #95a5a6; padding: 10px;")
        layout.addWidget(options_label)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.yes_btn = QPushButton("是")
        self.yes_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 10px 30px;
                font-weight: bold;
                font-size: 14px;
                border-radius: 5px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        self.yes_btn.clicked.connect(lambda: self.done(1))  # 返回1表示"是"
        
        self.no_btn = QPushButton("否")
        self.no_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 10px 30px;
                font-weight: bold;
                font-size: 14px;
                border-radius: 5px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.no_btn.clicked.connect(lambda: self.done(2))  # 返回2表示"否"
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                padding: 10px 30px;
                font-size: 14px;
                border-radius: 5px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        self.cancel_btn.clicked.connect(lambda: self.done(0))  # 返回0表示"取消"
        
        button_layout.addWidget(self.yes_btn)
        button_layout.addWidget(self.no_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    @staticmethod
    def ask_save(parent=None):
        """
        显示未保存警告对话框
        
        Returns:
            int: 1=是, 2=否, 0=取消
        """
        dialog = UnsavedWarningDialog(parent)
        return dialog.exec()

