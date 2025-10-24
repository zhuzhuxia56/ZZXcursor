#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动绑卡配置对话框
独立的配置界面，用于设置绑卡相关参数
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCheckBox, QGroupBox, QTextEdit,
    QMessageBox, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon

import json
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils.app_paths import get_config_file


class PaymentConfigDialog(QDialog):
    """自动绑卡配置对话框"""
    
    config_changed = pyqtSignal()  # 配置变更信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_file = get_config_file()
        self.config = self._load_config()
        self.init_ui()
        self._load_current_config()
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("💳 自动绑卡配置")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("自动绑卡配置")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # 说明文字
        desc = QLabel(
            "配置注册成功后是否自动绑定支付方式，开启 7 天 Cursor Pro 免费试用。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #7f8c8d; padding: 10px;")
        layout.addWidget(desc)
        
        # 基础配置
        basic_group = self._create_basic_config_group()
        layout.addWidget(basic_group)
        
        # 高级配置
        advanced_group = self._create_advanced_config_group()
        layout.addWidget(advanced_group)
        
        # 说明信息
        info_group = self._create_info_group()
        layout.addWidget(info_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("💾 保存配置")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 10px 30px;
                font-weight: bold;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        self.save_btn.clicked.connect(self._on_save)
        
        self.test_btn = QPushButton("🧪 测试绑卡")
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 10px 30px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.test_btn.clicked.connect(self._on_test)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 30px;
                font-size: 14px;
                border-radius: 5px;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.test_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _create_basic_config_group(self):
        """创建基础配置组"""
        group = QGroupBox("基础配置")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout()
        
        # 启用/禁用绑卡
        self.enable_checkbox = QCheckBox("启用自动绑卡")
        self.enable_checkbox.setStyleSheet("font-size: 13px; font-weight: normal;")
        self.enable_checkbox.stateChanged.connect(self._on_enable_changed)
        layout.addWidget(self.enable_checkbox)
        
        # 提示信息
        enable_hint = QLabel("✓ 启用后，注册成功会自动绑定支付方式，开启 7 天免费试用")
        enable_hint.setStyleSheet("color: #27ae60; font-size: 11px; padding-left: 25px;")
        layout.addWidget(enable_hint)
        
        enable_hint2 = QLabel("✗ 禁用后，只注册账号，不绑定支付方式")
        enable_hint2.setStyleSheet("color: #95a5a6; font-size: 11px; padding-left: 25px;")
        layout.addWidget(enable_hint2)
        
        layout.addSpacing(10)
        
        # 自动填写
        self.auto_fill_checkbox = QCheckBox("自动填写支付信息")
        self.auto_fill_checkbox.setStyleSheet("font-size: 13px; font-weight: normal;")
        layout.addWidget(self.auto_fill_checkbox)
        
        auto_fill_hint = QLabel("自动生成虚拟银行账户信息并填写（使用 Luhn 算法生成）")
        auto_fill_hint.setStyleSheet("color: #7f8c8d; font-size: 11px; padding-left: 25px;")
        layout.addWidget(auto_fill_hint)
        
        group.setLayout(layout)
        return group
    
    def _create_advanced_config_group(self):
        """创建高级配置组"""
        group = QGroupBox("高级配置")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout()
        
        # 失败处理
        failure_label = QLabel("绑卡失败时的处理方式：")
        failure_label.setStyleSheet("font-weight: normal; font-size: 13px; margin-bottom: 5px;")
        layout.addWidget(failure_label)
        
        self.failure_group = QButtonGroup(self)
        
        self.skip_radio = QRadioButton("跳过继续（推荐）")
        self.skip_radio.setStyleSheet("font-size: 12px; font-weight: normal; padding-left: 10px;")
        self.failure_group.addButton(self.skip_radio, 1)
        layout.addWidget(self.skip_radio)
        
        skip_hint = QLabel("绑卡失败后跳过，账号仍会保存，可手动绑卡")
        skip_hint.setStyleSheet("color: #7f8c8d; font-size: 11px; padding-left: 35px;")
        layout.addWidget(skip_hint)
        
        self.abort_radio = QRadioButton("中止注册")
        self.abort_radio.setStyleSheet("font-size: 12px; font-weight: normal; padding-left: 10px;")
        self.failure_group.addButton(self.abort_radio, 2)
        layout.addWidget(self.abort_radio)
        
        abort_hint = QLabel("绑卡失败则中止注册，不保存账号")
        abort_hint.setStyleSheet("color: #7f8c8d; font-size: 11px; padding-left: 35px;")
        layout.addWidget(abort_hint)
        
        group.setLayout(layout)
        return group
    
    def _create_info_group(self):
        """创建说明信息组"""
        group = QGroupBox("📋 重要说明")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #f39c12;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #fef5e7;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #f39c12;
            }
        """)
        
        layout = QVBoxLayout()
        
        info_text = """
<b style="color: #e74c3c;">⚠️ 法律合规声明：</b>
<ul style="margin-top: 5px; color: #7f8c8d;">
<li>本功能仅供学习和测试使用</li>
<li>不要用于欺诈或非法用途</li>
<li>使用虚拟卡信息可能违反 Cursor 和 Stripe 的服务条款</li>
</ul>

<b style="color: #3498db;">💡 技术说明：</b>
<ul style="margin-top: 5px; color: #7f8c8d;">
<li>使用虚拟银行账户信息（Luhn 算法生成）</li>
<li>Stripe 可能检测到虚拟卡并拒绝</li>
<li>建议使用 Stripe 测试卡：<code>4242424242424242</code></li>
<li>或使用真实的银行账户信息（自行承担风险）</li>
</ul>

<b style="color: #27ae60;">✅ 使用建议：</b>
<ul style="margin-top: 5px; color: #7f8c8d;">
<li>首次使用建议先测试（点击"测试绑卡"按钮）</li>
<li>失败处理建议选择"跳过继续"</li>
<li>浏览器会保持打开，方便查看和调试</li>
</ul>
        """
        
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setTextFormat(Qt.TextFormat.RichText)
        info_label.setStyleSheet("font-size: 12px; font-weight: normal; background: transparent;")
        layout.addWidget(info_label)
        
        group.setLayout(layout)
        return group
    
    def _load_config(self):
        """加载配置文件"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {}
        except Exception as e:
            QMessageBox.warning(self, "警告", f"加载配置失败：{e}")
            return {}
    
    def _load_current_config(self):
        """加载当前配置到界面"""
        payment_config = self.config.get('payment_binding', {})
        
        # 基础配置
        self.enable_checkbox.setChecked(payment_config.get('enabled', False))
        self.auto_fill_checkbox.setChecked(payment_config.get('auto_fill', True))
        
        # 高级配置
        skip_on_error = payment_config.get('skip_on_error', True)
        if skip_on_error:
            self.skip_radio.setChecked(True)
        else:
            self.abort_radio.setChecked(True)
        
        # 初始状态
        self._on_enable_changed()
    
    def _on_enable_changed(self):
        """启用状态改变时"""
        enabled = self.enable_checkbox.isChecked()
        
        # 启用/禁用高级配置
        self.auto_fill_checkbox.setEnabled(enabled)
        self.skip_radio.setEnabled(enabled)
        self.abort_radio.setEnabled(enabled)
        
        # 更新测试按钮状态
        self.test_btn.setEnabled(enabled)
    
    def _on_save(self):
        """保存配置"""
        try:
            # ⭐ 重新加载最新配置，避免覆盖其他模块的修改
            latest_config = self._load_config()
            
            # 读取界面配置
            payment_config = {
                'enabled': self.enable_checkbox.isChecked(),
                'auto_fill': self.auto_fill_checkbox.isChecked(),
                'skip_on_error': self.skip_radio.isChecked()
            }
            
            # 更新配置
            if 'payment_binding' not in latest_config:
                latest_config['payment_binding'] = {}
            
            latest_config['payment_binding'].update(payment_config)
            
            # ⭐ 更新本地配置为最新版本
            self.config = latest_config
            
            # 保存到文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(latest_config, f, indent=2, ensure_ascii=False)
            
            # 显示成功消息
            QMessageBox.information(
                self,
                "保存成功",
                f"配置已保存！\n\n"
                f"当前设置：\n"
                f"  • 自动绑卡：{'✅ 已启用' if payment_config['enabled'] else '❌ 已禁用'}\n"
                f"  • 自动填写：{'✅ 是' if payment_config['auto_fill'] else '❌ 否'}\n"
                f"  • 失败处理：{'跳过继续' if payment_config['skip_on_error'] else '中止注册'}"
            )
            
            # 发送配置变更信号
            self.config_changed.emit()
            
            # 关闭对话框
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "保存失败",
                f"保存配置时出错：\n{e}"
            )
    
    def _on_test(self):
        """测试绑卡"""
        # 检查是否启用
        if not self.enable_checkbox.isChecked():
            QMessageBox.warning(
                self,
                "提示",
                "请先启用自动绑卡功能"
            )
            return
        
        # 提示用户
        reply = QMessageBox.question(
            self,
            "测试绑卡",
            "即将启动浏览器进行绑卡测试。\n\n"
            "测试前请确保：\n"
            "  1. 已注册 Cursor 账号\n"
            "  2. 浏览器中有有效的登录 Cookie\n"
            "  3. 账号未绑定过支付方式\n\n"
            "是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 启动测试
        try:
            import subprocess
            import sys
            
            # 运行测试脚本
            subprocess.Popen([sys.executable, "test_payment_binding.py"])
            
            QMessageBox.information(
                self,
                "测试启动",
                "测试程序已启动！\n\n"
                "请在新窗口中查看测试过程。\n"
                "浏览器会保持打开，方便您观察结果。"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "启动失败",
                f"无法启动测试程序：\n{e}\n\n"
                f"请手动运行：python test_payment_binding.py"
            )


# 方便测试的主函数
def main():
    """测试对话框"""
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    dialog = PaymentConfigDialog()
    result = dialog.exec()
    
    if result == QDialog.DialogCode.Accepted:
        print("✅ 配置已保存")
    else:
        print("❌ 已取消")
    
    sys.exit(0)


if __name__ == '__main__':
    main()

