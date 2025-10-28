#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aug账号管理面板
管理Augment Code账号
"""

import sys
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QGroupBox, QMessageBox,
    QFrame, QGridLayout, QApplication, QDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.logger import get_logger

logger = get_logger("aug_account_panel")


class AugAccountCard(QFrame):
    """Aug账号卡片"""
    
    def __init__(self, account_data, account_index, parent=None):
        super().__init__(parent)
        self.account_data = account_data
        self.account_index = account_index  # 保存索引用于更新
        self.parent_panel = parent
        self.setFrameShape(QFrame.Shape.Box)
        
        # ⭐ 限制卡片最大宽度
        self.setMaximumWidth(650)
        self.setMinimumWidth(400)
        
        self.setStyleSheet("""
            AugAccountCard {
                background-color: white;
                border: 2px solid #e0e0e0;
                border-radius: 12px;
                padding: 15px;
            }
            AugAccountCard:hover {
                border-color: #3498db;
                background-color: #f8f9fa;
            }
        """)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置卡片UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 顶部：API地址和标签
        top_row = QHBoxLayout()
        
        # API地址
        api_label = QLabel(self.account_data.get('api_url', 'N/A'))
        api_font = QFont()
        api_font.setPointSize(13)
        api_font.setBold(True)
        api_label.setFont(api_font)
        top_row.addWidget(api_label)
        
        top_row.addStretch()
        
        # 个人标签
        personal_badge = QLabel("👤 个人")
        personal_badge.setStyleSheet("""
            background-color: #fff3cd;
            color: #856404;
            border: 1px solid #ffc107;
            border-radius: 12px;
            padding: 4px 12px;
            font-size: 11px;
            font-weight: bold;
        """)
        top_row.addWidget(personal_badge)
        
        # 状态标签
        status = self.account_data.get('status', '正常')
        if status == '正常':
            status_badge = QLabel("✅ 正常")
            status_badge.setStyleSheet("""
                background-color: #d4edda;
                color: #155724;
                border: 1px solid #28a745;
                border-radius: 12px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: bold;
            """)
        else:
            status_badge = QLabel("❌ 异常")
            status_badge.setStyleSheet("""
                background-color: #f8d7da;
                color: #721c24;
                border: 1px solid #dc3545;
                border-radius: 12px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: bold;
            """)
        top_row.addWidget(status_badge)
        
        layout.addLayout(top_row)
        
        # 中间：时间和邮箱
        info_row = QHBoxLayout()
        
        # 时间
        time_label = QLabel(self.account_data.get('time', 'N/A'))
        time_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        info_row.addWidget(time_label)
        
        info_row.addSpacing(20)
        
        # 邮箱（带复制按钮）
        email_container = QHBoxLayout()
        email_label = QLabel(f"📧 {self._mask_email(self.account_data.get('email', 'N/A'))}")
        email_label.setStyleSheet("color: #495057; font-size: 12px;")
        email_container.addWidget(email_label)
        
        copy_email_btn = QPushButton("📋")
        copy_email_btn.setFixedSize(24, 24)
        copy_email_btn.setToolTip("复制完整邮箱")
        copy_email_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
        """)
        copy_email_btn.clicked.connect(lambda: self._copy_to_clipboard(self.account_data.get('email', '')))
        email_container.addWidget(copy_email_btn)
        
        info_row.addLayout(email_container)
        info_row.addStretch()
        
        layout.addLayout(info_row)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #dee2e6;")
        layout.addWidget(line)
        
        # 底部：操作按钮
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)
        
        # 按钮数据
        buttons = [
            ("🔷", "打开VSCode", self._on_open_vscode, "#0078d4"),
            ("📋", "复制信息", self._on_copy_info, "#6c757d"),
            ("🔗", "复制链接", self._on_copy_link, "#6c757d"),
            ("🔄", "刷新", self._on_refresh, "#ffc107"),
            ("✏️", "编辑", self._on_edit, "#28a745"),
            ("🔗", "分享", self._on_share, "#6c757d"),
            ("🗑️", "删除", self._on_delete, "#dc3545"),
        ]
        
        for icon, tooltip, callback, color in buttons:
            btn = QPushButton(icon)
            btn.setFixedSize(36, 36)
            btn.setToolTip(tooltip)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    font-size: 16px;
                }}
                QPushButton:hover {{
                    background-color: {color};
                    color: white;
                    border-color: {color};
                }}
            """)
            btn.clicked.connect(callback)
            actions_row.addWidget(btn)
        
        actions_row.addStretch()
        layout.addLayout(actions_row)
    
    def _mask_email(self, email):
        """隐藏邮箱部分字符"""
        if '@' not in email:
            return email
        local, domain = email.split('@', 1)
        if len(local) > 6:
            masked = local[:3] + '****' + local[-2:]
        else:
            masked = local[:2] + '****'
        return f"{masked}@{domain}"
    
    def _copy_to_clipboard(self, text):
        """复制到剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        logger.info(f"已复制: {text}")
    
    def _on_open_vscode(self):
        """打开VSCode"""
        QMessageBox.information(self, "功能开发中", "打开VSCode功能开发中...")
    
    def _on_copy_info(self):
        """复制信息"""
        QMessageBox.information(self, "功能开发中", "复制信息功能开发中...")
    
    def _on_copy_link(self):
        """复制链接"""
        QMessageBox.information(self, "功能开发中", "复制链接功能开发中...")
    
    def _on_refresh(self):
        """刷新"""
        QMessageBox.information(self, "功能开发中", "刷新功能开发中...")
    
    def _on_edit(self):
        """编辑账号信息"""
        try:
            from gui.dialogs.aug_account_edit_dialog import AugAccountEditDialog
            
            # 打开编辑对话框
            dialog = AugAccountEditDialog(self.account_data, self)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # 获取编辑后的数据
                updated_data = dialog.get_data()
                
                # 保存到存储
                from core.aug_account_storage import get_aug_storage
                storage = get_aug_storage()
                
                if storage.update_account(self.account_index, updated_data):
                    QMessageBox.information(self, "成功", "账号信息已更新！")
                    
                    # 通知父面板刷新
                    if self.parent_panel:
                        self.parent_panel._refresh_account_list()
                else:
                    QMessageBox.warning(self, "失败", "保存账号信息失败！")
                    
        except Exception as e:
            logger.error(f"编辑账号失败: {e}")
            QMessageBox.critical(self, "错误", f"编辑账号时出错：\n\n{e}")
    
    def _on_share(self):
        """分享"""
        QMessageBox.information(self, "功能开发中", "分享功能开发中...")
    
    def _on_delete(self):
        """删除"""
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除账号 {self.account_data.get('email', '')} 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            QMessageBox.information(self, "功能开发中", "删除功能开发中...")


class AugAccountPanel(QWidget):
    """Aug账号管理面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AugAccountPanel")
        
        self.accounts = []  # Aug账号列表
        
        self._setup_ui()
        self._load_test_data()  # 加载测试数据
    
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
        
        # ⭐ 刷新和批量注册按钮
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setProperty("secondary", True)
        refresh_btn.clicked.connect(self._on_refresh_list)
        title_row.addWidget(refresh_btn)
        
        batch_register_btn = QPushButton("📝 批量注册")
        batch_register_btn.setProperty("primary", True)
        batch_register_btn.clicked.connect(self._on_batch_register)
        title_row.addWidget(batch_register_btn)
        
        main_layout.addLayout(title_row)
        
        # 统计信息
        self.stats_label = QLabel("共 0 个Aug账号")
        self.stats_label.setStyleSheet("color: #7f8c8d; font-size: 13px; padding: 5px 0;")
        main_layout.addWidget(self.stats_label)
        
        # ⭐ 滚动区域（包含账号卡片网格）
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_area.setStyleSheet("background-color: transparent;")
        
        # 账号列表容器（使用网格布局）
        self.account_list_widget = QWidget()
        self.account_list_widget.setStyleSheet("background-color: transparent;")
        self.account_grid_layout = QGridLayout(self.account_list_widget)
        self.account_grid_layout.setSpacing(15)
        self.account_grid_layout.setContentsMargins(5, 5, 5, 5)
        
        scroll_area.setWidget(self.account_list_widget)
        
        main_layout.addWidget(scroll_area)
    
    def _load_test_data(self):
        """加载Aug账号数据"""
        try:
            from core.aug_account_storage import get_aug_storage
            
            storage = get_aug_storage()
            self.accounts = storage.get_all_accounts()
            
            logger.info(f"✅ 加载了 {len(self.accounts)} 个Aug账号")
            self._refresh_account_list()
            
        except Exception as e:
            logger.error(f"加载Aug账号失败: {e}")
            self.accounts = []
            self._refresh_account_list()
    
    def _refresh_account_list(self):
        """刷新账号列表显示"""
        # 清空现有卡片
        while self.account_grid_layout.count():
            item = self.account_grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 更新统计
        self.stats_label.setText(f"共 {len(self.accounts)} 个Aug账号")
        
        # 添加账号卡片（每行2列）
        row = 0
        col = 0
        
        for index, account in enumerate(self.accounts):
            card = AugAccountCard(account, index, self)  # 传递索引和父面板引用
            self.account_grid_layout.addWidget(card, row, col)
            
            col += 1
            if col >= 2:  # 每行2列
                col = 0
                row += 1
        
        # 添加占位符填充剩余空间
        self.account_grid_layout.setRowStretch(row + 1, 1)
        
        logger.info(f"✅ 刷新Aug账号列表: {len(self.accounts)} 个账号")
    
    def _on_refresh_list(self):
        """刷新账号列表"""
        QMessageBox.information(
            self,
            "功能开发中",
            "Aug账号刷新功能正在开发中...\n\n"
            "即将支持：\n"
            "• 刷新所有账号状态\n"
            "• 验证账号有效性\n"
            "• 更新账号信息"
        )
    
    def _on_batch_register(self):
        """批量注册Aug账号"""
        try:
            from gui.dialogs.aug_batch_register_dialog import AugBatchRegisterDialog
            
            # 打开批量注册对话框
            dialog = AugBatchRegisterDialog(self)
            dialog.registration_completed.connect(self._on_registration_completed)
            dialog.exec()
            
        except Exception as e:
            logger.error(f"打开批量注册对话框失败: {e}")
            QMessageBox.critical(self, "错误", f"打开批量注册对话框失败：\n\n{e}")
    
    def _on_registration_completed(self, count):
        """注册完成后刷新列表"""
        logger.info(f"批量注册完成，成功 {count} 个账号")
        # ⭐ 重新加载账号数据
        self._load_test_data()

