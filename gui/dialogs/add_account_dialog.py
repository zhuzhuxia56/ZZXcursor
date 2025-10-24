#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
添加账号对话框
通过 AccessToken 直接添加账号
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTextEdit, QGroupBox, QFrame, QLineEdit,
    QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont
from typing import Optional, Dict, Any
import json
import base64

from utils.logger import get_logger

logger = get_logger("add_account_dialog")


class BatchImportThread(QThread):
    """批量导入线程"""
    
    # 信号
    log_signal = pyqtSignal(str)  # 日志信号
    progress_signal = pyqtSignal(int, int)  # 进度信号 (当前, 总数)
    finished_signal = pyqtSignal(int, int)  # 完成信号 (成功数, 失败数)
    
    def __init__(self, tokens: list, parent=None):
        super().__init__(parent)
        self.tokens = tokens
    
    def run(self):
        """批量导入AccessToken"""
        success_count = 0
        fail_count = 0
        
        for i, token in enumerate(self.tokens, 1):
            self.log_signal.emit(f"[{i}/{len(self.tokens)}] 处理中...\n")
            self.log_signal.emit(f"   Token: {token[:40]}...\n")
            self.progress_signal.emit(i, len(self.tokens))
            
            try:
                from core.cursor_api import get_api_client
                from core.account_storage import get_storage
                import base64, json
                
                # 提取user_id
                parts = token.split('.')
                if len(parts) >= 2:
                    payload = parts[1]
                    padding = len(payload) % 4
                    if padding:
                        payload += '=' * (4 - padding)
                    decoded = base64.urlsafe_b64decode(payload)
                    token_data = json.loads(decoded)
                    user_id = token_data.get('sub', '').replace('auth0|', '')
                    
                    # 验证并保存
                    api = get_api_client()
                    temp_format = f"{user_id}::{token}"
                    details = api.get_account_details_by_cookie(temp_format)
                    
                    if details and 'email' in details:
                        storage = get_storage()
                        account_data = {
                            'email': details.get('email'),
                            'user_id': user_id,
                            'access_token': token,
                            'membership_type': details.get('membership_type', 'free'),
                        }
                        storage.upsert_account(account_data)
                        
                        self.log_signal.emit(f"   ✅ 成功: {details.get('email')}\n\n")
                        success_count += 1
                    else:
                        self.log_signal.emit(f"   ❌ 失败: 无法获取账号信息\n\n")
                        fail_count += 1
                else:
                    self.log_signal.emit(f"   ❌ 失败: Token格式错误\n\n")
                    fail_count += 1
                    
            except Exception as e:
                self.log_signal.emit(f"   ❌ 失败: {str(e)}\n\n")
                fail_count += 1
        
        # 发送完成信号
        self.finished_signal.emit(success_count, fail_count)


class SessionTokenImportThread(QThread):
    """SessionToken 导入线程（无头浏览器）"""
    
    # 信号
    log_signal = pyqtSignal(str)  # 日志信号
    success_signal = pyqtSignal(str)  # 成功信号，携带AccessToken
    failed_signal = pyqtSignal(str)  # 失败信号，携带错误信息
    
    def __init__(self, session_token: str, parent=None):
        super().__init__(parent)
        self.session_token = session_token
    
    def run(self):
        """执行导入"""
        try:
            self.log_signal.emit("="*50 + "\n")
            self.log_signal.emit("🚀 开始 SessionToken 导入流程\n")
            self.log_signal.emit("="*50 + "\n\n")
            
            self.log_signal.emit("[步骤1] 启动无头浏览器...\n")
            
            from core.browser_manager import BrowserManager
            browser_mgr = BrowserManager()
            
            # 使用无头模式
            browser = browser_mgr.init_browser(headless=True)
            tab = browser.latest_tab
            
            self.log_signal.emit("✅ 无头浏览器已启动（后台运行）\n\n")
            
            self.log_signal.emit("[步骤2] 设置 SessionToken 到 Cookie...\n")
            self.log_signal.emit(f"   Token: {self.session_token[:40]}...\n\n")
            
            self.log_signal.emit("[步骤3] 通过深度登录获取 AccessToken...\n")
            
            from core.deep_token_getter import DeepTokenGetter
            
            access_token = DeepTokenGetter.get_access_token_from_session_token(
                tab, 
                self.session_token,
                max_attempts=3
            )
            
            # 关闭浏览器
            self.log_signal.emit("[步骤4] 关闭浏览器...\n")
            browser_mgr.quit()
            self.log_signal.emit("✅ 浏览器已关闭\n\n")
            
            if access_token:
                self.log_signal.emit("="*50 + "\n")
                self.log_signal.emit("🎉 成功获取 AccessToken!\n")
                self.log_signal.emit("="*50 + "\n")
                self.log_signal.emit(f"Token长度: {len(access_token)} 字符\n")
                self.log_signal.emit(f"Token前缀: {access_token[:50]}...\n\n")
                self.success_signal.emit(access_token)
            else:
                self.failed_signal.emit(
                    "深度登录失败\n\n"
                    "可能原因：\n"
                    "• SessionToken 已失效\n"
                    "• SessionToken 格式错误\n"
                    "• 网络连接问题\n\n"
                    "请检查 SessionToken 是否正确"
                )
                
        except Exception as e:
            logger.error(f"SessionToken 导入失败: {e}")
            try:
                if 'browser_mgr' in locals():
                    browser_mgr.quit()
            except:
                pass
            self.failed_signal.emit(f"SessionToken 导入失败：\n{str(e)}")


class ValidateThread(QThread):
    """验证线程 - 验证 AccessToken 并获取账号信息"""
    
    # 信号
    validation_success = pyqtSignal(dict)  # 验证成功，携带账号数据
    validation_failed = pyqtSignal(str)  # 验证失败，携带错误信息
    
    def __init__(self, access_token: str, session_token: str = "", parent=None):
        """
        初始化验证线程
        
        Args:
            access_token: AccessToken
            session_token: SessionToken (可选，用于转换)
            parent: 父对象
        """
        super().__init__(parent)
        self.access_token = access_token
        self.session_token = session_token
    
    def run(self):
        """执行验证"""
        try:
            from core.cursor_api import get_api_client
            api = get_api_client()
            
            # 处理用户输入
            if self.access_token:
                # ===== 用户提供纯 AccessToken =====
                logger.info("用户提供 AccessToken，开始验证...")
                
                # 步骤 1：从 JWT 提取 user_id
                import base64, json
                parts = self.access_token.split('.')
                if len(parts) < 2:
                    self.validation_failed.emit("AccessToken 格式错误")
                    return
                
                payload = parts[1]
                padding = len(payload) % 4
                if padding:
                    payload += '=' * (4 - padding)
                
                decoded = base64.urlsafe_b64decode(payload)
                token_data = json.loads(decoded)
                user_id = token_data.get('sub', '').replace('auth0|', '')
                
                if not user_id.startswith('user_'):
                    self.validation_failed.emit("无法从 AccessToken 提取有效的用户ID")
                    return
                
                logger.info(f"✓ 提取用户ID: {user_id}")
                
                # 步骤 2：构造临时格式用于 API 调用（仅临时使用，不保存）
                temp_format = f"{user_id}::{self.access_token}"
                logger.info(f"✓ 构造临时格式用于 API 调用: {user_id}::...")
                logger.info("⚠️  注意：此格式仅用于 API 调用，不会保存到数据库")
                
                # 步骤 3：使用构造的格式调用 API（Cookie 认证）
                details = api.get_account_details_by_cookie(temp_format)
                
                if details and 'email' in details:
                    # ✅ 成功获取完整信息
                    account_data = {
                        'email': details.get('email'),
                        'user_id': user_id,
                        'access_token': self.access_token,  # ⭐ 原始 AccessToken
                        'refresh_token': self.access_token,  # ⭐ 用 access_token 填充（通常相同）
                        'session_token': '',  # ⭐ 空字符串（导出时会转为 null）
                        'membership_type': details.get('membership_type', 'free'),
                        'usage_percent': details.get('usage_percent', 0),
                        'used': details.get('used', 0),
                        'limit': details.get('limit', 1000),
                        'days_remaining': details.get('days_remaining', 0)
                    }
                    
                    logger.info(f"✓ 成功验证并获取完整信息: {account_data['email']}")
                    logger.info(f"✓ 套餐: {account_data['membership_type'].upper()}")
                    logger.info(f"✓ 使用率: {account_data['usage_percent']}%")
                    self.validation_success.emit(account_data)
                else:
                    self.validation_failed.emit("AccessToken 无效或已失效")
                    
            elif self.session_token:
                # ===== 用户提供 SessionToken (type='web') =====
                # ⚠️ 真正的 SessionToken 需要 OAuth 流程转换
                # 当前简化方案：提取其中的 JWT 部分
                logger.info("用户提供 SessionToken，尝试提取 AccessToken...")
                
                # URL 解码
                import urllib.parse
                decoded_token = self.session_token
                if '%3A%3A' in decoded_token:
                    decoded_token = urllib.parse.unquote(decoded_token)
                
                # 分割获取 JWT 部分
                if '::' in decoded_token:
                    parts = decoded_token.split('::', 1)
                    extracted_access_token = parts[1]
                    
                    logger.info(f"✓ 从 SessionToken 提取 AccessToken: {extracted_access_token[:50]}...")
                    
                    # 递归调用，使用提取的 AccessToken
                    self.access_token = extracted_access_token
                    self.session_token = ""
                    self.run()
                else:
                    self.validation_failed.emit("SessionToken 格式错误\n必须包含 :: 分隔符")
            else:
                self.validation_failed.emit("请提供 AccessToken")
            
        except Exception as e:
            logger.error(f"验证异常: {e}", exc_info=True)
            self.validation_failed.emit(f"验证失败: {str(e)}")


import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from gui.dialogs.animated_dialog import AnimatedDialog


class AddAccountDialog(AnimatedDialog):
    """添加账号对话框"""
    
    # ⚡ 定义信号
    account_added = pyqtSignal()  # 账号添加成功信号
    
    def __init__(self, parent=None):
        """
        初始化对话框
        
        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        
        self.account_data = None
        self.validate_thread = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置 UI"""
        self.setWindowTitle("添加账号")
        self.setMinimumWidth(900)  # 增加宽度以容纳左右布局
        self.setMinimumHeight(600)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        
        # 标题
        self._add_title(main_layout)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(line)
        
        # ⚡ 左右分栏布局
        content_layout = QHBoxLayout()
        
        # 左侧：Token 输入区域
        left_layout = QVBoxLayout()
        self._add_input_section(left_layout)
        content_layout.addLayout(left_layout, 1)  # 占1份
        
        # 右侧：实时日志区域
        right_layout = QVBoxLayout()
        self._add_log_section(right_layout)
        content_layout.addLayout(right_layout, 1)  # 占1份
        
        main_layout.addLayout(content_layout)
        
        # 按钮
        self._add_buttons(main_layout)
    
    def _add_title(self, layout: QVBoxLayout):
        """添加标题"""
        title_label = QLabel("📥 添加账号")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        subtitle_label = QLabel("通过 AccessToken 快速添加账号（自动获取完整信息）")
        subtitle_label.setStyleSheet("color: #666;")
        layout.addWidget(subtitle_label)
    
    def _add_input_section(self, layout: QVBoxLayout):
        """添加输入区域（左侧）"""
        input_group = QGroupBox("💡 Token 输入")
        input_layout = QVBoxLayout(input_group)
        
        # ⭐ Token类型选择
        type_layout = QHBoxLayout()
        type_label = QLabel("Token类型:")
        type_label.setStyleSheet("font-weight: bold;")
        type_layout.addWidget(type_label)
        
        self.token_type_group = QButtonGroup(self)
        self.access_token_radio = QRadioButton("AccessToken")
        self.session_token_radio = QRadioButton("SessionToken")
        self.access_token_radio.setChecked(True)  # 默认AccessToken
        
        self.token_type_group.addButton(self.access_token_radio, 1)
        self.token_type_group.addButton(self.session_token_radio, 2)
        self.token_type_group.buttonClicked.connect(self._on_token_type_changed)
        
        type_layout.addWidget(self.access_token_radio)
        type_layout.addWidget(self.session_token_radio)
        type_layout.addStretch()
        input_layout.addLayout(type_layout)
        
        # AccessToken 输入
        access_label = QLabel("AccessToken <span style='color:red;'>*</span>:")
        access_label.setTextFormat(Qt.TextFormat.RichText)
        self.access_label = access_label
        input_layout.addWidget(access_label)
        
        self.access_token_input = QTextEdit()
        self.access_token_input.setPlaceholderText(
            "粘贴 AccessToken，支持以下格式：\n"
            "• 明文 JWT Token（eyJhbGc...）\n"
            "• 加密 Token（gAAAAA...，自动解密）\n"
            "• 🔥 批量导入：用 / 分隔多个Token\n"
            "  例如：token1/token2/token3"
        )
        self.access_token_input.setMinimumHeight(280)
        self.access_token_input.setMaximumHeight(350)
        input_layout.addWidget(self.access_token_input)
        
        # ⭐ SessionToken 输入
        session_label = QLabel("SessionToken <span style='color:red;'>*</span>:")
        session_label.setTextFormat(Qt.TextFormat.RichText)
        self.session_label = session_label
        self.session_label.setVisible(False)
        input_layout.addWidget(session_label)
        
        self.session_token_input = QTextEdit()
        self.session_token_input.setPlaceholderText(
            "粘贴 SessionToken，格式：\n"
            "• user_01XXXXX::eyJhbGc...\n"
            "• 或 WorkosCursorSessionToken 完整值\n"
            "• 🔥 批量导入：用 / 分隔多个Token\n"
            "  例如：token1/token2/token3"
        )
        self.session_token_input.setMinimumHeight(280)
        self.session_token_input.setMaximumHeight(350)
        self.session_token_input.setVisible(False)
        input_layout.addWidget(self.session_token_input)
        
        # ⚡ 简化的提示信息
        hint_label = QLabel(
            "<small>💡 或使用「检测当前账号」→「导入」功能</small>"
        )
        hint_label.setTextFormat(Qt.TextFormat.RichText)
        hint_label.setStyleSheet("color: #7f8c8d; padding: 5px;")
        input_layout.addWidget(hint_label)
        
        layout.addWidget(input_group)
        layout.addStretch()  # 添加弹性空间，让输入区域紧凑
    
    def _add_instructions(self, layout: QVBoxLayout):
        """添加说明"""
        instructions_group = QGroupBox("📖 获取 AccessToken 的方法")
        instructions_layout = QVBoxLayout(instructions_group)
        
        instructions_text = QLabel(
            "<b>方法 1: 使用检测功能（最简单）⭐</b><br>"
            "• 右侧面板点击「🔍 检测当前账号」<br>"
            "• 等待检测完成后点击「➕ 导入」<br>"
            "• 一键完成，无需手动输入！<br><br>"
            "<b>方法 2: 从 Cursor 数据库提取</b><br>"
            "• Windows: <code>%APPDATA%\\Cursor\\User\\globalStorage\\state.vscdb</code><br>"
            "• 使用 SQLite 工具打开数据库<br>"
            "• 查看 <code>ItemTable</code> 表<br>"
            "• 找到 key=<code>cursorAuth/accessToken</code> 的记录<br>"
            "• 复制其 value 值（JWT 格式）<br><br>"
            "<b>方法 3: 从其他工具导入</b><br>"
            "• 如果有账号 JSON 文件，使用主窗口「导入」功能批量导入<br><br>"
            "<b>技术说明：</b><br>"
            "• 程序会从 AccessToken 提取用户ID<br>"
            "• 构造临时格式 <code>user_xxx::jwt</code> 调用 API<br>"
            "• 保存时只保存原始 AccessToken"
        )
        instructions_text.setTextFormat(Qt.TextFormat.RichText)
        instructions_text.setWordWrap(True)
        instructions_text.setOpenExternalLinks(True)
        instructions_text.setStyleSheet(
            "padding: 10px; "
            "background-color: #f5f5f5; "
            "border-radius: 4px;"
        )
        instructions_layout.addWidget(instructions_text)
        
        layout.addWidget(instructions_group)
    
    def _add_log_section(self, layout: QVBoxLayout):
        """添加实时日志显示区域（右侧）"""
        log_group = QGroupBox("📋 导入日志")
        log_layout = QVBoxLayout(log_group)
        
        # 实时日志文本框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("点击「验证并添加」后，这里会显示导入过程...")
        self.log_text.setStyleSheet(
            "QTextEdit {"
            "  background-color: #2c3e50;"
            "  color: #ecf0f1;"
            "  font-family: 'Consolas', 'Monaco', monospace;"
            "  font-size: 10pt;"
            "  padding: 8px;"
            "  border: 1px solid #34495e;"
            "  border-radius: 4px;"
            "}"
        )
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
    
    
    def _add_buttons(self, layout: QVBoxLayout):
        """添加按钮"""
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 取消按钮
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setMinimumWidth(100)
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        # 验证并添加按钮
        self.add_btn = QPushButton("验证并添加")
        self.add_btn.setMinimumWidth(120)
        self.add_btn.setDefault(True)
        self.add_btn.setStyleSheet(
            "QPushButton {"
            "  background-color: #4CAF50; "
            "  color: white; "
            "  font-weight: bold; "
            "  padding: 8px;"
            "}"
            "QPushButton:hover {"
            "  background-color: #45a049;"
            "}"
            "QPushButton:disabled {"
            "  background-color: #ccc;"
            "}"
        )
        self.add_btn.clicked.connect(self._on_add_clicked)
        button_layout.addWidget(self.add_btn)
        
        layout.addLayout(button_layout)
    
    def _on_token_type_changed(self, button):
        """Token类型改变"""
        is_access_token = self.access_token_radio.isChecked()
        
        # 显示/隐藏对应的输入框和标签
        self.access_label.setVisible(is_access_token)
        self.access_token_input.setVisible(is_access_token)
        
        self.session_label.setVisible(not is_access_token)
        self.session_token_input.setVisible(not is_access_token)
        
        # ⭐ 强制更新布局
        self.access_label.updateGeometry()
        self.access_token_input.updateGeometry()
        self.session_label.updateGeometry()
        self.session_token_input.updateGeometry()
        
        # ⭐ 刷新父容器布局
        if self.access_label.parent():
            self.access_label.parent().updateGeometry()
            self.access_label.parent().update()
    
    def _on_add_clicked(self):
        """验证并添加按钮点击 - 支持批量导入"""
        # ⭐ 根据选择的类型获取Token
        if self.access_token_radio.isChecked():
            # 方法1：使用AccessToken
            access_token_input = self.access_token_input.toPlainText().strip()
            
            if not access_token_input:
                self._show_error("请输入 AccessToken")
                return
            
            # ⚡ 解析Token（支持 / 分隔或换行）
            # 优先使用 / 分隔，如果没有 / 则使用换行
            if '/' in access_token_input:
                tokens = [t.strip() for t in access_token_input.split('/') if t.strip()]
            else:
                tokens = [line.strip() for line in access_token_input.split('\n') if line.strip()]
            
            if len(tokens) == 1:
                # 单个导入
                self._import_by_access_token(tokens[0])
            else:
                # 批量导入
                self.log_text.append(f"\n🔥 检测到 {len(tokens)} 个 AccessToken，开始批量导入...\n\n")
                self._batch_import_access_tokens(tokens)
                
        else:
            # 方法2：使用SessionToken
            session_token_input = self.session_token_input.toPlainText().strip()
            
            if not session_token_input:
                self._show_error("请输入 SessionToken")
                return
            
            # ⚡ 解析Token（支持 / 分隔或换行）
            # 优先使用 / 分隔，如果没有 / 则使用换行
            if '/' in session_token_input:
                tokens = [t.strip() for t in session_token_input.split('/') if t.strip()]
            else:
                tokens = [line.strip() for line in session_token_input.split('\n') if line.strip()]
            
            if len(tokens) == 1:
                # 单个导入
                self._import_by_session_token(tokens[0])
            else:
                # 批量导入
                self.log_text.append(f"\n🔥 检测到 {len(tokens)} 个 SessionToken，开始批量导入...\n\n")
                self._batch_import_session_tokens(tokens)
    
    def _import_by_access_token(self, access_token_input: str):
        """通过AccessToken导入"""
        # 验证输入
        if not access_token_input:
            self._show_error("请输入 AccessToken")
            return
        
        # ⭐ 智能识别Token格式（明文 or 加密）
        access_token = access_token_input
        
        # 格式1: 明文JWT（以eyJ开头）
        if access_token.startswith('eyJ'):
            logger.info("✓ 识别为明文 AccessToken（JWT格式）")
        
        # 格式2: 加密Token（以gAAAAA开头，Fernet加密）
        elif access_token.startswith('gAAAAA'):
            logger.info("✓ 识别为加密 AccessToken，尝试解密...")
            try:
                from utils.crypto import get_crypto_manager
                crypto = get_crypto_manager()
                decrypted_token = crypto.decrypt(access_token)
                
                # 验证解密后的Token是否是有效的JWT
                if decrypted_token.startswith('eyJ') and decrypted_token.count('.') >= 2:
                    access_token = decrypted_token
                    logger.info(f"✓ 解密成功，Token长度: {len(access_token)}")
                    # 显示提示到日志框
                    self.log_text.append(f"✓ 已自动解密 Token\n")
                    self.log_text.append(f"✓ 解密后长度: {len(decrypted_token)} 字符\n")
                    self.log_text.append(f"✓ 正在验证...\n\n")
                else:
                    self._show_error("解密后的内容不是有效的 AccessToken")
                    return
            except Exception as e:
                logger.error(f"解密失败: {e}")
                self._show_error(f"无法解密 Token\n\n可能原因：\n• 不是本软件加密的Token\n• Token已损坏\n\n请使用明文 AccessToken")
                return
        
        # 格式3: 其他格式（尝试判断）
        else:
            # 可能是其他加密格式或错误输入
            self._show_error(
                "无法识别 Token 格式\n\n"
                "支持的格式：\n"
                "• 明文 JWT Token（以 eyJ 开头）\n"
                "• 本软件加密的 Token（以 gAAAAA 开头）\n\n"
                f"当前输入以 '{access_token[:20]}...' 开头"
            )
            return
        
        # 验证 JWT 格式（解密后的token）
        if not access_token.startswith('eyJ'):
            self._show_error("AccessToken 格式错误\n应以 eyJ 开头（JWT 格式）")
            return
        
        if access_token.count('.') < 2:
            self._show_error("AccessToken 格式错误\n应包含至少 2 个点号（JWT 格式：xxx.xxx.xxx）")
            return
        
        # 禁用按钮和输入
        self.add_btn.setEnabled(False)
        self.add_btn.setText("验证中...")
        self.access_token_input.setReadOnly(True)
        
        # 创建并启动验证线程
        # ⭐ 只传 AccessToken，SessionToken 留空
        self.validate_thread = ValidateThread(access_token, "", self)
        self.validate_thread.validation_success.connect(self._on_validation_success)
        self.validate_thread.validation_failed.connect(self._on_validation_failed)
        self.validate_thread.start()
    
    def _import_by_session_token(self, session_token: str):
        """
        通过SessionToken导入（使用无头浏览器+深度登录）- 异步方式
        
        Args:
            session_token: SessionToken
        """
        logger.info("="*60)
        logger.info("通过 SessionToken 导入账号（异步模式）")
        logger.info("="*60)
        
        # 禁用按钮
        self.add_btn.setEnabled(False)
        self.add_btn.setText("导入中...")
        
        # 清空日志
        self.log_text.setPlainText("")
        
        # ⚡ 创建并启动导入线程
        self.import_thread = SessionTokenImportThread(session_token, self)
        
        # 连接信号
        self.import_thread.log_signal.connect(self._on_import_log)
        self.import_thread.success_signal.connect(self._on_import_success)
        self.import_thread.failed_signal.connect(self._on_import_failed)
        
        # 启动线程
        self.import_thread.start()
    
    def _on_import_log(self, message: str):
        """处理导入日志 - 显示到右侧日志框"""
        self.log_text.append(message)
    
    def _on_import_success(self, access_token: str):
        """处理导入成功"""
        self.log_text.append("[步骤5] 验证账号信息...\n")
        
        # 使用获取到的AccessToken导入（会触发 _on_validation_success）
        self._import_by_access_token(access_token)
    
    def _on_import_failed(self, error_message: str):
        """处理导入失败"""
        self._show_error(error_message)
        self.add_btn.setEnabled(True)
        self.add_btn.setText("验证并添加")
    
    def _batch_import_access_tokens(self, tokens: list):
        """批量导入 AccessToken - 异步方式"""
        self.log_text.append("="*50 + "\n")
        self.log_text.append(f"📦 批量导入模式：共 {len(tokens)} 个 AccessToken\n")
        self.log_text.append("="*50 + "\n\n")
        
        self.add_btn.setEnabled(False)
        self.add_btn.setText(f"导入中 (0/{len(tokens)})")
        
        # ⚡ 创建并启动批量导入线程
        self.batch_thread = BatchImportThread(tokens, self)
        self.batch_thread.log_signal.connect(self._on_batch_log)
        self.batch_thread.progress_signal.connect(self._on_batch_progress)
        self.batch_thread.finished_signal.connect(self._on_batch_finished)
        self.batch_thread.start()
    
    def _on_batch_log(self, message: str):
        """处理批量导入日志"""
        self.log_text.append(message)
    
    def _on_batch_progress(self, current: int, total: int):
        """处理批量导入进度"""
        self.add_btn.setText(f"导入中 ({current}/{total})")
    
    def _on_batch_finished(self, success: int, fail: int):
        """处理批量导入完成"""
        self.log_text.append("="*50 + "\n")
        self.log_text.append(f"✅ 批量导入完成！\n")
        self.log_text.append(f"   成功: {success} 个\n")
        self.log_text.append(f"   失败: {fail} 个\n")
        self.log_text.append("="*50 + "\n")
        
        self.add_btn.setEnabled(True)
        self.add_btn.setText("验证并添加")
        
        # 提示并关闭（如果有成功的）
        if success > 0:
            # ⚡ 发送账号添加信号，通知主窗口刷新
            self.account_added.emit()
            
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "批量导入完成", 
                                   f"成功导入 {success} 个账号\n失败 {fail} 个")
            if fail == 0:
                self.accept()
    
    def _batch_import_session_tokens(self, tokens: list):
        """批量导入 SessionToken - 逐个处理"""
        self.log_text.append("="*50 + "\n")
        self.log_text.append(f"📦 批量SessionToken导入：共 {len(tokens)} 个\n")
        self.log_text.append("="*50 + "\n")
        self.log_text.append("⚠️ SessionToken导入较慢（需启动浏览器获取AccessToken）\n")
        self.log_text.append(f"💡 预计耗时：约 {len(tokens) * 15} 秒\n\n")
        
        self.add_btn.setEnabled(False)
        self.add_btn.setText(f"导入中 (0/{len(tokens)})")
        
        # 保存状态
        self.batch_session_tokens = tokens
        self.batch_session_index = 0
        self.batch_session_success = 0
        self.batch_session_fail = 0
        
        # 开始处理第一个
        self._process_next_session_token()
    
    def _process_next_session_token(self):
        """处理下一个SessionToken"""
        if self.batch_session_index >= len(self.batch_session_tokens):
            # 全部完成
            self._on_batch_session_finished()
            return
        
        token = self.batch_session_tokens[self.batch_session_index]
        self.batch_session_index += 1
        
        self.log_text.append(f"\n[{self.batch_session_index}/{len(self.batch_session_tokens)}] 处理 SessionToken...\n")
        self.log_text.append(f"   Token: {token[:40]}...\n")
        self.add_btn.setText(f"导入中 ({self.batch_session_index}/{len(self.batch_session_tokens)})")
        
        # ⚡ 清理旧线程（如果存在）
        if hasattr(self, 'current_session_thread') and self.current_session_thread:
            try:
                self.current_session_thread.log_signal.disconnect()
                self.current_session_thread.success_signal.disconnect()
                self.current_session_thread.failed_signal.disconnect()
            except:
                pass
        
        # 创建新线程处理这个SessionToken
        self.current_session_thread = SessionTokenImportThread(token, self)
        self.current_session_thread.log_signal.connect(lambda msg: self.log_text.append("   " + msg))
        self.current_session_thread.success_signal.connect(self._on_batch_session_success)
        self.current_session_thread.failed_signal.connect(self._on_batch_session_failed)
        self.current_session_thread.finished.connect(lambda: None)  # 标记线程已完成
        self.current_session_thread.start()
    
    def _on_batch_session_success(self, access_token: str):
        """单个SessionToken成功 - 保存并继续下一个"""
        # 直接保存（简化版）
        try:
            from core.cursor_api import get_api_client
            from core.account_storage import get_storage
            import base64, json
            
            parts = access_token.split('.')
            if len(parts) >= 2:
                payload = parts[1]
                padding = len(payload) % 4
                if padding:
                    payload += '=' * (4 - padding)
                decoded = base64.urlsafe_b64decode(payload)
                token_data = json.loads(decoded)
                user_id = token_data.get('sub', '').replace('auth0|', '')
                
                api = get_api_client()
                temp_format = f"{user_id}::{access_token}"
                details = api.get_account_details_by_cookie(temp_format)
                
                if details and 'email' in details:
                    storage = get_storage()
                    storage.upsert_account({
                        'email': details.get('email'),
                        'user_id': user_id,
                        'access_token': access_token,
                        'membership_type': details.get('membership_type', 'free'),
                    })
                    self.log_text.append(f"   ✅ 成功: {details.get('email')}\n")
                    self.batch_session_success += 1
                else:
                    self.log_text.append(f"   ❌ 失败: 无法获取账号信息\n")
                    self.batch_session_fail += 1
        except Exception as e:
            self.log_text.append(f"   ❌ 失败: {str(e)}\n")
            self.batch_session_fail += 1
        
        # ⚡ 等待线程完全结束后再继续
        if hasattr(self, 'current_session_thread') and self.current_session_thread:
            self.current_session_thread.wait(1000)  # 等待最多1秒
        
        # 使用 QTimer 延迟继续下一个（避免卡死）
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(500, self._process_next_session_token)
    
    def _on_batch_session_failed(self, error: str):
        """单个SessionToken失败 - 继续下一个"""
        self.log_text.append(f"   ❌ 失败\n")
        self.batch_session_fail += 1
        
        # ⚡ 等待线程完全结束后再继续
        if hasattr(self, 'current_session_thread') and self.current_session_thread:
            self.current_session_thread.wait(1000)
        
        # 使用 QTimer 延迟继续下一个（避免卡死）
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(500, self._process_next_session_token)
    
    def _on_batch_session_finished(self):
        """批量SessionToken导入完成"""
        self.log_text.append("\n" + "="*50 + "\n")
        self.log_text.append(f"✅ 批量SessionToken导入完成！\n")
        self.log_text.append(f"   成功: {self.batch_session_success} 个\n")
        self.log_text.append(f"   失败: {self.batch_session_fail} 个\n")
        self.log_text.append("="*50 + "\n")
        
        self.add_btn.setEnabled(True)
        self.add_btn.setText("验证并添加")
        
        # 提示
        if self.batch_session_success > 0:
            # ⚡ 发送账号添加信号，通知主窗口刷新
            self.account_added.emit()
            
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "批量导入完成", 
                                   f"成功导入 {self.batch_session_success} 个账号\n失败 {self.batch_session_fail} 个")
            if self.batch_session_fail == 0:
                self.accept()
    
    def _on_validation_success(self, account_data: Dict[str, Any]):
        """验证成功"""
        # 保存账号数据
        self.account_data = account_data
        
        # ⚡ 在日志框显示成功信息
        self.log_text.append("\n" + "="*50 + "\n")
        self.log_text.append("✅ 验证成功！账号信息已获取\n")
        self.log_text.append(f"📧 邮箱: {account_data.get('email')}\n")
        self.log_text.append(f"💎 套餐: {account_data.get('membership_type', 'FREE').upper()}\n")
        self.log_text.append("="*50 + "\n")
        
        # 显示结果
        usage_percent = account_data.get('usage_percent', 0)
        days = account_data.get('days_remaining', 0)
        used = account_data.get('used', 0)
        limit = account_data.get('limit', 1000)
        
        result_text = (
            f"✅ 验证成功！已获取完整账号信息\n\n"
            f"📧 邮箱: {account_data.get('email', 'unknown')}\n"
            f"👤 用户ID: {account_data.get('user_id', 'unknown')}\n"
            f"🎫 套餐: {account_data.get('membership_type', 'free').upper()}\n"
            f"📊 使用量: {used}/{limit} ({usage_percent}%)\n"
            f"⏰ 剩余天数: {days} 天\n\n"
            f"✅ 已通过 Cookie 认证获取完整信息\n"
            f"点击下方「确定」添加到管理器"
        )
        
        # 显示到日志框
        self.log_text.setPlainText(result_text)
        
        # 更新按钮
        self.add_btn.setText("确定")
        self.add_btn.setEnabled(True)
        self.add_btn.clicked.disconnect()
        self.add_btn.clicked.connect(self.accept)
    
    def _on_validation_failed(self, error_msg: str):
        """验证失败"""
        # 显示错误到日志框
        result_text = f"❌ 验证失败\n\n{error_msg}\n\n请检查 AccessToken 是否正确和有效"
        self.log_text.setPlainText(result_text)
        
        # 恢复按钮和输入
        self.add_btn.setEnabled(True)
        self.add_btn.setText("验证并添加")
        self.access_token_input.setReadOnly(False)
    
    def _show_error(self, message: str):
        """显示错误提示（在界面上显示，不弹窗）"""
        # ⭐ 在日志框显示错误
        self.log_text.setPlainText(f"❌ {message}")
        
    
    def get_account_data(self) -> Optional[Dict[str, Any]]:
        """
        获取验证后的账号数据
        
        Returns:
            Optional[Dict]: 账号数据或 None
        """
        return self.account_data
    
    def closeEvent(self, event):
        """关闭事件"""
        # 如果验证线程还在运行，终止它
        if self.validate_thread and self.validate_thread.isRunning():
            self.validate_thread.terminate()
            self.validate_thread.wait()
        
        super().closeEvent(event)

