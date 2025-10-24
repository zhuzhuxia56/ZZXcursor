#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账号切换确认对话框
账号切换确认界面
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QCheckBox, QGroupBox, QFrame, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from typing import Dict, Any

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from gui.dialogs.animated_dialog import AnimatedDialog


class SwitchAccountDialog(AnimatedDialog):
    """账号切换确认对话框"""
    
    # 信号：用户确认切换，携带切换选项
    confirmed = pyqtSignal(dict)
    
    def __init__(self, account: Dict[str, Any], parent=None):
        """
        初始化对话框
        
        Args:
            account: 要切换到的账号信息
            parent: 父窗口
        """
        super().__init__(parent)
        self.account = account
        self.switch_options = {
            'machine_id_mode': 'generate_new',  # 默认：生成新机器码
            'reset_cursor_config': False,
        }
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置 UI"""
        self.setWindowTitle("切换账号确认")
        self.setMinimumWidth(450)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 标题和账号信息
        self._add_account_info(layout)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        # 切换选项
        self._add_switch_options(layout)
        
        # ⭐ 已移除警告信息横幅
        # self._add_warning(layout)
        
        # 按钮
        self._add_buttons(layout)
    
    def _add_account_info(self, layout: QVBoxLayout):
        """添加账号信息显示"""
        # 标题
        title_label = QLabel("🔄 确定要切换账号吗？")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # 账号信息分组
        info_group = QGroupBox("目标账号")
        info_layout = QVBoxLayout(info_group)
        
        # 邮箱
        email = self.account.get('email', '未知')
        email_label = QLabel(f"📧 邮箱: <b>{email}</b>")
        email_label.setTextFormat(Qt.TextFormat.RichText)
        info_layout.addWidget(email_label)
        
        # 套餐类型
        membership = self.account.get('membership_type', 'free').upper()
        membership_color = self._get_membership_color(membership)
        membership_label = QLabel(f"🎫 套餐: <b style='color:{membership_color}'>{membership}</b>")
        membership_label.setTextFormat(Qt.TextFormat.RichText)
        info_layout.addWidget(membership_label)
        
        # 剩余天数（如果有）
        days_remaining = self.account.get('days_remaining', 0)
        if days_remaining > 0:
            days_label = QLabel(f"⏰ 剩余: <b>{days_remaining}</b> 天")
            days_label.setTextFormat(Qt.TextFormat.RichText)
            info_layout.addWidget(days_label)
        
        layout.addWidget(info_group)
    
    def _add_switch_options(self, layout: QVBoxLayout):
        """添加切换选项"""
        options_group = QGroupBox("切换选项")
        options_layout = QVBoxLayout(options_group)
        
        # === 机器码选项 ===
        machine_label = QLabel("<b>🔑 机器码管理</b>")
        machine_label.setTextFormat(Qt.TextFormat.RichText)
        options_layout.addWidget(machine_label)
        
        # 单选按钮组
        self.machine_button_group = QButtonGroup(self)
        
        # 选项1：使用绑定的机器码
        self.use_bound_radio = QRadioButton("使用该账号绑定的机器码")
        has_machine_info = bool(self.account.get('machine_info'))
        
        if has_machine_info:
            from core.machine_id_generator import MachineIdGenerator
            machine_info = self.account.get('machine_info', {})
            preview = MachineIdGenerator.get_machine_id_preview(machine_info, 35)
            self.use_bound_radio.setToolTip(f"使用账号注册时的机器码\n预览: {preview}")
        else:
            self.use_bound_radio.setEnabled(False)
            self.use_bound_radio.setToolTip("该账号没有绑定机器码信息")
        
        self.machine_button_group.addButton(self.use_bound_radio, 1)
        options_layout.addWidget(self.use_bound_radio)
        
        # 选项2：随机生成新的机器码（默认）
        self.generate_new_radio = QRadioButton("随机生成新的机器码（推荐）")
        self.generate_new_radio.setChecked(True)  # 默认选中
        self.generate_new_radio.setToolTip(
            "每次切换生成全新的设备标识\n"
            "推荐使用，可避免账号关联"
        )
        self.machine_button_group.addButton(self.generate_new_radio, 2)
        options_layout.addWidget(self.generate_new_radio)
        
        # 选项3：完全重置
        self.reset_all_radio = QRadioButton("完全重置 Cursor 配置")
        self.reset_all_radio.setToolTip(
            "清空所有机器码和配置\n"
            "仅在出现问题时使用"
        )
        self.machine_button_group.addButton(self.reset_all_radio, 3)
        options_layout.addWidget(self.reset_all_radio)
        
        # 说明文字
        note_label = QLabel(
            "<small><i>💡 提示: 生成新机器码可以避免多个账号被关联到同一设备</i></small>"
        )
        note_label.setTextFormat(Qt.TextFormat.RichText)
        note_label.setWordWrap(True)
        note_label.setStyleSheet("color: #666; margin-top: 5px;")
        options_layout.addWidget(note_label)
        
        # === 进程管理选项 ===
        process_label = QLabel("<b>🔄 进程管理</b>")
        process_label.setTextFormat(Qt.TextFormat.RichText)
        process_label.setStyleSheet("margin-top: 10px;")
        options_layout.addWidget(process_label)
        
        # 自动关闭 Cursor
        self.auto_kill_checkbox = QCheckBox("自动关闭 Cursor 进程（推荐）")
        self.auto_kill_checkbox.setChecked(True)
        self.auto_kill_checkbox.setToolTip("切换前自动关闭 Cursor，避免冲突")
        options_layout.addWidget(self.auto_kill_checkbox)
        
        # 自动重启 Cursor
        self.auto_restart_checkbox = QCheckBox("切换后自动重启 Cursor")
        self.auto_restart_checkbox.setChecked(True)
        self.auto_restart_checkbox.setToolTip("切换完成后自动启动 Cursor")
        options_layout.addWidget(self.auto_restart_checkbox)
        
        layout.addWidget(options_group)
    
    def _add_warning(self, layout: QVBoxLayout):
        """添加警告信息"""
        warning_label = QLabel(
            "⚠️ <b>注意</b>: 切换账号前请确保 <b>Cursor 已完全关闭</b>！\n"
            "否则可能导致切换失败或配置异常。"
        )
        warning_label.setTextFormat(Qt.TextFormat.RichText)
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet(
            "background-color: #fff3cd; "
            "color: #856404; "
            "padding: 10px; "
            "border-radius: 4px; "
            "border: 1px solid #ffeaa7;"
        )
        layout.addWidget(warning_label)
    
    def _add_buttons(self, layout: QVBoxLayout):
        """添加按钮"""
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.setMinimumWidth(100)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        # 确认按钮
        confirm_btn = QPushButton("确认切换")
        confirm_btn.setMinimumWidth(100)
        confirm_btn.setDefault(True)
        confirm_btn.setStyleSheet(
            "QPushButton {"
            "  background-color: #4CAF50; "
            "  color: white; "
            "  font-weight: bold; "
            "  padding: 8px;"
            "}"
            "QPushButton:hover {"
            "  background-color: #45a049;"
            "}"
        )
        confirm_btn.clicked.connect(self._on_confirm)
        button_layout.addWidget(confirm_btn)
        
        layout.addLayout(button_layout)
    
    def _on_confirm(self):
        """确认按钮点击"""
        # 确定机器码模式
        machine_id_mode = 'generate_new'  # 默认
        reset_cursor_config = False
        
        if self.use_bound_radio.isChecked():
            machine_id_mode = 'use_bound'
        elif self.generate_new_radio.isChecked():
            machine_id_mode = 'generate_new'
        elif self.reset_all_radio.isChecked():
            machine_id_mode = 'reset_all'
            reset_cursor_config = True  # 完全重置时也重置配置
        
        # 收集用户选择的选项
        self.switch_options = {
            'machine_id_mode': machine_id_mode,
            'reset_cursor_config': reset_cursor_config,
            'auto_kill': self.auto_kill_checkbox.isChecked(),      # 自动关闭
            'auto_restart': self.auto_restart_checkbox.isChecked()  # 自动重启
        }
        
        # 发送信号
        self.confirmed.emit(self.switch_options)
        
        # 关闭对话框
        self.accept()
    
    def _get_membership_color(self, membership: str) -> str:
        """根据套餐类型获取颜色"""
        membership_lower = membership.lower()
        
        if 'pro' in membership_lower or 'trial' in membership_lower:
            return '#4CAF50'  # 绿色
        elif 'team' in membership_lower:
            return '#2196F3'  # 蓝色
        elif 'enterprise' in membership_lower:
            return '#9C27B0'  # 紫色
        else:
            return '#999'  # 灰色
    
    def get_switch_options(self) -> Dict[str, bool]:
        """获取切换选项"""
        return self.switch_options


