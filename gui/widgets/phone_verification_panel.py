#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手机验证配置面板
让用户自定义手机验证代码（因接码平台不同）
"""

import sys
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QGroupBox, QMessageBox, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QMovie

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.logger import get_logger
from utils.app_paths import get_config_file

logger = get_logger("phone_verification_panel")


class PhoneVerificationPanel(QWidget):
    """手机验证配置面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PhoneVerificationPanel")  # 设置对象名用于CSS
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
            
            # ⭐ 重新加载最新配置（避免覆盖其他面板的修改）
            latest_config = self._load_config()
            
            # ⭐ 只更新手机验证配置部分
            if 'phone_verification' not in latest_config:
                latest_config['phone_verification'] = {}
            latest_config['phone_verification'] = self.config.get('phone_verification', {})
            
            # 保存完整配置
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(latest_config, f, ensure_ascii=False, indent=2)
            
            # ⭐ 更新本地配置为最新版本
            self.config = latest_config
            
            logger.info("✅ 手机验证配置已保存（不影响其他配置）")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
    
    def _setup_ui(self):
        """设置 UI"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setObjectName("PhoneScrollArea")  # 设置对象名
        
        content = QWidget()
        content.setObjectName("PhoneContainer")  # 设置对象名用于CSS
        scroll.setWidget(content)
        
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(scroll)
        
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title = QLabel("📱 自动过手机号验证")
        title.setProperty("heading", True)
        layout.addWidget(title)
        
        # 状态显示
        status_group = QGroupBox("当前状态")
        status_group.setObjectName("PhoneStatusGroup")  # 设置对象名
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel()
        self._update_status_display()
        status_layout.addWidget(self.status_label)
        
        layout.addWidget(status_group)
        
        # 创建水平布局：左边是功能说明，右边是提醒动图
        info_horizontal_layout = QHBoxLayout()
        info_horizontal_layout.setSpacing(15)
        
        # 功能说明（左侧）
        info_group = QGroupBox("💡 功能说明")
        info_group.setObjectName("PhoneInfoGroup")  # 设置对象名
        info_layout = QVBoxLayout(info_group)
        
        info_text = QLabel(
            "<b>为什么需要自定义代码？</b><br>"
            "• Cursor 可能要求手机验证（在输入邮箱验证码后）<br>"
            "• 不同用户使用不同的接码平台<br>"
            "• 因此需要您自己编写接码逻辑<br><br>"
            "<b>配置步骤：</b><br>"
            "1. 在下方编辑器中编写您的手机验证代码<br>"
            "2. 点击【运行测试】验证代码是否有效<br>"
            "3. 测试通过后点击【保存配置】<br>"
            "4. 自动注册时会自动调用您的代码<br><br>"
            "<b>如果不配置：</b><br>"
            "• 遇到手机验证时会提示您手动操作<br>"
            "• 程序每3秒检测是否验证完成"
        )
        info_text.setWordWrap(True)
        info_text.setTextFormat(Qt.TextFormat.RichText)
        info_layout.addWidget(info_text)
        
        info_horizontal_layout.addWidget(info_group, stretch=2)
        
        # 贴心提醒区（右侧）
        reminder_group = QGroupBox()
        reminder_layout = QVBoxLayout(reminder_group)
        reminder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        reminder_layout.setSpacing(10)
        
        # 动图标签
        gif_label = QLabel()
        gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 加载并播放 GIF
        gif_path = Path(__file__).parent.parent / "resources" / "images" / "suggest_not_do.gif"
        if gif_path.exists():
            movie = QMovie(str(gif_path))
            # 设置缩放大小
            movie.setScaledSize(movie.scaledSize().scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio))
            gif_label.setMovie(movie)
            movie.start()
        else:
            gif_label.setText("🐥")
            gif_label.setStyleSheet("font-size: 80px;")
        
        reminder_layout.addWidget(gif_label)
        
        # 提醒文字
        warning_text = QLabel("我建议你别整，\n因为我没整，\n嘿嘿~~~")
        warning_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        warning_text.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
            color: #ffa500;
            padding: 10px;
            line-height: 1.6;
        """)
        reminder_layout.addWidget(warning_text)
        
        reminder_layout.addStretch()
        
        info_horizontal_layout.addWidget(reminder_group, stretch=1)
        
        layout.addLayout(info_horizontal_layout)
        
        # 代码编辑器
        code_group = QGroupBox("📝 自定义验证代码")
        code_group.setObjectName("PhoneCodeGroup")  # 设置对象名
        code_layout = QVBoxLayout(code_group)
        
        # 代码模板说明
        template_label = QLabel(
            "<b>函数接口：</b><br>"
            "<code>def verify_phone(tab, phone_number) -> bool</code><br><br>"
            "<b>参数说明：</b><br>"
            "• <code>tab</code>: DrissionPage 的 tab 对象（页面操作）<br>"
            "• <code>phone_number</code>: 自动生成的美国手机号<br><br>"
            "<b>返回值：</b><br>"
            "• 成功返回 <code>True</code>，失败返回 <code>False</code>"
        )
        template_label.setObjectName("PhoneTemplateLabel")  # 设置对象名
        template_label.setWordWrap(True)
        template_label.setTextFormat(Qt.TextFormat.RichText)
        code_layout.addWidget(template_label)
        
        # 代码编辑器
        self.code_editor = QTextEdit()
        self.code_editor.setObjectName("PhoneCodeEditor")  # 设置对象名
        self.code_editor.setFont(QFont("Consolas", 10))
        self.code_editor.setMinimumHeight(300)
        
        # 默认模板
        default_code = self.config.get('phone_verification', {}).get('custom_code', '')
        if not default_code:
            default_code = """def verify_phone(tab, phone_number):
    \"\"\"
    自定义手机验证逻辑
    
    Args:
        tab: DrissionPage 的 tab 对象
        phone_number: 生成的手机号（格式：3125551234）
    
    Returns:
        bool: 验证是否成功
    \"\"\"
    import time
    
    # ========== 示例代码：请根据您的接码平台修改 ==========
    
    # 1. 调用您的接码平台 API 获取验证码
    # sms_code = your_sms_api.get_code(phone_number)
    
    # 2. 找到验证码输入框
    # code_inputs = tab.eles("@type=text")
    
    # 3. 输入验证码
    # for i, digit in enumerate(sms_code[:6]):
    #     code_inputs[i].input(digit)
    #     time.sleep(0.2)
    
    # 4. 点击提交按钮
    # submit_btn = tab.ele("@type=submit")
    # submit_btn.click()
    
    # 5. 等待验证完成
    # time.sleep(5)
    
    # ========== 请在此编写您的代码 ==========
    
    # 如果您暂时没有接码平台，返回 False
    # 程序会提示您手动操作
    return False
"""
        
        self.code_editor.setPlainText(default_code)
        code_layout.addWidget(self.code_editor)
        
        layout.addWidget(code_group)
        
        # 按钮行
        btn_layout = QHBoxLayout()
        
        self.test_btn = QPushButton("▶️ 运行测试")
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.test_btn.clicked.connect(self._on_test)
        btn_layout.addWidget(self.test_btn)
        
        self.save_btn = QPushButton("💾 保存配置")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        self.save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self.save_btn)
        
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        layout.addStretch()
    
    def _update_status_display(self):
        """更新状态显示"""
        phone_config = self.config.get('phone_verification', {})
        enabled = phone_config.get('enabled', False)
        
        if enabled:
            self.status_label.setText("✅ 已配置自动过手机号验证")
            self.status_label.setStyleSheet("color: #27ae60; font-size: 14px; font-weight: bold;")
        else:
            self.status_label.setText("❌ 未配置自动过手机号验证")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 14px; font-weight: bold;")
    
    def _on_test(self):
        """测试代码"""
        code = self.code_editor.toPlainText().strip()
        
        if not code:
            QMessageBox.warning(self, "错误", "请先编写验证代码")
            return
        
        try:
            logger.info("开始测试手机验证代码...")
            
            # 创建测试环境
            test_globals = {}
            test_locals = {}
            
            # 执行代码
            exec(code, test_globals, test_locals)
            
            # 检查函数是否定义
            if 'verify_phone' not in test_locals:
                QMessageBox.warning(
                    self,
                    "测试失败",
                    "❌ 代码中未找到 verify_phone 函数！\n\n"
                    "请确保定义了：\n"
                    "def verify_phone(tab, phone_number):"
                )
                return
            
            verify_func = test_locals['verify_phone']
            
            # 模拟调用（传入 None 测试）
            try:
                # 测试函数签名
                import inspect
                sig = inspect.signature(verify_func)
                params = list(sig.parameters.keys())
                
                if len(params) != 2:
                    QMessageBox.warning(
                        self,
                        "测试失败",
                        f"❌ 函数参数错误！\n\n"
                        f"需要2个参数：(tab, phone_number)\n"
                        f"您的参数：{params}"
                    )
                    return
                
                logger.info("✅ 代码语法正确，函数签名正确")
                
                QMessageBox.information(
                    self,
                    "测试通过",
                    "✅ 代码测试通过！\n\n"
                    "• 语法正确\n"
                    "• 函数签名正确\n"
                    "• 可以保存配置\n\n"
                    "⚠️ 注意：实际效果需要在注册时验证"
                )
                
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "测试失败",
                    f"❌ 函数调用测试失败！\n\n{str(e)}"
                )
                return
            
        except SyntaxError as e:
            QMessageBox.warning(
                self,
                "语法错误",
                f"❌ 代码语法错误！\n\n{str(e)}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "测试错误",
                f"❌ 测试过程发生错误！\n\n{str(e)}"
            )
    
    def _on_save(self):
        """保存配置"""
        code = self.code_editor.toPlainText().strip()
        
        if not code:
            QMessageBox.warning(self, "错误", "请先编写验证代码")
            return
        
        # 先测试代码
        try:
            test_globals = {}
            test_locals = {}
            exec(code, test_globals, test_locals)
            
            if 'verify_phone' not in test_locals:
                QMessageBox.warning(self, "保存失败", "代码中未找到 verify_phone 函数")
                return
        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"代码有错误：\n{str(e)}")
            return
        
        # 保存配置
        if 'phone_verification' not in self.config:
            self.config['phone_verification'] = {}
        
        self.config['phone_verification']['enabled'] = True
        self.config['phone_verification']['custom_code'] = code
        
        self._save_config()
        self._update_status_display()
        
        # 重置未保存标记
        self.has_unsaved_changes = False
        
        # ⭐ 使用 Toast 通知
        from gui.widgets.toast_notification import show_toast
        main_window = self.window()
        show_toast(main_window, "✅ 手机验证配置已保存！", duration=2000)
    
    def _connect_change_signals(self):
        """连接所有变更信号"""
        self.code_editor.textChanged.connect(self._mark_as_changed)
        
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
            # ⚡ 临时断开信号
            self.code_editor.textChanged.disconnect()
            
            # 重新加载配置文件
            self.config = self._load_config()
            
            # 恢复界面控件的值
            phone_config = self.config.get('phone_verification', {})
            custom_code = phone_config.get('custom_code', '')
            
            # 恢复代码编辑器的内容
            self.code_editor.setPlainText(custom_code)
            
            # ⚡ 重新连接信号
            self.code_editor.textChanged.connect(self._mark_as_changed)
            
            # ⚡ 确保标记为未修改
            self.has_unsaved_changes = False
            
            logger.info("✅ 手机验证配置已恢复到修改前的状态")
        except Exception as e:
            logger.error(f"恢复配置失败: {e}")
    
    def is_configured(self) -> bool:
        """检查是否已配置"""
        phone_config = self.config.get('phone_verification', {})
        return phone_config.get('enabled', False)

