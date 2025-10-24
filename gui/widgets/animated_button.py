#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
带动画效果的按钮组件
实现 macOS 风格的交互动画
"""

from PyQt6.QtWidgets import QPushButton, QGraphicsDropShadowEffect
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QSize, QPoint, QTimer
from PyQt6.QtGui import QColor, QPainter, QRadialGradient


class AnimatedButton(QPushButton):
    """带动画效果的按钮"""
    
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        
        self._original_size = None
        self._scale_animation = None
        self._ripple_animations = []
        
        # 启用鼠标追踪
        self.setMouseTracking(True)
        
        # 设置阴影效果
        self._setup_shadow()
    
    def _setup_shadow(self):
        """设置暖粉色阴影效果"""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(255, 154, 158, 50))  # 暖粉色阴影
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)
        self._shadow = shadow
    
    def enterEvent(self, event):
        """鼠标进入（悬停放大 + 阴影增强）"""
        super().enterEvent(event)
        self._animate_scale(1.05)
        
        # 增强阴影
        if hasattr(self, '_shadow'):
            self._shadow_anim = QPropertyAnimation(self._shadow, b"blurRadius")
            self._shadow_anim.setDuration(200)
            self._shadow_anim.setStartValue(12)
            self._shadow_anim.setEndValue(18)
            self._shadow_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
            self._shadow_anim.start()
            
            self._shadow.setColor(QColor(255, 154, 158, 80))
    
    def leaveEvent(self, event):
        """鼠标离开（恢复原大小 + 阴影恢复）"""
        super().leaveEvent(event)
        self._animate_scale(1.0)
        
        # 恢复阴影
        if hasattr(self, '_shadow'):
            self._shadow_anim = QPropertyAnimation(self._shadow, b"blurRadius")
            self._shadow_anim.setDuration(200)
            self._shadow_anim.setStartValue(18)
            self._shadow_anim.setEndValue(12)
            self._shadow_anim.setEasingCurve(QEasingCurve.Type.InQuad)
            self._shadow_anim.start()
            
            self._shadow.setColor(QColor(255, 154, 158, 50))
    
    def mousePressEvent(self, event):
        """鼠标按下（缩小 + 涟漪效果）"""
        self._animate_scale(0.95)
        self._add_ripple(event.pos())
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放（恢复悬停大小）"""
        self._animate_scale(1.05 if self.underMouse() else 1.0)
        super().mouseReleaseEvent(event)
    
    def _animate_scale(self, target_scale: float):
        """缩放动画"""
        if not self._original_size:
            self._original_size = self.size()
        
        target_size = QSize(
            int(self._original_size.width() * target_scale),
            int(self._original_size.height() * target_scale)
        )
        
        # 停止之前的动画
        if self._scale_animation:
            self._scale_animation.stop()
        
        # 创建新动画
        self._scale_animation = QPropertyAnimation(self, b"size")
        self._scale_animation.setDuration(150)
        self._scale_animation.setStartValue(self.size())
        self._scale_animation.setEndValue(target_size)
        self._scale_animation.setEasingCurve(QEasingCurve.Type.OutBack)
        self._scale_animation.start()
    
    def _add_ripple(self, position: QPoint):
        """添加涟漪效果"""
        # 简化版：创建一个渐变的圆形扩散效果
        # 实际实现需要自定义绘制，这里先占位
        pass


class AnimatedIconButton(AnimatedButton):
    """带图标动画的按钮"""
    
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self._rotation_angle = 0
        self._rotation_timer = None
    
    def start_rotation(self):
        """启动旋转动画（用于加载状态）"""
        if not self._rotation_timer:
            self._rotation_timer = QTimer(self)
            self._rotation_timer.timeout.connect(self._rotate)
        
        self._rotation_timer.start(50)  # 每50ms旋转
    
    def stop_rotation(self):
        """停止旋转动画"""
        if self._rotation_timer:
            self._rotation_timer.stop()
            self._rotation_angle = 0
    
    def _rotate(self):
        """旋转图标"""
        self._rotation_angle = (self._rotation_angle + 30) % 360
        self.update()

