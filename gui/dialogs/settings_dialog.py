#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设置对话框
管理程序配置
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFileDialog, QTabWidget,
    QWidget, QGroupBox, QComboBox, QCheckBox, QTimeEdit
)
from PyQt6.QtCore import Qt, QTime
import json
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from gui.widgets.email_test_panel import EmailTestPanel


import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from gui.dialogs.animated_dialog import AnimatedDialog
from utils.theme_manager import get_theme_manager
from utils.app_paths import get_config_file


class SettingsDialog(AnimatedDialog):
    """设置对话框"""
    
    def __init__(self, config_path: str = None, parent=None):
        """
        初始化设置对话框
        
        Args:
            config_path: 配置文件路径（可选，默认使用用户目录配置）
            parent: 父组件
        """
        super().__init__(parent)
        
        # 如果未指定路径，使用用户目录配置文件
        if config_path is None:
            self.config_path = get_config_file()
        else:
            self.config_path = Path(config_path)
        self.config = self._load_config()
        
        # 初始化主题管理器
        self.theme_manager = get_theme_manager(str(self.config_path))
        
        self.setWindowTitle("⚙️ 设置")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        self._setup_ui()
        self._load_settings()
    
    def _load_config(self) -> dict:
        """加载配置文件"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        
        # 默认配置
        return {
            "email": {"domain": "yourdomain.com"},
            "browser": {"headless": False},
            "fingerprint": {"profile": "windows_chrome"}
        }
    
    def _setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标签页
        tabs = QTabWidget()
        
        # Tempmail 配置和测试标签页
        email_test_tab = EmailTestPanel()
        tabs.addTab(email_test_tab, "📧 邮箱测试")
        
        # 浏览器设置标签页（已删除，等待重新实现）
        # browser_tab = self._create_browser_tab()
        # tabs.addTab(browser_tab, "🌐 浏览器")
        
        # 指纹设置标签页（已删除，等待重新实现）
        # fingerprint_tab = self._create_fingerprint_tab()
        # tabs.addTab(fingerprint_tab, "🔐 指纹")
        
        # 主题设置标签页
        theme_tab = self._create_theme_tab()
        tabs.addTab(theme_tab, "🎨 主题")
        
        layout.addWidget(tabs)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setProperty("secondary", True)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("💾 保存")
        save_btn.clicked.connect(self._save_settings)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
    
    
    def _create_browser_tab(self) -> QWidget:
        """创建浏览器设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 浏览器设置
        browser_group = QGroupBox("浏览器配置")
        browser_layout = QVBoxLayout(browser_group)
        
        # Chrome 路径
        chrome_path_row = QHBoxLayout()
        chrome_path_row.addWidget(QLabel("Chrome 路径:"))
        self.chrome_path_input = QLineEdit()
        self.chrome_path_input.setPlaceholderText("留空则使用默认")
        chrome_path_row.addWidget(self.chrome_path_input)
        
        auto_find_btn = QPushButton("🔍 自动查找")
        auto_find_btn.setProperty("secondary", True)
        auto_find_btn.clicked.connect(self._auto_find_chrome)
        chrome_path_row.addWidget(auto_find_btn)
        
        browse_btn = QPushButton("📁 浏览")
        browse_btn.setProperty("secondary", True)
        browse_btn.clicked.connect(self._browse_chrome_path)
        chrome_path_row.addWidget(browse_btn)
        
        browser_layout.addLayout(chrome_path_row)
        
        # 无头模式
        self.headless_checkbox = QCheckBox("无头模式（不显示浏览器窗口）")
        browser_layout.addWidget(self.headless_checkbox)
        
        layout.addWidget(browser_group)
        layout.addStretch()
        
        return tab
    
    def _create_fingerprint_tab(self) -> QWidget:
        """创建指纹设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 指纹配置
        fingerprint_group = QGroupBox("指纹配置文件")
        fingerprint_layout = QVBoxLayout(fingerprint_group)
        
        # 配置文件选择
        profile_row = QHBoxLayout()
        profile_row.addWidget(QLabel("配置文件:"))
        
        self.profile_combo = QComboBox()
        self.profile_combo.addItems([
            "windows_chrome",
            "mac_chrome",
            "random (随机)"
        ])
        profile_row.addWidget(self.profile_combo)
        
        fingerprint_layout.addLayout(profile_row)
        
        # 说明
        info_label = QLabel(
            "🔐 指纹配置包含:\n"
            "  • User-Agent 伪装\n"
            "  • WebGL 指纹随机化\n"
            "  • Canvas 指纹随机化\n"
            "  • AudioContext 噪声\n"
            "  • 时区和语言设置"
        )
        info_label.setProperty("subtitle", True)
        info_label.setWordWrap(True)
        fingerprint_layout.addWidget(info_label)
        
        layout.addWidget(fingerprint_group)
        layout.addStretch()
        
        return tab
    
    def _create_theme_tab(self) -> QWidget:
        """创建主题设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 主题选择
        theme_group = QGroupBox("主题模式")
        theme_layout = QVBoxLayout(theme_group)
        
        # 当前主题显示
        current_theme_row = QHBoxLayout()
        current_theme_row.addWidget(QLabel("当前主题:"))
        self.current_theme_label = QLabel()
        self.current_theme_label.setProperty("subtitle", True)
        current_theme_row.addWidget(self.current_theme_label)
        current_theme_row.addStretch()
        theme_layout.addLayout(current_theme_row)
        
        # 手动切换按钮
        manual_switch_row = QHBoxLayout()
        manual_switch_row.addWidget(QLabel("手动切换:"))
        self.switch_theme_btn = QPushButton()
        self.switch_theme_btn.setProperty("secondary", True)
        self.switch_theme_btn.clicked.connect(self._on_manual_theme_switch)
        manual_switch_row.addWidget(self.switch_theme_btn)
        manual_switch_row.addStretch()
        theme_layout.addLayout(manual_switch_row)
        
        layout.addWidget(theme_group)
        
        # 自动切换设置
        auto_group = QGroupBox("自动切换")
        auto_layout = QVBoxLayout(auto_group)
        
        # 启用自动切换
        self.auto_switch_checkbox = QCheckBox("启用自动切换")
        self.auto_switch_checkbox.stateChanged.connect(self._on_auto_switch_changed)
        auto_layout.addWidget(self.auto_switch_checkbox)
        
        # 深色模式开始时间
        dark_time_row = QHBoxLayout()
        dark_time_row.addWidget(QLabel("深色模式开始时间:"))
        self.dark_start_time = QTimeEdit()
        self.dark_start_time.setTime(QTime(19, 0))  # 默认19:00
        self.dark_start_time.setDisplayFormat("HH:mm")
        dark_time_row.addWidget(self.dark_start_time)
        dark_time_row.addStretch()
        auto_layout.addLayout(dark_time_row)
        
        # 浅色模式开始时间
        light_time_row = QHBoxLayout()
        light_time_row.addWidget(QLabel("浅色模式开始时间:"))
        self.light_start_time = QTimeEdit()
        self.light_start_time.setTime(QTime(7, 0))  # 默认07:00
        self.light_start_time.setDisplayFormat("HH:mm")
        light_time_row.addWidget(self.light_start_time)
        light_time_row.addStretch()
        auto_layout.addLayout(light_time_row)
        
        # 说明
        info_label = QLabel(
            "🌙 自动切换功能说明:\n"
            "  • 程序会在指定时间自动切换主题\n"
            "  • 深色模式适合夜间使用，保护眼睛\n"
            "  • 浅色模式适合白天使用，界面更清晰\n"
            "  • 您也可以随时手动切换主题"
        )
        info_label.setProperty("subtitle", True)
        info_label.setWordWrap(True)
        auto_layout.addWidget(info_label)
        
        layout.addWidget(auto_group)
        layout.addStretch()
        
        return tab
    
    def _on_manual_theme_switch(self):
        """手动切换主题"""
        try:
            # 切换主题
            self.theme_manager.switch_theme()
            
            # 更新界面显示
            self._update_theme_display()
            
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "错误", f"切换主题失败: {e}")
    
    def _on_auto_switch_changed(self, state):
        """自动切换开关状态改变"""
        enabled = state == Qt.CheckState.Checked.value
        
        # 启用/禁用时间选择控件
        self.dark_start_time.setEnabled(enabled)
        self.light_start_time.setEnabled(enabled)
    
    def _update_theme_display(self):
        """更新主题显示"""
        if self.theme_manager.is_dark_theme():
            self.current_theme_label.setText("🌙 深色模式")
            self.switch_theme_btn.setText("☀️ 切换到浅色")
        else:
            self.current_theme_label.setText("☀️ 浅色模式")
            self.switch_theme_btn.setText("🌙 切换到深色")
    
    def _open_link(self, url):
        """打开链接"""
        import webbrowser
        webbrowser.open(url)
    
    def _auto_find_chrome(self):
        """自动查找 Chrome 路径"""
        import os
        import sys
        from PyQt6.QtWidgets import QMessageBox
        
        # 常见的 Chrome 安装路径
        possible_paths = []
        
        if sys.platform == 'win32':
            # Windows 路径
            possible_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.join(os.getenv('LOCALAPPDATA', ''), r"Google\Chrome\Application\chrome.exe"),
                os.path.join(os.getenv('PROGRAMFILES', ''), r"Google\Chrome\Application\chrome.exe"),
                os.path.join(os.getenv('PROGRAMFILES(X86)', ''), r"Google\Chrome\Application\chrome.exe"),
            ]
        elif sys.platform == 'darwin':
            # macOS 路径
            possible_paths = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            ]
        else:
            # Linux 路径
            possible_paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/usr/bin/chromium-browser",
                "/usr/bin/chromium",
            ]
        
        # 查找第一个存在的路径
        for chrome_path in possible_paths:
            if chrome_path and os.path.exists(chrome_path):
                self.chrome_path_input.setText(chrome_path)
                QMessageBox.information(
                    self,
                    "找到 Chrome",
                    f"✅ 已自动找到 Chrome:\n\n{chrome_path}"
                )
                return
        
        # 未找到
        QMessageBox.warning(
            self,
            "未找到 Chrome",
            "❌ 未能自动找到 Chrome 安装路径\n\n"
            "请点击\"浏览\"按钮手动选择 chrome.exe\n\n"
            "或从以下地址下载安装 Chrome:\n"
            "https://www.google.com/chrome/"
        )
    
    def _browse_chrome_path(self):
        """浏览 Chrome 路径"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 Chrome 执行文件",
            "",
            "Executable Files (*.exe);;All Files (*.*)"
        )
        
        if file_path:
            self.chrome_path_input.setText(file_path)
    
    def _load_settings(self):
        """加载设置到界面"""
        # 浏览器设置
        browser_config = self.config.get('browser', {})
        self.chrome_path_input.setText(browser_config.get('chrome_path', ''))
        self.headless_checkbox.setChecked(browser_config.get('headless', False))
        
        # 指纹设置
        fingerprint_config = self.config.get('fingerprint', {})
        profile = fingerprint_config.get('profile', 'windows_chrome')
        index = self.profile_combo.findText(profile)
        if index >= 0:
            self.profile_combo.setCurrentIndex(index)
        
        # 主题设置
        theme_config = self.config.get('theme', {})
        
        # 更新主题显示
        self._update_theme_display()
        
        # 自动切换设置
        auto_switch = theme_config.get('auto_switch', False)
        self.auto_switch_checkbox.setChecked(auto_switch)
        
        # 切换时间设置
        dark_start = theme_config.get('dark_start_time', '19:00')
        light_start = theme_config.get('light_start_time', '07:00')
        
        # 解析时间字符串并设置到控件
        try:
            dark_time = QTime.fromString(dark_start, "HH:mm")
            if dark_time.isValid():
                self.dark_start_time.setTime(dark_time)
        except:
            self.dark_start_time.setTime(QTime(19, 0))
        
        try:
            light_time = QTime.fromString(light_start, "HH:mm")
            if light_time.isValid():
                self.light_start_time.setTime(light_time)
        except:
            self.light_start_time.setTime(QTime(7, 0))
        
        # 启用/禁用时间控件
        self.dark_start_time.setEnabled(auto_switch)
        self.light_start_time.setEnabled(auto_switch)
    
    def _save_settings(self):
        """保存设置"""
        # ⭐ 重新加载最新配置（避免覆盖其他面板的修改）
        latest_config = {}
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    latest_config = json.load(f)
        except:
            latest_config = self.config
        
        # ⭐ 只更新浏览器配置的部分字段（保留 incognito_mode 等其他设置）
        if 'browser' not in latest_config:
            latest_config['browser'] = {}
        
        latest_config['browser']['chrome_path'] = self.chrome_path_input.text().strip()
        latest_config['browser']['headless'] = self.headless_checkbox.isChecked()
        # ⭐ incognito_mode 保持不变，不删除！
        
        if 'fingerprint' not in latest_config:
            latest_config['fingerprint'] = {}
        latest_config['fingerprint']['profile'] = self.profile_combo.currentText()
        
        # 更新本地配置引用
        self.config = latest_config
        
        # 主题设置
        auto_switch_enabled = self.auto_switch_checkbox.isChecked()
        dark_time = self.dark_start_time.time().toString("HH:mm")
        light_time = self.light_start_time.time().toString("HH:mm")
        
        # ⭐ 更新主题配置（保留其他可能存在的主题设置）
        if 'theme' not in self.config:
            self.config['theme'] = {}
        
        self.config['theme']['current_theme'] = self.theme_manager.get_current_theme()
        self.config['theme']['auto_switch'] = auto_switch_enabled
        self.config['theme']['dark_start_time'] = dark_time
        self.config['theme']['light_start_time'] = light_time
        
        # 应用自动切换设置到主题管理器
        try:
            self.theme_manager.set_auto_switch(auto_switch_enabled, dark_time, light_time)
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "警告", f"应用自动切换设置失败: {e}")
        
        # 保存到文件
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            
            self.accept()
            
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"保存配置失败: {e}")
    
    def get_config(self) -> dict:
        """获取当前配置"""
        return self.config.copy()


