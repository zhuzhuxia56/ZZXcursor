#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮箱配置面板
Tempmail.plus 邮箱配置
"""

import sys
import json
from pathlib import Path
import webbrowser

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMovie

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.logger import get_logger
from utils.app_paths import get_config_file
from utils.resource_path import get_gui_resource

logger = get_logger("email_test_panel")


class EmailTestPanel(QWidget):
    """邮箱配置面板"""
    
    def __init__(self, parent=None):
        """初始化"""
        super().__init__(parent)
        
        self.config = self._load_config()
        self.has_unsaved_changes = False  # 未保存标记
        
        self._setup_ui()
        self._connect_change_signals()  # 连接变更信号
    
    def _load_config(self) -> dict:
        """加载配置"""
        try:
            config_path = get_config_file()
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return {}
    
    def _save_config(self):
        """保存配置（先重新加载最新配置，避免覆盖其他面板的修改）"""
        try:
            config_path = get_config_file()
            
            # ⭐ 记录保存操作
            logger.info(f"开始保存邮箱配置到: {config_path}")
            
            # ⭐ 重新加载最新配置（避免覆盖其他面板的修改）
            latest_config = self._load_config()
            
            # ⭐ 只更新邮箱配置部分
            if 'email' not in latest_config:
                latest_config['email'] = {}
            latest_config['email'] = self.config.get('email', {})
            
            # 确保目录存在
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存完整配置
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(latest_config, f, ensure_ascii=False, indent=2)
            
            # ⭐ 验证保存
            with open(config_path, 'r', encoding='utf-8') as f:
                verify_config = json.load(f)
            if 'email' in verify_config:
                logger.info(f"✅ 邮箱配置验证成功")
            
            # ⭐ 更新本地配置为最新版本
            self.config = latest_config
            
            logger.info("✅ 邮箱配置已保存（不影响其他配置）")
        except PermissionError as e:
            logger.error(f"❌ 权限错误: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "保存失败",
                f"❌ 无法保存配置文件，权限不足。\n\n"
                f"📁 文件位置：\n{config_path}\n\n"
                f"请以管理员身份运行程序。"
            )
        except Exception as e:
            logger.error(f"❌ 保存配置失败: {e}", exc_info=True)
    
    def _setup_ui(self):
        """设置 UI"""
        # 创建滚动区域
        from PyQt6.QtWidgets import QScrollArea
        
        scroll_area = QScrollArea()
        scroll_area.setObjectName("EmailTestScrollArea")  # ⭐ 设置对象名用于CSS
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        
        # 内容容器
        content_widget = QWidget()
        content_widget.setObjectName("EmailTestContent")  # ⭐ 设置对象名用于CSS
        scroll_area.setWidget(content_widget)
        
        # 设置为主布局
        wrapper_layout = QVBoxLayout(self)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(scroll_area)
        
        # 内容布局
        main_layout = QVBoxLayout(content_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("📧 Tempmail 配置")
        title_label.setProperty("heading", True)
        main_layout.addWidget(title_label)
        
        # 配置组
        config_group = QGroupBox()
        config_layout = QVBoxLayout(config_group)
        config_layout.setSpacing(12)
        
        # 域名
        domain_label = QLabel("域名:")
        config_layout.addWidget(domain_label)
        
        self.domain_input = QLineEdit()
        self.domain_input.setPlaceholderText("单个: porktrotter.xyz  或  多个: sharklasers.com/grr.la/guerrillamailblock.com")
        self.domain_input.setText(self.config.get('email', {}).get('domain', ''))
        config_layout.addWidget(self.domain_input)
        
        # 域名提示
        domain_hint = QLabel("💡 支持域名池：多个域名用 <b>/</b> 分隔，每次注册随机抽取一个（提高成功率）")
        domain_hint.setWordWrap(True)
        domain_hint.setStyleSheet("color: #888; font-size: 11px; padding: 2px 0;")
        config_layout.addWidget(domain_hint)
        
        # 接收邮箱
        email_label = QLabel("接收邮箱:")
        config_layout.addWidget(email_label)
        
        self.receiving_email_input = QLineEdit()
        self.receiving_email_input.setPlaceholderText("例如: ******@fexpost.com")
        self.receiving_email_input.setText(self.config.get('email', {}).get('receiving_email', ''))
        config_layout.addWidget(self.receiving_email_input)
        
        # PIN 码
        pin_label = QLabel("PIN码:")
        config_layout.addWidget(pin_label)
        
        self.pin_input = QLineEdit()
        self.pin_input.setPlaceholderText("例如: 123456")
        self.pin_input.setText(self.config.get('email', {}).get('receiving_email_pin', ''))
        config_layout.addWidget(self.pin_input)
        
        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        
        self.save_btn = QPushButton("💾 保存配置")
        self.save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(self.save_btn)
        
        self.help_btn = QPushButton("🔗 申请 tempmail")
        self.help_btn.setProperty("secondary", True)
        self.help_btn.clicked.connect(lambda: webbrowser.open('https://tempmail.plus'))
        btn_row.addWidget(self.help_btn)
        
        config_layout.addLayout(btn_row)
        
        main_layout.addWidget(config_group)
        
        # 创建水平布局：左边是配置说明，右边是动图
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(15)
        
        # 配置说明（左侧）
        info_group = QGroupBox("配置说明")
        info_layout = QVBoxLayout(info_group)
        
        hint_label = QLabel(
            "<b>📖 配置步骤:</b><br><br>"
            "<b>1. 申请 tempmail 邮箱</b><br>"
            "   • 访问 tempmail.plus<br>"
            "   • 获取一个固定邮箱（如 evewowa@fexpost.com）<br>"
            "   • 记录 PIN 码（如 123456）<br><br>"
            "<b>2. 配置域名（支持域名池）</b><br>"
            "   • 单个域名: porktrotter.xyz<br>"
            "   • 多个域名（推荐）: sharklasers.com/grr.la/guerrillamailblock.com<br>"
            "   • 域名池优势: 分散风险，提高成功率 20-40%<br><br>"
            "<b>3. 推荐域名配置</b><br>"
            "   • 高信誉: sharklasers.com/grr.la/guerrillamailblock.com/pokemail.net/spam4.me<br>"
            "   • 精简版: sharklasers.com/grr.la/guerrillamailblock.com<br><br>"
            "<b>4. 使用说明</b><br>"
            "   • 注册时自动生成: random@随机域名.com<br>"
            "   • 每次从域名池中随机抽取，降低风控<br>"
            "   • 程序自动从接收邮箱读取验证码"
        )
        hint_label.setWordWrap(True)
        hint_label.setTextFormat(Qt.TextFormat.RichText)
        info_layout.addWidget(hint_label)
        
        bottom_layout.addWidget(info_group, stretch=2)
        
        # 可爱提醒区（右侧）
        reminder_group = QGroupBox()
        reminder_layout = QVBoxLayout(reminder_group)
        reminder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        reminder_layout.setSpacing(10)
        
        # 动图标签
        gif_label = QLabel()
        gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 加载并播放 GIF
        gif_path = get_gui_resource("watch_you_fill.gif")
        if gif_path.exists():
            movie = QMovie(str(gif_path))
            # 设置缩放大小（调大一些）
            movie.setScaledSize(movie.scaledSize().scaled(280, 280, Qt.AspectRatioMode.KeepAspectRatio))
            gif_label.setMovie(movie)
            movie.start()
        else:
            gif_label.setText("🐷")
            gif_label.setStyleSheet("font-size: 100px;")
        
        reminder_layout.addWidget(gif_label)
        
        # 提醒文字
        warning_text = QLabel("我就看着你填，\n填错了打死你！！！")
        warning_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        warning_text.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #ff6b6b;
            padding: 10px;
            line-height: 1.5;
        """)
        reminder_layout.addWidget(warning_text)
        
        reminder_layout.addStretch()
        
        bottom_layout.addWidget(reminder_group, stretch=1)
        
        main_layout.addLayout(bottom_layout)
        
        main_layout.addStretch()
    
    def _on_test_connection(self):
        """测试邮箱连接"""
        receiving_email = self.receiving_email_input.text().strip()
        pin = self.pin_input.text().strip()
        
        if not receiving_email or not pin:
            QMessageBox.warning(self, "错误", "请先填写接收邮箱和PIN码")
            return
        
        try:
            # 导入邮箱验证处理器
            from core.email_verification import EmailVerificationHandler
            
            # 创建测试处理器
            handler = EmailVerificationHandler(
                account="test@test.com",  # 测试用的账号
                receiving_email=receiving_email,
                receiving_pin=pin
            )
            
            # 测试连接
            logger.info("开始测试邮箱连接...")
            success, message = handler.test_connection()
            
            if success:
                QMessageBox.information(
                    self,
                    "测试成功",
                    f"✅ 邮箱连接测试成功！\n\n"
                    f"接收邮箱: {receiving_email}\n"
                    f"PIN码: {pin}\n\n"
                    f"API 状态: {message}\n\n"
                    f"现在可以使用自动注册功能了。"
                )
            else:
                QMessageBox.warning(
                    self,
                    "测试失败",
                    f"❌ 邮箱连接测试失败！\n\n"
                    f"错误信息: {message}\n\n"
                    f"请检查：\n"
                    f"1. 接收邮箱是否正确（完整邮箱地址）\n"
                    f"2. PIN码是否正确\n"
                    f"3. 网络连接是否正常\n"
                    f"4. tempmail.plus 是否可访问"
                )
                
        except Exception as e:
            logger.error(f"测试邮箱连接异常: {e}")
            QMessageBox.critical(
                self,
                "测试错误",
                f"❌ 测试过程发生错误！\n\n{str(e)}"
            )
    
    def _connect_change_signals(self):
        """连接所有变更信号"""
        self.domain_input.textChanged.connect(self._mark_as_changed)
        self.receiving_email_input.textChanged.connect(self._mark_as_changed)
        self.pin_input.textChanged.connect(self._mark_as_changed)
        
        # 初始化后重置标记
        self.has_unsaved_changes = False
    
    def _mark_as_changed(self):
        """标记为有未保存的修改"""
        self.has_unsaved_changes = True
    
    def check_unsaved_changes(self) -> bool:
        """检查是否有未保存的修改"""
        if self.has_unsaved_changes:
            from gui.dialogs.unsaved_warning_dialog import UnsavedWarningDialog
            
            reply = UnsavedWarningDialog.ask_save(self)
            
            if reply == 1:  # 是 - 保存修改
                self._on_save()
                return True
            elif reply == 2:  # 否 - 放弃修改，恢复原状态
                self.has_unsaved_changes = False
                # ⚡ 重新加载配置，恢复到修改前的状态
                self._reload_config()
                return True
            else:  # 取消 - 留在当前页面
                return False
        
        return True
    
    def _reload_config(self):
        """重新加载配置，恢复到修改前的状态"""
        try:
            # ⚡ 临时断开信号连接（避免恢复时触发变更）
            self.domain_input.textChanged.disconnect()
            self.receiving_email_input.textChanged.disconnect()
            self.pin_input.textChanged.disconnect()
            
            # 重新加载配置文件
            self.config = self._load_config()
            
            # 恢复界面控件的值
            email_config = self.config.get('email', {})
            self.domain_input.setText(email_config.get('domain', ''))
            self.receiving_email_input.setText(email_config.get('receiving_email', ''))
            self.pin_input.setText(email_config.get('receiving_email_pin', ''))
            
            # ⚡ 重新连接信号
            self.domain_input.textChanged.connect(self._mark_as_changed)
            self.receiving_email_input.textChanged.connect(self._mark_as_changed)
            self.pin_input.textChanged.connect(self._mark_as_changed)
            
            # ⚡ 确保标记为未修改
            self.has_unsaved_changes = False
            
            logger.info("✅ 配置已恢复到修改前的状态")
        except Exception as e:
            logger.error(f"恢复配置失败: {e}")
    
    def _on_save(self):
        """保存配置"""
        domain = self.domain_input.text().strip()
        receiving_email = self.receiving_email_input.text().strip()
        pin = self.pin_input.text().strip()
        
        if not domain or not receiving_email or not pin:
            QMessageBox.warning(self, "错误", "请填写完整配置")
            return
        
        # 更新配置
        if 'email' not in self.config:
            self.config['email'] = {}
        
        self.config['email']['domain'] = domain
        self.config['email']['receiving_email'] = receiving_email
        self.config['email']['receiving_email_pin'] = pin
        
        # 保存
        self._save_config()
        
        # 重置未保存标记
        self.has_unsaved_changes = False
        
        # ⭐ 使用 Toast 通知
        from gui.widgets.toast_notification import show_toast
        main_window = self.window()
        show_toast(main_window, "✅ 邮箱配置已保存！", duration=2000)
