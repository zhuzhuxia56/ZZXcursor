#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账号卡片组件
显示单个账号的信息和操作按钮
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QGraphicsOpacityEffect, QCheckBox,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, 
    QParallelAnimationGroup, QSequentialAnimationGroup, QTimer, QSize, QPoint
)
from PyQt6.QtGui import QFont, QColor
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils.logger import get_logger
from gui.widgets.rotating_button import RotatingIconButton

logger = get_logger("account_card")


class AccountCard(QFrame):
    """账号卡片组件"""
    
    # 信号定义
    switch_clicked = pyqtSignal(int)  # 切换账号
    detail_clicked = pyqtSignal(int)  # 查看详情
    delete_clicked = pyqtSignal(int)  # 删除账号
    refresh_clicked = pyqtSignal(int)  # 刷新信息
    selection_changed = pyqtSignal(int, bool)  # 选择状态改变（account_id, selected）
    drag_select_start = pyqtSignal(object)  # 拖动多选开始（card对象）
    drag_select_move = pyqtSignal(object, object)  # 拖动多选中（card对象, event）
    drag_select_end = pyqtSignal(object)  # 拖动多选结束（card对象）
    
    def __init__(self, account_data: dict, parent=None, enable_animation: bool = False):
        """
        初始化账号卡片
        
        Args:
            account_data: 账号数据字典
            parent: 父组件
            enable_animation: 是否启用淡入动画（默认禁用以提升性能）
        """
        super().__init__(parent)
        
        self.account_id = account_data.get('id')
        self.account_data = account_data
        self.enable_animation = enable_animation
        self.is_current = False  # 是否为当前登录账号
        self._is_dragging = False  # 是否正在拖动
        self._hover_animation = None  # 悬停动画
        self._shadow_effect = None  # 阴影效果
        self._is_loading = False  # 是否正在加载中（刷新期间禁用悬停）
        self._is_invalid = False  # 账号是否失效
        
        self._setup_ui()
        self._setup_hover_effects()  # 设置悬停效果
        self._update_switch_button()  # 初始化切换按钮状态
        self._update_display()
        if enable_animation:
            self._setup_animations()
    
    def _setup_ui(self):
        """设置 UI 布局"""
        self.setObjectName("AccountCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        
        # ⭐ 设置固定宽度（确保FlowLayout正确计算列数）
        # 卡片固定270px宽度，便于响应式布局精确计算
        self.setFixedWidth(270)
        
        # ⭐ 启用鼠标追踪（用于拖动多选功能）
        self.setMouseTracking(True)
        
        # ⭐ 接受鼠标事件
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        
        # 初始样式（会在set_current中根据状态更新）
        self._update_style()
        
        # 主布局（进一步缩小间距）
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)
        
        # 顶部：复选框 + 邮箱 + 状态
        top_layout = QHBoxLayout()
        
        # 复选框 - 使用 stateChanged 信号，单击即可选中
        self.checkbox = QCheckBox()
        self.checkbox.stateChanged.connect(self._on_checkbox_state_changed)
        # ⭐ 设置复选框接受鼠标事件但不拦截
        self.checkbox.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        # ⭐ 强制设置透明背景（代码层面双重保障）
        self.checkbox.setStyleSheet("""
            QCheckBox {
                background: transparent;
                background-color: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        top_layout.addWidget(self.checkbox)
        
        # 邮箱标签（进一步缩小字体）
        self.email_label = QLabel()
        self.email_label.setObjectName("emailLabel")  # ⭐ 设置对象名
        email_font = QFont()
        email_font.setPointSize(11)  # ⭐ 稍微加大字号
        email_font.setBold(True)
        self.email_label.setFont(email_font)
        self.email_label.setWordWrap(True)
        top_layout.addWidget(self.email_label)
        
        top_layout.addStretch()
        
        # 状态指示器（进一步缩小）
        self.status_label = QLabel()
        self.status_label.setStyleSheet("""
            QLabel {
                padding: 2px 8px;
                border-radius: 6px;
                font-size: 9px;
                font-weight: bold;
            }
        """)
        top_layout.addWidget(self.status_label)
        
        main_layout.addLayout(top_layout)
        
        # 中部：账号信息
        info_layout = QHBoxLayout()
        
        # 套餐信息（进一步缩小）
        self.plan_label = QLabel()
        self.plan_label.setObjectName("planLabel")  # ⭐ 设置对象名，便于主题控制
        info_layout.addWidget(self.plan_label)
        
        info_layout.addSpacing(8)
        
        # 使用率
        self.usage_label = QLabel()
        self.usage_label.setObjectName("usageLabel")  # ⭐ 设置对象名
        info_layout.addWidget(self.usage_label)
        
        info_layout.addSpacing(8)
        
        # 剩余天数
        self.days_label = QLabel()
        self.days_label.setObjectName("daysLabel")  # ⭐ 设置对象名
        info_layout.addWidget(self.days_label)
        
        info_layout.addStretch()
        
        main_layout.addLayout(info_layout)
        
        # 时间信息行
        time_layout = QHBoxLayout()
        
        # 注册时间（进一步缩小）
        self.created_label = QLabel()
        self.created_label.setObjectName("createdLabel")  # ⭐ 设置对象名
        time_layout.addWidget(self.created_label)
        
        time_layout.addSpacing(8)
        
        # 最后使用时间
        self.last_used_label = QLabel()
        self.last_used_label.setObjectName("lastUsedLabel")  # ⭐ 设置对象名
        time_layout.addWidget(self.last_used_label)
        
        time_layout.addStretch()
        
        main_layout.addLayout(time_layout)
        
        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #f5e8ea; max-height: 1px;")
        main_layout.addWidget(separator)
        
        # 分隔线（额外间距）
        main_layout.addSpacing(4)
        
        # 底部：操作按钮（网格布局2行，彻底避免重叠）
        from PyQt6.QtWidgets import QGridLayout
        
        button_grid = QGridLayout()
        button_grid.setSpacing(8)  # 增加间距到8px，避免拥挤
        button_grid.setContentsMargins(0, 0, 0, 0)
        button_grid.setColumnStretch(0, 1)  # 第0列拉伸因子1
        button_grid.setColumnStretch(1, 1)  # 第1列拉伸因子1
        button_grid.setColumnStretch(2, 1)  # 第2列拉伸因子1
        
        # 第一行：切换按钮（占满整行）
        self.switch_btn = QPushButton("🔑 切换账号")
        self.switch_btn.setProperty("success", True)
        self.switch_btn.setMinimumHeight(34)
        self.switch_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 10px;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        self.switch_btn.clicked.connect(lambda: self.switch_clicked.emit(self.account_id))
        button_grid.addWidget(self.switch_btn, 0, 0, 1, 3)  # 第0行，跨3列
        
        # 第二行：三个小按钮均分（刷新按钮使用可旋转组件）
        self.refresh_btn = RotatingIconButton("🔄")
        self.refresh_btn.setProperty("secondary", True)
        self.refresh_btn.setToolTip("刷新账号信息")
        self.refresh_btn.setMinimumHeight(30)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                padding: 4px 6px;
                font-size: 16px;
            }
        """)
        self.refresh_btn.clicked.connect(lambda: self.refresh_clicked.emit(self.account_id))
        button_grid.addWidget(self.refresh_btn, 1, 0)  # 第1行，第0列
        
        self.detail_btn = QPushButton("📊")
        self.detail_btn.setProperty("secondary", True)
        self.detail_btn.setToolTip("查看详情")
        self.detail_btn.setMinimumHeight(30)
        self.detail_btn.setStyleSheet("""
            QPushButton {
                padding: 4px 6px;
                font-size: 16px;
            }
        """)
        self.detail_btn.clicked.connect(lambda: self.detail_clicked.emit(self.account_id))
        button_grid.addWidget(self.detail_btn, 1, 1)  # 第1行，第1列
        
        self.delete_btn = QPushButton("🗑️")
        self.delete_btn.setProperty("danger", True)
        self.delete_btn.setToolTip("删除账号")
        self.delete_btn.setMinimumHeight(30)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                padding: 4px 6px;
                font-size: 16px;
            }
        """)
        self.delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self.account_id))
        button_grid.addWidget(self.delete_btn, 1, 2)  # 第1行，第2列
        
        main_layout.addLayout(button_grid)
        
        # ⭐ 失效标记层（大红×）
        self.invalid_overlay = QLabel(self)
        self.invalid_overlay.setObjectName("InvalidOverlay")
        self.invalid_overlay.setText("❌")
        self.invalid_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.invalid_overlay.setStyleSheet("""
            QLabel {
                font-size: 80px;
                color: #ff0000;
                background-color: rgba(255, 0, 0, 0.1);
                border-radius: 8px;
            }
        """)
        self.invalid_overlay.setVisible(False)  # 默认隐藏
        # 设置为覆盖层（在最上层）
        self.invalid_overlay.raise_()
    
    def _setup_hover_effects(self):
        """设置悬停效果（彻底禁用版：移除阴影，完全使用CSS）"""
        # ⭐ 完全禁用QGraphicsDropShadowEffect阴影效果
        # 原因：阴影是GPU渲染操作，每次样式更新都会触发重新渲染，导致闪烁
        # 改用CSS的box-shadow，性能更好且不会触发重排
        self._shadow_effect = None
        
        # 悬停效果完全通过CSS实现，不使用任何Qt动画
    
    def enterEvent(self, event):
        """鼠标进入事件（简化版：不使用动画）"""
        super().enterEvent(event)
        # 悬停效果通过CSS的:hover实现，更稳定
    
    def leaveEvent(self, event):
        """鼠标离开事件（简化版：不使用动画）"""
        super().leaveEvent(event)
        # 悬停效果通过CSS的:hover实现，更稳定
    
    def _get_theme_colors(self):
        """获取当前主题的基础颜色"""
        try:
            from utils.theme_manager import get_theme_manager
            theme_manager = get_theme_manager()
            is_dark = theme_manager.is_dark_theme()
        except:
            is_dark = False
        
        if is_dark:
            return {
                'bg_normal_start': '#242938',
                'bg_normal_end': '#2d3348',
                'bg_current_start': '#3a2f1f',
                'bg_current_end': '#4a3d28',
                'bg_warning_start': '#3a2818',
                'bg_warning_end': '#4a3520',
                'bg_error_start': '#3a1f1f',
                'bg_error_end': '#4a2828',
                'border_normal': '#8b5cf6',
                'border_current': '#ffd89b',
                'border_warning': '#f59e0b',
                'border_error': '#ef4444',
                'text_primary': '#f0f3f7',         # ⭐ 更亮的主文本
                'text_secondary': '#c4b5fd',       # ⭐ 更亮的次要文本（紫色调）
                'text_tertiary': '#a8b4c0',        # ⭐ 更亮的第三级文本
                'separator': '#374151',
            }
        else:
            return {
                'bg_normal_start': '#ffffff',
                'bg_normal_end': '#f8fff5',
                'bg_current_start': '#fffef8',
                'bg_current_end': '#fff8e8',
                'bg_warning_start': '#ffffff',
                'bg_warning_end': '#fffaf5',
                'bg_error_start': '#ffffff',
                'bg_error_end': '#fff8f8',
                'border_normal': '#a8e6cf',
                'border_current': '#ffd89b',
                'border_warning': '#ffd3a5',
                'border_error': '#ffaaa5',
                'text_primary': '#2c3e50',
                'text_secondary': '#a0a0a0',
                'text_tertiary': '#808080',
                'separator': '#f5e8ea',
            }
    
    def _update_style(self):
        """更新卡片样式（根据当前账号和欠费状态，优化版：减少不必要的setStyleSheet调用）"""
        try:
            # ⭐ 获取主题颜色
            colors = self._get_theme_colors()
            
            # ⭐ 根据欠费金额和总花费判断边框颜色
            unpaid = self.account_data.get('unpaid_amount', 0)
            if unpaid is None:
                unpaid = 0
            else:
                unpaid = float(unpaid)
            
            # 获取总花费
            total_cost = self.account_data.get('total_cost', 0)
            if total_cost is None:
                total_cost = 0
            else:
                total_cost = float(total_cost)
            
            # 获取套餐类型判断规则
            membership = self.account_data.get('membership_type', 'free').lower()
            
            if self.is_current:
                # 当前登录账号：深橙金色高亮边框（优先级最高）
                border_color = "#FF8C00"  # 深橙金色（浅色和深色模式都明显）
                hover_color = "#FFD700"  # 金色
                # 根据主题选择背景
                if self._get_is_dark():
                    bg_start = "#3a2e1e"  # 深色模式：深橙背景
                    bg_end = "#4a3e2e"
                    hover_bg_start = "#4a3e2e"
                    hover_bg_end = "#5a4e3e"
                else:
                    bg_start = "#fff8e1"  # 浅色模式：浅橙背景
                    bg_end = "#ffe8c1"
                    hover_bg_start = "#ffe8c1"
                    hover_bg_end = "#ffd8a1"
            elif unpaid > 20 or total_cost > 60:
                # ⭐ 严重：欠费>$20 或 总花费>$60 → 深红色边框
                border_color = "#CC0000"  # 深红色
                hover_color = "#ff9590"
                bg_start = "#ffe5e5" if not self._get_is_dark() else "#3a1e1e"
                bg_end = "#ffe5e5" if not self._get_is_dark() else "#3a1e1e"
                hover_bg_start = "#ffd5d5" if not self._get_is_dark() else "#4a2e2e"
                hover_bg_end = "#ffd5d5" if not self._get_is_dark() else "#4a2e2e"
            elif unpaid > 0 or total_cost > 40:
                # ⭐ 警告：欠费>$0 或 总花费>$40 → 深橙色边框
                border_color = "#FF6600"  # 深橙色
                hover_color = "#ffc68a"
                bg_start = "#fff5e5" if not self._get_is_dark() else "#3a2e1e"
                bg_end = "#fff5e5" if not self._get_is_dark() else "#3a2e1e"
                hover_bg_start = "#ffe5d5" if not self._get_is_dark() else "#4a3e2e"
                hover_bg_end = "#ffe5d5" if not self._get_is_dark() else "#4a3e2e"
            elif total_cost > 20:
                # ⭐ 注意：总花费>$20 → 橙色边框
                border_color = colors['border_warning']
                hover_color = "#ffc68a"
                bg_start = colors['bg_warning_start']
                bg_end = colors['bg_warning_end']
                hover_bg_start = colors['bg_warning_start']
                hover_bg_end = colors['bg_warning_end']
            else:
                # 正常：绿色边框
                border_color = colors['border_normal']
                hover_color = "#90d8b8" if not self._get_is_dark() else "#7c3aed"
                bg_start = colors['bg_normal_start']
                bg_end = colors['bg_normal_end']
                hover_bg_start = colors['bg_normal_start']
                hover_bg_end = colors['bg_normal_end']
            
            # ⭐ 根据状态设置边框宽度（欠费/高花费时加粗）
            if self.is_current:
                border_width = "4px"  # 当前账号：4px（最明显）
            elif unpaid > 20 or total_cost > 60:
                border_width = "4px"  # 严重欠费：4px粗边框
            elif unpaid > 0 or total_cost > 40:
                border_width = "3px"  # 警告：3px粗边框
            else:
                border_width = "2px"  # 正常：2px
            
            # ⭐ 计算新样式字符串（添加过渡效果减少闪烁）
            new_style = f"""
                #AccountCard {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                               stop:0 {bg_start}, stop:1 {bg_end});
                    border: {border_width} solid {border_color};
                    border-radius: 14px;
                    padding: 14px;
                }}
                #AccountCard:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                               stop:0 {hover_bg_start}, stop:1 {hover_bg_end});
                    border-color: {hover_color};
                }}
            """
            
            # ⭐ 只在样式真正改变时才调用setStyleSheet（减少闪烁）
            if not hasattr(self, '_last_style') or self._last_style != new_style:
                self.setStyleSheet(new_style)
                self._last_style = new_style
            
            # ⭐ 更新子组件颜色
            self._update_label_colors()
        except Exception as e:
            # 异常时使用默认样式
            logger.debug(f"更新样式异常: {e}")
            colors = self._get_theme_colors()
            self.setStyleSheet(f"""
                #AccountCard {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                               stop:0 {colors['bg_normal_start']}, stop:1 {colors['bg_normal_end']});
                    border: 2px solid {colors['border_normal']};
                    border-radius: 14px;
                    padding: 14px;
                }}
            """)
    
    def _get_is_dark(self):
        """判断是否为深色主题"""
        try:
            from utils.theme_manager import get_theme_manager
            return get_theme_manager().is_dark_theme()
        except:
            return False
    
    def _update_label_colors(self):
        """更新标签颜色（根据主题）"""
        try:
            colors = self._get_theme_colors()
            
            # ⭐ 移除通用标签颜色设置，让QSS样式生效
            # QSS已经处理了基础颜色，只在特殊情况（欠费、费用）时设置即可
            
            # 更新分隔线颜色
            if hasattr(self, 'findChildren'):
                for separator in self.findChildren(QFrame):
                    if separator.frameShape() == QFrame.Shape.HLine:
                        separator.setStyleSheet(f"background-color: {colors['separator']}; max-height: 1px;")
        except Exception as e:
            logger.debug(f"更新标签颜色失败: {e}")
    
    def _update_display(self):
        """更新显示内容"""
        # 邮箱（当前登录账号添加标记）
        email = self.account_data.get('email', 'unknown@cursor.com')
        if self.is_current:
            self.email_label.setText(f"⭐ {email}")  # 添加星标
        else:
            self.email_label.setText(f"📧 {email}")
        
        # 状态（进一步缩小）
        status = self.account_data.get('status', 'active')
        if status == 'active':
            self.status_label.setText("✅ 正常")
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #107c10;
                    color: white;
                    padding: 2px 8px;
                    border-radius: 6px;
                    font-size: 9px;
                    font-weight: bold;
                }
            """)
        elif status == 'expired':
            self.status_label.setText("⚠️ 已失效")
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #ffa500;
                    color: white;
                    padding: 2px 8px;
                    border-radius: 6px;
                    font-size: 9px;
                    font-weight: bold;
                }
            """)
        else:
            self.status_label.setText("❌ 失效")
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #e81123;
                    color: white;
                    padding: 2px 8px;
                    border-radius: 6px;
                    font-size: 9px;
                    font-weight: bold;
                }
            """)
        
        # 套餐（简化显示，节省空间）
        membership = self.account_data.get('membership_type', 'free')
        
        # 简化套餐名称显示
        membership_display = {
            'free': 'FREE',
            'free_trial': 'FREE',  # ⭐ FREE TRIAL 简化为 FREE
            'pro': 'PRO',
            'pro_trial': 'PRO',
            'business': 'BUSINESS',
            'team': 'TEAM',
            'enterprise': 'ENTERPRISE'
        }
        
        display_name = membership_display.get(membership.lower(), membership.upper())
        self.plan_label.setText(f"🎫 {display_name}")
        
        # ⭐ 费用显示：优先显示真实费用，否则显示估算
        membership = self.account_data.get('membership_type', 'free').lower()
        
        # 检查是否有真实费用数据
        total_cost = self.account_data.get('total_cost')
        
        # 调试：确保total_cost是有效数字
        if total_cost is not None:
            try:
                total_cost = float(total_cost)
                # 确保不是负数
                if total_cost < 0:
                    total_cost = 0
            except:
                total_cost = None
        
        # ⭐ 检查是否有模型详情（区分快速/详细模式）
        model_usage = self.account_data.get('model_usage', {})
        is_quick_mode = (total_cost == 0 and not model_usage and membership != 'free')
        
        if is_quick_mode:
            # 快速模式：提示点击📊按钮查看详细费用
            colors = self._get_theme_colors()
            self.usage_label.setText(f"💰 点📊查看费用")
            self.usage_label.setStyleSheet(f"color: {colors['text_secondary']}; font-size: 9px; font-style: italic; background: transparent; border: none;")
        elif total_cost is not None and total_cost >= 0 and membership != 'free':
            # 有真实费用数据，直接显示（详细模式）
            # ⭐ 优先检查是否有欠费
            unpaid_check = self.account_data.get('unpaid_amount', 0)
            try:
                unpaid_check = float(unpaid_check) if unpaid_check is not None else 0
            except:
                unpaid_check = 0
            
            # ⭐ 根据主题选择颜色
            is_dark = self._get_is_dark()
            
            if total_cost == 0:
                cost_text = "$0.00"
                color = "#10b981" if is_dark else "#107c10"  # 绿色（深色模式更亮）
            else:
                cost_text = f"${total_cost:.2f}"
                # ⭐ PRO套餐欠费规则（深色模式使用更亮的颜色）
                if unpaid_check > 20 or total_cost > 60:
                    color = "#ff5252" if is_dark else "#CC0000"  # 红色
                elif unpaid_check > 0 or total_cost > 40:
                    color = "#ff9800" if is_dark else "#FF6600"  # 橙色
                elif total_cost > 20:
                    color = "#ffc107" if is_dark else "#FFA500"  # 黄橙色
                else:
                    color = "#10b981" if is_dark else "#107c10"  # 绿色
            
            self.usage_label.setText(f"💰 已花费: {cost_text}")
            self.usage_label.setStyleSheet(f"color: {color}; font-size: 9px; font-weight: bold; background: transparent; border: none;")
        
        elif membership != 'free':
            # 没有真实费用，使用估算
            from utils.cost_calculator import calculate_cost_info, format_cost, get_cost_color
            cost_info = calculate_cost_info(self.account_data)
            used_value = cost_info['used_value']
            
            # 确保used_value不是负数
            if used_value < 0:
                used_value = 0
            
            cost_text = format_cost(used_value)
            color = get_cost_color(used_value, cost_info['monthly_cost'])
            self.usage_label.setText(f"💰 ~{cost_text}")
            self.usage_label.setStyleSheet(f"color: {color}; font-size: 9px; font-weight: bold; background: transparent; border: none;")
        
        else:
            # Free账号，显示使用率
            usage = self.account_data.get('usage_percent', 0)
            colors = self._get_theme_colors()
            self.usage_label.setText(f"📊 使用: {usage}%")
            self.usage_label.setStyleSheet(f"color: {colors['text_secondary']}; font-size: 9px; background: transparent; border: none;")
        
        # 剩余天数 / 订阅状态 / 欠费警告
        days = self.account_data.get('days_remaining', 0)
        membership = self.account_data.get('membership_type', 'free').lower()
        subscription_status = self.account_data.get('subscription_status', '')
        unpaid = self.account_data.get('unpaid_amount', 0)
        
        # ⭐ 安全转换欠费金额
        try:
            unpaid = float(unpaid) if unpaid is not None else 0
        except:
            unpaid = 0
        
        # ⭐ 根据主题选择颜色
        is_dark = self._get_is_dark()
        colors = self._get_theme_colors()
        
        # ⭐ 优先显示欠费警告（不同套餐规则不同）
        if membership in ['free', 'free_trial']:
            # FREE套餐：只要有欠费就立即限制（红色）
            if unpaid > 0:
                color = "#ff5252" if is_dark else "#e81123"
                self.days_label.setText(f"🚫 欠费: ${unpaid:.2f}")
                self.days_label.setStyleSheet(f"color: {color}; font-size: 9px; font-weight: bold; background: transparent; border: none;")
            elif days > 0:
                # 有剩余天数（试用期），显示剩余天数
                self.days_label.setText(f"⏰ 剩余: {days} 天")
                self.days_label.setStyleSheet(f"color: {colors['text_secondary']}; font-size: 9px; background: transparent; border: none;")
            elif subscription_status:
                # ⭐ FREE账号已绑卡（有订阅状态），显示订阅状态
                if subscription_status == 'active':
                    self.days_label.setText("✅ 已绑卡")
                    color_style = colors['text_secondary']
                elif subscription_status == 'trialing':
                    self.days_label.setText("⏰ 试用中")
                    color_style = colors['text_secondary']
                elif subscription_status == 'unpaid':
                    # ⭐ 未支付状态（有绑卡但未付款）
                    self.days_label.setText("💳 待付款")
                    color_style = "#ff9800" if is_dark else "#ffa500"  # 橙色警告
                elif subscription_status in ['past_due', 'incomplete']:
                    # ⭐ 支付逾期或未完成
                    self.days_label.setText("⚠️ 支付逾期")
                    color_style = "#ff9800" if is_dark else "#ffa500"  # 橙色警告
                elif subscription_status == 'canceled':
                    # ⭐ 订阅已取消
                    self.days_label.setText("❌ 已取消")
                    color_style = "#9e9e9e" if is_dark else "#757575"  # 灰色
                else:
                    self.days_label.setText(f"📋 {subscription_status}")
                    color_style = colors['text_secondary']
                self.days_label.setStyleSheet(f"color: {color_style}; font-size: 9px; background: transparent; border: none;")
            else:
                # ⭐ FREE账号未绑卡（无剩余天数且无订阅状态）
                color = "#9e9e9e" if is_dark else "#757575"
                self.days_label.setText("💳 未绑卡")
                self.days_label.setStyleSheet(f"color: {color}; font-size: 9px; background: transparent; border: none;")
        elif unpaid > 20:
            # PRO套餐：欠费超过$20才限制（红色）
            color = "#ff5252" if is_dark else "#e81123"
            self.days_label.setText(f"🚫 欠费: ${unpaid:.2f}")
            self.days_label.setStyleSheet(f"color: {color}; font-size: 9px; font-weight: bold; background: transparent; border: none;")
        elif unpaid > 0:
            # PRO套餐：有欠费但<=20，警告（橙色）
            color = "#ff9800" if is_dark else "#ffa500"
            self.days_label.setText(f"⚠️ 欠费: ${unpaid:.2f}")
            self.days_label.setStyleSheet(f"color: {color}; font-size: 9px; font-weight: bold; background: transparent; border: none;")
        # 判断是否为试用账号
        elif days > 0:
            # 试用账号或有试用期的账号，显示剩余天数
            self.days_label.setText(f"⏰ 剩余: {days} 天")
            self.days_label.setStyleSheet(f"color: {colors['text_secondary']}; font-size: 9px; background: transparent; border: none;")
        elif membership in ['pro', 'business', 'team', 'enterprise']:
            # 付费账号，显示订阅状态
            if subscription_status == 'active':
                self.days_label.setText("✅ 订阅: 正常")
            elif subscription_status == 'past_due':
                self.days_label.setText("⚠️ 订阅: 过期")
            elif subscription_status == 'canceled':
                self.days_label.setText("❌ 订阅: 已取消")
            elif subscription_status == 'trialing':
                self.days_label.setText("🆓 订阅: 试用中")
            elif subscription_status:
                # 有状态但是未知类型
                self.days_label.setText(f"📋 订阅: {subscription_status}")
            else:
                # 没有状态信息
                self.days_label.setText("❓ 订阅: 未知")
            self.days_label.setStyleSheet(f"color: {colors['text_secondary']}; font-size: 9px; background: transparent; border: none;")
        else:
            # Free账号
            self.days_label.setText(f"⏰ 剩余: {days} 天")
            self.days_label.setStyleSheet(f"color: {colors['text_secondary']}; font-size: 9px; background: transparent; border: none;")
        
        # 注册时间
        created_at = self.account_data.get('created_at', '')
        if created_at:
            try:
                # 解析时间字符串
                if 'T' in created_at or ' ' in created_at:
                    created_date = created_at[:10]
                else:
                    created_date = created_at
                self.created_label.setText(f"📅 注册: {created_date}")
            except:
                self.created_label.setText("📅 注册: --")
        else:
            self.created_label.setText("📅 注册: --")
        
        # 最后使用时间（从API使用记录获取）
        last_used = self.account_data.get('last_used', '')
        if last_used:
            try:
                # 处理多种时间格式
                # API格式: 2025-10-17T08:30:45.123Z
                # ISO格式: 2025-10-17T08:30:45+00:00
                time_str = last_used.replace('Z', '+00:00').replace('.000+00:00', '+00:00')
                
                # 尝试解析
                try:
                    last_used_time = datetime.fromisoformat(time_str)
                except:
                    # 如果失败，尝试只取日期时间部分
                    if 'T' in time_str:
                        time_str = time_str.split('.')[0]  # 移除毫秒
                    last_used_time = datetime.fromisoformat(time_str)
                
                # 转换为本地时区并计算时间差
                from datetime import timezone
                if last_used_time.tzinfo:
                    last_used_time = last_used_time.astimezone()
                
                now = datetime.now()
                if last_used_time.tzinfo:
                    now = datetime.now(timezone.utc).astimezone()
                
                delta = now - last_used_time
                
                if delta.days > 0:
                    time_text = f"{delta.days}天前"
                elif delta.seconds >= 3600:
                    hours = delta.seconds // 3600
                    time_text = f"{hours}小时前"
                elif delta.seconds >= 60:
                    minutes = delta.seconds // 60
                    time_text = f"{minutes}分钟前"
                else:
                    time_text = "刚刚"
                
                self.last_used_label.setText(f"🕐 最后使用: {time_text}")
            except Exception as e:
                # 解析失败，显示原始时间
                try:
                    # 尝试显示日期部分
                    date_part = last_used[:10] if len(last_used) >= 10 else last_used
                    self.last_used_label.setText(f"🕐 最后使用: {date_part}")
                except:
                    self.last_used_label.setText("🕐 最后使用: --")
        else:
            self.last_used_label.setText("🕐 最后使用: 从未")
    
    def _setup_animations(self):
        """设置动画效果（已禁用，避免闪烁）"""
        # 完全禁用淡入动画，避免刷新时的闪烁问题
        pass
    
    def update_account_data(self, account_data: dict):
        """
        更新账号数据（简化版）
        
        Args:
            account_data: 新的账号数据
        """
        try:
            if not account_data:
                return
            
            # ⭐ 简化：移除复杂的防抖逻辑（由主窗口统一管理）
            self.account_data = account_data
            
            # 更新样式
            try:
                self._update_style()
            except Exception as e:
                logger.debug(f"更新样式失败: {e}")
            
            # 更新显示
            try:
                self._update_display()
            except Exception as e:
                logger.debug(f"更新显示失败: {e}")
            
        except Exception as e:
            logger.error(f"更新账号数据失败: {e}")
    
    def update_account_data_silent(self, account_data: dict):
        """
        静默更新账号数据（不触发布局重排）
        用于批量更新时避免连续抖动
        
        Args:
            account_data: 新的账号数据
        """
        try:
            if not account_data:
                return
            
            # 保存当前几何信息
            saved_geometry = self.geometry()
            
            # 更新数据
            self.account_data = account_data
            
            # 更新样式（可能改变边框颜色）
            try:
                self._update_style()
            except Exception as e:
                logger.debug(f"更新样式失败: {e}")
            
            # 更新显示内容
            try:
                self._update_display()
            except Exception as e:
                logger.debug(f"更新显示失败: {e}")
            
            # 恢复几何信息（防止位置漂移）
            self.setGeometry(saved_geometry)
            
        except Exception as e:
            logger.error(f"静默更新失败: {e}")
    
    def _update_style_silent(self):
        """
        静默更新样式（只改变视觉，不触发重排）
        """
        try:
            # 保存几何信息
            saved_geometry = self.geometry()
            
            # 更新样式
            self._update_style()
            
            # 恢复几何信息
            self.setGeometry(saved_geometry)
            
        except Exception as e:
            logger.debug(f"静默样式更新失败: {e}")
    
    def set_loading(self, loading: bool):
        """
        设置加载状态（旋转动画）
        
        Args:
            loading: 是否加载中
        """
        # ⭐ 设置加载标志（刷新期间禁用悬停动画）
        self._is_loading = loading
        
        self.switch_btn.setEnabled(not loading)
        self.refresh_btn.setEnabled(not loading)
        self.detail_btn.setEnabled(not loading)
        self.delete_btn.setEnabled(not loading)
        
        if loading:
            self.refresh_btn.setToolTip("刷新中...")
            # 启动旋转动画
            self.refresh_btn.start_rotation()
        else:
            self.refresh_btn.setToolTip("刷新账号信息")
            # 停止旋转动画
            self.refresh_btn.stop_rotation()
    
    def _update_switch_button(self):
        """更新切换按钮的文字和样式"""
        if not hasattr(self, 'switch_btn'):
            return
        
        # 获取当前主题
        try:
            from utils.theme_manager import get_theme_manager
            theme_manager = get_theme_manager()
            is_dark = theme_manager.is_dark_theme()
        except:
            is_dark = False
        
        if self.is_current:
            # 当前登录账号：黄色按钮，文字改为"当前登录"
            self.switch_btn.setText("⭐ 当前登录")
            self.switch_btn.setProperty("success", False)
            self.switch_btn.setProperty("warning", True)
            
            if is_dark:
                # 深色主题：金黄色
                self.switch_btn.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                   stop:0 #FFD700, stop:1 #FFA500);
                        color: #2c3e50;
                        padding: 6px 10px;
                        font-size: 12px;
                        font-weight: bold;
                        border: 2px solid #FFD700;
                        border-radius: 8px;
                    }
                    QPushButton:hover {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                   stop:0 #FFC700, stop:1 #FF9500);
                        border-color: #FFC700;
                    }
                    QPushButton:pressed {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                   stop:0 #FFB700, stop:1 #FF8500);
                    }
                """)
            else:
                # 浅色主题：橙黄色
                self.switch_btn.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                   stop:0 #FFA500, stop:1 #FF8C00);
                        color: white;
                        padding: 6px 10px;
                        font-size: 12px;
                        font-weight: bold;
                        border: 2px solid #FF8C00;
                        border-radius: 8px;
                    }
                    QPushButton:hover {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                   stop:0 #FF9500, stop:1 #FF7C00);
                        border-color: #FF7C00;
                    }
                    QPushButton:pressed {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                   stop:0 #FF8500, stop:1 #FF6C00);
                    }
                """)
        else:
            # 非当前账号：恢复默认绿色，文字为"切换账号"
            self.switch_btn.setText("🔑 切换账号")
            self.switch_btn.setProperty("warning", False)
            self.switch_btn.setProperty("success", True)
            self.switch_btn.setStyleSheet("""
                QPushButton {
                    padding: 6px 10px;
                    font-size: 12px;
                    font-weight: bold;
                }
            """)
    
    def set_current(self, is_current: bool):
        """
        设置是否为当前登录账号
        
        Args:
            is_current: 是否为当前登录账号
        """
        self.is_current = is_current
        self._update_switch_button()
        self._update_style()
        self._update_display()
    
    def set_current_silent(self, is_current: bool):
        """
        静默设置是否为当前登录账号（不触发重排）
        
        Args:
            is_current: 是否为当前登录账号
        """
        # 保存几何信息
        saved_geometry = self.geometry()
        
        # 更新状态
        self.is_current = is_current
        self._update_switch_button()
        self._update_style()
        self._update_display()
        
        # 恢复几何信息
        self.setGeometry(saved_geometry)
    
    def set_selected(self, selected: bool):
        """
        设置选中状态（添加动画效果）
        
        Args:
            selected: 是否选中
        """
        # 阻塞信号，避免触发 stateChanged
        self.checkbox.blockSignals(True)
        was_selected = self.checkbox.isChecked()
        self.checkbox.setChecked(selected)
        self.checkbox.blockSignals(False)
        
        # 禁用选中动画，避免布局闪烁
        # if selected != was_selected:
        #     self._animate_selection(selected)
    
    def is_selected(self) -> bool:
        """
        获取选中状态
        
        Returns:
            bool: 是否选中
        """
        return self.checkbox.isChecked()
    
    def _animate_selection(self, selected: bool):
        """
        选中状态动画（优化版：不改变尺寸，避免布局闪烁）
        
        Args:
            selected: 是否选中
        """
        # 禁用选中动画，避免布局闪烁
        # 如果需要反馈，可以使用边框闪烁或其他不影响布局的效果
        pass
    
    def _on_checkbox_state_changed(self, state):
        """复选框状态改变事件 - 单击即可选中"""
        from PyQt6.QtCore import Qt
        checked = (state == Qt.CheckState.Checked.value)
        self.selection_changed.emit(self.account_id, checked)
        
        # 禁用选中动画，避免布局闪烁
        # self._animate_selection(checked)
    
    def fade_out(self, callback=None):
        """
        淡出动画
        
        Args:
            callback: 动画完成后的回调函数
        """
        # 如果没有启用动画，则创建临时的透明度效果
        if not hasattr(self, 'opacity_effect'):
            self.opacity_effect = QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(self.opacity_effect)
        
        fade_out_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        fade_out_animation.setDuration(200)  # 缩短动画时间
        fade_out_animation.setStartValue(1.0)
        fade_out_animation.setEndValue(0.0)
        fade_out_animation.setEasingCurve(QEasingCurve.Type.InCubic)  # 使用更快的缓动
        
        if callback:
            fade_out_animation.finished.connect(callback)
        
        fade_out_animation.start()
    
    def mousePressEvent(self, event):
        """鼠标按下事件（用于拖动多选）"""
        from PyQt6.QtCore import Qt
        
        if event.button() == Qt.MouseButton.LeftButton:
            # 检查是否在复选框区域
            pos = event.pos()
            checkbox_rect = self.checkbox.geometry()
            
            logger.debug(f"鼠标按下 - 位置: {pos}, 复选框区域: {checkbox_rect}, 卡片: {self.account_data.get('email', 'unknown')}")
            
            checkbox_rect.adjust(-5, -5, 5, 5)  # 扩大区域
            
            if checkbox_rect.contains(pos):
                logger.info(f"✅ 复选框区域点击，开始拖动: {self.account_data.get('email', 'unknown')}")
                self._is_dragging = True
                # 切换当前卡片的选中状态
                current_state = self.is_selected()
                self.set_selected(not current_state)
                # 通知主窗口开始拖动
                self.drag_select_start.emit(self)
                event.accept()
                return
            else:
                logger.debug(f"点击位置不在复选框区域")
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件（用于拖动多选）"""
        if self._is_dragging:
            # 通知主窗口鼠标移动
            logger.debug(f"卡片鼠标移动事件 - 位置: {event.pos()}, 卡片: {self.account_data.get('email', 'unknown')}")
            self.drag_select_move.emit(self, event)
            event.accept()
            return
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件（用于拖动多选）"""
        from PyQt6.QtCore import Qt
        
        if event.button() == Qt.MouseButton.LeftButton and self._is_dragging:
            self._is_dragging = False
            # 通知主窗口结束拖动
            self.drag_select_end.emit(self)
            event.accept()
            return
        
        super().mouseReleaseEvent(event)
    
    def resizeEvent(self, event):
        """窗口大小改变事件 - 更新失效标记的大小和位置"""
        super().resizeEvent(event)
        if hasattr(self, 'invalid_overlay'):
            # 让失效标记覆盖整个卡片
            self.invalid_overlay.setGeometry(0, 0, self.width(), self.height())
    
    def set_invalid(self, is_invalid: bool = True):
        """
        设置账号失效状态
        
        Args:
            is_invalid: 是否失效
        """
        self._is_invalid = is_invalid
        if hasattr(self, 'invalid_overlay'):
            self.invalid_overlay.setVisible(is_invalid)
            if is_invalid:
                # 确保覆盖层在最上层
                self.invalid_overlay.raise_()
                # 更新大小
                self.invalid_overlay.setGeometry(0, 0, self.width(), self.height())
                
                # ⭐ 更新状态标签为"已失效"
                if hasattr(self, 'status_label'):
                    self.status_label.setText("❌ 已失效")
                    self.status_label.setStyleSheet("""
                        QLabel {
                            background-color: #e81123;
                            color: white;
                            padding: 2px 8px;
                            border-radius: 6px;
                            font-size: 9px;
                            font-weight: bold;
                        }
                    """)
                
                logger.info(f"账号已标记为失效: {self.account_data.get('email', 'unknown')}")


