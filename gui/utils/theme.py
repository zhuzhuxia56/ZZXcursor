#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主题配置类
定义暖粉/奶白/米色配色方案和动画参数
"""

from PyQt6.QtGui import QColor


class ThemeConfig:
    """暖粉主题配色方案"""
    
    # ==================== 主色调 ====================
    PRIMARY_START = "#ff9a9e"  # 暖粉色渐变起点
    PRIMARY_END = "#fecfef"    # 暖粉色渐变终点
    PRIMARY_DARK = "#ff758c"   # 珊瑚粉（强调色）
    PRIMARY_LIGHT = "#ffa8d8"  # 淡粉色
    
    # ==================== 背景色 ====================
    BG_MAIN_START = "#faf8f5"  # 主背景渐变起点（奶白色）
    BG_MAIN_END = "#fff5f8"    # 主背景渐变终点（浅粉色）
    BG_SECONDARY = "#f5f2ed"   # 次要背景（浅米色）
    BG_CARD_START = "#ffffff"  # 卡片背景渐变起点（纯白）
    BG_CARD_END = "#fffbfc"    # 卡片背景渐变终点（微粉）
    
    # ==================== 功能色 ====================
    SUCCESS_START = "#a8e6cf"  # 成功色渐变起点（薄荷绿）
    SUCCESS_END = "#c8f2e0"    # 成功色渐变终点
    WARNING_START = "#ffd3a5"  # 警告色渐变起点（蜜桃橙）
    WARNING_END = "#ffe8c5"    # 警告色渐变终点
    DANGER_START = "#ffaaa5"   # 危险色渐变起点（淡红）
    DANGER_END = "#ffd3cf"     # 危险色渐变终点
    HIGHLIGHT = "#ffd89b"      # 高亮色（杏粉）
    
    # ==================== 文字颜色 ====================
    TEXT_PRIMARY = "#5a4a42"   # 主文字（深灰棕）
    TEXT_SECONDARY = "#8a7a72"  # 次要文字（暖灰）
    TEXT_DISABLED = "#b8a8a5"  # 禁用文字
    TEXT_WHITE = "#ffffff"     # 白色文字
    
    # ==================== 边框颜色 ====================
    BORDER_LIGHT = "#f5e8ea"   # 浅边框
    BORDER_NORMAL = "#ffd3d8"  # 普通边框
    BORDER_ACTIVE = "#ff9a9e"  # 激活边框
    
    # ==================== 阴影颜色 ====================
    SHADOW_LIGHT = QColor(255, 154, 158, 30)   # 浅阴影（rgba 0.12）
    SHADOW_NORMAL = QColor(255, 154, 158, 50)  # 普通阴影（rgba 0.20）
    SHADOW_HEAVY = QColor(255, 154, 158, 80)   # 重阴影（rgba 0.31）
    
    # ==================== 动画参数 ====================
    ANIM_FAST = 150      # 快速动画（毫秒）
    ANIM_NORMAL = 300    # 普通动画（毫秒）
    ANIM_SLOW = 600      # 慢速动画（毫秒）
    ANIM_STAGGER = 50    # 瀑布流延迟（毫秒）
    
    # ==================== 圆角半径 ====================
    RADIUS_SMALL = 6     # 小圆角
    RADIUS_NORMAL = 10   # 普通圆角
    RADIUS_LARGE = 14    # 大圆角
    
    # ==================== 阴影参数 ====================
    SHADOW_BLUR_LIGHT = 12   # 浅阴影模糊半径
    SHADOW_BLUR_HEAVY = 20   # 重阴影模糊半径
    SHADOW_OFFSET = 2        # 阴影偏移
    
    @classmethod
    def get_gradient_style(cls, start: str, end: str, direction: str = "vertical") -> str:
        """
        获取渐变样式字符串
        
        Args:
            start: 起始颜色
            end: 结束颜色
            direction: 方向（'vertical' 或 'horizontal'）
        
        Returns:
            str: QSS渐变样式
        """
        if direction == "vertical":
            return f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {start}, stop:1 {end})"
        else:
            return f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {start}, stop:1 {end})"
    
    @classmethod
    def get_primary_gradient(cls, direction: str = "horizontal") -> str:
        """获取主色调渐变"""
        return cls.get_gradient_style(cls.PRIMARY_START, cls.PRIMARY_END, direction)
    
    @classmethod
    def get_bg_gradient(cls) -> str:
        """获取背景渐变"""
        return cls.get_gradient_style(cls.BG_MAIN_START, cls.BG_MAIN_END, "diagonal")
    
    @classmethod
    def get_card_gradient(cls) -> str:
        """获取卡片渐变"""
        return cls.get_gradient_style(cls.BG_CARD_START, cls.BG_CARD_END, "vertical")
    
    @classmethod
    def get_success_gradient(cls) -> str:
        """获取成功色渐变"""
        return cls.get_gradient_style(cls.SUCCESS_START, cls.SUCCESS_END, "horizontal")
    
    @classmethod
    def get_warning_gradient(cls) -> str:
        """获取警告色渐变"""
        return cls.get_gradient_style(cls.WARNING_START, cls.WARNING_END, "horizontal")
    
    @classmethod
    def get_danger_gradient(cls) -> str:
        """获取危险色渐变"""
        return cls.get_gradient_style(cls.DANGER_START, cls.DANGER_END, "horizontal")


class AnimationPresets:
    """动画预设配置"""
    
    # 缓动曲线类型
    EASE_OUT_QUAD = "OutQuad"
    EASE_IN_QUAD = "InQuad"
    EASE_IN_OUT_CUBIC = "InOutCubic"
    EASE_OUT_BACK = "OutBack"
    EASE_OUT_ELASTIC = "OutElastic"
    
    # 悬停动画
    HOVER_SCALE = 1.05
    HOVER_LIFT = 4  # 像素
    
    # 点击动画
    PRESS_SCALE = 0.95
    
    # 入场动画
    ENTRY_SCALE_FROM = 0.85
    ENTRY_OPACITY_FROM = 0.0
    
    # 透明度动画
    PULSE_MIN = 0.92
    PULSE_MAX = 1.0
    
    # 阴影动画
    SHADOW_BLUR_MIN = 12
    SHADOW_BLUR_MAX = 20

