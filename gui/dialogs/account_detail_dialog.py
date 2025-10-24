#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账号详情对话框
显示账号的详细信息
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QGroupBox, QGridLayout, QApplication, QMessageBox,
    QWidget, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QWheelEvent
import jwt
from datetime import datetime


import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from gui.dialogs.animated_dialog import AnimatedDialog


class TokenTextEdit(QTextEdit):
    """支持横向滚动的Token文本编辑框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def wheelEvent(self, event: QWheelEvent):
        """鼠标滚轮事件 - 支持Shift+滚轮进行横向滚动"""
        modifiers = event.modifiers()
        
        # 如果按住Shift键，则进行横向滚动
        if modifiers == Qt.KeyboardModifier.ShiftModifier:
            # 获取横向滚动条
            h_scrollbar = self.horizontalScrollBar()
            # 根据滚轮方向滚动
            delta = event.angleDelta().y()
            if delta > 0:
                h_scrollbar.setValue(h_scrollbar.value() - 20)
            else:
                h_scrollbar.setValue(h_scrollbar.value() + 20)
        else:
            # 否则执行默认的纵向滚动
            super().wheelEvent(event)


class AccountDetailDialog(AnimatedDialog):
    """账号详情对话框"""
    
    def __init__(self, account_data: dict, parent=None, auto_refresh: bool = False):
        """
        初始化详情对话框
        
        Args:
            account_data: 账号数据
            parent: 父组件
            auto_refresh: 是否自动刷新数据
        """
        super().__init__(parent)
        
        self.setObjectName("AccountDetailDialog")  # 设置对象名用于CSS
        
        self.account_data = account_data
        self.auto_refresh = auto_refresh
        self.is_refreshing = False
        
        self.setWindowTitle(f"📊 账号详情 - {account_data.get('email', 'Unknown')}")
        self.setMinimumWidth(700)
        self.setMinimumHeight(700)  # 增加最小高度，确保Token信息组能完整显示
        self.setMaximumHeight(800)  # 设置最大高度，避免对话框过大
        
        self._setup_ui()
        
        # ⭐ 如果需要自动刷新，显示刷新提示
        if auto_refresh:
            self.show_refreshing_hint()
    
    def _setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题（邮箱 + 复制按钮）
        title_layout = QHBoxLayout()
        
        title_label = QLabel(f"📧 {self.account_data.get('email', 'Unknown')}")
        title_label.setProperty("heading", True)
        title_layout.addWidget(title_label)
        
        # 复制邮箱按钮
        copy_email_btn = QPushButton("📋 复制邮箱")
        copy_email_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        copy_email_btn.clicked.connect(self._copy_email)
        copy_email_btn.setMaximumWidth(100)
        title_layout.addWidget(copy_email_btn)
        
        title_layout.addStretch()
        
        layout.addLayout(title_layout)
        
        # ⭐ 刷新提示标签（默认隐藏）
        self.refresh_hint_label = QLabel("🔄 正在刷新最新数据...")
        self.refresh_hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.refresh_hint_label.setStyleSheet("""
            QLabel {
                background-color: rgba(139, 92, 246, 0.2);
                color: #8b5cf6;
                padding: 8px 15px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        self.refresh_hint_label.setVisible(False)
        layout.addWidget(self.refresh_hint_label)
        
        # 基本信息组
        basic_group = QGroupBox("基本信息")
        basic_layout = QGridLayout(basic_group)
        basic_layout.setSpacing(10)
        
        row = 0
        
        # ⭐ 用户 ID（隐藏）
        # basic_layout.addWidget(QLabel("用户 ID:"), row, 0)
        # self.user_id_label = QLabel(self.account_data.get('user_id', 'N/A'))
        # self.user_id_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        # basic_layout.addWidget(self.user_id_label, row, 1)
        # row += 1
        
        # 套餐类型
        basic_layout.addWidget(QLabel("套餐类型:"), row, 0)
        self.membership_label = QLabel(self.account_data.get('membership_type', 'free').upper())
        basic_layout.addWidget(self.membership_label, row, 1)
        row += 1
        
        # 剩余天数
        basic_layout.addWidget(QLabel("剩余天数:"), row, 0)
        self.days_label_detail = QLabel(f"{self.account_data.get('days_remaining', 0)} 天")
        basic_layout.addWidget(self.days_label_detail, row, 1)
        row += 1
        
        # ⭐ 费用信息：优先显示真实费用，否则显示估算
        membership_type = self.account_data.get('membership_type', 'free').lower()
        total_cost = self.account_data.get('total_cost')  # 真实费用
        
        if membership_type != 'free':
            from utils.cost_calculator import calculate_cost_info, format_cost, SUBSCRIPTION_PRICES
            
            monthly_cost = SUBSCRIPTION_PRICES.get(membership_type, 20)
            
            basic_layout.addWidget(QLabel("订阅费用:"), row, 0)
            self.monthly_cost_label = QLabel(f"${monthly_cost}/月")
            basic_layout.addWidget(self.monthly_cost_label, row, 1)
            row += 1
            
            basic_layout.addWidget(QLabel("已使用:"), row, 0)
            if total_cost is not None:
                # 有真实费用数据
                self.used_cost_label = QLabel(f"${total_cost:.2f}")
                self.used_cost_label.setStyleSheet(f"color: #e81123; font-weight: bold; font-size: 13px;")
                total_tokens = self.account_data.get('total_tokens', 0)
                if total_tokens > 0:
                    tokens_text = f" ({total_tokens/10000:.1f}万tokens)" if total_tokens >= 10000 else f" ({total_tokens} tokens)"
                else:
                    tokens_text = ""
                self.used_cost_label.setToolTip(f"真实费用{tokens_text}")
            else:
                # 估算费用
                cost_info = calculate_cost_info(self.account_data)
                used_value = cost_info['used_value']
                self.used_cost_label = QLabel(f"~{format_cost(used_value)}")
                self.used_cost_label.setStyleSheet(f"color: #ffa500; font-weight: bold; font-size: 13px;")
                self.used_cost_label.setToolTip("估算费用（基于使用率）")
            basic_layout.addWidget(self.used_cost_label, row, 1)
            row += 1
            
            basic_layout.addWidget(QLabel("剩余价值:"), row, 0)
            if total_cost is not None:
                remaining_value = monthly_cost - total_cost
                self.remaining_label = QLabel(f"${remaining_value:.2f}")
                self.remaining_label.setToolTip("剩余价值（基于真实费用）")
            else:
                cost_info = calculate_cost_info(self.account_data)
                remaining_value = cost_info['remaining_value']
                self.remaining_label = QLabel(f"~{format_cost(remaining_value)}")
                self.remaining_label.setToolTip("估算剩余（基于使用率）")
            self.remaining_label.setStyleSheet(f"color: #107c10; font-weight: bold; font-size: 13px;")
            basic_layout.addWidget(self.remaining_label, row, 1)
            row += 1
        else:
            # ⭐ Free账号时，初始化为None，避免update_data时报错
            self.monthly_cost_label = None
            self.used_cost_label = None
            self.remaining_label = None
        
        # ⭐ 使用详情（隐藏）
        # basic_layout.addWidget(QLabel("使用量:"), row, 0)
        # used = self.account_data.get('used', 0)
        # limit = self.account_data.get('limit_value', 1000)
        # usage_percent = self.account_data.get('usage_percent', 0)
        # self.used_label = QLabel(f"{used} / {limit}")
        # basic_layout.addWidget(self.used_label, row, 1)
        # row += 1
        
        # ⭐ 不调用API，避免卡顿
        
        # 创建时间
        basic_layout.addWidget(QLabel("创建时间:"), row, 0)
        created_at = self.account_data.get('created_at', 'N/A')
        if created_at and created_at != 'N/A':
            try:
                created_dt = datetime.fromisoformat(created_at)
                created_at = created_dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass
        self.created_label = QLabel(created_at)
        basic_layout.addWidget(self.created_label, row, 1)
        row += 1
        
        # 最后使用
        basic_layout.addWidget(QLabel("最后使用:"), row, 0)
        last_used = self.account_data.get('last_used', '从未使用')
        if last_used and last_used != '从未使用':
            try:
                last_dt = datetime.fromisoformat(last_used)
                last_used = last_dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass
        self.last_used_label = QLabel(last_used)
        basic_layout.addWidget(self.last_used_label, row, 1)
        
        layout.addWidget(basic_group)
        
        # Token 信息组（添加滚动区域）
        token_group = QGroupBox("Token 信息  (整个框可滚动查看)")
        token_group.setObjectName("TokenInfoGroup")  # 设置对象名
        token_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #3a3a3a;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        token_main_layout = QVBoxLayout(token_group)
        
        # 创建滚动区域
        from PyQt6.QtWidgets import QScrollArea
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_area.setMinimumHeight(350)  # 减小高度，确保能出现滚动条
        scroll_area.setMaximumHeight(400)  # 限制最大高度
        
        # 设置滚动条策略 - 始终显示垂直滚动条
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)  # 始终显示垂直滚动条
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # ⭐ 设置滚动区域的样式
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #2b2b2b;
                width: 12px;
                border-radius: 6px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background: #5a5a5a;
                min-height: 30px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #7a7a7a;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        scroll_content = QWidget()
        scroll_content.setObjectName("TokenScrollContent")  # 设置对象名用于样式
        token_layout = QVBoxLayout(scroll_content)
        token_layout.setContentsMargins(10, 10, 10, 10)  # 增加内边距
        token_layout.setSpacing(15)  # 增加元素间距
        
        scroll_area.setWidget(scroll_content)
        token_main_layout.addWidget(scroll_area)
        
        # AccessToken（加密显示）
        access_label_layout = QHBoxLayout()
        access_label_layout.addWidget(QLabel("AccessToken:"))
        
        # 添加提示标签
        tip_label = QLabel("(滚轮可上下滚动)")
        tip_label.setStyleSheet("color: #666; font-size: 11px; font-style: italic;")
        access_label_layout.addWidget(tip_label)
        
        access_label_layout.addStretch()
        token_layout.addLayout(access_label_layout)
        
        self.access_token_text = QTextEdit()  # 使用普通QTextEdit
        self.access_token_text.setObjectName("AccessTokenText")  # 设置对象名
        self.access_token_text.setFixedHeight(100)  # 固定高度
        self.access_token_text.setReadOnly(True)
        
        # ⭐ 设置滑动条策略 - 允许双向滑动
        self.access_token_text.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # 关闭横向滚动条
        self.access_token_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)  # 自动显示纵向滚动条
        # 启用自动换行，这样可以看到完整内容
        self.access_token_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)  # 按窗口宽度换行
        # 设置字体
        self.access_token_text.setFont(QFont("Consolas", 9))
        
        # ⭐ 设置样式，美化滑动条和外观
        self.access_token_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 8px;
                background-color: rgba(255, 255, 255, 0.05);
                color: #e0e0e0;
            }
            /* 滑动条样式 */
            QScrollBar:horizontal {
                border: none;
                background: #2b2b2b;
                height: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal {
                background: #5a5a5a;
                min-width: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #7a7a7a;
            }
            QScrollBar:vertical {
                border: none;
                background: #2b2b2b;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #5a5a5a;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #7a7a7a;
            }
            QScrollBar::add-line, QScrollBar::sub-line {
                border: none;
                background: none;
            }
        """)
        
        access_token = self.account_data.get('access_token', '')
        
        # ⭐ 使用加密显示，不暴露真实Token
        if access_token:
            from utils.crypto import get_crypto_manager
            crypto = get_crypto_manager()
            try:
                encrypted_token = crypto.encrypt(access_token)
                self.access_token_text.setPlainText(encrypted_token)
            except:
                # 如果加密失败，显示星号
                self.access_token_text.setPlainText('*' * 100)
        else:
            self.access_token_text.setPlainText('未设置')
        
        token_layout.addWidget(self.access_token_text)
        
        # Token 解析信息
        if access_token:
            token_info = self._parse_token(access_token)
            if token_info:
                info_text = (
                    f"类型: {token_info.get('type', 'unknown')} | "
                    f"过期时间: {token_info.get('expires_at', 'N/A')}"
                )
                token_info_label = QLabel(info_text)
                token_info_label.setProperty("subtitle", True)
                token_layout.addWidget(token_info_label)
        
        # SessionToken（明文显示）⭐ 新增
        session_label_layout = QHBoxLayout()
        session_label = QLabel("SessionToken:")
        session_label.setStyleSheet("margin-top: 10px;")
        session_label_layout.addWidget(session_label)
        
        # 添加提示标签
        session_tip_label = QLabel("(滚轮可上下滚动)")
        session_tip_label.setStyleSheet("color: #666; font-size: 11px; font-style: italic; margin-top: 10px;")
        session_label_layout.addWidget(session_tip_label)
        
        # 添加编辑/保存按钮
        self.edit_session_btn = QPushButton("✏️ 编辑")
        self.edit_session_btn.setMaximumWidth(80)
        self.edit_session_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 4px 8px;
                border-radius: 3px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.edit_session_btn.clicked.connect(self._toggle_session_edit)
        session_label_layout.addWidget(self.edit_session_btn)
        
        self.save_session_btn = QPushButton("💾 保存")
        self.save_session_btn.setMaximumWidth(80)
        self.save_session_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 4px 8px;
                border-radius: 3px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        self.save_session_btn.clicked.connect(self._save_session_token)
        self.save_session_btn.hide()  # 默认隐藏保存按钮
        session_label_layout.addWidget(self.save_session_btn)
        
        session_label_layout.addStretch()
        token_layout.addLayout(session_label_layout)
        
        # 尝试多个字段名获取 SessionToken
        session_token = (
            self.account_data.get('session_token_plain') or  # 内存中的明文
            self.account_data.get('session_token') or  # 数据库中的字段
            ''
        )
        
        # 如果是加密的，尝试解密
        if session_token and not session_token.startswith('user_'):
            try:
                from utils.crypto import get_crypto_manager
                crypto = get_crypto_manager()
                decrypted = crypto.decrypt(session_token)
                if decrypted:
                    session_token = decrypted
            except:
                pass
        
        self.session_token_text = QTextEdit()  # 使用普通QTextEdit
        self.session_token_text.setObjectName("SessionTokenText")  # 设置对象名
        self.session_token_text.setPlainText(session_token if session_token else '未设置')
        self.session_token_text.setReadOnly(True)
        self.session_token_text.setFixedHeight(120)  # 固定高度
        self.session_token_text.setFont(QFont("Consolas", 9))
        
        # ⭐ 设置滑动条策略 - 主要使用垂直滚动
        self.session_token_text.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # 关闭横向滚动条
        self.session_token_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)  # 自动显示纵向滚动条
        # 启用自动换行，确保可以看到完整内容
        self.session_token_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)  # 按窗口宽度换行
        
        # ⭐ 设置样式，美化滑动条
        self.session_token_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 8px;
                background-color: rgba(255, 255, 255, 0.05);
            }
            QTextEdit:focus {
                border: 1px solid #4a90e2;
            }
            /* 滑动条样式 */
            QScrollBar:horizontal {
                border: none;
                background: #2b2b2b;
                height: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal {
                background: #5a5a5a;
                min-width: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #7a7a7a;
            }
            QScrollBar:vertical {
                border: none;
                background: #2b2b2b;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #5a5a5a;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #7a7a7a;
            }
        """)
        
        token_layout.addWidget(self.session_token_text)
        
        # 保存原始的SessionToken用于检测是否有变化
        self.original_session_token = session_token
        
        # SessionToken 解析信息
        if session_token and '::' in session_token:
            try:
                # 提取 JWT 部分
                jwt_part = session_token.split('::')[1]
                payload = jwt.decode(jwt_part, options={"verify_signature": False})
                token_type = payload.get('type', 'unknown')
                
                # 获取更多JWT信息
                exp = payload.get('exp')
                exp_str = 'N/A'
                if exp:
                    try:
                        from datetime import datetime
                        exp_dt = datetime.fromtimestamp(exp)
                        exp_str = exp_dt.strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        pass
                
                # 创建信息容器
                info_widget = QWidget()
                info_layout = QVBoxLayout(info_widget)
                info_layout.setContentsMargins(0, 10, 0, 10)
                
                info_label1 = QLabel(f"Token类型: {token_type}")
                info_label1.setStyleSheet("color: #999; padding: 5px;")
                info_layout.addWidget(info_label1)
                
                info_label2 = QLabel(f"过期时间: {exp_str}")
                info_label2.setStyleSheet("color: #999; padding: 5px;")
                info_layout.addWidget(info_label2)
                
                token_layout.addWidget(info_widget)
            except:
                pass
        
        # 添加一个空白区域，确保内容高度足够触发滚动
        spacer = QWidget()
        spacer.setMinimumHeight(50)
        token_layout.addWidget(spacer)
        
        # 添加提示信息
        hint_label = QLabel("💡 提示: 使用鼠标滚轮可以上下滚动查看更多内容")
        hint_label.setStyleSheet("""
            color: #666;
            font-size: 11px;
            padding: 10px;
            background-color: rgba(255, 255, 255, 0.03);
            border-radius: 4px;
        """)
        hint_label.setWordWrap(True)
        token_layout.addWidget(hint_label)
        
        # 再添加一些底部空间
        bottom_spacer = QWidget()
        bottom_spacer.setMinimumHeight(30)
        token_layout.addWidget(bottom_spacer)
        
        layout.addWidget(token_group)
        
        # 底部：关闭按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        copy_token_btn = QPushButton("📋 复制 AccessToken")
        copy_token_btn.setProperty("secondary", True)
        copy_token_btn.clicked.connect(self._copy_token)
        button_layout.addWidget(copy_token_btn)
        
        copy_session_btn = QPushButton("📋 复制 SessionToken")
        copy_session_btn.setProperty("secondary", True)
        copy_session_btn.clicked.connect(self._copy_session_token)
        button_layout.addWidget(copy_session_btn)
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _parse_token(self, token: str) -> dict:
        """
        解析 JWT Token
        
        Args:
            token: JWT Token
            
        Returns:
            dict: Token 信息
        """
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            
            exp = payload.get('exp')
            expires_at = 'N/A'
            if exp:
                try:
                    exp_dt = datetime.fromtimestamp(exp)
                    expires_at = exp_dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    pass
            
            return {
                'type': payload.get('type', 'unknown'),
                'expires_at': expires_at
            }
        except:
            return {}
    
    def _copy_token(self):
        """复制加密后的 Token 到剪贴板"""
        from PyQt6.QtWidgets import QApplication
        
        # ⭐ 复制加密后的Token，不复制原始Token
        encrypted_token = self.access_token_text.toPlainText()
        if encrypted_token and encrypted_token != '未设置':
            clipboard = QApplication.clipboard()
            clipboard.setText(encrypted_token)
            
            # 临时提示
            from PyQt6.QtWidgets import QMessageBox
            # 显示 Toast 提示（2秒自动消失，无声）
            from gui.widgets.toast_notification import show_toast
            show_toast(self, "✅ 加密 Token 已复制到剪贴板", duration=2000, success=True)
    
    def show_refreshing_hint(self):
        """显示刷新提示"""
        if hasattr(self, 'refresh_hint_label'):
            self.refresh_hint_label.setVisible(True)
            self.is_refreshing = True
    
    def hide_refreshing_hint(self):
        """隐藏刷新提示"""
        if hasattr(self, 'refresh_hint_label'):
            self.refresh_hint_label.setVisible(False)
            self.is_refreshing = False
    
    def update_data(self, account_data: dict):
        """
        更新详情对话框的数据（只更新文本，不重建UI）
        
        Args:
            account_data: 新的账号数据
        """
        try:
            self.account_data = account_data
            
            # ⭐ 隐藏刷新提示
            self.hide_refreshing_hint()
            
            # ⭐ 只更新各个标签的文本内容（不重建UI）
            # 更新标题
            self.setWindowTitle(f"📊 账号详情 - {account_data.get('email', 'Unknown')}")
            
            # 更新基本信息
            # ⭐ 用户ID已隐藏
            # if hasattr(self, 'user_id_label'):
            #     self.user_id_label.setText(account_data.get('user_id', 'N/A'))
            
            if hasattr(self, 'membership_label'):
                self.membership_label.setText(account_data.get('membership_type', 'free').upper())
            
            if hasattr(self, 'days_label_detail'):
                self.days_label_detail.setText(f"{account_data.get('days_remaining', 0)} 天")
            
            # 更新费用信息
            membership_type = account_data.get('membership_type', 'free').lower()
            total_cost = account_data.get('total_cost')
            
            if membership_type != 'free':
                from utils.cost_calculator import calculate_cost_info, format_cost, SUBSCRIPTION_PRICES
                monthly_cost = SUBSCRIPTION_PRICES.get(membership_type, 20)
                
                if hasattr(self, 'monthly_cost_label') and self.monthly_cost_label:
                    self.monthly_cost_label.setText(f"${monthly_cost}/月")
                
                if hasattr(self, 'used_cost_label') and self.used_cost_label:
                    if total_cost is not None:
                        self.used_cost_label.setText(f"${total_cost:.2f}")
                        self.used_cost_label.setStyleSheet(f"color: #e81123; font-weight: bold; font-size: 13px;")
                        total_tokens = account_data.get('total_tokens', 0)
                        if total_tokens > 0:
                            tokens_text = f" ({total_tokens/10000:.1f}万tokens)" if total_tokens >= 10000 else f" ({total_tokens} tokens)"
                        else:
                            tokens_text = ""
                        self.used_cost_label.setToolTip(f"真实费用{tokens_text}")
                    else:
                        cost_info = calculate_cost_info(account_data)
                        used_value = cost_info['used_value']
                        self.used_cost_label.setText(f"~{format_cost(used_value)}")
                        self.used_cost_label.setStyleSheet(f"color: #ffa500; font-weight: bold; font-size: 13px;")
                
                if hasattr(self, 'remaining_label') and self.remaining_label:
                    if total_cost is not None:
                        remaining_value = monthly_cost - total_cost
                        self.remaining_label.setText(f"${remaining_value:.2f}")
                    else:
                        cost_info = calculate_cost_info(account_data)
                        remaining_value = cost_info['remaining_value']
                        self.remaining_label.setText(f"~{format_cost(remaining_value)}")
            
            # ⭐ 使用量已隐藏
            # if hasattr(self, 'used_label'):
            #     used = account_data.get('used', 0)
            #     limit = account_data.get('limit_value', 1000)
            #     self.used_label.setText(f"{used} / {limit}")
            
            # 更新时间
            if hasattr(self, 'created_label'):
                created_at = account_data.get('created_at', 'N/A')
                if created_at and created_at != 'N/A':
                    try:
                        created_dt = datetime.fromisoformat(created_at)
                        created_at = created_dt.strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        pass
                self.created_label.setText(created_at)
            
            if hasattr(self, 'last_used_label'):
                last_used = account_data.get('last_used', '从未使用')
                if last_used and last_used != '从未使用':
                    try:
                        last_dt = datetime.fromisoformat(last_used)
                        last_used = last_dt.strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        pass
                self.last_used_label.setText(last_used)
            
        except Exception as e:
            from utils.logger import get_logger
            logger = get_logger("account_detail_dialog")
            logger.error(f"更新详情数据失败: {e}")
    
    def _copy_email(self):
        """复制邮箱到剪贴板"""
        try:
            email = self.account_data.get('email', '')
            if email:
                clipboard = QApplication.clipboard()
                clipboard.setText(email)
                
                # 显示 Toast 提示（2秒自动消失，无声）
                from gui.widgets.toast_notification import show_toast
                show_toast(self, f"✅ 邮箱已复制！\n{email}", duration=2000, success=True)
            else:
                from gui.widgets.toast_notification import show_toast
                show_toast(self, "邮箱地址为空", duration=2000, success=False)
        except Exception as e:
            from gui.widgets.toast_notification import show_toast
            show_toast(self, f"复制失败：{str(e)}", duration=2000, success=False)
    
    def _copy_session_token(self):
        """复制SessionToken到剪贴板"""
        try:
            session_token = self.session_token_text.toPlainText().strip()
            
            if not session_token or session_token == '未设置':
                from gui.widgets.toast_notification import show_toast
                show_toast(self, "SessionToken 未设置", duration=2000, success=False)
                return
            
            clipboard = QApplication.clipboard()
            clipboard.setText(session_token)
            
            # 显示 Toast 提示（2秒自动消失，无声）
            from gui.widgets.toast_notification import show_toast
            show_toast(self, "✅ SessionToken 已复制到剪贴板！", duration=2000, success=True)
            
        except Exception as e:
            from utils.logger import get_logger
            logger = get_logger("account_detail_dialog")
            logger.error(f"复制SessionToken失败: {e}")
            from gui.widgets.toast_notification import show_toast
            show_toast(self, f"复制失败：{str(e)}", duration=2000, success=False)
    
    def _toggle_session_edit(self):
        """切换SessionToken编辑模式"""
        if self.session_token_text.isReadOnly():
            # 进入编辑模式
            self.session_token_text.setReadOnly(False)
            
            # 如果当前是"未设置"，清空文本框
            if self.session_token_text.toPlainText() == '未设置':
                self.session_token_text.clear()
            
            # 修改按钮状态
            self.edit_session_btn.setText("❌ 取消")
            self.edit_session_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
            
            # 显示保存按钮
            self.save_session_btn.show()
            
            # 改变文本框样式，提示用户正在编辑
            self.session_token_text.setStyleSheet("""
                QTextEdit {
                    border: 2px solid #3498db;
                    border-radius: 4px;
                    padding: 8px;
                    background-color: rgba(52, 152, 219, 0.1);
                    color: #e0e0e0;
                }
                /* 保持滑动条样式 */
                QScrollBar:horizontal {
                    border: none;
                    background: #2b2b2b;
                    height: 10px;
                    border-radius: 5px;
                }
                QScrollBar::handle:horizontal {
                    background: #5a5a5a;
                    min-width: 20px;
                    border-radius: 5px;
                }
                QScrollBar::handle:horizontal:hover {
                    background: #7a7a7a;
                }
                QScrollBar:vertical {
                    border: none;
                    background: #2b2b2b;
                    width: 10px;
                    border-radius: 5px;
                }
                QScrollBar::handle:vertical {
                    background: #5a5a5a;
                    min-height: 20px;
                    border-radius: 5px;
                }
                QScrollBar::handle:vertical:hover {
                    background: #7a7a7a;
                }
                QScrollBar::add-line, QScrollBar::sub-line {
                    border: none;
                    background: none;
                }
            """)
            
            # 聚焦到文本框
            self.session_token_text.setFocus()
            
        else:
            # 退出编辑模式（取消编辑）
            self.session_token_text.setReadOnly(True)
            
            # 恢复原始内容
            self.session_token_text.setPlainText(
                self.original_session_token if self.original_session_token else '未设置'
            )
            
            # 恢复按钮状态
            self.edit_session_btn.setText("✏️ 编辑")
            self.edit_session_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
            """)
            
            # 隐藏保存按钮
            self.save_session_btn.hide()
            
            # 恢复文本框样式
            self.session_token_text.setStyleSheet("""
                QTextEdit {
                    border: 1px solid #3a3a3a;
                    border-radius: 4px;
                    padding: 8px;
                    background-color: rgba(255, 255, 255, 0.05);
                }
                QTextEdit:focus {
                    border: 1px solid #4a90e2;
                }
                /* 滑动条样式 */
                QScrollBar:horizontal {
                    border: none;
                    background: #2b2b2b;
                    height: 10px;
                    border-radius: 5px;
                }
                QScrollBar::handle:horizontal {
                    background: #5a5a5a;
                    min-width: 20px;
                    border-radius: 5px;
                }
                QScrollBar::handle:horizontal:hover {
                    background: #7a7a7a;
                }
                QScrollBar:vertical {
                    border: none;
                    background: #2b2b2b;
                    width: 10px;
                    border-radius: 5px;
                }
                QScrollBar::handle:vertical {
                    background: #5a5a5a;
                    min-height: 20px;
                    border-radius: 5px;
                }
                QScrollBar::handle:vertical:hover {
                    background: #7a7a7a;
                }
                QScrollBar::add-line, QScrollBar::sub-line {
                    border: none;
                    background: none;
                }
            """)
    
    def _save_session_token(self):
        """保存SessionToken"""
        try:
            new_token = self.session_token_text.toPlainText().strip()
            
            # 验证Token格式
            if not new_token:
                QMessageBox.warning(self, "提示", "SessionToken不能为空")
                return
            
            # 基本格式验证（SessionToken通常以user_开头，包含两个::分隔的部分）
            if not new_token.startswith('user_'):
                reply = QMessageBox.question(
                    self,
                    "确认",
                    "SessionToken通常以'user_'开头。\n您确定要保存这个Token吗？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            # 更新账号数据
            from core.account_storage import get_storage
            from utils.crypto import get_crypto_manager
            
            # 使用全局存储实例（与主窗口一致）
            storage = get_storage()
            crypto = get_crypto_manager()
            
            # 加密Token
            encrypted_token = crypto.encrypt(new_token)
            
            # 更新账号信息
            account_id = self.account_data.get('id')
            if account_id:
                # 更新数据
                self.account_data['session_token'] = encrypted_token
                self.account_data['session_token_plain'] = new_token  # 保存明文用于显示
                
                # 保存到数据库
                success = storage.update_account(
                    account_id,  # 使用account_id而不是email
                    {
                        'session_token': encrypted_token  # 只需要session_token字段
                    }
                )
                
                if success:
                    # 保存新的原始值
                    self.original_session_token = new_token
                    
                    # 退出编辑模式
                    self.session_token_text.setReadOnly(True)
                    
                    # 恢复按钮状态
                    self.edit_session_btn.setText("✏️ 编辑")
                    self.edit_session_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #3498db;
                            color: white;
                            padding: 4px 8px;
                            border-radius: 3px;
                            font-size: 11px;
                        }
                        QPushButton:hover {
                            background-color: #2980b9;
                        }
                    """)
                    
                    # 隐藏保存按钮
                    self.save_session_btn.hide()
                    
                    # 恢复文本框样式
                    self.session_token_text.setStyleSheet("""
                        QTextEdit {
                            border: 1px solid #3a3a3a;
                            border-radius: 4px;
                            padding: 8px;
                            background-color: rgba(255, 255, 255, 0.05);
                        }
                        QTextEdit:focus {
                            border: 1px solid #4a90e2;
                        }
                        /* 滑动条样式 */
                        QScrollBar:horizontal {
                            border: none;
                            background: #2b2b2b;
                            height: 10px;
                            border-radius: 5px;
                        }
                        QScrollBar::handle:horizontal {
                            background: #5a5a5a;
                            min-width: 20px;
                            border-radius: 5px;
                        }
                        QScrollBar::handle:horizontal:hover {
                            background: #7a7a7a;
                        }
                        QScrollBar:vertical {
                            border: none;
                            background: #2b2b2b;
                            width: 10px;
                            border-radius: 5px;
                        }
                        QScrollBar::handle:vertical {
                            background: #5a5a5a;
                            min-height: 20px;
                            border-radius: 5px;
                        }
                        QScrollBar::handle:vertical:hover {
                            background: #7a7a7a;
                        }
                        QScrollBar::add-line, QScrollBar::sub-line {
                            border: none;
                            background: none;
                        }
                    """)
                    
                    # 更新SessionToken解析信息
                    if new_token and '::' in new_token:
                        # 这里可以更新解析信息的显示
                        pass
                    
                    QMessageBox.information(self, "成功", "✅ SessionToken已保存成功！")
                    
                    # 发送信号通知主窗口更新（如果需要）
                    if hasattr(self.parent(), 'refresh_accounts'):
                        self.parent().refresh_accounts()
                    
                else:
                    QMessageBox.critical(self, "错误", "保存失败，请重试")
            else:
                QMessageBox.critical(self, "错误", "账号ID无效")
                
        except Exception as e:
            from utils.logger import get_logger
            logger = get_logger("account_detail_dialog")
            logger.error(f"保存SessionToken失败: {e}")
            QMessageBox.critical(self, "错误", f"保存失败：\n{str(e)}")


