#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可旋转图标的按钮组件
用于刷新按钮的旋转动画
"""

from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import QTimer


class RotatingIconButton(QPushButton):
    """带旋转图标动画的按钮（使用Unicode符号序列）"""
    
    # 旋转图标序列（使用不同的旋转箭头符号）
    ROTATION_ICONS = ["🔄", "🔃", "🔄", "🔁", "🔄", "🔃"]
    
    def __init__(self, text: str = "🔄", parent=None):
        super().__init__(text, parent)
        
        self._default_text = text
        self._rotation_timer = None
        self._rotation_index = 0
        self._is_rotating = False
    
    def start_rotation(self):
        """启动连续旋转动画"""
        if self._is_rotating:
            return
        
        self._is_rotating = True
        self._rotation_index = 0
        
        # 创建旋转定时器
        if not self._rotation_timer:
            self._rotation_timer = QTimer(self)
            self._rotation_timer.timeout.connect(self._update_icon)
        
        # 每100ms切换一次图标（流畅度：10fps）
        self._rotation_timer.start(100)
    
    def stop_rotation(self):
        """停止旋转动画"""
        if not self._is_rotating:
            return
        
        self._is_rotating = False
        
        if self._rotation_timer:
            self._rotation_timer.stop()
        
        # 恢复默认图标
        self.setText(self._default_text)
        self._rotation_index = 0
    
    def _update_icon(self):
        """更新旋转图标"""
        if not self._is_rotating:
            return
        
        # 循环显示旋转图标
        icon = self.ROTATION_ICONS[self._rotation_index]
        self.setText(icon)
        
        # 移到下一个图标
        self._rotation_index = (self._rotation_index + 1) % len(self.ROTATION_ICONS)
