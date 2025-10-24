#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
当前账号信息面板
显示当前登录的账号信息、余额、使用情况和日志
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QGroupBox, QProgressBar,
    QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QTextCursor
from datetime import datetime


class DetectionThread(QThread):
    """账号检测线程"""
    
    detection_complete = pyqtSignal(dict)  # 检测完成信号（账号数据）
    detection_failed = pyqtSignal(str)  # 检测失败信号（错误消息）
    
    def __init__(self):
        super().__init__()
        self.running = True
    
    def run(self):
        """执行检测"""
        try:
            from core.current_account_detector import get_detector
            
            detector = get_detector()
            account = detector.detect_current_account()
            
            if account and account.get('status') == 'active':
                self.detection_complete.emit(account)
            else:
                error_msg = account.get('error', '未找到账号或检测失败') if account else '未找到账号'
                self.detection_failed.emit(error_msg)
                
        except Exception as e:
            self.detection_failed.emit(f"检测异常: {str(e)}")


class CurrentAccountPanel(QWidget):
    """当前账号信息面板"""
    
    # 信号
    register_clicked = pyqtSignal()  # 一键注册
    account_detected = pyqtSignal(dict)  # 账号检测完成
    
    def __init__(self, parent=None):
        """初始化面板"""
        super().__init__(parent)
        
        self.current_account = None
        self.detection_thread = None
        self._setup_ui()
        
        # ⭐ 确保初始主题样式正确应用
        try:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, self._apply_theme_styles)
        except:
            pass
    
    def _setup_ui(self):
        """设置 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(4)  # ⭐ 最小间距，让所有组件紧密贴合
        
        # 一键注册按钮（添加脉冲光晕效果）
        self.register_btn = QPushButton("🤖 一键注册新账号")
        self.register_btn.setMinimumHeight(40)
        self.register_btn.setProperty("primary", True)  # 使用主色调
        self.register_btn.clicked.connect(lambda: self.register_clicked.emit())
        main_layout.addWidget(self.register_btn)
        
        # 为注册按钮添加脉冲光晕
        self._setup_register_button_glow()
        
        # 当前账号信息组
        account_group = QGroupBox("当前账号")
        account_layout = QVBoxLayout(account_group)
        account_layout.setSpacing(8)
        
        # 邮箱
        self.email_label = QLabel("邮箱: 未登录")
        self.email_label.setWordWrap(True)
        account_layout.addWidget(self.email_label)
        
        # 套餐类型
        self.plan_label = QLabel("套餐: --")
        account_layout.addWidget(self.plan_label)
        
        # 剩余天数
        self.days_label = QLabel("剩余: -- 天")
        account_layout.addWidget(self.days_label)
        
        # 检测按钮
        detect_btn_layout = QHBoxLayout()
        detect_btn_layout.setSpacing(5)
        
        self.detect_btn = QPushButton("🔍 检测当前账号")
        self.detect_btn.setProperty("secondary", True)
        self.detect_btn.clicked.connect(self.start_detection)
        detect_btn_layout.addWidget(self.detect_btn)
        
        self.import_btn = QPushButton("➕ 导入")
        self.import_btn.setProperty("secondary", True)
        self.import_btn.setEnabled(False)
        self.import_btn.clicked.connect(self.import_current_account)
        detect_btn_layout.addWidget(self.import_btn)
        
        account_layout.addLayout(detect_btn_layout)
        
        main_layout.addWidget(account_group)
        
        # 使用情况组（改为模型费用详情）- 设置固定高度
        usage_group = QGroupBox("使用情况")
        usage_group.setFixedHeight(120)  # ⭐ 固定高度，防止挤压日志区域
        usage_layout = QVBoxLayout(usage_group)
        usage_layout.setSpacing(5)
        usage_layout.setContentsMargins(8, 8, 8, 8)
        
        # 使用滚动区域容纳模型费用列表
        from PyQt6.QtWidgets import QScrollArea
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameStyle(QScrollArea.Shape.NoFrame)
        # 滚动区域使用透明背景，继承父容器样式
        scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        
        # 模型费用列表容器widget
        usage_content = QWidget()
        usage_content.setObjectName("UsageContent")  # 设置对象名用于CSS选择器
        self.model_usage_layout = QVBoxLayout(usage_content)
        self.model_usage_layout.setSpacing(3)
        self.model_usage_layout.setContentsMargins(0, 0, 0, 0)
        
        # 初始提示
        self.no_usage_label = QLabel("暂无使用记录")
        self.no_usage_label.setProperty("usageHint", True)  # 使用属性标记
        self.model_usage_layout.addWidget(self.no_usage_label)
        
        # 在布局末尾添加弹性空间
        self.model_usage_layout.addStretch()
        
        scroll_area.setWidget(usage_content)
        usage_layout.addWidget(scroll_area)
        
        main_layout.addWidget(usage_group)
        
        # 日志输出组 - 使用内置标题，更紧凑的布局
        self.log_group = QGroupBox()  # 不使用标题，完全自定义
        self.log_group.setObjectName("LogGroup")  # 设置对象名用于CSS选择器
        
        # 紧凑的布局，最小间距
        log_layout = QVBoxLayout(self.log_group)
        log_layout.setContentsMargins(6, 5, 6, 6)  # ⭐ 最小边距
        log_layout.setSpacing(3)  # ⭐ 最小间距
        
        # 紧凑的标题栏
        title_container = QHBoxLayout()
        title_container.setContentsMargins(0, 0, 0, 0)
        title_container.setSpacing(5)
        
        # 日志标题 - 更小字体
        log_title = QLabel("操作日志")
        log_title.setProperty("logTitle", True)  # 使用属性标记
        log_title.setFixedHeight(18)  # ⭐ 固定高度，减少占用空间
        title_container.addWidget(log_title)
        
        title_container.addStretch()
        
        # 更小的清空按钮
        clear_btn = QPushButton("清空")
        clear_btn.setProperty("logClear", True)  # 使用属性标记
        clear_btn.setFixedSize(35, 18)  # ⭐ 更小尺寸
        title_container.addWidget(clear_btn)
        
        # 添加标题栏
        log_layout.addLayout(title_container)
        
        # 日志文本区域 - 紧贴标题
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(180)  # ⭐ 稍微减小高度，腾出空间
        self.log_text.setObjectName("LogText")  # 设置对象名用于CSS选择器
        
        # 连接清空功能
        clear_btn.clicked.connect(self.log_text.clear)
        
        # 添加日志文本区域
        log_layout.addWidget(self.log_text)
        
        # 应用主题样式
        self._apply_theme_styles()
        
        # ⭐ 日志组设置为扩展模式，让它占据剩余所有空间
        main_layout.addWidget(self.log_group, 1)  # stretch factor = 1
    
    def _apply_theme_styles(self):
        """应用主题样式（支持深色模式）"""
        from utils.theme_manager import get_theme_manager
        theme_manager = get_theme_manager()
        
        # 判断当前是否为深色模式
        is_dark = theme_manager.get_current_theme() == "dark"
        
        if is_dark:
            # 深色模式样式
            log_group_style = """
                QGroupBox#LogGroup {
                    border: 1px solid #374151;
                    border-radius: 8px;
                    background-color: #242938;
                    margin: 0px;
                    padding: 0px;
                }
            """
            
            log_title_style = """
                QLabel[logTitle="true"] {
                    font-weight: bold;
                    font-size: 10px;
                    color: #a78bfa;
                    padding: 0px;
                    margin: 0px;
                }
            """
            
            clear_btn_style = """
                QPushButton[logClear="true"] {
                    background-color: #dc2626;
                    color: white;
                    border: none;
                    border-radius: 2px;
                    font-size: 8px;
                    padding: 0px;
                    margin: 0px;
                }
                QPushButton[logClear="true"]:hover {
                    background-color: #ef4444;
                }
                QPushButton[logClear="true"]:pressed {
                    background-color: #b91c1c;
                }
            """
            
            log_text_style = """
                QTextEdit#LogText {
                    background-color: #2b2b2b;
                    color: #e0e3ea;
                    font-family: 'Microsoft YaHei', 'Consolas', monospace;
                    font-size: 9px;
                    padding: 8px;
                    border: 1px solid #444;
                    border-radius: 4px;
                    margin: 0px;
                }
                QTextEdit#LogText:focus {
                    border: 1px solid #8b5cf6;
                }
            """
            
            usage_hint_style = """
                QLabel[usageHint="true"] {
                    color: #9ca3af;
                    font-size: 10px;
                }
            """
            
            usage_model_style = """
                QLabel[usageModel="true"] {
                    color: #9ca3af;
                    font-size: 10px;
                }
            """
            
            usage_cost_style = """
                QLabel[usageCost="true"] {
                    color: #10b981;
                    font-size: 11px;
                    font-weight: bold;
                }
            """
        else:
            # 浅色模式样式
            log_group_style = """
                QGroupBox#LogGroup {
                    border: 1px solid #f8d7da;
                    border-radius: 8px;
                    background-color: #ffffff;
                    margin: 0px;
                    padding: 0px;
                }
            """
            
            log_title_style = """
                QLabel[logTitle="true"] {
                    font-weight: bold;
                    font-size: 10px;
                    color: #ff758c;
                    padding: 0px;
                    margin: 0px;
                }
            """
            
            clear_btn_style = """
                QPushButton[logClear="true"] {
                    background-color: #ff9aa2;
                    color: white;
                    border: none;
                    border-radius: 2px;
                    font-size: 8px;
                    padding: 0px;
                    margin: 0px;
                }
                QPushButton[logClear="true"]:hover {
                    background-color: #ff8a94;
                }
                QPushButton[logClear="true"]:pressed {
                    background-color: #ff7a86;
                }
            """
            
            log_text_style = """
                QTextEdit#LogText {
                    background-color: #ffffff;
                    color: #2c3e50;
                    font-family: 'Microsoft YaHei', 'Consolas', monospace;
                    font-size: 9px;
                    padding: 8px;
                    border: 1px solid #ffe8ea;
                    border-radius: 4px;
                    margin: 0px;
                }
                QTextEdit#LogText:focus {
                    border: 1px solid #ff9aa2;
                }
            """
            
            usage_hint_style = """
                QLabel[usageHint="true"] {
                    color: #666666;
                    font-size: 10px;
                }
            """
            
            usage_model_style = """
                QLabel[usageModel="true"] {
                    color: #a0a0a0;
                    font-size: 10px;
                }
            """
            
            usage_cost_style = """
                QLabel[usageCost="true"] {
                    color: #107c10;
                    font-size: 11px;
                    font-weight: bold;
                }
            """
        
        # 应用样式（安全地应用，避免 None 错误）
        try:
            if hasattr(self, 'log_group') and self.log_group:
                self.log_group.setStyleSheet(log_group_style)
            if hasattr(self, 'log_text') and self.log_text:
                self.log_text.setStyleSheet(log_text_style)
            
            # 应用全局样式（用于标签和按钮）
            self.setStyleSheet(log_title_style + clear_btn_style + usage_hint_style + usage_model_style + usage_cost_style)
        except Exception as e:
            # 静默处理样式应用错误，避免阻塞UI启动
            logger = None
            try:
                from utils.logger import get_logger
                logger = get_logger("current_account_panel")
                logger.warning(f"应用主题样式时出错: {e}")
            except:
                pass
    
    def update_account_info(self, account_data: dict):
        """
        更新账号信息
        
        Args:
            account_data: 账号数据字典
        """
        self.current_account = account_data
        
        # 更新显示
        email = account_data.get('email', '未知')
        self.email_label.setText(f"📧 {email}")
        
        # 套餐
        plan = account_data.get('membership_type', 'free')
        self.plan_label.setText(f"🎫 {plan.upper()}")
        
        # 剩余天数/绑卡状态
        days = account_data.get('days_remaining', 0)
        subscription_status = account_data.get('subscription_status', '')
        membership = plan.lower()
        
        # ⭐ 根据套餐类型和状态显示不同信息
        if membership in ['free', 'free_trial']:
            if days > 0:
                self.days_label.setText(f"⏰ 剩余: {days} 天")
            elif subscription_status:
                if subscription_status == 'active':
                    self.days_label.setText("✅ 已绑卡")
                elif subscription_status == 'trialing':
                    self.days_label.setText("⏰ 试用中")
                elif subscription_status == 'unpaid':
                    self.days_label.setText("💳 待付款")
                elif subscription_status in ['past_due', 'incomplete']:
                    self.days_label.setText("⚠️ 支付逾期")
                elif subscription_status == 'canceled':
                    self.days_label.setText("❌ 已取消")
                else:
                    self.days_label.setText(f"📋 {subscription_status}")
            else:
                self.days_label.setText("💳 未绑卡")
        else:
            # PRO/BUSINESS等付费套餐
            if days > 0:
                self.days_label.setText(f"⏰ 剩余: {days} 天")
            elif subscription_status:
                if subscription_status == 'active':
                    self.days_label.setText("✅ 订阅: 正常")
                elif subscription_status == 'trialing':
                    self.days_label.setText("⏰ 试用中")
                else:
                    self.days_label.setText(f"📋 {subscription_status}")
            else:
                self.days_label.setText("-- 天")
        
        # ⭐ 更新模型费用详情
        self._update_model_usage(account_data)
        
        # ⭐ 确保主题样式正确（防止被其他操作覆盖）
        try:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(50, self._apply_theme_styles)
        except:
            pass
    
    def clear_account_info(self):
        """清空账号信息"""
        self.current_account = None
        self.email_label.setText("邮箱: 未登录")
        self.plan_label.setText("套餐: --")
        self.days_label.setText("剩余: -- 天")
        self._clear_model_usage()
    
    def _clear_model_usage(self):
        """清空模型费用显示"""
        # 清除所有模型费用widget
        while self.model_usage_layout.count():
            item = self.model_usage_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 显示"暂无使用记录"
        self.no_usage_label = QLabel("暂无使用记录")
        self.no_usage_label.setProperty("usageHint", True)
        self.model_usage_layout.addWidget(self.no_usage_label)
    
    def _update_model_usage(self, account_data: dict):
        """更新模型费用详情（从数据库读取，不调用API）"""
        # 清除旧内容
        while self.model_usage_layout.count():
            item = self.model_usage_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 从数据库读取模型费用JSON
        model_usage_json = account_data.get('model_usage_json')
        
        if not model_usage_json:
            # 如果没有模型详情，但有总费用，显示总费用
            total_cost = account_data.get('total_cost', 0)
            if total_cost and total_cost > 0:
                # 显示总费用
                total_row = QHBoxLayout()
                total_label = QLabel("总计")
                total_label.setProperty("usageModel", True)
                total_row.addWidget(total_label)
                total_row.addStretch()
                cost_label = QLabel(f"${total_cost:.2f}")
                cost_label.setProperty("usageCost", True)
                total_row.addWidget(cost_label)
                
                total_widget = QWidget()
                total_widget.setLayout(total_row)
                self.model_usage_layout.addWidget(total_widget)
                
                # 提示刷新获取详情
                hint = QLabel("刷新账号可查看详情")
                hint.setProperty("usageHint", True)
                self.model_usage_layout.addWidget(hint)
            else:
                # 没有任何数据
                no_usage = QLabel("暂无使用记录")
                no_usage.setProperty("usageHint", True)
                self.model_usage_layout.addWidget(no_usage)
            return
        
        # 解析JSON
        try:
            import json
            by_model = json.loads(model_usage_json)
            
            if by_model:
                # ⭐ 先显示总费用（醒目）
                total_cost = account_data.get('total_cost', 0)
                if total_cost and total_cost > 0:
                    total_row = QHBoxLayout()
                    total_label = QLabel("💰 总费用")
                    total_label.setStyleSheet("font-weight: bold; font-size: 12px;")
                    total_row.addWidget(total_label)
                    total_row.addStretch()
                    
                    total_cost_label = QLabel(f"${total_cost:.2f}")
                    total_cost_label.setStyleSheet("color: #e74c3c; font-weight: bold; font-size: 13px;")
                    total_row.addWidget(total_cost_label)
                    
                    total_widget = QWidget()
                    total_widget.setLayout(total_row)
                    self.model_usage_layout.addWidget(total_widget)
                    
                    # 分隔线
                    from PyQt6.QtWidgets import QFrame
                    line = QFrame()
                    line.setFrameShape(QFrame.Shape.HLine)
                    line.setStyleSheet("background-color: #444; margin: 3px 0;")
                    self.model_usage_layout.addWidget(line)
                
                # 按费用排序，显示前3个模型
                sorted_models = sorted(by_model.items(), key=lambda x: x[1]['cost'], reverse=True)
                
                for model, data in sorted_models[:3]:  # ⭐ 只显示费用最高的3个模型
                    # 创建模型行
                    model_row = QHBoxLayout()
                    
                    # 模型名称（简化）
                    model_name = model.replace('claude-', '').replace('-sonnet-thinking', '').replace('gpt-', 'gpt-')
                    model_label = QLabel(model_name)
                    model_label.setProperty("usageModel", True)
                    model_row.addWidget(model_label)
                    
                    model_row.addStretch()
                    
                    # 费用
                    cost_label = QLabel(f"${data['cost']:.2f}")
                    cost_label.setProperty("usageCost", True)
                    model_row.addWidget(cost_label)
                    
                    # 创建widget容器
                    model_widget = QWidget()
                    model_widget.setLayout(model_row)
                    self.model_usage_layout.addWidget(model_widget)
                
                # 如果模型超过3个，显示提示
                if len(sorted_models) > 3:
                    more_hint = QLabel(f"... 还有 {len(sorted_models) - 3} 个模型")
                    more_hint.setProperty("usageHint", True)
                    more_hint.setStyleSheet("font-size: 10px; color: #999;")
                    self.model_usage_layout.addWidget(more_hint)
            else:
                # 没有模型数据
                no_model = QLabel("暂无模型使用")
                no_model.setProperty("usageHint", True)
                self.model_usage_layout.addWidget(no_model)
                
        except Exception as e:
            # 解析失败
            error_label = QLabel("数据加载失败")
            error_label.setProperty("usageHint", True)
            self.model_usage_layout.addWidget(error_label)
    
    def log(self, message: str):
        """
        添加日志（带颜色标记，支持深色/浅色模式）
        
        Args:
            message: 日志消息
        """
        try:
            from utils.theme_manager import get_theme_manager
            
            current_time = datetime.now().strftime("%H:%M:%S")
            
            # ⭐ 判断当前主题
            theme_manager = get_theme_manager()
            is_dark = theme_manager.current_theme == 'dark'
            
            # ⭐ 根据消息内容和主题设置颜色（浅色模式使用更深的颜色）
            if "✅" in message or "成功" in message:
                # 成功：绿色
                color = "#4CAF50" if is_dark else "#1B5E20"  # 浅色模式用更深的绿
            elif "❌" in message or "失败" in message or "错误" in message:
                # 失败/错误：红色
                color = "#F44336" if is_dark else "#B71C1C"  # 浅色模式用更深的红
            elif "⚠️" in message or "警告" in message:
                # 警告：橙色
                color = "#FF9800" if is_dark else "#E65100"
            elif "🔄" in message or "刷新" in message:
                # 刷新：蓝色
                color = "#2196F3" if is_dark else "#0D47A1"  # 浅色模式用更深的蓝
            elif "📊" in message or "批量" in message:
                # 批量操作：紫色
                color = "#9C27B0" if is_dark else "#4A148C"  # 浅色模式用更深的紫
            else:
                # 普通消息：默认颜色
                color = "#e0e3ea" if is_dark else "#1a1a1a"  # 浅色模式用更深的灰黑色
            
            # HTML格式化日志（时间戳在浅色模式下也用深色）
            time_color = "#999" if is_dark else "#666"  # 浅色模式时间戳用深灰
            log_entry = f'<span style="color: {time_color};">[{current_time}]</span> <span style="color: {color}; font-weight: 500;">{message}</span>'
            
            # 添加日志
            self.log_text.append(log_entry)
            
            # ⭐ 限制日志行数（最多保留500行，超出则清除最旧的）
            document = self.log_text.document()
            if document.blockCount() > 500:
                # 删除前100行
                cursor = self.log_text.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.Start)
                for _ in range(100):
                    cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                    cursor.removeSelectedText()
                    cursor.deleteChar()  # 删除换行符
            
            # 平滑滚动到底部
            self._smooth_scroll_to_bottom()
            
        except Exception as e:
            # 静默处理，避免日志函数本身导致崩溃
            pass
    
    def _smooth_scroll_to_bottom(self):
        """平滑滚动到底部"""
        scrollbar = self.log_text.verticalScrollBar()
        target_value = scrollbar.maximum()
        current_value = scrollbar.value()
        
        # 如果已经在底部，直接返回
        if abs(target_value - current_value) < 10:
            scrollbar.setValue(target_value)
            return
        
        # 创建平滑滚动动画
        animation = QPropertyAnimation(scrollbar, b"value")
        animation.setDuration(300)
        animation.setStartValue(current_value)
        animation.setEndValue(target_value)
        animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        animation.start()
        
        # 保存引用
        self._scroll_animation = animation
    
    def start_detection(self, silent=False):
        """
        开始检测当前账号
        
        Args:
            silent: 是否静默检测（不输出日志和禁用按钮）
        """
        if self.detection_thread and self.detection_thread.isRunning():
            if not silent:
                self.log("⏳ 检测正在进行中...")
            return
        
        # 清理旧线程
        if self.detection_thread:
            self.detection_thread.deleteLater()
            self.detection_thread = None
        
        if not silent:
            self.log("🔍 开始检测当前 Cursor 账号...")
            self.detect_btn.setEnabled(False)
            self.detect_btn.setText("⏳ 检测中...")
        
        # 创建并启动检测线程
        self.detection_thread = DetectionThread()
        self.detection_thread.detection_complete.connect(self.on_detection_complete)
        self.detection_thread.detection_failed.connect(lambda msg: self.on_detection_failed(msg, silent))
        self.detection_thread.finished.connect(lambda: self.on_detection_finished(silent))
        self.detection_thread.start()
    
    def on_detection_complete(self, account_data: dict):
        """检测完成回调"""
        self.log(f"✅ 检测成功: {account_data.get('email', '未知')}")
        
        # ⭐ 如果有 model_usage（字典），转换为 model_usage_json（字符串）
        if 'model_usage' in account_data and account_data['model_usage']:
            import json
            try:
                account_data['model_usage_json'] = json.dumps(account_data['model_usage'])
            except:
                pass
        
        # 更新显示
        self.update_account_info(account_data)
        
        # 启用导入按钮
        self.import_btn.setEnabled(True)
        
        # ⭐ 确保主题样式正确（防止被覆盖）
        try:
            self._apply_theme_styles()
        except Exception as e:
            pass
        
        # 发送信号
        self.account_detected.emit(account_data)
    
    def on_detection_failed(self, error_msg: str, silent=False):
        """检测失败回调"""
        if not silent:
            self.log(f"❌ 检测失败: {error_msg}")
            self.clear_account_info()
        self.import_btn.setEnabled(False)
    
    def on_detection_finished(self, silent=False):
        """检测线程结束回调"""
        if not silent:
            self.detect_btn.setEnabled(True)
            self.detect_btn.setText("🔍 检测当前账号")
        
        # 清理线程
        if self.detection_thread:
            self.detection_thread.deleteLater()
            self.detection_thread = None
    
    def import_current_account(self):
        """导入当前账号到管理器"""
        if not self.current_account:
            self.log("❌ 没有可导入的账号")
            return
        
        try:
            from core.account_storage import get_storage
            
            storage = get_storage()
            
            # 准备账号数据
            account_data = {
                'email': self.current_account.get('email'),
                'access_token': self.current_account.get('access_token'),
                'refresh_token': self.current_account.get('refresh_token'),
                'user_id': self.current_account.get('user_id'),
                'membership_type': self.current_account.get('membership_type'),
                'usage_percent': self.current_account.get('usage_percent'),
                'used': self.current_account.get('used'),
                'limit': self.current_account.get('limit'),
                'days_remaining': self.current_account.get('days_remaining', 0)
            }
            
            # 添加到数据库
            account_id = storage.add_account(account_data)
            
            if account_id:
                self.log(f"✅ 账号已导入: {account_data['email']}")
            else:
                self.log(f"⚠️ 账号可能已存在: {account_data['email']}")
                
        except Exception as e:
            self.log(f"❌ 导入失败: {str(e)}")
    
    def _setup_register_button_glow(self):
        """为注册按钮添加温柔的脉冲光晕（优化版：避免跳动）"""
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QGraphicsOpacityEffect
        from PyQt6.QtGui import QColor
        from PyQt6.QtCore import QPropertyAnimation, QEasingCurve
        
        # ⭐ 改用透明度脉冲，避免阴影大小变化导致的跳动
        # 创建固定的阴影效果（不变化）
        self._register_glow = QGraphicsDropShadowEffect(self.register_btn)
        self._register_glow.setBlurRadius(16)  # 固定大小
        self._register_glow.setColor(QColor(255, 117, 140, 80))  # 珊瑚粉光晕
        self._register_glow.setOffset(0, 0)
        self.register_btn.setGraphicsEffect(self._register_glow)
        
        # 注意：不使用脉冲动画，避免跳动
        # 光晕保持恒定，视觉稳定
        # 如果需要动态效果，可以改用CSS动画或更细微的透明度变化
    

