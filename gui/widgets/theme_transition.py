#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主题切换过渡动画组件
提供丝滑的全屏淡入淡出效果，掩盖主题切换过程
"""

from PyQt6.QtWidgets import QWidget, QGraphicsOpacityEffect
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, Qt, QTimer
from PyQt6.QtGui import QPainter, QRadialGradient, QColor

from utils.logger import get_logger

logger = get_logger("theme_transition")


class ThemeTransitionWidget(QWidget):
    """主题切换过渡动画（全屏淡入淡出遮罩）"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        # 全屏覆盖父窗口
        self.setGeometry(parent.rect())
        
        # 设置属性
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)  # 初始不拦截鼠标
        
        # 初始隐藏
        self.hide()
        
        # 透明度效果
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0)
        
        # 动画引用
        self._fade_in = None
        self._fade_out = None
    
    def paintEvent(self, event):
        """绘制径向渐变遮罩（中心亮，边缘暗）"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # ⭐ 创建径向渐变（从中心向边缘扩散）
        gradient = QRadialGradient(
            self.width() / 2,       # 中心X
            self.height() / 2,      # 中心Y
            max(self.width(), self.height()) * 0.7  # 半径
        )
        
        # 渐变色阶（黑色，不同透明度）
        gradient.setColorAt(0.0, QColor(0, 0, 0, 200))    # 中心：较暗
        gradient.setColorAt(0.5, QColor(0, 0, 0, 220))    # 中间
        gradient.setColorAt(1.0, QColor(0, 0, 0, 240))    # 边缘：最暗
        
        # 填充整个widget
        painter.fillRect(self.rect(), gradient)
    
    def play_transition(self, switch_callback):
        """
        播放完整过渡动画（淡入→切换→淡出）
        
        Args:
            switch_callback: 主题切换回调函数（在黑屏期间执行）
        """
        try:
            logger.debug("开始播放主题切换过渡动画")
            
            # 显示遮罩并置顶
            self.show()
            self.raise_()
            
            # ⭐ 在动画期间拦截鼠标（防止用户操作）
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
            
            # ⭐ 阶段1：快速淡入（0→1，120ms）
            self._fade_in = QPropertyAnimation(self.opacity_effect, b"opacity")
            self._fade_in.setDuration(120)  # 快速变黑
            self._fade_in.setStartValue(0.0)
            self._fade_in.setEndValue(1.0)
            self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)  # 加速淡入
            
            # 淡入完成后执行切换
            def on_fade_in_complete():
                try:
                    # ⭐ 阶段2：在黑屏期间执行主题切换
                    logger.debug("遮罩淡入完成，开始执行主题切换")
                    switch_callback()
                    
                    # ⭐ 阶段3：延迟50ms后淡出（确保样式应用完成）
                    QTimer.singleShot(50, self._start_fade_out)
                    
                except Exception as e:
                    logger.error(f"主题切换回调失败: {e}")
                    # 即使失败也要淡出
                    self._start_fade_out()
            
            self._fade_in.finished.connect(on_fade_in_complete)
            
            # 启动淡入动画
            self._fade_in.start()
            
        except Exception as e:
            logger.error(f"播放过渡动画失败: {e}")
            # 失败时直接隐藏
            self.hide()
    
    def _start_fade_out(self):
        """开始淡出动画"""
        try:
            logger.debug("开始淡出遮罩，显示新主题")
            
            # ⭐ 淡出动画（1→0，150ms，缓慢显现）
            self._fade_out = QPropertyAnimation(self.opacity_effect, b"opacity")
            self._fade_out.setDuration(150)  # 缓慢淡出
            self._fade_out.setStartValue(1.0)
            self._fade_out.setEndValue(0.0)
            self._fade_out.setEasingCurve(QEasingCurve.Type.InCubic)  # 减速淡出
            
            # 淡出完成后隐藏并恢复鼠标穿透
            def on_fade_out_complete():
                self.hide()
                self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
                logger.debug("过渡动画完成")
            
            self._fade_out.finished.connect(on_fade_out_complete)
            
            # 启动淡出动画
            self._fade_out.start()
            
        except Exception as e:
            logger.error(f"淡出动画失败: {e}")
            self.hide()
    
    def resizeEvent(self, event):
        """窗口大小改变时，同步更新遮罩大小"""
        super().resizeEvent(event)
        if self.parent():
            self.setGeometry(self.parent().rect())

