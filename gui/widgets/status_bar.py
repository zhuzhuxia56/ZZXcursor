#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
状态栏组件
显示程序状态和统计信息
"""

from PyQt6.QtWidgets import QStatusBar, QLabel, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QFont
from datetime import datetime


class CustomStatusBar(QStatusBar):
    """自定义状态栏"""
    
    def __init__(self, parent=None):
        """
        初始化状态栏
        
        Args:
            parent: 父组件
        """
        super().__init__(parent)
        
        self._setup_ui()
        self._start_clock()
    
    def _setup_ui(self):
        """设置 UI"""
        # 账号总数标签
        self.account_count_label = QLabel("📋 账号总数: 0")
        self.addWidget(self.account_count_label)
        
        # 分隔符
        self.addWidget(QLabel("|"))
        
        # 最后刷新时间
        self.last_refresh_label = QLabel("🔄 最后刷新: 未刷新")
        self.addWidget(self.last_refresh_label)
        
        # 右侧：实时时钟
        self.addPermanentWidget(QLabel("|"))
        
        self.clock_label = QLabel()
        self.addPermanentWidget(self.clock_label)
    
    def _start_clock(self):
        """启动时钟"""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_clock)
        self.timer.start(1000)  # 每秒更新
        self._update_clock()
    
    def _update_clock(self):
        """更新时钟显示"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.clock_label.setText(f"🕐 {current_time}")
    
    def show_message(self, message: str, timeout: int = 0):
        """
        显示消息（带滑入动画）
        
        Args:
            message: 消息内容
            timeout: 超时时间（毫秒），0表示持续显示
        """
        # 创建临时消息标签（如果不存在）
        if not hasattr(self, 'temp_message_label'):
            self.temp_message_label = QLabel()
            self.insertWidget(0, self.temp_message_label, 1)
        
        # 设置消息内容
        self.temp_message_label.setText(message)
        
        # 滑入动画
        if not hasattr(self, 'temp_message_opacity'):
            self.temp_message_opacity = QGraphicsOpacityEffect(self.temp_message_label)
            self.temp_message_label.setGraphicsEffect(self.temp_message_opacity)
        
        fade_in = QPropertyAnimation(self.temp_message_opacity, b"opacity")
        fade_in.setDuration(300)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.OutQuad)
        fade_in.start()
        
        # 保存动画引用防止被回收
        self._message_fade_anim = fade_in
        
        # 设置超时
        if timeout > 0:
            QTimer.singleShot(timeout, self._hide_temp_message)
    
    def _hide_temp_message(self):
        """隐藏临时消息（淡出动画）"""
        if hasattr(self, 'temp_message_label') and hasattr(self, 'temp_message_opacity'):
            fade_out = QPropertyAnimation(self.temp_message_opacity, b"opacity")
            fade_out.setDuration(300)
            fade_out.setStartValue(1.0)
            fade_out.setEndValue(0.0)
            fade_out.setEasingCurve(QEasingCurve.Type.InQuad)
            fade_out.finished.connect(lambda: self.temp_message_label.clear())
            fade_out.start()
            
            self._message_fade_anim = fade_out
    
    def update_account_count(self, count: int):
        """
        更新账号总数（添加数字滚动动画）
        
        Args:
            count: 账号数量
        """
        # 获取旧值
        old_text = self.account_count_label.text()
        try:
            old_count = int(old_text.split(": ")[1])
        except:
            old_count = 0
        
        # 如果数字变化，启动滚动动画
        if old_count != count and count > 0:
            self._animate_count_change(self.account_count_label, old_count, count, "📋 账号总数: ")
        else:
            self.account_count_label.setText(f"📋 账号总数: {count}")
    
    def update_last_refresh(self):
        """更新最后刷新时间（带淡入效果）"""
        refresh_time = datetime.now().strftime("%H:%M:%S")
        old_text = self.last_refresh_label.text()
        self.last_refresh_label.setText(f"🔄 最后刷新: {refresh_time}")
        
        # 如果时间变化，添加淡入效果
        if old_text != self.last_refresh_label.text():
            if not hasattr(self, '_refresh_opacity'):
                self._refresh_opacity = QGraphicsOpacityEffect(self.last_refresh_label)
                self.last_refresh_label.setGraphicsEffect(self._refresh_opacity)
            
            flash = QPropertyAnimation(self._refresh_opacity, b"opacity")
            flash.setDuration(400)
            flash.setStartValue(0.3)
            flash.setEndValue(1.0)
            flash.setEasingCurve(QEasingCurve.Type.OutQuad)
            flash.start()
            
            self._refresh_flash_anim = flash
    
    def _animate_count_change(self, label: QLabel, from_value: int, to_value: int, prefix: str = ""):
        """
        数字滚动动画（简化版：直接更新，避免属性动画问题）
        
        Args:
            label: 目标标签
            from_value: 起始值
            to_value: 结束值
            prefix: 前缀文字
        """
        # 简化实现：使用定时器逐步更新数字
        steps = 20  # 20步完成
        step_value = (to_value - from_value) / steps
        current_step = [0]  # 使用列表避免闭包问题
        
        def update_number():
            current_step[0] += 1
            if current_step[0] <= steps:
                value = int(from_value + step_value * current_step[0])
                label.setText(f"{prefix}{value}")
                
                if current_step[0] < steps:
                    QTimer.singleShot(30, update_number)  # 30ms后继续
            else:
                # 确保最终值准确
                label.setText(f"{prefix}{to_value}")
        
        # 启动更新
        update_number()


