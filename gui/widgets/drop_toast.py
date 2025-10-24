#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
掉落Toast提示框
从屏幕顶部自由落体掉落的提示框（超好看版）
"""

from PyQt6.QtWidgets import (
    QWidget, QLabel, QGraphicsOpacityEffect, QApplication, 
    QGraphicsDropShadowEffect, QVBoxLayout, QHBoxLayout
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, QTimer, QSequentialAnimationGroup
from PyQt6.QtGui import QFont, QColor

from utils.logger import get_logger

logger = get_logger("drop_toast")


class DropToast(QWidget):
    """掉落Toast提示框（自由落体动画+弹跳+摇晃）"""
    
    def __init__(self, message: str, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        
        self.message = message
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """初始化UI（超华丽协调版）"""
        # ⭐ 设置合理大小（既醒目又协调）
        self.setFixedSize(600, 160)
        
        # ⭐ 创建透明度效果（用于整个widget的淡入淡出）
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)
        
        # 创建容器Widget（用于样式和阴影）
        container = QWidget(self)
        container.setGeometry(0, 0, 600, 160)
        
        # 创建布局
        layout = QHBoxLayout(container)
        layout.setContentsMargins(25, 20, 25, 20)  # ⭐ 增加内边距
        layout.setSpacing(20)  # ⭐ 增加间距
        
        # ⭐ 左侧：超大表情符号
        emoji_label = QLabel("🔫", container)
        emoji_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        emoji_font = QFont()
        emoji_font.setPointSize(64)  # ⭐ 更大的表情（从48增加到64）
        emoji_label.setFont(emoji_font)
        emoji_label.setFixedWidth(120)  # ⭐ 更宽的表情区域
        layout.addWidget(emoji_label)
        
        # ⭐ 右侧：文本内容
        self.label = QLabel(self.message, container)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setWordWrap(True)
        
        # ⭐ 设置更大的字体
        font = QFont()
        font.setPointSize(20)  # ⭐ 从16增加到20
        font.setBold(True)
        self.label.setFont(font)
        
        layout.addWidget(self.label, 1)
        
        # ⭐ 设置超华丽的渐变样式
        container.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #FF6B6B, 
                    stop:0.3 #FF5252, 
                    stop:0.7 #FF4444,
                    stop:1 #FF2222);
                color: white;
                border: 6px solid #CC0000;
                border-radius: 24px;
                padding: 0px;
            }
            QLabel {
                background: transparent;
                color: white;
                font-weight: bold;
                border: none;
            }
        """)
    
    def show_drop_animation(self):
        """显示并播放超华丽的掉落动画（掉落+弹跳+摇晃+脉冲）"""
        try:
            # 获取屏幕中心位置
            screen = QApplication.primaryScreen().geometry()
            screen_center_x = screen.center().x()
            
            # 起始位置：屏幕顶部以上
            start_x = screen_center_x - self.width() // 2
            start_y = -self.height() - 100  # 从更高处开始
            
            # 目标位置：屏幕顶部往下120px
            end_x = start_x
            end_y = 120
            
            # 设置初始位置
            self.setGeometry(start_x, start_y, self.width(), self.height())
            
            # 显示窗口
            self.show()
            
            # ⭐ 阶段1：掉落动画（自由落体+弹跳）
            self.drop_animation = QPropertyAnimation(self, b"geometry")
            self.drop_animation.setDuration(900)  # 0.9秒掉落+弹跳（更优雅）
            self.drop_animation.setStartValue(QRect(start_x, start_y, self.width(), self.height()))
            self.drop_animation.setEndValue(QRect(end_x, end_y, self.width(), self.height()))
            self.drop_animation.setEasingCurve(QEasingCurve.Type.OutBounce)  # 弹跳效果
            
            # ⭐ 透明度动画（快速淡入）
            self.fade_in_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
            self.fade_in_animation.setDuration(300)  # 淡入
            self.fade_in_animation.setStartValue(0.0)
            self.fade_in_animation.setEndValue(1.0)
            self.fade_in_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            
            # 启动动画
            self.drop_animation.start()
            self.fade_in_animation.start()
            
            # ⭐ 掉落完成后，播放摇晃动画
            self.drop_animation.finished.connect(self._start_shake_animation)
            
            logger.debug(f"Toast超华丽掉落动画已启动: {self.message}")
            
        except Exception as e:
            logger.error(f"显示掉落动画失败: {e}")
            self.close()
    
    def _start_shake_animation(self):
        """着陆后摇晃动画（左右摇晃3次）"""
        try:
            # 获取当前位置
            current_rect = self.geometry()
            center_x = current_rect.x()
            y = current_rect.y()
            
            # ⭐ 创建摇晃序列动画
            shake_group = QSequentialAnimationGroup(self)
            
            # 第1次摇晃：向左
            shake1 = QPropertyAnimation(self, b"geometry")
            shake1.setDuration(100)
            shake1.setStartValue(QRect(center_x, y, self.width(), self.height()))
            shake1.setEndValue(QRect(center_x - 15, y, self.width(), self.height()))
            shake1.setEasingCurve(QEasingCurve.Type.InOutQuad)
            
            # 第2次摇晃：向右
            shake2 = QPropertyAnimation(self, b"geometry")
            shake2.setDuration(100)
            shake2.setStartValue(QRect(center_x - 15, y, self.width(), self.height()))
            shake2.setEndValue(QRect(center_x + 15, y, self.width(), self.height()))
            shake2.setEasingCurve(QEasingCurve.Type.InOutQuad)
            
            # 第3次摇晃：向左
            shake3 = QPropertyAnimation(self, b"geometry")
            shake3.setDuration(100)
            shake3.setStartValue(QRect(center_x + 15, y, self.width(), self.height()))
            shake3.setEndValue(QRect(center_x - 10, y, self.width(), self.height()))
            shake3.setEasingCurve(QEasingCurve.Type.InOutQuad)
            
            # 第4次摇晃：回中心
            shake4 = QPropertyAnimation(self, b"geometry")
            shake4.setDuration(100)
            shake4.setStartValue(QRect(center_x - 10, y, self.width(), self.height()))
            shake4.setEndValue(QRect(center_x, y, self.width(), self.height()))
            shake4.setEasingCurve(QEasingCurve.Type.InOutQuad)
            
            # 添加到序列
            shake_group.addAnimation(shake1)
            shake_group.addAnimation(shake2)
            shake_group.addAnimation(shake3)
            shake_group.addAnimation(shake4)
            
            # 摇晃完成后开始脉冲
            shake_group.finished.connect(self._start_pulse_animation)
            
            # 启动摇晃
            shake_group.start()
            self._shake_group = shake_group  # 保存引用
            
        except Exception as e:
            logger.error(f"摇晃动画失败: {e}")
            self._start_stay_timer()
    
    def _start_pulse_animation(self):
        """脉冲动画（轻微放大缩小，吸引注意）"""
        try:
            # 获取当前位置
            current_rect = self.geometry()
            
            # ⭐ 创建脉冲序列（放大→缩小，重复2次）
            pulse_group = QSequentialAnimationGroup(self)
            
            # 放大
            pulse_expand = QPropertyAnimation(self, b"geometry")
            pulse_expand.setDuration(400)
            pulse_expand.setStartValue(current_rect)
            expand_rect = QRect(
                current_rect.x() - 10,
                current_rect.y() - 5,
                current_rect.width() + 20,
                current_rect.height() + 10
            )
            pulse_expand.setEndValue(expand_rect)
            pulse_expand.setEasingCurve(QEasingCurve.Type.InOutQuad)
            
            # 缩小回原大小
            pulse_shrink = QPropertyAnimation(self, b"geometry")
            pulse_shrink.setDuration(400)
            pulse_shrink.setStartValue(expand_rect)
            pulse_shrink.setEndValue(current_rect)
            pulse_shrink.setEasingCurve(QEasingCurve.Type.InOutQuad)
            
            # 添加到序列（脉冲1次）
            pulse_group.addAnimation(pulse_expand)
            pulse_group.addAnimation(pulse_shrink)
            
            # 脉冲完成后停留
            pulse_group.finished.connect(self._start_stay_timer)
            
            # 启动脉冲
            pulse_group.start()
            self._pulse_group = pulse_group  # 保存引用
            
        except Exception as e:
            logger.error(f"脉冲动画失败: {e}")
            self._start_stay_timer()
    
    def _start_stay_timer(self):
        """停留2秒后开始消失"""
        QTimer.singleShot(2000, self._fade_out_and_close)
    
    def _fade_out_and_close(self):
        """华丽淡出并向上飞走"""
        try:
            # 获取当前位置
            current_rect = self.geometry()
            
            # ⭐ 创建向上飞走动画（反向掉落）
            fly_up = QPropertyAnimation(self, b"geometry")
            fly_up.setDuration(600)
            fly_up.setStartValue(current_rect)
            # 向上飞到屏幕顶部以上
            fly_target = QRect(
                current_rect.x(),
                -self.height() - 50,
                current_rect.width(),
                current_rect.height()
            )
            fly_up.setEndValue(fly_target)
            fly_up.setEasingCurve(QEasingCurve.Type.InBack)  # 向后加速（像被拉回去）
            
            # ⭐ 创建淡出动画（同时进行）
            self.fade_out_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
            self.fade_out_animation.setDuration(600)
            self.fade_out_animation.setStartValue(1.0)
            self.fade_out_animation.setEndValue(0.0)
            self.fade_out_animation.setEasingCurve(QEasingCurve.Type.InQuad)
            
            # 动画完成后关闭
            fly_up.finished.connect(self.close)
            
            # 同时启动两个动画
            fly_up.start()
            self.fade_out_animation.start()
            
            # 保存引用
            self._fly_up = fly_up
            
        except Exception as e:
            logger.error(f"淡出动画失败: {e}")
            self.close()


def show_drop_toast(message: str, parent=None):
    """
    显示掉落Toast提示框
    
    Args:
        message: 提示消息
        parent: 父窗口
    """
    toast = DropToast(message, parent)
    toast.show_drop_animation()
    return toast

