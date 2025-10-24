#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
带动画效果的对话框基类
实现 macOS 风格的对话框动画
"""

from PyQt6.QtWidgets import QDialog, QGraphicsOpacityEffect, QGraphicsDropShadowEffect
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QSize
from PyQt6.QtGui import QColor


class AnimatedDialog(QDialog):
    """带动画效果的对话框基类"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._enter_animation = None
        self._exit_animation = None
        self._original_size = None
        
        # 设置对话框样式
        self._setup_effects()
    
    def _setup_effects(self):
        """设置视觉效果（暖粉主题）"""
        # 添加暖粉色阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(35)
        shadow.setColor(QColor(255, 154, 158, 60))  # 暖粉色阴影
        shadow.setOffset(0, 6)
        self.setGraphicsEffect(shadow)
    
    def showEvent(self, event):
        """显示事件（播放进入动画）"""
        super().showEvent(event)
        
        # 记录原始尺寸
        if not self._original_size:
            self._original_size = self.size()
        
        # 播放进入动画
        self._play_enter_animation()
    
    def _play_enter_animation(self):
        """播放进入动画（优化版：只淡入，不缩放，避免闪烁）"""
        # 创建透明度效果
        opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(opacity_effect)
        
        # ⭐ 只播放快速淡入动画（不缩放，避免闪烁）
        opacity_anim = QPropertyAnimation(opacity_effect, b"opacity")
        opacity_anim.setDuration(150)  # ⭐ 缩短到150ms，更快
        opacity_anim.setStartValue(0.0)
        opacity_anim.setEndValue(1.0)
        opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)  # ⭐ 更平滑的曲线
        
        # 动画完成后恢复阴影效果
        opacity_anim.finished.connect(self._setup_effects)
        
        opacity_anim.start()
        self._enter_animation = opacity_anim
    
    def closeEvent(self, event):
        """关闭事件（播放退出动画）"""
        # 先接受事件
        event.accept()
        
        # 播放退出动画（可选，可能影响关闭速度）
        # self._play_exit_animation()
        
        super().closeEvent(event)
    
    def _play_exit_animation(self):
        """播放退出动画（淡出 + 缩小）"""
        # 创建透明度效果
        if not self.graphicsEffect():
            opacity_effect = QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(opacity_effect)
        else:
            opacity_effect = self.graphicsEffect()
        
        # 淡出动画
        opacity_anim = QPropertyAnimation(opacity_effect, b"opacity")
        opacity_anim.setDuration(200)
        opacity_anim.setStartValue(1.0)
        opacity_anim.setEndValue(0.0)
        opacity_anim.setEasingCurve(QEasingCurve.Type.InQuad)
        
        # 缩放动画（缩小到95%）
        scale_anim = QPropertyAnimation(self, b"size")
        scale_anim.setDuration(200)
        scale_anim.setStartValue(self.size())
        scale_anim.setEndValue(QSize(
            int(self.size().width() * 0.95),
            int(self.size().height() * 0.95)
        ))
        scale_anim.setEasingCurve(QEasingCurve.Type.InQuad)
        
        # 并行播放
        group = QParallelAnimationGroup(self)
        group.addAnimation(opacity_anim)
        group.addAnimation(scale_anim)
        group.start()
        
        self._exit_animation = group

