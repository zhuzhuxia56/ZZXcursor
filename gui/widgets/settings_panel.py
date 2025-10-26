#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设置面板
包含主题、动画、性能等各种设置选项
"""

import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QCheckBox, QComboBox, QSpinBox,
    QPushButton, QTimeEdit, QScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt, QTime, pyqtSignal
from PyQt6.QtGui import QFont, QMovie

from utils.logger import get_logger
from utils.theme_manager import get_theme_manager
from utils.app_paths import get_config_file
from utils.resource_path import get_gui_resource

logger = get_logger("settings_panel")


class SettingsPanel(QWidget):
    """设置面板"""
    
    # 信号
    settings_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 使用用户目录的配置文件路径
        self.config_path = get_config_file()
        self.config = self._load_config()
        self.theme_manager = get_theme_manager(str(self.config_path))
        
        # ⭐ 激活倒计时定时器（每秒更新）
        from PyQt6.QtCore import QTimer
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self._update_activation_countdown)
        self.countdown_timer.start(1000)  # 每秒更新
        
        self._setup_ui()
        self._load_settings()
    
    def _load_config(self) -> dict:
        """加载配置文件"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
        
        return {}
    
    def _save_config(self):
        """保存配置文件"""
        try:
            # ⭐ 记录保存操作
            logger.info(f"开始保存设置配置到: {self.config_path}")
            
            # 确保目录存在
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存配置
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            
            # ⭐ 验证保存
            with open(self.config_path, 'r', encoding='utf-8') as f:
                verify_config = json.load(f)
            logger.info(f"✅ 设置配置验证成功，配置项数: {len(verify_config)}")
            
            logger.info("✅ 设置配置已保存")
            return True
        except PermissionError as e:
            logger.error(f"❌ 权限错误: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "保存失败",
                f"❌ 无法保存配置文件，权限不足。\n\n"
                f"📁 文件位置：\n{self.config_path}\n\n"
                f"请以管理员身份运行程序。"
            )
            return False
        except Exception as e:
            logger.error(f"❌ 保存配置失败: {e}", exc_info=True)
            return False
    
    def _setup_ui(self):
        """设置UI"""
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setObjectName("SettingsScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        
        # 内容容器
        content = QWidget()
        content.setObjectName("SettingsContent")
        scroll.setWidget(content)
        
        # 主布局
        wrapper_layout = QVBoxLayout(self)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(scroll)
        
        # 内容布局
        main_layout = QVBoxLayout(content)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # 标题
        title = QLabel("⚙️ 系统设置")
        title.setProperty("heading", True)
        main_layout.addWidget(title)
        
        # ========== 主题设置组 ==========
        theme_group = self._create_theme_settings()
        main_layout.addWidget(theme_group)
        
        # ========== UI动画设置组 ==========
        animation_group = self._create_animation_settings()
        main_layout.addWidget(animation_group)
        
        # ========== 性能设置组 ==========
        performance_group = self._create_performance_settings()
        main_layout.addWidget(performance_group)
        
        # ========== 浏览器设置组 ==========
        browser_group = self._create_browser_settings()
        main_layout.addWidget(browser_group)
        
        # ========== 自动检测设置组 ==========
        auto_detect_group = self._create_auto_detect_settings()
        main_layout.addWidget(auto_detect_group)
        
        # ========== 激活码绑定组 ==========
        activation_group = self._create_activation_settings()
        main_layout.addWidget(activation_group)
        
        # ========== 操作按钮 ==========
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton("💾 保存设置")
        save_btn.setProperty("primary", True)
        save_btn.setMinimumWidth(120)
        save_btn.clicked.connect(self._save_settings)
        button_layout.addWidget(save_btn)
        
        reset_btn = QPushButton("🔄 恢复默认")
        reset_btn.setProperty("secondary", True)
        reset_btn.setMinimumWidth(120)
        reset_btn.clicked.connect(self._reset_settings)
        button_layout.addWidget(reset_btn)
        
        main_layout.addLayout(button_layout)
        
        main_layout.addStretch()
    
    def _create_theme_settings(self) -> QGroupBox:
        """创建主题设置组"""
        group = QGroupBox("🎨 主题设置")
        main_layout = QHBoxLayout(group)
        main_layout.setSpacing(15)
        
        # 左侧：设置项
        left_widget = QWidget()
        layout = QVBoxLayout(left_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # 当前主题显示
        current_theme_layout = QHBoxLayout()
        current_theme_layout.addWidget(QLabel("当前主题:"))
        self.current_theme_label = QLabel()
        current_theme_layout.addWidget(self.current_theme_label)
        current_theme_layout.addStretch()
        layout.addLayout(current_theme_layout)
        
        # 自动切换开关
        self.auto_switch_checkbox = QCheckBox("启用自动切换深色/浅色模式")
        self.auto_switch_checkbox.stateChanged.connect(self._on_auto_switch_changed)
        layout.addWidget(self.auto_switch_checkbox)
        
        # 时间设置（缩进显示）
        time_container = QWidget()
        time_layout = QVBoxLayout(time_container)
        time_layout.setContentsMargins(30, 10, 0, 0)
        time_layout.setSpacing(12)
        
        # 深色模式开始时间
        dark_time_layout = QHBoxLayout()
        dark_time_layout.addWidget(QLabel("🌙 深色模式开始时间:"))
        self.dark_start_time = QTimeEdit()
        self.dark_start_time.setDisplayFormat("HH:mm")
        self.dark_start_time.setTime(QTime(19, 0))  # 默认19:00
        dark_time_layout.addWidget(self.dark_start_time)
        dark_time_layout.addStretch()
        time_layout.addLayout(dark_time_layout)
        
        # 浅色模式开始时间
        light_time_layout = QHBoxLayout()
        light_time_layout.addWidget(QLabel("☀️ 浅色模式开始时间:"))
        self.light_start_time = QTimeEdit()
        self.light_start_time.setDisplayFormat("HH:mm")
        self.light_start_time.setTime(QTime(7, 0))  # 默认07:00
        light_time_layout.addWidget(self.light_start_time)
        light_time_layout.addStretch()
        time_layout.addLayout(light_time_layout)
        
        # 提示
        hint = QLabel("💡 例如：19:00切换到深色，次日07:00切换回浅色")
        hint.setStyleSheet("color: #888; font-size: 11px; padding: 5px 0;")
        hint.setWordWrap(True)
        time_layout.addWidget(hint)
        
        self.time_container = time_container
        layout.addWidget(time_container)
        
        layout.addStretch()
        main_layout.addWidget(left_widget, stretch=2)
        
        # 右侧：可爱动图
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 动图标签
        gif_label = QLabel()
        gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 加载并播放 GIF
        gif_path = get_gui_resource("zhuzhuxia.gif")
        if gif_path.exists():
            movie = QMovie(str(gif_path))
            # 设置缩放大小
            movie.setScaledSize(movie.scaledSize().scaled(180, 180, Qt.AspectRatioMode.KeepAspectRatio))
            gif_label.setMovie(movie)
            movie.start()
        else:
            gif_label.setText("🐷")
            gif_label.setStyleSheet("font-size: 60px;")
        
        right_layout.addStretch()
        right_layout.addWidget(gif_label)
        right_layout.addStretch()
        
        main_layout.addWidget(right_widget, stretch=1)
        
        return group
    
    def _create_animation_settings(self) -> QGroupBox:
        """创建UI动画设置组"""
        group = QGroupBox("🎬 UI动画设置")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        
        # 启用动画
        self.enable_animations_checkbox = QCheckBox("启用UI动画效果")
        layout.addWidget(self.enable_animations_checkbox)
        
        # 动画速度
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("动画速度:"))
        self.animation_speed_combo = QComboBox()
        self.animation_speed_combo.addItems(["快速", "正常", "慢速"])
        speed_layout.addWidget(self.animation_speed_combo)
        speed_layout.addStretch()
        layout.addLayout(speed_layout)
        
        # 减少动效（无障碍功能）
        self.reduce_motion_checkbox = QCheckBox("减少动效（适合性能较弱的电脑）")
        layout.addWidget(self.reduce_motion_checkbox)
        
        # 提示
        hint = QLabel("💡 禁用动画可以提升性能，适合老旧电脑")
        hint.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(hint)
        
        return group
    
    def _create_performance_settings(self) -> QGroupBox:
        """创建性能设置组"""
        group = QGroupBox("⚡ 性能设置")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        
        # 批量刷新并发数（带锁定功能）
        concurrent_layout = QHBoxLayout()
        concurrent_layout.addWidget(QLabel("批量刷新并发数:"))
        
        self.batch_concurrent_spin = QSpinBox()
        self.batch_concurrent_spin.setMinimum(1)
        self.batch_concurrent_spin.setMaximum(5)
        self.batch_concurrent_spin.setValue(2)
        self.batch_concurrent_spin.setSuffix(" 个")
        self.batch_concurrent_spin.setEnabled(False)  # ⭐ 默认锁定
        concurrent_layout.addWidget(self.batch_concurrent_spin)
        
        # ⭐ 锁定/解锁按钮
        self.concurrent_lock_btn = QPushButton("🔒 点击解锁")
        self.concurrent_lock_btn.setProperty("secondary", True)
        self.concurrent_lock_btn.setFixedWidth(100)
        self.concurrent_lock_btn.clicked.connect(self._toggle_concurrent_lock)
        self.concurrent_locked = True  # 锁定状态
        concurrent_layout.addWidget(self.concurrent_lock_btn)
        
        concurrent_layout.addStretch()
        layout.addLayout(concurrent_layout)
        
        # ⭐ 并发数说明（带警告）
        concurrent_hint = QLabel("⚠️ 默认2个最稳定！改动需谨慎：\n• 并发数过高可能触发API限流(429错误)\n• 建议保持默认值，除非你知道自己在做什么")
        concurrent_hint.setStyleSheet("color: #ff6600; font-size: 11px; font-weight: bold;")
        concurrent_hint.setWordWrap(True)
        layout.addWidget(concurrent_hint)
        
        # 布局缓存阈值
        cache_layout = QHBoxLayout()
        cache_layout.addWidget(QLabel("布局缓存阈值:"))
        self.cache_threshold_spin = QSpinBox()
        self.cache_threshold_spin.setMinimum(5)
        self.cache_threshold_spin.setMaximum(50)
        self.cache_threshold_spin.setValue(10)
        self.cache_threshold_spin.setSuffix(" px")
        cache_layout.addWidget(self.cache_threshold_spin)
        cache_layout.addStretch()
        layout.addLayout(cache_layout)
        
        # 防抖延迟
        debounce_layout = QHBoxLayout()
        debounce_layout.addWidget(QLabel("批量更新防抖:"))
        self.debounce_spin = QSpinBox()
        self.debounce_spin.setMinimum(50)
        self.debounce_spin.setMaximum(500)
        self.debounce_spin.setValue(200)
        self.debounce_spin.setSuffix(" ms")
        debounce_layout.addWidget(self.debounce_spin)
        debounce_layout.addStretch()
        layout.addLayout(debounce_layout)
        
        # 提示
        hint = QLabel("💡 并发数越高刷新越快，但可能触发API限制；\n阈值越大性能越好，但响应式布局不够灵敏")
        hint.setStyleSheet("color: #888; font-size: 11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        
        return group
    
    def _create_browser_settings(self) -> QGroupBox:
        """创建浏览器设置组"""
        group = QGroupBox("🌐 浏览器设置")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        
        # 无痕模式开关
        self.incognito_checkbox = QCheckBox("启用无痕模式（推荐）")
        self.incognito_checkbox.setChecked(True)  # 默认启用
        layout.addWidget(self.incognito_checkbox)
        
        # 提示说明
        hint_text = (
            "<b>💡 无痕模式说明：</b><br><br>"
            "<b style='color: #27ae60;'>✅ 启用时（推荐）：</b><br>"
            "  • Cookie 不会保留，每次都是全新环境<br>"
            "  • 浏览器扩展配置不会保存<br>"
            "  • 更安全，不留注册痕迹<br>"
            "  • 适合批量注册<br><br>"
            "<b style='color: #e67e22;'>❌ 禁用时：</b><br>"
            "  • Cookie 会保留在浏览器中<br>"
            "  • 浏览器扩展配置会保留<br>"
            "  • 可以手动添加扩展，下次注册时仍然存在<br>"
            "  • 可能留下注册痕迹<br><br>"
            "<b style='color: #3498db;'>📍 浏览器数据目录：</b><br>"
            f"  <code style='background: #34495e; padding: 2px 6px; border-radius: 3px;'>"
            f"C:\\Users\\..\\AppData\\Local\\Temp\\zzx_cursor_auto_browser</code>"
        )
        hint = QLabel(hint_text)
        hint.setStyleSheet("color: #888; font-size: 11px; padding: 10px; background: #2c3e50; border-radius: 5px;")
        hint.setWordWrap(True)
        hint.setOpenExternalLinks(True)
        layout.addWidget(hint)
        
        return group
    
    def _create_auto_detect_settings(self) -> QGroupBox:
        """创建自动检测设置组"""
        group = QGroupBox("🔍 自动检测设置")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        
        # 启用自动检测
        self.auto_detect_checkbox = QCheckBox("启用后台自动检测当前账号")
        layout.addWidget(self.auto_detect_checkbox)
        
        # 检测间隔
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("检测间隔:"))
        self.detect_interval_spin = QSpinBox()
        self.detect_interval_spin.setMinimum(10)
        self.detect_interval_spin.setMaximum(300)
        self.detect_interval_spin.setValue(30)
        self.detect_interval_spin.setSuffix(" 秒")
        interval_layout.addWidget(self.detect_interval_spin)
        interval_layout.addStretch()
        layout.addLayout(interval_layout)
        
        # 提示
        hint = QLabel("💡 自动检测会定期读取Cursor配置，可能影响性能\n建议禁用，仅在启动时检测一次")
        hint.setStyleSheet("color: #888; font-size: 11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        
        return group
    
    def _create_activation_settings(self) -> QGroupBox:
        """创建激活码绑定设置组"""
        group = QGroupBox("🎫 激活码绑定")
        layout = QVBoxLayout(group)
        layout.setSpacing(15)
        
        # ⭐ 激活状态显示
        self.activation_status_label = QLabel("状态：加载中...")
        self.activation_status_label.setStyleSheet("font-size: 13px; font-weight: bold;")
        layout.addWidget(self.activation_status_label)
        
        # ⭐ 使用横向布局：左侧二维码 + 右侧输入
        qr_and_input_layout = QHBoxLayout()
        
        # 左侧：二维码
        qr_container = QWidget()
        qr_layout = QVBoxLayout(qr_container)
        qr_layout.setSpacing(8)
        
        qr_label = QLabel("扫码进入小程序获取激活码：")
        qr_label.setStyleSheet("font-size: 12px;")
        qr_layout.addWidget(qr_label)
        
        # ⭐ 二维码图片
        from PyQt6.QtWidgets import QLabel as QLabelImage
        from PyQt6.QtGui import QPixmap
        from pathlib import Path
        
        self.qr_image_label = QLabelImage()
        self.qr_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_image_label.setStyleSheet("border: 2px solid #ddd; border-radius: 8px; padding: 5px; background: white;")
        
        # ⭐ 加载二维码图片（使用软件内部资源路径）
        qr_path = get_gui_resource("wechat_qr.jpg")
        if qr_path.exists():
            pixmap = QPixmap(str(qr_path))
            scaled_pixmap = pixmap.scaled(180, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.qr_image_label.setPixmap(scaled_pixmap)
            logger.info(f"✅ 二维码图片已加载: {qr_path}")
        else:
            self.qr_image_label.setText("二维码图片\n未找到")
            self.qr_image_label.setFixedSize(180, 180)
            logger.warning(f"❌ 二维码图片未找到: {qr_path}")
        
        qr_layout.addWidget(self.qr_image_label)
        qr_and_input_layout.addWidget(qr_container)
        
        # 右侧：激活码输入
        input_container = QWidget()
        input_layout = QVBoxLayout(input_container)
        input_layout.setSpacing(12)
        
        input_label = QLabel("输入激活码：")
        input_label.setStyleSheet("font-size: 12px;")
        input_layout.addWidget(input_label)
        
        # 激活码输入框
        from PyQt6.QtWidgets import QLineEdit
        self.activation_code_input = QLineEdit()
        self.activation_code_input.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.activation_code_input.setMaxLength(19)  # 16位+3个横杠
        input_layout.addWidget(self.activation_code_input)
        
        # 绑定按钮
        bind_btn = QPushButton("🔗 绑定激活码")
        bind_btn.setProperty("success", True)
        bind_btn.clicked.connect(self._on_bind_activation_code)
        input_layout.addWidget(bind_btn)
        
        # 解绑按钮
        self.unbind_btn = QPushButton("🔓 解绑设备")
        self.unbind_btn.setProperty("danger", True)
        self.unbind_btn.clicked.connect(self._on_unbind)
        self.unbind_btn.setEnabled(False)
        input_layout.addWidget(self.unbind_btn)
        
        # 设备ID显示
        self.device_id_label = QLabel("设备ID：加载中...")
        self.device_id_label.setStyleSheet("color: #888; font-size: 10px;")
        self.device_id_label.setWordWrap(True)
        input_layout.addWidget(self.device_id_label)
        
        input_layout.addStretch()
        qr_and_input_layout.addWidget(input_container, 1)
        
        layout.addLayout(qr_and_input_layout)
        
        # 说明文字
        hint = QLabel(
            "💡 激活说明：\n"
            "• 未激活设备：每天只能注册 5 个账号\n"
            "• 激活后：每天可无限次使用自动注册\n"
            "• 每个激活码只能绑定一个设备，绑定后立即失效\n"
            "• 激活状态永久有效，除非手动解绑"
        )
        hint.setStyleSheet("color: #888; font-size: 11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        
        return group
    
    def _on_auto_switch_changed(self, state):
        """自动切换开关改变"""
        # 启用/禁用时间设置
        enabled = (state == Qt.CheckState.Checked.value)
        self.time_container.setEnabled(enabled)
    
    def _toggle_concurrent_lock(self):
        """切换并发数锁定状态"""
        self.concurrent_locked = not self.concurrent_locked
        
        if self.concurrent_locked:
            # 锁定状态
            self.batch_concurrent_spin.setEnabled(False)
            self.concurrent_lock_btn.setText("🔒 点击解锁")
            self.concurrent_lock_btn.setProperty("danger", False)
            self.concurrent_lock_btn.setProperty("secondary", True)
            self.concurrent_lock_btn.setStyleSheet("")  # 清除样式
            self.concurrent_lock_btn.style().unpolish(self.concurrent_lock_btn)
            self.concurrent_lock_btn.style().polish(self.concurrent_lock_btn)
        else:
            # 解锁状态（显示为危险红色）
            self.batch_concurrent_spin.setEnabled(True)
            self.concurrent_lock_btn.setText("🔓 已解锁")
            self.concurrent_lock_btn.setProperty("secondary", False)
            self.concurrent_lock_btn.setProperty("danger", True)
            self.concurrent_lock_btn.setStyleSheet("")  # 清除样式
            self.concurrent_lock_btn.style().unpolish(self.concurrent_lock_btn)
            self.concurrent_lock_btn.style().polish(self.concurrent_lock_btn)
    
    def _on_bind_activation_code(self):
        """绑定激活码"""
        try:
            code = self.activation_code_input.text().strip().upper()
            
            if not code:
                QMessageBox.warning(self, "提示", "请输入激活码")
                return
            
            # ⭐ 使用新的激活管理器
            from core.machine_id_manager import get_machine_id_manager
            from core.activation_manager import get_activation_manager
            
            machine_mgr = get_machine_id_manager()
            activation_mgr = get_activation_manager()
            
            # 获取机器码
            machine_id = machine_mgr.load_machine_id()
            if not machine_id:
                machine_id = machine_mgr.get_machine_id()
                machine_mgr.save_machine_id(machine_id)
            
            # 激活
            success, message = activation_mgr.activate(code, machine_id)
            
            if success:
                # 创建自定义对话框（带动图，无系统声音）
                from PyQt6.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
                from PyQt6.QtGui import QMovie
                from PyQt6.QtCore import Qt, QSize
                from pathlib import Path
                
                dialog = QDialog(self)
                dialog.setWindowTitle("激活成功")
                dialog.setFixedSize(550, 280)
                
                # 禁用系统声音
                dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
                
                # 主布局
                main_layout = QHBoxLayout(dialog)
                main_layout.setSpacing(15)
                main_layout.setContentsMargins(20, 20, 20, 20)
                
                # 左侧：动图
                gif_label = QLabel()
                gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                gif_path = get_gui_resource("warning_save.gif")
                if gif_path.exists():
                    movie = QMovie(str(gif_path))
                    movie.setScaledSize(QSize(150, 150))
                    gif_label.setMovie(movie)
                    movie.start()
                else:
                    gif_label.setText("✅")
                    gif_label.setStyleSheet("font-size: 80px;")
                
                main_layout.addWidget(gif_label)
                
                # 右侧：信息和按钮
                right_layout = QVBoxLayout()
                right_layout.setSpacing(10)
                
                # 成功图标
                success_icon = QLabel("✅ 激活成功！ 每日注册无限制")
                success_icon.setStyleSheet("font-size: 16px; font-weight: bold; color: #27ae60;")
                right_layout.addWidget(success_icon)
                
                # 激活信息
                info_text = QLabel(
                    f"激活码：{code}\n"
                    f"设备ID：{machine_id[:16]}...\n\n"
                    f"🎉 激活后每天可无限次使用自动注册！\n"
                    f"激活状态将永久保留"
                )
                info_text.setWordWrap(True)
                info_text.setStyleSheet("font-size: 13px; line-height: 1.6;")
                right_layout.addWidget(info_text)
                
                right_layout.addStretch()
                
                # OK按钮
                ok_btn = QPushButton("OK")
                ok_btn.setFixedWidth(100)
                ok_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #5e72e4;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        padding: 8px 16px;
                        font-weight: bold;
                        font-size: 13px;
                    }
                    QPushButton:hover {
                        background-color: #4c63d2;
                    }
                """)
                ok_btn.clicked.connect(dialog.accept)
                
                btn_layout = QHBoxLayout()
                btn_layout.addStretch()
                btn_layout.addWidget(ok_btn)
                right_layout.addLayout(btn_layout)
                
                main_layout.addLayout(right_layout, stretch=1)
                
                # 显示对话框（无系统声音）
                dialog.exec()
                
                # 更新显示
                self._update_activation_display()
                
                # 清空输入框
                self.activation_code_input.clear()
            else:
                # 失败时也禁用系统声音
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setWindowTitle("激活失败")
                msg_box.setText(f"❌ {message}")
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                # 禁用系统声音
                msg_box.setWindowFlags(msg_box.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
                msg_box.exec()
            
        except Exception as e:
            logger.error(f"绑定激活码失败: {e}")
            QMessageBox.critical(self, "错误", f"绑定失败：\n{e}")
    
    def _on_unbind(self):
        """解绑设备"""
        reply = QMessageBox.question(
            self,
            "确认解绑",
            "确定要解绑当前设备吗？\n\n"
            "解绑后将恢复每日5个账号的限制",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                from core.activation_manager import get_activation_manager
                activation_mgr = get_activation_manager()
                
                if activation_mgr.deactivate():
                    QMessageBox.information(self, "解绑成功", "✅ 设备已解绑\n\n恢复每日5个账号限制")
                    self._update_activation_display()
                else:
                    QMessageBox.warning(self, "解绑失败", "❌ 解绑失败")
            except Exception as e:
                logger.error(f"解绑失败: {e}")
                QMessageBox.critical(self, "错误", f"解绑失败：\n{e}")
    
    def _update_activation_countdown(self):
        """更新激活状态显示（每秒调用）"""
        try:
            from core.activation_manager import get_activation_manager
            
            activation_mgr = get_activation_manager()
            
            # 获取激活信息
            if activation_mgr.is_activated():
                # 已激活（永久有效）
                self.activation_status_label.setText("状态：✅ 已激活（每天无限注册）")
                self.activation_status_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #4caf50;")
            else:
                # 未激活，显示今日限制
                today_used = activation_mgr.get_today_registered_count()
                daily_limit = activation_mgr.get_daily_limit()
                remaining = daily_limit - today_used
                
                self.activation_status_label.setText(f"状态：❌ 未激活（今日剩余：{remaining}/{daily_limit}）")
                
                if remaining > 0:
                    self.activation_status_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffa500;")
                else:
                    self.activation_status_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #e74c3c;")
        except:
            pass
    
    def _update_activation_display(self):
        """更新激活状态显示"""
        try:
            from core.machine_id_manager import get_machine_id_manager
            from core.activation_manager import get_activation_manager
            
            machine_mgr = get_machine_id_manager()
            activation_mgr = get_activation_manager()
            
            # 获取机器码
            machine_id = machine_mgr.load_machine_id()
            if not machine_id:
                machine_id = machine_mgr.get_machine_id()
            
            # 显示设备ID
            self.device_id_label.setText(f"设备ID：{machine_id[:16]}...")
            
            # 检查激活状态
            if activation_mgr.is_activated():
                # 已激活
                activation_info = activation_mgr.get_activation_info()
                code = activation_info.get('activation_code', '')
                
                self.activation_status_label.setText(f"状态：✅ 已激活（每天无限注册）")
                self.activation_status_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #4caf50;")
                
                self.activation_code_input.setEnabled(False)
                self.unbind_btn.setEnabled(True)
            else:
                # 未激活
                today_used = activation_mgr.get_today_registered_count()
                daily_limit = activation_mgr.get_daily_limit()
                remaining = daily_limit - today_used
                
                self.activation_status_label.setText(f"状态：❌ 未激活（今日剩余：{remaining}/{daily_limit}）")
                
                if remaining > 0:
                    self.activation_status_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffa500;")
                else:
                    self.activation_status_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #e74c3c;")
                
                self.activation_code_input.setEnabled(True)
                self.unbind_btn.setEnabled(False)
            
        except Exception as e:
            logger.error(f"更新激活状态失败: {e}")
            self.activation_status_label.setText("状态：加载失败")
            self.device_id_label.setText("设备ID：加载失败")
    
    def _load_settings(self):
        """加载设置到UI"""
        try:
            # ========== 主题设置 ==========
            theme_config = self.config.get('theme', {})
            
            # 当前主题
            current_theme = self.theme_manager.get_current_theme()
            theme_text = "🌙 深色模式" if current_theme == "dark" else "☀️ 浅色模式"
            self.current_theme_label.setText(theme_text)
            
            # 自动切换
            auto_switch = theme_config.get('auto_switch', False)
            self.auto_switch_checkbox.setChecked(auto_switch)
            
            # 切换时间
            dark_start = theme_config.get('dark_start_time', '19:00')
            light_start = theme_config.get('light_start_time', '07:00')
            
            dark_hour, dark_min = map(int, dark_start.split(':'))
            self.dark_start_time.setTime(QTime(dark_hour, dark_min))
            
            light_hour, light_min = map(int, light_start.split(':'))
            self.light_start_time.setTime(QTime(light_hour, light_min))
            
            # 启用/禁用时间设置
            self.time_container.setEnabled(auto_switch)
            
            # ========== UI动画设置 ==========
            ui_config = self.config.get('ui', {})
            
            enable_animations = ui_config.get('enable_animations', True)
            self.enable_animations_checkbox.setChecked(enable_animations)
            
            animation_speed = ui_config.get('animation_speed', 'normal')
            speed_map = {'fast': 0, 'normal': 1, 'slow': 2}
            self.animation_speed_combo.setCurrentIndex(speed_map.get(animation_speed, 1))
            
            reduce_motion = ui_config.get('reduce_motion', False)
            self.reduce_motion_checkbox.setChecked(reduce_motion)
            
            # ========== 性能设置 ==========
            performance_config = self.config.get('performance', {})
            
            batch_concurrent = performance_config.get('batch_concurrent', 2)
            self.batch_concurrent_spin.setValue(batch_concurrent)
            # ⭐ 加载后确保锁定状态
            self.concurrent_locked = True
            self.batch_concurrent_spin.setEnabled(False)
            self.concurrent_lock_btn.setText("🔒 点击解锁")
            
            cache_threshold = performance_config.get('cache_threshold', 10)
            self.cache_threshold_spin.setValue(cache_threshold)
            
            debounce_delay = performance_config.get('debounce_delay', 200)
            self.debounce_spin.setValue(debounce_delay)
            
            # ========== 浏览器设置 ==========
            browser_config = self.config.get('browser', {})
            incognito_mode = browser_config.get('incognito_mode', True)  # 默认启用
            self.incognito_checkbox.setChecked(incognito_mode)
            
            # ========== 自动检测设置 ==========
            cursor_config = self.config.get('cursor', {})
            
            auto_detect = cursor_config.get('auto_detect', False)
            self.auto_detect_checkbox.setChecked(auto_detect)
            
            detect_interval = cursor_config.get('detect_interval', 30)
            self.detect_interval_spin.setValue(detect_interval)
            
            # ========== 激活状态显示 ==========
            self._update_activation_display()
            
        except Exception as e:
            logger.error(f"加载设置失败: {e}")
    
    def _save_settings(self):
        """保存设置"""
        try:
            # ⭐ 如果并发数被修改且不是默认值2，显示警告
            concurrent_value = self.batch_concurrent_spin.value()
            if concurrent_value != 2 and not self.concurrent_locked:
                reply = QMessageBox.warning(
                    self,
                    "⚠️ 警告",
                    f"你将批量刷新并发数设置为 {concurrent_value} 个！\n\n"
                    f"默认值2个是最稳定的配置。\n"
                    f"并发数过高可能导致：\n"
                    f"• API限流(429错误)\n"
                    f"• 账号被风控\n"
                    f"• 刷新失败率增加\n\n"
                    f"确定要修改吗？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.No:
                    # 用户取消，恢复为2
                    self.batch_concurrent_spin.setValue(2)
                    return
            
            # ⭐ 重新加载最新配置（避免覆盖其他面板的修改）
            latest_config = self._load_config()
            
            # ========== 主题设置 ==========
            if 'theme' not in latest_config:
                latest_config['theme'] = {}
            
            auto_switch = self.auto_switch_checkbox.isChecked()
            latest_config['theme']['auto_switch'] = auto_switch
            
            dark_time = self.dark_start_time.time()
            latest_config['theme']['dark_start_time'] = dark_time.toString("HH:mm")
            
            light_time = self.light_start_time.time()
            latest_config['theme']['light_start_time'] = light_time.toString("HH:mm")
            
            # ========== UI动画设置 ==========
            if 'ui' not in latest_config:
                latest_config['ui'] = {}
            
            latest_config['ui']['enable_animations'] = self.enable_animations_checkbox.isChecked()
            
            speed_map = {0: 'fast', 1: 'normal', 2: 'slow'}
            latest_config['ui']['animation_speed'] = speed_map.get(
                self.animation_speed_combo.currentIndex(), 'normal'
            )
            
            latest_config['ui']['reduce_motion'] = self.reduce_motion_checkbox.isChecked()
            
            # ========== 性能设置 ==========
            if 'performance' not in latest_config:
                latest_config['performance'] = {}
            
            latest_config['performance']['batch_concurrent'] = concurrent_value  # ⭐ 使用验证后的值
            latest_config['performance']['cache_threshold'] = self.cache_threshold_spin.value()
            latest_config['performance']['debounce_delay'] = self.debounce_spin.value()
            
            # ========== 浏览器设置 ==========
            if 'browser' not in latest_config:
                latest_config['browser'] = {}
            
            latest_config['browser']['incognito_mode'] = self.incognito_checkbox.isChecked()
            
            # ========== 自动检测设置 ==========
            if 'cursor' not in latest_config:
                latest_config['cursor'] = {}
            
            latest_config['cursor']['auto_detect'] = self.auto_detect_checkbox.isChecked()
            latest_config['cursor']['detect_interval'] = self.detect_interval_spin.value()
            
            # ⭐ 更新本地配置引用
            self.config = latest_config
            
            # 保存到文件
            if self._save_config():
                # ⭐ 应用主题自动切换设置
                self.theme_manager.set_auto_switch(
                    auto_switch,
                    self.dark_start_time.time().toString("HH:mm"),
                    self.light_start_time.time().toString("HH:mm")
                )
                
                # ⭐ 保存成功后，重新锁定并发数（安全措施）
                if not self.concurrent_locked:
                    self.concurrent_locked = True
                    self.batch_concurrent_spin.setEnabled(False)
                    self.concurrent_lock_btn.setText("🔒 点击解锁")
                    self.concurrent_lock_btn.setProperty("secondary", True)
                    self.concurrent_lock_btn.style().unpolish(self.concurrent_lock_btn)
                    self.concurrent_lock_btn.style().polish(self.concurrent_lock_btn)
                
                # 发出设置改变信号
                self.settings_changed.emit()
                
                # ⭐ 根据是否修改并发数显示不同提示
                if concurrent_value != 2:
                    QMessageBox.information(
                        self,
                        "保存成功",
                        f"✅ 设置已保存！\n\n"
                        f"批量刷新并发数已设为: {concurrent_value} 个\n"
                        f"⚠️ 请注意观察刷新是否稳定\n\n"
                        f"部分设置需要重启程序后生效"
                    )
                else:
                    QMessageBox.information(
                        self,
                        "保存成功",
                        "✅ 设置已保存！\n\n部分设置需要重启程序后生效"
                    )
            else:
                QMessageBox.warning(self, "保存失败", "❌ 保存配置文件失败")
                
        except Exception as e:
            logger.error(f"保存设置失败: {e}")
            QMessageBox.critical(self, "错误", f"保存失败:\n{e}")
    
    def _reset_settings(self):
        """恢复默认设置"""
        reply = QMessageBox.question(
            self,
            "确认恢复",
            "确定要恢复所有设置为默认值吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 设置默认值
            self.auto_switch_checkbox.setChecked(False)
            self.dark_start_time.setTime(QTime(19, 0))
            self.light_start_time.setTime(QTime(7, 0))
            
            self.enable_animations_checkbox.setChecked(True)
            self.animation_speed_combo.setCurrentIndex(1)
            self.reduce_motion_checkbox.setChecked(False)
            
            # ⭐ 并发数恢复为2并重新锁定
            self.batch_concurrent_spin.setValue(2)
            if not self.concurrent_locked:
                self.concurrent_locked = True
                self.batch_concurrent_spin.setEnabled(False)
                self.concurrent_lock_btn.setText("🔒 点击解锁")
                self.concurrent_lock_btn.setProperty("secondary", True)
                self.concurrent_lock_btn.style().unpolish(self.concurrent_lock_btn)
                self.concurrent_lock_btn.style().polish(self.concurrent_lock_btn)
            
            self.cache_threshold_spin.setValue(10)
            self.debounce_spin.setValue(200)
            
            # 浏览器设置
            self.incognito_checkbox.setChecked(True)  # 默认启用无痕模式
            
            self.auto_detect_checkbox.setChecked(False)
            self.detect_interval_spin.setValue(30)
            
            QMessageBox.information(self, "恢复完成", "✅ 已恢复默认设置\n\n请点击「保存设置」以应用")

