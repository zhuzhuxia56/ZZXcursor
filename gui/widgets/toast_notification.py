#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Toast 通知组件
轻量级提示，自动淡出消失
"""

from PyQt6.QtWidgets import QLabel, QGraphicsOpacityEffect, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QFont, QColor


class ToastNotification(QLabel):
    """Toast 通知组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # 设置样式（类似横幅按钮风格）
        self.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #27ae60, stop:1 #2ecc71);
                color: white;
                padding: 12px 40px;
                border: 2px solid #1e8449;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        
        # 设置字体
        font = QFont()
        font.setPointSize(15)
        font.setBold(True)
        self.setFont(font)
        
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 阴影效果（增强浅色模式下的可见性）
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 4)
        
        # 透明度效果
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0.0)
        
        # 保存阴影效果供后续使用
        self._shadow_effect = shadow
    
    def show_message(self, message: str, duration: int = 2000):
        """
        显示消息
        
        Args:
            message: 消息内容
            duration: 显示时长（毫秒）
        """
        self.setText(message)
        self.adjustSize()
        
        # 显示在窗口下方（距离底部80px）
        if self.parent():
            parent_rect = self.parent().geometry()
            x = parent_rect.center().x() - self.width() // 2
            y = parent_rect.bottom() - self.height() - 80  # 距离底部80px
            self.move(x, y)
        
        # 显示
        self.show()
        
        # 淡入动画
        self.fade_in = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in.setDuration(300)
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(1.0)
        self.fade_in.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_in.start()
        
        # 定时淡出
        QTimer.singleShot(duration, self.fade_out_and_close)
    
    def fade_out_and_close(self):
        """淡出并关闭"""
        self.fade_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out.setDuration(300)
        self.fade_out.setStartValue(1.0)
        self.fade_out.setEndValue(0.0)
        self.fade_out.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_out.finished.connect(self.close)
        self.fade_out.start()


def show_toast(parent, message: str, duration: int = 2000, success: bool = True):
    """
    显示 Toast 通知
    
    Args:
        parent: 父窗口
        message: 消息内容
        duration: 显示时长（毫秒）
        success: 是否为成功消息（影响颜色）
    """
    toast = ToastNotification(parent)
    
    # 添加强阴影效果（浅色模式下超明显）
    shadow = QGraphicsDropShadowEffect(toast)
    shadow.setBlurRadius(35)
    shadow.setColor(QColor(0, 0, 0, 220))
    shadow.setOffset(0, 8)
    
    # 根据类型设置颜色（深色背景，白色文字，超强对比度）
    if success:
        toast.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0d4d25, stop:1 #1B5E20);
                color: white;
                padding: 14px 45px;
                border: 4px solid #0a3d1d;
                border-radius: 10px;
                font-size: 17px;
                font-weight: bold;
            }
        """)
    else:
        toast.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #c0392b, stop:1 #e74c3c);
                color: white;
                padding: 12px 40px;
                border: 3px solid #a93226;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }
        """)
    
    toast.show_message(message, duration)
    return toast

