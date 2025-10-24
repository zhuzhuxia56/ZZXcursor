#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动画工具类
提供通用的UI动画效果，类似 macOS 风格
"""

from PyQt6.QtCore import (
    QPropertyAnimation, QEasingCurve, QSequentialAnimationGroup,
    QParallelAnimationGroup, QPoint, QSize, QTimer, pyqtProperty
)
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QWidget, QLabel, QProgressBar
from PyQt6.QtGui import QPainter, QColor, QPen
from typing import Optional, Callable


# 缓动曲线预设（macOS 风格）
EASE_IN_OUT_CUBIC = QEasingCurve.Type.InOutCubic
EASE_OUT_BACK = QEasingCurve.Type.OutBack
EASE_OUT_ELASTIC = QEasingCurve.Type.OutElastic
EASE_OUT_QUAD = QEasingCurve.Type.OutQuad
EASE_IN_QUAD = QEasingCurve.Type.InQuad


def fade_in(widget: QWidget, duration: int = 300, callback: Optional[Callable] = None) -> QPropertyAnimation:
    """
    淡入动画
    
    Args:
        widget: 目标组件
        duration: 持续时间（毫秒）
        callback: 完成回调
    
    Returns:
        QPropertyAnimation: 动画对象
    """
    # 创建或获取透明度效果
    if not widget.graphicsEffect():
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
    else:
        effect = widget.graphicsEffect()
    
    # 创建动画
    animation = QPropertyAnimation(effect, b"opacity")
    animation.setDuration(duration)
    animation.setStartValue(0.0)
    animation.setEndValue(1.0)
    animation.setEasingCurve(EASE_OUT_QUAD)
    
    if callback:
        animation.finished.connect(callback)
    
    animation.start()
    return animation


def fade_out(widget: QWidget, duration: int = 200, callback: Optional[Callable] = None) -> QPropertyAnimation:
    """
    淡出动画
    
    Args:
        widget: 目标组件
        duration: 持续时间（毫秒）
        callback: 完成回调
    
    Returns:
        QPropertyAnimation: 动画对象
    """
    # 创建或获取透明度效果
    if not widget.graphicsEffect():
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
    else:
        effect = widget.graphicsEffect()
    
    # 创建动画
    animation = QPropertyAnimation(effect, b"opacity")
    animation.setDuration(duration)
    animation.setStartValue(1.0)
    animation.setEndValue(0.0)
    animation.setEasingCurve(EASE_IN_QUAD)
    
    if callback:
        animation.finished.connect(callback)
    
    animation.start()
    return animation


def slide_in(widget: QWidget, direction: str = 'bottom', duration: int = 300, 
             distance: int = 30, callback: Optional[Callable] = None) -> QParallelAnimationGroup:
    """
    滑入动画（淡入 + 位移）
    
    Args:
        widget: 目标组件
        direction: 方向 ('top', 'bottom', 'left', 'right')
        duration: 持续时间（毫秒）
        distance: 移动距离（像素）
        callback: 完成回调
    
    Returns:
        QParallelAnimationGroup: 动画组
    """
    # 保存原始位置
    original_pos = widget.pos()
    
    # 设置起始位置
    if direction == 'bottom':
        start_pos = QPoint(original_pos.x(), original_pos.y() + distance)
    elif direction == 'top':
        start_pos = QPoint(original_pos.x(), original_pos.y() - distance)
    elif direction == 'left':
        start_pos = QPoint(original_pos.x() - distance, original_pos.y())
    elif direction == 'right':
        start_pos = QPoint(original_pos.x() + distance, original_pos.y())
    else:
        start_pos = original_pos
    
    widget.move(start_pos)
    
    # 创建位移动画
    move_animation = QPropertyAnimation(widget, b"pos")
    move_animation.setDuration(duration)
    move_animation.setStartValue(start_pos)
    move_animation.setEndValue(original_pos)
    move_animation.setEasingCurve(EASE_OUT_BACK)
    
    # 创建淡入动画
    if not widget.graphicsEffect():
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
    else:
        effect = widget.graphicsEffect()
    
    opacity_animation = QPropertyAnimation(effect, b"opacity")
    opacity_animation.setDuration(duration)
    opacity_animation.setStartValue(0.0)
    opacity_animation.setEndValue(1.0)
    opacity_animation.setEasingCurve(EASE_OUT_QUAD)
    
    # 并行播放
    group = QParallelAnimationGroup()
    group.addAnimation(move_animation)
    group.addAnimation(opacity_animation)
    
    if callback:
        group.finished.connect(callback)
    
    group.start()
    return group


def slide_out(widget: QWidget, direction: str = 'top', duration: int = 200,
              distance: int = 30, callback: Optional[Callable] = None) -> QParallelAnimationGroup:
    """
    滑出动画（淡出 + 位移）
    
    Args:
        widget: 目标组件
        direction: 方向 ('top', 'bottom', 'left', 'right')
        duration: 持续时间（毫秒）
        distance: 移动距离（像素）
        callback: 完成回调
    
    Returns:
        QParallelAnimationGroup: 动画组
    """
    original_pos = widget.pos()
    
    # 设置结束位置
    if direction == 'top':
        end_pos = QPoint(original_pos.x(), original_pos.y() - distance)
    elif direction == 'bottom':
        end_pos = QPoint(original_pos.x(), original_pos.y() + distance)
    elif direction == 'left':
        end_pos = QPoint(original_pos.x() - distance, original_pos.y())
    elif direction == 'right':
        end_pos = QPoint(original_pos.x() + distance, original_pos.y())
    else:
        end_pos = original_pos
    
    # 创建位移动画
    move_animation = QPropertyAnimation(widget, b"pos")
    move_animation.setDuration(duration)
    move_animation.setStartValue(original_pos)
    move_animation.setEndValue(end_pos)
    move_animation.setEasingCurve(EASE_IN_QUAD)
    
    # 创建淡出动画
    if not widget.graphicsEffect():
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
    else:
        effect = widget.graphicsEffect()
    
    opacity_animation = QPropertyAnimation(effect, b"opacity")
    opacity_animation.setDuration(duration)
    opacity_animation.setStartValue(1.0)
    opacity_animation.setEndValue(0.0)
    opacity_animation.setEasingCurve(EASE_IN_QUAD)
    
    # 并行播放
    group = QParallelAnimationGroup()
    group.addAnimation(move_animation)
    group.addAnimation(opacity_animation)
    
    if callback:
        group.finished.connect(callback)
    
    group.start()
    return group


def scale_animation(widget: QWidget, from_scale: float = 0.9, to_scale: float = 1.0,
                   duration: int = 300, callback: Optional[Callable] = None) -> QPropertyAnimation:
    """
    缩放动画
    
    Args:
        widget: 目标组件
        from_scale: 起始缩放比例
        to_scale: 结束缩放比例
        duration: 持续时间（毫秒）
        callback: 完成回调
    
    Returns:
        QPropertyAnimation: 动画对象
    """
    # 保存原始尺寸
    original_size = widget.size()
    
    # 创建尺寸动画
    animation = QPropertyAnimation(widget, b"size")
    animation.setDuration(duration)
    animation.setStartValue(QSize(
        int(original_size.width() * from_scale),
        int(original_size.height() * from_scale)
    ))
    animation.setEndValue(original_size)
    animation.setEasingCurve(EASE_OUT_BACK)
    
    if callback:
        animation.finished.connect(callback)
    
    animation.start()
    return animation


def shake_animation(widget: QWidget, duration: int = 500, distance: int = 10) -> QSequentialAnimationGroup:
    """
    抖动动画（错误提示）
    
    Args:
        widget: 目标组件
        duration: 持续时间（毫秒）
        distance: 抖动距离（像素）
    
    Returns:
        QSequentialAnimationGroup: 动画组
    """
    original_pos = widget.pos()
    
    # 创建抖动序列
    group = QSequentialAnimationGroup()
    
    # 4次左右抖动
    for i in range(4):
        # 向右
        anim_right = QPropertyAnimation(widget, b"pos")
        anim_right.setDuration(duration // 8)
        anim_right.setStartValue(original_pos)
        anim_right.setEndValue(QPoint(original_pos.x() + distance, original_pos.y()))
        anim_right.setEasingCurve(QEasingCurve.Type.InOutSine)
        group.addAnimation(anim_right)
        
        # 向左
        anim_left = QPropertyAnimation(widget, b"pos")
        anim_left.setDuration(duration // 8)
        anim_left.setStartValue(QPoint(original_pos.x() + distance, original_pos.y()))
        anim_left.setEndValue(QPoint(original_pos.x() - distance, original_pos.y()))
        anim_left.setEasingCurve(QEasingCurve.Type.InOutSine)
        group.addAnimation(anim_left)
        
        # 距离逐渐减小
        distance = int(distance * 0.7)
    
    # 回到原位
    anim_return = QPropertyAnimation(widget, b"pos")
    anim_return.setDuration(duration // 8)
    anim_return.setStartValue(widget.pos())
    anim_return.setEndValue(original_pos)
    anim_return.setEasingCurve(QEasingCurve.Type.InOutSine)
    group.addAnimation(anim_return)
    
    group.start()
    return group


def pulse_animation(widget: QWidget, duration: int = 1000, loop: bool = True,
                   min_opacity: float = 0.6, max_opacity: float = 1.0) -> QPropertyAnimation:
    """
    脉冲动画（循环闪烁）
    
    Args:
        widget: 目标组件
        duration: 单次脉冲持续时间（毫秒）
        loop: 是否循环
        min_opacity: 最小透明度
        max_opacity: 最大透明度
    
    Returns:
        QPropertyAnimation: 动画对象
    """
    # 创建或获取透明度效果
    if not widget.graphicsEffect():
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
    else:
        effect = widget.graphicsEffect()
    
    # 创建动画
    animation = QPropertyAnimation(effect, b"opacity")
    animation.setDuration(duration)
    animation.setStartValue(max_opacity)
    animation.setEndValue(min_opacity)
    animation.setEasingCurve(QEasingCurve.Type.InOutSine)
    
    if loop:
        animation.setLoopCount(-1)  # 无限循环
    
    animation.start()
    return animation


def number_count_animation(label: QLabel, from_value: float, to_value: float,
                          duration: int = 800, decimals: int = 0) -> QPropertyAnimation:
    """
    数字滚动动画
    
    Args:
        label: 目标标签
        from_value: 起始值
        to_value: 结束值
        duration: 持续时间（毫秒）
        decimals: 小数位数
    
    Returns:
        QPropertyAnimation: 动画对象
    """
    # 创建自定义属性动画
    animation = QPropertyAnimation(label, b"value")
    animation.setDuration(duration)
    animation.setStartValue(from_value)
    animation.setEndValue(to_value)
    animation.setEasingCurve(EASE_OUT_QUAD)
    
    # 动态添加属性
    def get_value(self):
        return getattr(self, '_anim_value', from_value)
    
    def set_value(self, value):
        self._anim_value = value
        if decimals > 0:
            self.setText(f"{value:.{decimals}f}")
        else:
            self.setText(f"{int(value)}")
    
    # 绑定方法
    label.__class__.value = pyqtProperty(float, get_value, set_value)
    
    animation.start()
    return animation


def smooth_progress(progress_bar: QProgressBar, target_value: int,
                   duration: int = 500) -> QPropertyAnimation:
    """
    进度条平滑动画
    
    Args:
        progress_bar: 目标进度条
        target_value: 目标值
        duration: 持续时间（毫秒）
    
    Returns:
        QPropertyAnimation: 动画对象
    """
    animation = QPropertyAnimation(progress_bar, b"value")
    animation.setDuration(duration)
    animation.setStartValue(progress_bar.value())
    animation.setEndValue(target_value)
    animation.setEasingCurve(EASE_OUT_QUAD)
    
    animation.start()
    return animation


def sequential_animation(*animations) -> QSequentialAnimationGroup:
    """
    顺序播放动画
    
    Args:
        *animations: 动画对象列表
    
    Returns:
        QSequentialAnimationGroup: 动画组
    """
    group = QSequentialAnimationGroup()
    for anim in animations:
        group.addAnimation(anim)
    return group


def parallel_animation(*animations) -> QParallelAnimationGroup:
    """
    并行播放动画
    
    Args:
        *animations: 动画对象列表
    
    Returns:
        QParallelAnimationGroup: 动画组
    """
    group = QParallelAnimationGroup()
    for anim in animations:
        group.addAnimation(anim)
    return group


def stagger_animation(widgets: list, animation_func: Callable,
                     delay: int = 50, **kwargs) -> QSequentialAnimationGroup:
    """
    瀑布流动画（依次播放）
    
    Args:
        widgets: 组件列表
        animation_func: 动画函数
        delay: 每个动画间隔（毫秒）
        **kwargs: 传递给动画函数的参数
    
    Returns:
        QSequentialAnimationGroup: 动画组
    """
    group = QSequentialAnimationGroup()
    
    for i, widget in enumerate(widgets):
        # 添加延迟
        if i > 0:
            timer = QTimer()
            timer.setSingleShot(True)
            timer.setInterval(delay)
            # group无法直接添加QTimer，使用暂停动画代替
            pause = QPropertyAnimation(widget, b"pos")
            pause.setDuration(delay)
            pause.setStartValue(widget.pos())
            pause.setEndValue(widget.pos())
            group.addAnimation(pause)
        
        # 添加动画
        anim = animation_func(widget, **kwargs)
        group.addAnimation(anim)
    
    group.start()
    return group


class RippleEffect:
    """涟漪效果（按钮点击）"""
    
    def __init__(self, widget: QWidget):
        self.widget = widget
        self.ripples = []
        self.widget.installEventFilter(self)
    
    def add_ripple(self, position: QPoint, color: QColor = QColor(255, 255, 255, 100)):
        """添加涟漪"""
        ripple = {
            'position': position,
            'radius': 0,
            'max_radius': max(self.widget.width(), self.widget.height()),
            'opacity': 1.0,
            'color': color
        }
        self.ripples.append(ripple)
        
        # 启动动画定时器
        timer = QTimer(self.widget)
        timer.timeout.connect(lambda: self._update_ripple(ripple, timer))
        timer.start(16)  # 约60fps
    
    def _update_ripple(self, ripple: dict, timer: QTimer):
        """更新涟漪"""
        ripple['radius'] += ripple['max_radius'] / 20  # 20步完成
        ripple['opacity'] -= 0.05
        
        if ripple['opacity'] <= 0:
            self.ripples.remove(ripple)
            timer.stop()
        
        self.widget.update()
    
    def paint(self, painter: QPainter):
        """绘制涟漪"""
        for ripple in self.ripples:
            color = QColor(ripple['color'])
            color.setAlphaF(ripple['opacity'])
            
            painter.setPen(QPen(color, 2))
            painter.setBrush(color)
            painter.drawEllipse(
                ripple['position'],
                int(ripple['radius']),
                int(ripple['radius'])
            )


def ripple_effect(widget: QWidget, position: QPoint, color: QColor = QColor(255, 255, 255, 100)):
    """
    在组件上创建涟漪效果
    
    Args:
        widget: 目标组件
        position: 点击位置
        color: 涟漪颜色
    """
    if not hasattr(widget, '_ripple_effect'):
        widget._ripple_effect = RippleEffect(widget)
    
    widget._ripple_effect.add_ripple(position, color)


def gentle_pulse(widget: QWidget, duration: int = 2000, min_opacity: float = 0.92, 
                 max_opacity: float = 1.0) -> QPropertyAnimation:
    """
    温柔的呼吸灯动画（适用于重要提示）
    
    Args:
        widget: 目标组件
        duration: 单次脉冲持续时间（毫秒）
        min_opacity: 最小透明度
        max_opacity: 最大透明度
    
    Returns:
        QPropertyAnimation: 动画对象
    """
    if not widget.graphicsEffect():
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
    else:
        effect = widget.graphicsEffect()
    
    animation = QPropertyAnimation(effect, b"opacity")
    animation.setDuration(duration)
    animation.setStartValue(max_opacity)
    animation.setEndValue(min_opacity)
    animation.setEasingCurve(QEasingCurve.Type.InOutSine)
    animation.setLoopCount(-1)  # 无限循环
    
    animation.start()
    return animation


def bounce_in(widget: QWidget, duration: int = 600, callback: Optional[Callable] = None) -> QParallelAnimationGroup:
    """
    弹跳入场动画（适用于卡片和对话框）
    
    Args:
        widget: 目标组件
        duration: 持续时间（毫秒）
        callback: 完成回调
    
    Returns:
        QParallelAnimationGroup: 动画组
    """
    # 缩放动画：从0.8到1.0
    original_size = widget.size()
    size_animation = QPropertyAnimation(widget, b"size")
    size_animation.setDuration(duration)
    size_animation.setStartValue(QSize(
        int(original_size.width() * 0.85),
        int(original_size.height() * 0.85)
    ))
    size_animation.setEndValue(original_size)
    size_animation.setEasingCurve(EASE_OUT_BACK)
    
    # 透明度动画：从0到1
    if not widget.graphicsEffect():
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
    else:
        effect = widget.graphicsEffect()
    
    opacity_animation = QPropertyAnimation(effect, b"opacity")
    opacity_animation.setDuration(duration)
    opacity_animation.setStartValue(0.0)
    opacity_animation.setEndValue(1.0)
    opacity_animation.setEasingCurve(EASE_OUT_QUAD)
    
    # 组合动画
    group = QParallelAnimationGroup()
    group.addAnimation(size_animation)
    group.addAnimation(opacity_animation)
    
    if callback:
        group.finished.connect(callback)
    
    group.start()
    return group


def hover_lift(widget: QWidget, lift_distance: int = 4, duration: int = 200) -> QPropertyAnimation:
    """
    悬停上浮动画（适用于卡片）
    
    Args:
        widget: 目标组件
        lift_distance: 上浮距离（像素）
        duration: 持续时间（毫秒）
    
    Returns:
        QPropertyAnimation: 动画对象
    """
    original_pos = widget.pos()
    target_pos = QPoint(original_pos.x(), original_pos.y() - lift_distance)
    
    animation = QPropertyAnimation(widget, b"pos")
    animation.setDuration(duration)
    animation.setStartValue(original_pos)
    animation.setEndValue(target_pos)
    animation.setEasingCurve(EASE_OUT_QUAD)
    
    # 保存原始位置供hover_drop使用
    widget._original_pos = original_pos
    
    animation.start()
    return animation


def hover_drop(widget: QWidget, duration: int = 200) -> QPropertyAnimation:
    """
    悬停下落动画（恢复原位）
    
    Args:
        widget: 目标组件
        duration: 持续时间（毫秒）
    
    Returns:
        QPropertyAnimation: 动画对象
    """
    if not hasattr(widget, '_original_pos'):
        return None
    
    current_pos = widget.pos()
    original_pos = widget._original_pos
    
    animation = QPropertyAnimation(widget, b"pos")
    animation.setDuration(duration)
    animation.setStartValue(current_pos)
    animation.setEndValue(original_pos)
    animation.setEasingCurve(EASE_IN_QUAD)
    
    animation.start()
    return animation


def color_transition(widget: QWidget, from_color: QColor, to_color: QColor, 
                    duration: int = 300, property_name: str = "color") -> QPropertyAnimation:
    """
    颜色渐变动画（适用于文本和背景）
    
    Args:
        widget: 目标组件
        from_color: 起始颜色
        to_color: 结束颜色
        duration: 持续时间（毫秒）
        property_name: 属性名称
    
    Returns:
        QPropertyAnimation: 动画对象
    """
    animation = QPropertyAnimation(widget, property_name.encode())
    animation.setDuration(duration)
    animation.setStartValue(from_color)
    animation.setEndValue(to_color)
    animation.setEasingCurve(EASE_OUT_QUAD)
    
    animation.start()
    return animation


def rotate_continuous(widget: QWidget, duration: int = 1000, angle: int = 360) -> QPropertyAnimation:
    """
    连续旋转动画（适用于加载指示器）
    
    Args:
        widget: 目标组件
        duration: 旋转一圈的时间（毫秒）
        angle: 旋转角度
    
    Returns:
        QPropertyAnimation: 动画对象
    """
    animation = QPropertyAnimation(widget, b"rotation")
    animation.setDuration(duration)
    animation.setStartValue(0)
    animation.setEndValue(angle)
    animation.setLoopCount(-1)  # 无限循环
    animation.setEasingCurve(QEasingCurve.Type.Linear)
    
    animation.start()
    return animation


def spring_bounce(widget: QWidget, intensity: float = 1.05, duration: int = 300) -> QSequentialAnimationGroup:
    """
    弹簧回弹动画（点击反馈）
    
    Args:
        widget: 目标组件
        intensity: 回弹强度（>1.0为放大，<1.0为缩小）
        duration: 持续时间（毫秒）
    
    Returns:
        QSequentialAnimationGroup: 动画组
    """
    original_size = widget.size()
    
    # 第一阶段：放大/缩小
    expand = QPropertyAnimation(widget, b"size")
    expand.setDuration(duration // 2)
    expand.setStartValue(original_size)
    expand.setEndValue(QSize(
        int(original_size.width() * intensity),
        int(original_size.height() * intensity)
    ))
    expand.setEasingCurve(EASE_OUT_QUAD)
    
    # 第二阶段：恢复
    restore = QPropertyAnimation(widget, b"size")
    restore.setDuration(duration // 2)
    restore.setStartValue(expand.endValue())
    restore.setEndValue(original_size)
    restore.setEasingCurve(EASE_OUT_BACK)
    
    group = QSequentialAnimationGroup()
    group.addAnimation(expand)
    group.addAnimation(restore)
    
    group.start()
    return group


def glow_effect(widget: QWidget, intensity: int = 20, color: QColor = QColor(255, 154, 158)):
    """
    添加光晕效果
    
    Args:
        widget: 目标组件
        intensity: 光晕强度（模糊半径）
        color: 光晕颜色
    """
    from PyQt6.QtWidgets import QGraphicsDropShadowEffect
    
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(intensity)
    shadow.setColor(color)
    shadow.setOffset(0, 0)
    widget.setGraphicsEffect(shadow)


def remove_effect(widget: QWidget):
    """
    移除组件的图形效果
    
    Args:
        widget: 目标组件
    """
    widget.setGraphicsEffect(None)
