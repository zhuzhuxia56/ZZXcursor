#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口
Zzx-Cursor-Auto 的主界面
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QScrollArea, QMessageBox, QToolBar,
    QLabel, QSplitter, QSizePolicy, QTabWidget, QDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QAction

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.account_storage import get_storage
from core.cursor_api import get_api_client
from core.cursor_switcher import get_switcher
from core.email_generator import init_email_generator  # 保留（无限邮箱功能）
from gui.widgets.account_card import AccountCard
from gui.widgets.status_bar import CustomStatusBar
from gui.widgets.current_account_panel import CurrentAccountPanel
from gui.widgets.account_toolbar import AccountToolbar
from gui.widgets.flow_layout import FlowLayout
from gui.dialogs.settings_dialog import SettingsDialog
from gui.dialogs.account_detail_dialog import AccountDetailDialog
from gui.dialogs.switch_account_dialog import SwitchAccountDialog
from gui.dialogs.payment_config_dialog import PaymentConfigDialog
from core.thread_manager import get_thread_manager
from utils.error_handler import get_error_handler, safe_execute
from utils.logger import get_logger
from utils.theme_manager import get_theme_manager
from utils.app_paths import get_config_file

logger = get_logger("main_window")


class RefreshThread(QThread):
    """刷新账号线程（优化版：增强异常处理和资源清理）"""
    
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(int, dict)
    
    def __init__(self, account_id: int, session_token: str = None, access_token: str = None, is_batch: bool = False):
        super().__init__()
        self.account_id = account_id
        # ⭐ 优先使用 SessionToken (type=web) 调用 API
        # SessionToken 格式: user_xxx::jwt (用于 API 调用获取账号信息)
        # AccessToken 格式: eyJhbGc... (type=session，用于客户端登录)
        self.session_token = session_token
        self.access_token = access_token
        self.is_batch = is_batch  # ⭐ 是否为批量刷新（快速模式）
        self._is_running = True
        
    def stop(self):
        """停止线程"""
        self._is_running = False
        self.quit()
    
    def run(self):
        """执行刷新"""
        try:
            if not self._is_running:
                return
                
            api = get_api_client()
            
            # ⭐ 日志：准备调用 API
            logger.debug(f"  ↳ [线程] 准备调用 API (account_id={self.account_id})")
            if self._is_running:
                self.progress.emit(self.account_id, 30, "连接 API...")
            
            # ⭐ 优先使用 SessionToken 调用 API（用于获取账号信息）
            # 如果没有 SessionToken，则使用 AccessToken
            token = self.session_token or self.access_token
            
            if not token:
                logger.error(f"  ↳ [线程] 没有可用的 Token (account_id={self.account_id})")
                if self._is_running:
                    self.progress.emit(self.account_id, 0, "缺少 Token")
                    self.finished.emit(self.account_id, {})
                return
            
            if not self._is_running:
                return
            
            # ⭐ 日志：调用 API
            mode = "快速模式" if self.is_batch else "详细模式"
            logger.debug(f"  ↳ [线程] 调用 get_account_details ({mode})...")
            if self._is_running:
                self.progress.emit(self.account_id, 50, "获取账号信息...")
            
            # ⭐ 根据是否批量刷新决定是否获取详细数据
            detailed = not self.is_batch  # 批量刷新时不获取详细数据
            details = api.get_account_details(token, detailed=detailed)
            
            if not self._is_running:
                return
            
            if details:
                # ⭐ 日志：API 返回成功
                logger.debug(f"  ↳ [线程] API 返回成功")
                if self._is_running:
                    self.progress.emit(self.account_id, 100, "刷新成功")
                    self.finished.emit(self.account_id, details)
            else:
                # ⭐ 日志：API 返回失败
                logger.warning(f"  ↳ [线程] API 返回空数据")
                if self._is_running:
                    self.progress.emit(self.account_id, 0, "API 返回空")
                    self.finished.emit(self.account_id, {})
                
        except Exception as e:
            logger.error(f"  ↳ [线程] 刷新异常: {e}", exc_info=True)
            # ⭐ 即使出错也发送完成信号，确保批量刷新继续
            if self._is_running:
                try:
                    self.progress.emit(self.account_id, 0, f"错误: {e}")
                    self.finished.emit(self.account_id, {})
                except:
                    pass
        finally:
            # ⭐ 确保清理标志
            self._is_running = False


class MainWindow(QMainWindow):
    """主窗口类"""
    
    # 定义信号（确保在主线程中处理刷新完成）
    refresh_finished_signal = pyqtSignal(int, dict)
    
    def __init__(self, pre_detected_account=None):
        """初始化主窗口
        
        Args:
            pre_detected_account: 启动时预检测的账号信息
        """
        super().__init__()
        
        self.setWindowTitle("🎯 Zzx Cursor Auto Manager")
        self.setMinimumSize(1100, 700)  # 最小尺寸，确保舒适显示2列卡片
        
        # 设置初始窗口大小（启动时显示2列）
        self.resize(1100, 750)
        
        # 初始化核心组件
        self.thread_manager = get_thread_manager()
        self.error_handler = get_error_handler()
        
        # 初始化主题管理器
        self.theme_manager = get_theme_manager(str(get_config_file()))
        self.theme_manager.theme_changed.connect(self._on_theme_changed)
        
        # 初始化业务组件
        self.storage = get_storage()
        self.api = get_api_client()
        self.switcher = get_switcher()
        
        # UI组件
        self.account_cards = {}
        self.refresh_callbacks = {}  # 刷新回调函数 {account_id: callback}
        self.selected_account_ids = set()  # 选中的账号 ID 集合
        self.current_login_email = None  # 当前登录的邮箱地址
        self._is_closing = False  # ⭐ 关闭标志
        self._first_load = True  # ⭐ 是否首次加载（只在首次播放动画）
        
        # 连接信号，确保刷新完成在主线程处理
        self.refresh_finished_signal.connect(self._on_refresh_finished)
        
        # ⭐ 拖动多选功能
        self.is_drag_selecting = False  # 是否正在拖动多选
        self.drag_start_card = None  # 拖动起始的卡片
        
        # 筛选和排序状态
        self.current_filter = {}
        self.current_sort = ('created_at', False)
        
        # 自动检测定时器（已禁用，只在启动时检测一次）
        self.auto_detect_timer = None
        
        # 记录上一次窗口宽度，用于判断是否需要调整分割器
        self.last_window_width = 0
        
        # ⭐ 搜索防抖定时器（避免频繁刷新）
        # 搜索防抖定时器
        self.search_debounce_timer = QTimer()
        self.search_debounce_timer.setSingleShot(True)
        self.search_debounce_timer.timeout.connect(self._do_search_refresh)
        
        # ⭐ 筛选防抖定时器（防止筛选时闪烁）
        self.filter_debounce_timer = QTimer()
        self.filter_debounce_timer.setSingleShot(True)
        self.filter_debounce_timer.timeout.connect(self._do_filter_refresh)
        
        # ⭐ 排序防抖定时器（防止排序时闪烁）
        self.sort_debounce_timer = QTimer()
        self.sort_debounce_timer.setSingleShot(True)
        self.sort_debounce_timer.timeout.connect(self._do_sort_refresh)
        
        # ⭐ 新增：批量更新管理器
        self._batch_update_manager = {
            'pending_cards': {},      # {account_id: account_data}
            'timer': QTimer()
        }
        self._batch_update_manager['timer'].setSingleShot(True)
        self._batch_update_manager['timer'].timeout.connect(self._flush_card_updates)
        
        # 处理预检测的账号信息
        self._handle_pre_detected_account(pre_detected_account)
        
        # 加载配置
        self._load_config()
        
        # 设置 UI
        self._setup_ui()
        
        # 应用主题（替代原来的 _load_stylesheet）
        self.theme_manager.force_reload_current_theme()
        
        # 加载账号
        self.refresh_accounts()
        
        # ⭐ 如果有预检测的账号信息，更新右侧面板
        if pre_detected_account:
            # 延迟更新右侧面板，确保UI完全初始化
            QTimer.singleShot(1000, lambda: self._update_current_panel_from_predetected(pre_detected_account))
            logger.info(f"⏰ 已安排右侧面板更新任务，1秒后执行")
        
        # ⚠️ 禁用自动检测 - 启动时已完成检测
        # self._start_auto_detection()
        
        # ⚠️ 禁用启动后的自动检测 - 启动画面已完成检测
        # QTimer.singleShot(1000, self._auto_detect_account)
        
        # 设置窗口焦点策略，确保能接收键盘事件
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # 安装事件过滤器，确保主窗口能捕获所有键盘事件
        self.installEventFilter(self)
        
        # ⭐ 创建主题切换过渡组件（延迟创建，避免启动变慢）
        self.theme_transition = None
        
        logger.info("主窗口初始化完成")
    
    def _handle_pre_detected_account(self, detected_account):
        """处理启动时预检测的账号信息"""
        if detected_account:
            email = detected_account.get('email', '未知')
            plan = detected_account.get('membership_type', 'free').upper() 
            
            # 设置当前登录邮箱
            self.current_login_email = email
            
            logger.info(f"🎯 使用预检测账号: {email} ({plan})")
            
            # 保存/更新账号到数据库
            try:
                from core.account_storage import get_storage
                storage = get_storage()
                
                # 处理账号数据格式
                access_token = detected_account.get('access_token')
                refresh_token = detected_account.get('refresh_token')
                
                # 如果 refresh_token 为空，用 access_token 填充
                if not refresh_token and access_token:
                    refresh_token = access_token
                
                # 将模型费用转为JSON
                model_usage_json = None
                if 'model_usage' in detected_account and detected_account['model_usage']:
                    import json
                    try:
                        model_usage_json = json.dumps(detected_account['model_usage'])
                    except:
                        pass
                
                filtered_data = {
                    'email': detected_account.get('email'),
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'session_token': '',  # 空字符串
                    'user_id': detected_account.get('user_id'),
                    'membership_type': detected_account.get('membership_type'),
                    'usage_percent': detected_account.get('usage_percent'),
                    'used': detected_account.get('used'),
                    'limit': detected_account.get('limit'),
                    'days_remaining': detected_account.get('days_remaining', 0),
                    'subscription_status': detected_account.get('subscription_status'),
                    'total_cost': detected_account.get('total_cost'),
                    'total_tokens': detected_account.get('total_tokens'),
                    'unpaid_amount': detected_account.get('unpaid_amount'),
                    'model_usage_json': model_usage_json,
                    'last_used': detected_account.get('last_used'),
                    'machine_info': detected_account.get('machine_info')
                }
                
                # 保存到数据库
                account_id = storage.upsert_account(filtered_data)
                logger.info(f"✅ 预检测账号已保存到数据库 (ID: {account_id})")
                
            except Exception as e:
                logger.error(f"保存预检测账号失败: {e}")
        else:
            logger.info("无预检测账号信息")
    
    def _update_current_panel_from_predetected(self, detected_account):
        """使用预检测的账号信息更新右侧当前账号面板"""
        try:
            logger.debug("开始更新右侧面板...")
            
            if not hasattr(self, 'current_panel'):
                logger.warning("current_panel 未找到")
                return
                
            if not self.current_panel:
                logger.warning("current_panel 为空")
                return
                
            if not detected_account:
                logger.warning("detected_account 为空")
                return
            
            logger.debug(f"准备更新面板，账号: {detected_account.get('email')}")
            
            # 确保UI组件已创建
            if not hasattr(self.current_panel, 'email_label'):
                logger.warning("email_label 未找到，UI可能未初始化")
                return
            
            # 更新右侧面板显示
            self.current_panel.update_account_info(detected_account)
            
            email = detected_account.get('email', '未知')
            plan = detected_account.get('membership_type', 'free').upper()
            usage = detected_account.get('usage_percent', 0)
            
            logger.info(f"✨ 右侧面板已更新: {email} ({plan}, {usage}%)")
            
            # 强制刷新UI
            self.current_panel.update()
            self.current_panel.repaint()
            
            # 输出检测日志到面板
            self.current_panel.log(f"[启动检测] 检测成功: {email}")
            self.current_panel.log(f"[启动检测] 套餐: {plan} | 使用率: {usage}%")
            
            # 验证更新结果
            current_email_text = self.current_panel.email_label.text()
            logger.debug(f"验证更新结果 - 邮箱标签文本: {current_email_text}")
                
        except Exception as e:
            logger.error(f"更新右侧面板失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _load_config(self):
        """加载配置文件"""
        try:
            # 使用用户目录的配置文件路径
            config_path = get_config_file()
            
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            else:
                self.config = {"email": {"domain": "yourdomain.com"}}
            
            # 初始化邮箱生成器
            domain = self.config.get('email', {}).get('domain', 'yourdomain.com')
            init_email_generator(domain)
            
            # 读取UI动画配置
            self.ui_config = self.config.get('ui', {})
            self.enable_animations = self.ui_config.get('enable_animations', True)
            self.animation_speed = self.ui_config.get('animation_speed', 'normal')
            self.reduce_motion = self.ui_config.get('reduce_motion', False)
            self.card_animation_threshold = self.ui_config.get('card_animation_threshold', 50)
            
            logger.info(f"UI配置: 动画={self.enable_animations}, 速度={self.animation_speed}")
            
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            self.config = {}
            self.enable_animations = True
            self.animation_speed = 'normal'
            self.reduce_motion = False
            self.card_animation_threshold = 50
    
    def _setup_ui(self):
        """设置 UI"""
        # 创建工具栏
        self._create_toolbar()
        
        # 创建中央组件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建标签页
        from PyQt6.QtWidgets import QTabWidget
        tabs = QTabWidget()
        self.main_tabs = tabs  # 保存引用
        self.current_tab_index = 0  # 记录当前标签页索引
        
        # 账号管理标签页（左右布局）
        account_tab = self._create_account_tab()
        tabs.addTab(account_tab, "📋 账号管理")
        
        # 邮箱配置标签页
        from gui.widgets.email_test_panel import EmailTestPanel
        self.email_panel = EmailTestPanel()  # 保存引用
        tabs.addTab(self.email_panel, "📧 邮箱配置")
        
        # 手机验证配置标签页（新增）
        from gui.widgets.phone_verification_panel import PhoneVerificationPanel
        self.phone_panel = PhoneVerificationPanel()  # 保存引用
        tabs.addTab(self.phone_panel, "📱 手机验证")
        
        # 绑卡配置标签页（新增）
        try:
            from gui.widgets.payment_panel import PaymentPanel
            self.payment_panel = PaymentPanel()  # 保存引用
            self.payment_panel.config_changed.connect(self._on_payment_config_changed)
            tabs.addTab(self.payment_panel, "💳 绑卡配置")
        except Exception as e:
            logger.error(f"绑卡配置面板加载失败: {e}")
            self.payment_panel = None
        
        # 浏览器设置标签页（已删除，等待重新实现）
        # browser_tab = self._create_browser_settings_tab()
        # tabs.addTab(browser_tab, "🌐 浏览器")
        
        # 指纹设置标签页（已删除，等待重新实现）
        # fingerprint_tab = self._create_fingerprint_settings_tab()
        # tabs.addTab(fingerprint_tab, "🔐 指纹")
        
        # 系统监控标签页（已删除）
        # 功能已移除，减少依赖
        
        # ⭐ 设置标签页
        try:
            from gui.widgets.settings_panel import SettingsPanel
            settings_panel = SettingsPanel()
            settings_panel.settings_changed.connect(self._on_settings_changed)
            tabs.addTab(settings_panel, "⚙️ 设置")
        except Exception as e:
            logger.error(f"设置面板加载失败: {e}")
        
        main_layout.addWidget(tabs)
        
        # ⭐ 双重保护：事件过滤器 + 切换后检查
        tabs.installEventFilter(self)
        tabs.currentChanged.connect(self._on_tab_changed_backup)
        
        # 创建状态栏
        self.status_bar = CustomStatusBar()
        self.setStatusBar(self.status_bar)
    
    def _create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # 刷新按钮
        refresh_action = QAction("🔄 刷新账号", self)
        refresh_action.triggered.connect(self.refresh_accounts)
        toolbar.addAction(refresh_action)
        
        # 添加分隔符
        toolbar.addSeparator()
        
        # ⭐ 生成指纹浏览器按钮
        fingerprint_browser_action = QAction("🖐️ 生成指纹浏览器", self)
        fingerprint_browser_action.setToolTip("生成一个带设备指纹的浏览器实例")
        fingerprint_browser_action.triggered.connect(self._on_create_fingerprint_browser)
        toolbar.addAction(fingerprint_browser_action)
        
        # 添加分隔符
        toolbar.addSeparator()
        
        # 深色模式切换按钮
        self.theme_toggle_action = QAction(self._get_theme_icon(), self)
        self.theme_toggle_action.setToolTip("切换深色/浅色模式")
        self.theme_toggle_action.triggered.connect(self._on_theme_toggle)
        toolbar.addAction(self.theme_toggle_action)
        
        # 添加占位符
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)
        
        # ⭐ 服务器错误警告标签（默认隐藏）
        self.server_error_label = QLabel()
        self.server_error_label.setText("🚨 Cursor服务器修复中，等待恢复切勿刷新！")
        self.server_error_label.setStyleSheet("""
            QLabel {
                color: #FF6B6B;
                font-size: 13px;
                font-weight: bold;
                padding: 5px 15px;
                background-color: rgba(255, 107, 107, 0.2);
                border: 1px solid #FF6B6B;
                border-radius: 3px;
                margin-right: 10px;
            }
        """)
        self.server_error_label.setVisible(False)  # 默认隐藏
        toolbar.addWidget(self.server_error_label)
        
        # 关于按钮
        about_action = QAction("ℹ️ 关于", self)
        about_action.triggered.connect(self._on_about)
        toolbar.addAction(about_action)
    
    def _create_account_tab(self) -> QWidget:
        """创建账号管理标签页（左右布局）"""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：账号列表
        left_panel = self._create_account_panel()
        splitter.addWidget(left_panel)
        
        # 右侧：当前账号面板
        self.current_panel = CurrentAccountPanel()
        self.current_panel.register_clicked.connect(self._on_register)
        self.current_panel.account_detected.connect(self._on_account_detected)
        splitter.addWidget(self.current_panel)
        
        # 调整分割比例：智能动态计算以确保响应式布局
        # 窗口大小会在 resizeEvent 中根据实际宽度动态调整
        # - 小窗口(1100px)：左侧约620px显示2列
        # - 中窗口(1400-1800px)：左侧约950px显示3列或1220px显示4列
        # - 大窗口(1800px+)：左侧约1320px显示4列，右侧充足空间
        
        # 初始按58:42比例设置，启动时显示2列（会在首次显示时自动调整）
        splitter.setSizes([620, 480])
        
        # 设置拉伸因子（实际比例由resizeEvent动态计算）
        splitter.setStretchFactor(0, 11)  # 左侧基础拉伸因子
        splitter.setStretchFactor(1, 9)   # 右侧基础拉伸因子
        
        # 设置最小宽度约束
        left_panel.setMinimumWidth(600)  # 确保至少能显示2列
        self.current_panel.setMinimumWidth(450)  # 右侧面板最小宽度（增加以获得更好显示效果）
        
        # 保存分割器引用，用于动态调整
        self.main_splitter = splitter
        
        layout.addWidget(splitter)
        return tab
    
    def _create_account_panel(self) -> QWidget:
        """创建账号管理面板"""
        panel = QWidget()
        panel.setObjectName("AccountPanel")  # ⭐ 设置对象名用于CSS
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        
        # 工具栏
        self.toolbar = AccountToolbar()
        self.toolbar.filter_changed.connect(self._on_filter_changed)
        self.toolbar.sort_changed.connect(self._on_sort_changed)
        self.toolbar.add_clicked.connect(self._on_add_account)
        self.toolbar.import_clicked.connect(self._on_import_accounts)
        self.toolbar.export_clicked.connect(self._on_export_selected)
        # ⭐ 已移除查看加密文件功能
        self.toolbar.select_all_changed.connect(self._on_select_all)
        self.toolbar.batch_delete_clicked.connect(self._on_batch_delete)
        self.toolbar.batch_refresh_clicked.connect(self._on_batch_refresh)
        self.toolbar.batch_payment_clicked.connect(self._on_batch_payment)
        self.toolbar.search_text_changed.connect(self._on_search_changed)
        layout.addWidget(self.toolbar)
        
        # 滚动区域（优化版：启用平滑滚动和硬件加速）
        scroll_area = QScrollArea()
        scroll_area.setObjectName("AccountScrollArea")  # ⭐ 设置对象名用于CSS
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        
        # ⭐ 启用平滑滚动（像素级滚动，而非整项滚动）
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # ⭐ 优化滚动性能：使用双缓冲和自动填充背景
        scroll_area.viewport().setAutoFillBackground(False)
        
        # 账号列表容器（使用流式布局实现响应式多列）
        self.account_list_widget = QWidget()
        self.account_list_widget.setObjectName("AccountListWidget")  # ⭐ 设置对象名用于CSS
        # 间距调整为6px，减少4列时的额外占用（3×6=18px vs 3×8=24px）
        self.account_list_layout = FlowLayout(self.account_list_widget, margin=5, spacing=6)
        
        scroll_area.setWidget(self.account_list_widget)
        layout.addWidget(scroll_area)
        
        return panel
    
    def refresh_accounts(self, force_rebuild: bool = False):
        """
        刷新账号列表（防闪烁版：只在需要时重建，否则只更新数据）
        
        Args:
            force_rebuild: 是否强制重建所有卡片（筛选、排序时需要）
        """
        try:
            # ⭐ 调试：输出左侧面板实际宽度
            if hasattr(self, 'account_list_widget') and self.account_list_widget:
                actual_width = self.account_list_widget.width()
                logger.info(f"🔍 [调试] 账号列表容器实际宽度: {actual_width}px")
                # 计算理论上可显示的列数
                margin = 5 * 2  # 左右边距
                spacing = 6
                card_width = 270
                scrollbar = 12
                available = actual_width - margin - scrollbar
                theoretical_cols = int((available + spacing) / (card_width + spacing))
                logger.info(f"🔍 [调试] 可用宽度: {available}px, 理论列数: {theoretical_cols}")
            
            # ⭐ 禁用界面更新，避免中间状态显示导致卡片分离
            self.account_list_widget.setUpdatesEnabled(False)
            
            # 获取所有账号（应用筛选和排序）
            sort_by, ascending = self.current_sort
            accounts = self.storage.get_all_accounts(
                filter_type=self.current_filter.get('type'),
                filter_status=self.current_filter.get('status'),
                filter_month=self.current_filter.get('month'),
                sort_by=sort_by,
                ascending=ascending
            )
            
            # 检查是否需要重建（首次加载、筛选、排序、搜索、账号数量变化）
            need_rebuild = (
                force_rebuild or
                not self.account_cards or  # 首次加载
                len(self.account_cards) != len(accounts)  # 账号数量变化
            )
            
            # 应用搜索过滤
            if hasattr(self, 'toolbar') and self.toolbar.search_box.text():
                search_text = self.toolbar.search_box.text().lower()
                accounts = [acc for acc in accounts if search_text in acc.get('email', '').lower()]
                need_rebuild = True  # 搜索时需要重建
            
            # ⭐ 将当前登录的账号排到首位（无论是否重建都要排序）
            if self.current_login_email:
                current_account = None
                other_accounts = []
                
                for acc in accounts:
                    if acc.get('email') == self.current_login_email:
                        current_account = acc
                    else:
                        other_accounts.append(acc)
                
                # 重新组合：当前账号在最前
                if current_account:
                    old_first = accounts[0].get('email', '') if accounts else ''
                    accounts = [current_account] + other_accounts
                    logger.info(f"🔝 账号置顶: {old_first} → {self.current_login_email}")
                    
                    # ⭐ 检查是否需要重建（当前账号不在第一位时需要重建）
                    if self.account_cards and len(accounts) > 0:
                        # 直接检查排序后的第一个账号是否是当前登录账号
                        first_account_email = accounts[0].get('email')
                        
                        # 获取当前显示的第一个卡片（通过布局顺序）
                        current_first_card_email = None
                        if hasattr(self, 'account_list_layout') and self.account_list_layout.count() > 0:
                            first_widget = self.account_list_layout.itemAt(0).widget()
                            if hasattr(first_widget, 'account_data'):
                                current_first_card_email = first_widget.account_data.get('email')
                        
                        # 如果排序后的第一个账号与当前显示的第一个卡片不同，需要重建
                        if (current_first_card_email and 
                            current_first_card_email != first_account_email):
                            need_rebuild = True
                            logger.info(f"🔄 需要重新排序: {current_first_card_email} → {first_account_email}")
            
            # ⭐ 防闪烁核心逻辑：只在需要时重建，否则只更新数据
            if need_rebuild:
                # 需要重建：清空现有卡片
                logger.info("🔄 重建卡片列表")
                
                # ⭐ 冻结布局（防止中间状态触发重排）
                if hasattr(self, 'account_list_layout'):
                    self.account_list_layout.freeze()
                
                for card in self.account_cards.values():
                    card.deleteLater()
                self.account_cards.clear()
                
                # 创建新卡片
                for i, account in enumerate(accounts):
                    card = AccountCard(account, enable_animation=False)
                    
                    # 连接信号
                    card.switch_clicked.connect(self._on_switch_account)
                    card.detail_clicked.connect(lambda aid=account['id']: self._on_refresh_detail(aid))  # ⭐ 详情按钮触发详细刷新
                    card.delete_clicked.connect(self._on_delete_account)
                    card.refresh_clicked.connect(self._on_refresh_account)
                    card.selection_changed.connect(self._on_card_selection_changed)
                    
                    # ⭐ 连接拖动多选信号
                    card.drag_select_start.connect(self._on_drag_select_start)
                    card.drag_select_move.connect(self._on_drag_select_move)
                    card.drag_select_end.connect(self._on_drag_select_end)
                    
                    # 检查是否为当前登录账号并设置高亮
                    if self.current_login_email and account.get('email') == self.current_login_email:
                        card.set_current(True)
                        logger.debug(f"✨ 设置当前登录账号高亮: {account.get('email')}")
                    
                    # ⭐ 读取并应用失效状态（从数据库恢复）
                    if account.get('is_invalid') == 1:
                        card.set_invalid(True)
                        logger.debug(f"🔴 账号已从数据库恢复失效状态: {account.get('email')}")
                    
                    # 添加到流式布局
                    self.account_list_layout.addWidget(card)
                    self.account_cards[account['id']] = card
                
                # ⭐ 解冻布局（所有卡片创建完成后统一重排）
                if hasattr(self, 'account_list_layout'):
                    self.account_list_layout.unfreeze()
                    logger.debug("✅ 布局已解冻，准备统一重排")
            else:
                # 不需要重建：只更新现有卡片的数据（防闪烁，批量更新）
                logger.info("🔄 只更新卡片数据（批量静默更新）")
                
                # ⭐ 冻结布局（防止中途触发重排）
                if hasattr(self, 'account_list_layout'):
                    self.account_list_layout.freeze()
                
                for account in accounts:
                    account_id = account['id']
                    if account_id in self.account_cards:
                        card = self.account_cards[account_id]
                        # ⭐ 使用静默更新（不触发重排）
                        card.update_account_data_silent(account)
                        # ⭐ 使用静默设置当前状态（不触发重排）
                        is_current = (account.get('email') == self.current_login_email)
                        card.set_current_silent(is_current)
                        if is_current:
                            logger.debug(f"✨ 更新当前登录账号高亮: {account.get('email')}")
                
                # ⭐ 解冻布局并标记为脏（所有卡片更新完后统一重排）
                if hasattr(self, 'account_list_layout'):
                    self.account_list_layout.unfreeze()
            
            # ⭐ 重新启用界面更新（一次性重绘）
            self.account_list_widget.setUpdatesEnabled(True)
            self.account_list_widget.update()
            
            # 启动瀑布流动画（完全禁用，避免任何闪烁）
            # if enable_card_animation and cards_to_animate:
            #     self._animate_cards_in(cards_to_animate)
            
            # 更新工具栏和状态栏
            if hasattr(self, 'toolbar'):
                # 计算可见账号数
                visible_count = sum(1 for card in self.account_cards.values() if card.isVisible())
                self.toolbar.update_counts(0, len(self.account_cards), visible_count)
            
            self.status_bar.update_account_count(len(accounts))
            self.status_bar.update_last_refresh()
            
            logger.info(f"刷新账号列表: {len(accounts)} 个账号")
            
        except Exception as e:
            logger.error(f"刷新账号列表失败: {e}")
            # 确保即使出错也要重新启用界面更新
            self.account_list_widget.setUpdatesEnabled(True)
    
    def _on_switch_account(self, account_id: int):
        """切换账号"""
        try:
            account = self.storage.get_account_by_id(account_id)
            if not account:
                return
            
            # 验证 Cursor 安装
            if not self.switcher.validate_cursor_installation():
                QMessageBox.warning(self, "未找到 Cursor", "未检测到 Cursor 配置文件\n\n请确保 Cursor 已正确安装")
                return
            
            # 检查 AccessToken
            if not account.get('access_token'):
                reply = QMessageBox.question(
                    self,
                    "缺少 AccessToken",
                    f"账号 {account['email']} 没有 AccessToken\n\n"
                    "是否尝试从当前 Cursor 配置中读取？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # 尝试从配置读取
                    current_account = self.switcher.get_current_account()
                    if current_account and current_account.get('access_token'):
                        account['access_token'] = current_account['access_token']
                        logger.info("已从当前配置读取 AccessToken")
                    else:
                        QMessageBox.warning(
                            self, "失败",
                            "无法从当前配置读取 AccessToken\n\n"
                            "请先通过「检测当前账号」功能获取 Token"
                        )
                        return
                else:
                    return
            
            # ⭐ 已移除 Cursor 运行检查弹窗，直接进入切换流程
            # 用户可在切换对话框中选择是否自动关闭 Cursor
            
            # 打开切换确认对话框
            dialog = SwitchAccountDialog(account, self)
            
            # 连接确认信号
            dialog.confirmed.connect(lambda options: self._execute_switch(account_id, account, options))
            
            # 显示对话框
            dialog.exec()
                
        except Exception as e:
            logger.error(f"切换账号失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"切换失败:\n{e}")
    
    def _execute_switch(self, account_id: int, account: Dict[str, Any], options: Dict[str, Any]):
        """执行账号切换（快速版，3秒完成）"""
        try:
            import time
            start_time = time.time()
            
            logger.info("="*60)
            logger.info(f"开始切换账号: {account['email']}")
            logger.info(f"机器码模式: {options.get('machine_id_mode', 'generate_new')}")
            logger.info(f"自动关闭: {options.get('auto_kill', False)}")
            logger.info(f"自动重启: {options.get('auto_restart', False)}")
            logger.info("="*60)
            
            auto_kill = options.get('auto_kill', False)
            auto_restart = options.get('auto_restart', False)
            
            # 步骤 1：关闭 Cursor（如果勾选且正在运行）
            if auto_kill:
                if self.switcher.check_cursor_running():
                    self.status_bar.show_message("【1/5】关闭 Cursor...", 0)
                    
                    close_success = self.switcher.close_cursor_gracefully()
                    
                    if not close_success:
                        reply = QMessageBox.warning(
                            self,
                            "关闭失败",
                            "无法关闭 Cursor 进程\n\n"
                            "请手动关闭 Cursor 后点击「重试」\n"
                            "或点击「取消」放弃切换",
                            QMessageBox.StandardButton.Retry | QMessageBox.StandardButton.Cancel
                        )
                        
                        if reply == QMessageBox.StandardButton.Cancel:
                            logger.info("用户取消切换")
                            self.status_bar.show_message("切换已取消", 3000)
                            return
                        elif reply == QMessageBox.StandardButton.Retry:
                            if self.switcher.check_cursor_running():
                                QMessageBox.critical(self, "错误", "Cursor 仍在运行，切换取消")
                                self.status_bar.show_message("切换失败", 3000)
                                return
                else:
                    logger.info("【1/5】Cursor 未运行，跳过关闭步骤")
            
            # 步骤 2：写入账号配置
            logger.info("【2/5】正在写入账号配置...")
            self.status_bar.show_message("【2/5】写入配置...", 0)
            
            success = self.switcher.switch_account(
                account,
                machine_id_mode=options.get('machine_id_mode', 'generate_new'),
                reset_cursor_config=options.get('reset_cursor_config', False)
            )
            
            if not success:
                logger.error("写入配置失败")
                QMessageBox.critical(
                    self,
                    "切换失败",
                    "写入配置文件失败\n\n"
                    "可能原因:\n"
                    "• 配置文件被锁定\n"
                    "• 磁盘空间不足\n"
                    "• 权限不足\n\n"
                    "请查看日志了解详情"
                )
                self.status_bar.show_message("切换失败", 3000)
                return
            
            logger.info("  ✅ 配置写入成功")
            
            # 步骤 3：更新最后使用时间和当前登录邮箱
            logger.info("【3/5】更新账号使用记录...")
            self.storage.update_last_used(account_id)
            
            # 更新当前登录邮箱
            self.current_login_email = account.get('email')
            logger.info(f"  ✅ 记录已更新，当前登录: {self.current_login_email}")
            
            # 步骤 4：重启 Cursor（如果勾选）
            if auto_restart:
                logger.info("【4/5】正在启动 Cursor...")
                self.status_bar.show_message("【4/5】启动 Cursor...", 0)
                
                time.sleep(0.5)  # 短暂等待配置写入
                
                restart_success = self.switcher.start_cursor()
                
                if restart_success:
                    logger.info("  ✅ Cursor 已启动")
                else:
                    logger.warning("  ⚠️  自动启动失败")
            else:
                logger.info("【4/5】跳过自动重启")
            
            # 步骤 5：完成
            elapsed = time.time() - start_time
            logger.info("【5/5】✅ 切换完成！")
            logger.info(f"总耗时: {elapsed:.1f}秒")
            logger.info("="*60)
            
            # ⭐ 更新右侧当前账号面板并刷新最新数据
            if hasattr(self, 'current_panel') and self.current_panel:
                # 先用数据库数据更新（立即显示基本信息）
                self.current_panel.update_account_info(account)
                
                # 在右侧面板日志输出切换成功
                plan = account.get('membership_type', 'free').upper()
                usage = account.get('usage_percent', 0)
                days = account.get('days_remaining', 0)
                
                self.current_panel.log("="*50)
                self.current_panel.log(f"✅ 账号切换成功")
                self.current_panel.log(f"📧 新账号: {account['email']}")
                self.current_panel.log(f"🎫 套餐: {plan} | 使用率: {usage}% | 剩余: {days}天")
                self.current_panel.log(f"⏱️ 切换耗时: {elapsed:.1f}秒")
                if auto_restart and restart_success:
                    self.current_panel.log("✅ Cursor 已自动重启")
                elif auto_restart:
                    self.current_panel.log("⚠️ 请手动启动 Cursor")
                else:
                    self.current_panel.log("📌 请手动重启 Cursor 以应用更改")
                self.current_panel.log("="*50)
                
                # ⭐ 立即刷新账号获取最新使用情况
                self.current_panel.log("🔄 正在获取最新使用情况...")
                
                # 延迟1秒后刷新（等待Cursor重启）
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(1000, lambda: self._refresh_switched_account(account_id))
            
            # 刷新账号列表以更新高亮状态（不需要重建，只更新数据）
            self.refresh_accounts(force_rebuild=False)
            
            # 显示成功消息
            # ⭐ 不弹窗，只显示状态栏提示
            if auto_restart:
                if restart_success:
                    self.status_bar.show_message(
                        f"✅ 切换成功: {account['email']} | Cursor已自动重启 ({elapsed:.1f}秒)", 
                        5000
                    )
                else:
                    self.status_bar.show_message(
                        f"✅ 切换成功: {account['email']} | 请手动启动Cursor ({elapsed:.1f}秒)", 
                        5000
                    )
            else:
                self.status_bar.show_message(
                    f"✅ 切换成功: {account['email']} | 请手动重启Cursor ({elapsed:.1f}秒)", 
                    5000
                )
                
        except Exception as e:
            logger.error(f"执行切换失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"切换失败:\n{e}")
            self.status_bar.show_message("切换失败", 3000)
    
    def _refresh_switched_account(self, account_id: int):
        """刷新切换后的账号（获取最新使用情况）"""
        try:
            logger.info(f"刷新切换后的账号: ID={account_id}")
            
            # 调用刷新方法
            self._on_refresh_account(account_id)
            
        except Exception as e:
            logger.error(f"刷新切换账号失败: {e}")
            if hasattr(self, 'current_panel') and self.current_panel:
                self.current_panel.log(f"⚠️ 刷新使用情况失败: {str(e)}")
    
    def _on_show_detail(self, account_id: int):
        """显示详情"""
        try:
            account = self.storage.get_account_by_id(account_id)
            if account:
                dialog = AccountDetailDialog(account, self)
                dialog.exec()
        except Exception as e:
            logger.error(f"显示详情失败: {e}")
    
    def _on_delete_account(self, account_id: int):
        """删除账号"""
        try:
            account = self.storage.get_account_by_id(account_id)
            if not account:
                return
            
            reply = QMessageBox.question(
                self, "确认删除",
                f"删除账号: {account['email']}\n\n此操作不可恢复！",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # ⭐ 修复：使用partial或直接定义函数，避免lambda立即执行
                card = self.account_cards.get(account_id)
                if card:
                    # 使用闭包保存account_id
                    def on_fade_complete():
                        self._delete_confirmed(account_id)
                    card.fade_out(on_fade_complete)
                else:
                    self._delete_confirmed(account_id)
                    
        except Exception as e:
            logger.error(f"删除账号失败: {e}")
    
    def _delete_confirmed(self, account_id: int):
        """确认删除"""
        if self.storage.delete_account(account_id):
            card = self.account_cards.pop(account_id, None)
            if card:
                card.deleteLater()
            self.status_bar.update_account_count(len(self.account_cards))
            self.status_bar.show_message("✅ 账号已删除", 3000)
    
    def _on_refresh_account(self, account_id: int):
        """刷新账号（单个刷新，详细模式）"""
        self._on_refresh_account_with_callback(account_id, None, is_batch=False)
    
    def _on_refresh_detail(self, account_id: int):
        """查看账号详情（先打开对话框，然后刷新）"""
        logger.info(f"📊 用户点击查看详情: account_id={account_id}")
        
        try:
            # ⭐ 先获取当前账号数据
            account = self.storage.get_account_by_id(account_id)
            if not account:
                return
            
            # ⭐ 立即打开详情对话框（显示当前数据）
            from gui.dialogs.account_detail_dialog import AccountDetailDialog
            dialog = AccountDetailDialog(account, self, auto_refresh=True)
            
            # ⭐ 非阻塞显示对话框
            dialog.show()
            
            # ⭐ 启动后台刷新，刷新完成后更新对话框
            def refresh_callback(aid, success):
                if success:
                    # 刷新成功，重新获取数据并更新对话框
                    updated_account = self.storage.get_account_by_id(aid)
                    if updated_account and dialog.isVisible():
                        dialog.update_data(updated_account)
                        logger.info(f"✅ 详情对话框已更新: {updated_account.get('email')}")
                else:
                    # 刷新失败，隐藏刷新提示
                    if dialog.isVisible():
                        dialog.hide_refreshing_hint()
                        logger.warning(f"❌ 详情刷新失败: account_id={aid}")
            
            # 启动刷新
            self._on_refresh_account_with_callback(account_id, refresh_callback, is_batch=False)
            
        except Exception as e:
            logger.error(f"打开详情对话框失败: {e}")
    
    def _on_refresh_account_with_callback(self, account_id: int, callback=None, is_batch: bool = False):
        """
        刷新账号（带回调）
        
        Args:
            account_id: 账号ID
            callback: 完成回调函数
            is_batch: 是否为批量刷新（批量时使用快速模式）
        """
        try:
            account = self.storage.get_account_by_id(account_id)
            if not account:
                if callback:
                    callback(account_id, False)
                return
            
            email = account.get('email', 'unknown')
            
            # ⭐ 日志：开始刷新（同时输出到界面日志）
            logger.info(f"🔄 开始刷新账号: {email}")
            if not callback:  # 只有非批量刷新才输出到面板
                self.current_panel.log(f"🔄 开始刷新: {email}")
            if not callback:  # 只有非批量刷新才更新状态栏
                self.status_bar.show_message(f"🔄 刷新中: {email}", 0)
            
            # 获取 AccessToken
            access_token = account.get('access_token')
            
            if not access_token:
                logger.warning(f"❌ 账号 {email} 缺少 AccessToken")
                if not callback:
                    self.current_panel.log(f"❌ {email} 缺少 AccessToken")
                    self.status_bar.show_message(f"❌ 无法刷新: {email} (缺少Token)", 3000)
                # ⭐ 调用回调（批量刷新需要）
                if callback:
                    callback(account_id, False)
                return
            
            # ⚠️ 从 AccessToken 临时构造格式用于 API 调用
            # 不使用数据库中的 session_token（如果有的话也忽略）
            import base64, json
            try:
                parts = access_token.split('.')
                if len(parts) >= 2:
                    payload = parts[1]
                    padding = len(payload) % 4
                    if padding:
                        payload += '=' * (4 - padding)
                    decoded = base64.urlsafe_b64decode(payload)
                    token_data = json.loads(decoded)
                    user_id = token_data.get('sub', '').replace('auth0|', '')
                    
                    # 构造临时格式（仅用于 API 调用）
                    temp_session_format = f"{user_id}::{access_token}"
                else:
                    temp_session_format = None
            except:
                temp_session_format = None
            
            card = self.account_cards.get(account_id)
            if card:
                card.set_loading(True)
            
            # ⭐ 日志：正在调用 API
            logger.info(f"  ↳ 调用 Cursor API 获取最新信息...")
            if not callback:  # 只有非批量刷新才输出到面板
                self.current_panel.log(f"  ↳ 调用 API...")
            
            # 保存回调函数
            if callback:
                self.refresh_callbacks[account_id] = callback
            
            # 使用线程管理器执行刷新任务
            def refresh_task():
                """刷新任务函数（支持增量刷新）"""
                try:
                    from core.cursor_api import CursorServerError
                    api = get_api_client()
                    
                    # 优先使用 SessionToken 调用 API
                    token = temp_session_format or access_token
                    
                    if not token:
                        logger.error(f"没有可用的 Token (account_id={account_id})")
                        return {}
                    
                    # ⭐ 获取数据库中的增量刷新信息
                    account_data = self.storage.get_account_by_id(account_id)
                    last_refresh_time = account_data.get('last_refresh_time') if account_data else None
                    accumulated_cost = account_data.get('accumulated_cost', 0) if account_data else 0
                    
                    # ⭐ 调用API获取账号详情（使用增量刷新）
                    if last_refresh_time:
                        logger.info(f"账号 {account_id} 使用增量刷新（上次刷新: {last_refresh_time}，累计金额: ${accumulated_cost:.2f}）")
                    else:
                        logger.info(f"账号 {account_id} 首次刷新，获取完整记录")
                    
                    # 调用增量刷新API
                    details = api.get_account_details(
                        token, 
                        detailed=True,
                        last_refresh_time=last_refresh_time,
                        accumulated_cost=accumulated_cost
                    )
                    
                    if details:
                        logger.debug(f"API 返回成功 (account_id={account_id})")
                        return details
                    else:
                        logger.warning(f"API 返回空数据 (account_id={account_id})")
                        return {}
                        
                except CursorServerError as e:
                    # ⭐ Cursor服务器500错误 - 停止批量刷新
                    logger.error(f"🚨 Cursor服务器错误: {e}")
                    # 显示服务器错误提示
                    self._show_server_error_warning()
                    # 停止批量刷新
                    if hasattr(self, 'batch_refresh_queue'):
                        self.batch_refresh_queue.clear()
                    return {'_server_error': True}
                except Exception as e:
                    logger.error(f"刷新任务失败 (account_id={account_id}): {e}")
                    raise
            
            # 提交任务到线程池
            task_id = f"refresh_account_{account_id}_{int(time.time())}"
            logger.info(f"📤 提交刷新任务到线程池: task_id={task_id}, is_batch={is_batch}")
            
            # ⭐ 定义回调包装器，添加日志
            def task_callback(tid, result):
                logger.info(f"📥 线程池回调触发: task_id={tid}, account_id={account_id}, has_result={bool(result)}")
                # 直接调用，但确保回调在主线程执行
                self._on_refresh_finished_wrapper(account_id, result or {})
            
            self.thread_manager.submit_task(
                task_id=task_id,
                func=refresh_task,
                callback=task_callback
            )
            logger.info(f"✅ 任务已提交: {task_id}")
            
        except Exception as e:
            logger.error(f"❌ 刷新账号失败: {e}")
            if not callback:
                self.current_panel.log(f"❌ 刷新失败: {str(e)[:50]}")
                self.status_bar.show_message(f"❌ 刷新失败", 3000)
            # ⭐ 调用回调（批量刷新需要）
            if callback:
                callback(account_id, False)
    
    def _on_refresh_finished_wrapper(self, account_id: int, result: dict):
        """刷新完成的包装器（确保在主线程执行）"""
        # 发射信号，Qt会自动确保在主线程中处理
        self.refresh_finished_signal.emit(account_id, result)
    
    def _on_refresh_finished(self, account_id: int, result: dict):
        """刷新完成（优化版：增强错误处理和线程清理）"""
        logger.info(f"=" * 50)
        logger.info(f"🎯 _on_refresh_finished 被调用: account_id={account_id}, has_result={bool(result)}")
        logger.info(f"=" * 50)
        try:
            # ⭐ 不再需要清理线程（现在使用线程池）
            # 线程池会自动管理线程生命周期
            
            card = self.account_cards.get(account_id)
            if card:
                try:
                    card.set_loading(False)
                except:
                    pass
            
            # 获取账号信息用于日志
            account = self.storage.get_account_by_id(account_id)
            email = account.get('email', 'unknown') if account else 'unknown'
            
            # 检查是否为批量刷新
            has_callback = account_id in self.refresh_callbacks
            
            # ⭐ 检查是否是服务器错误
            if result and result.get('_server_error'):
                logger.error(f"❌ 服务器错误，停止刷新: {email}")
                # 调用回调（通知批量刷新停止）
                callback = self.refresh_callbacks.pop(account_id, None)
                if callback:
                    callback(account_id, False)
                return
            
            if result:
                # ⭐ 日志：刷新成功
                plan = result.get('membership_type', 'free').upper()
                usage = result.get('usage_percent', 0)
                days = result.get('days_remaining', 0)
                
                logger.info(f"✅ 刷新成功: {email}")
                logger.info(f"  ↳ 套餐: {plan} | 使用率: {usage}% | 剩余: {days}天")
                
                # ⭐ 输出到界面日志（仅非批量刷新）
                if not has_callback:
                    try:
                        if hasattr(self, 'current_panel') and self.current_panel:
                            self.current_panel.log(f"✅ 刷新成功: {email}")
                            self.current_panel.log(f"  ↳ {plan} | {usage}% | {days}天")
                    except Exception as e:
                        logger.debug(f"输出日志失败: {e}")
                
                # 更新数据库
                try:
                    self.storage.update_account_status(account_id, result)
                except Exception as e:
                    logger.error(f"更新数据库失败: {e}")
                
                # ⭐ 清除失效标记（刷新成功后）
                try:
                    if hasattr(self, 'account_cards') and account_id in self.account_cards:
                        card = self.account_cards[account_id]
                        card.set_invalid(False)
                except Exception as e:
                    logger.debug(f"清除失效标记失败: {e}")
                
                # ⭐ 持久化保存有效状态到数据库
                try:
                    self.storage.update_account(account_id, {'is_invalid': 0})
                    logger.debug(f"💾 有效状态已保存到数据库: {email}")
                except Exception as e:
                    logger.error(f"保存有效状态失败: {e}")
                
                # ⭐ 关键改动：收集更新而非立即更新
                account = self.storage.get_account_by_id(account_id)
                if account:
                    self._collect_card_update(account_id, account)
                
                # ⭐ 如果刷新的是当前登录账号，同步更新右侧面板
                if email == self.current_login_email and account:
                    def update_panel(acc=account):
                        try:
                            self._safe_update_current_panel(acc)
                        except:
                            pass
                    try:
                        QTimer.singleShot(150, update_panel)
                    except:
                        pass
                
                # 更新状态栏（仅非批量刷新）
                if not has_callback:
                    try:
                        if hasattr(self, 'status_bar') and self.status_bar:
                            self.status_bar.show_message(f"✅ {email} 刷新成功 ({plan}, {usage}%)", 3000)
                    except Exception as e:
                        logger.debug(f"更新状态栏失败: {e}")
            else:
                # ⭐ 日志：刷新失败
                logger.warning(f"❌ 刷新失败: {email} - API 返回空数据")
                
                # ⭐ 标记账号卡片为失效（显示大红×）
                try:
                    if hasattr(self, 'account_cards') and account_id in self.account_cards:
                        card = self.account_cards[account_id]
                        card.set_invalid(True)
                        logger.info(f"🔴 账号卡片已标记为失效: {email}")
                except Exception as e:
                    logger.error(f"标记失效卡片失败: {e}")
                
                # ⭐ 持久化保存失效状态到数据库
                try:
                    self.storage.update_account(account_id, {'is_invalid': 1})
                    logger.info(f"💾 失效状态已保存到数据库: {email}")
                except Exception as e:
                    logger.error(f"保存失效状态失败: {e}")
                
                if not has_callback:
                    try:
                        if hasattr(self, 'current_panel') and self.current_panel:
                            self.current_panel.log(f"❌ 刷新失败: {email} (可能已被删除)")
                        if hasattr(self, 'status_bar') and self.status_bar:
                            self.status_bar.show_message(f"❌ {email} 刷新失败 (可能已被删除)", 5000)
                    except Exception as e:
                        logger.debug(f"输出失败信息失败: {e}")
            
            # ⭐ 调用回调函数（用于批量刷新）
            callback = self.refresh_callbacks.pop(account_id, None)
            if callback:
                try:
                    success = bool(result)  # 有结果就是成功
                    logger.info(f"🔔 准备调用批量刷新回调: account_id={account_id}, success={success}")
                    callback(account_id, success)
                    logger.info(f"✅ 批量刷新回调已执行: account_id={account_id}")
                except Exception as e:
                    logger.error(f"回调函数执行失败: {e}", exc_info=True)
            else:
                # 非批量刷新
                logger.debug(f"非批量刷新完成: account_id={account_id}")
                
        except Exception as e:
            logger.error(f"❌ 处理刷新结果失败: {e}", exc_info=True)
            try:
                if hasattr(self, 'status_bar') and self.status_bar:
                    self.status_bar.show_message(f"❌ 刷新失败", 3000)
            except:
                pass
            
            # 即使出错也要调用回调
            try:
                callback = self.refresh_callbacks.pop(account_id, None)
                if callback:
                    callback(account_id, False)
            except Exception as e2:
                logger.error(f"调用回调失败: {e2}")
    
    def _create_browser_settings_tab(self) -> QWidget:
        """创建浏览器设置标签页（已删除，等待重新实现）"""
        placeholder = QWidget()
        layout = QVBoxLayout(placeholder)
        label = QLabel("浏览器设置已删除，等待重新实现")
        layout.addWidget(label)
        return placeholder
    
    def _create_fingerprint_settings_tab(self) -> QWidget:
        """创建指纹设置标签页（已删除，等待重新实现）"""
        placeholder = QWidget()
        layout = QVBoxLayout(placeholder)
        label = QLabel("指纹设置已删除，等待重新实现")
        layout.addWidget(label)
        return placeholder
    
    
    def _on_settings_changed(self):
        """设置改变回调"""
        try:
            logger.info("用户设置已更新")
            
            # 重新加载配置
            self._load_config()
            
            # 显示提示
            self.status_bar.show_message("✅ 设置已保存", 3000)
            
        except Exception as e:
            logger.error(f"处理设置改变失败: {e}")
    
    def _on_settings(self):
        """打开设置（已移除弹窗，设置在标签页中）"""
        pass
    
    def _on_payment_config(self):
        """打开绑卡配置对话框"""
        try:
            dialog = PaymentConfigDialog(self)
            
            # 连接配置变更信号
            dialog.config_changed.connect(self._on_payment_config_changed)
            
            # 显示对话框
            dialog.exec()
            
        except Exception as e:
            logger.error(f"打开绑卡配置失败: {e}")
            QMessageBox.critical(
                self,
                "错误",
                f"无法打开绑卡配置：\n{e}"
            )
    
    def _on_payment_config_changed(self):
        """绑卡配置变更回调"""
        try:
            logger.info("绑卡配置已更新")
            
            # 重新加载配置
            self._load_config()
            
            # 显示提示
            self.status_bar.show_message("✅ 绑卡配置已保存", 3000)
            
        except Exception as e:
            logger.error(f"处理绑卡配置变更失败: {e}")
    
    def eventFilter(self, obj, event):
        """事件过滤器，拦截标签页切换"""
        try:
            # 检查是否是 QTabWidget 且是鼠标释放事件
            from PyQt6.QtCore import QEvent
            from PyQt6.QtWidgets import QTabWidget
            
            if isinstance(obj, QTabWidget) and event.type() == QEvent.Type.MouseButtonRelease:
                # 获取点击的标签索引
                tab_bar = obj.tabBar()
                click_pos = event.pos()
                clicked_index = tab_bar.tabAt(click_pos)
                
                # 如果没有点击到标签或点击当前标签，不处理
                if clicked_index == -1 or clicked_index == self.current_tab_index:
                    return super().eventFilter(obj, event)
                
                # 检查所有配置面板是否有未保存的修改
                current_widget = self.main_tabs.widget(self.current_tab_index)
                
                # 检查当前面板是否有 check_unsaved_changes 方法
                if hasattr(current_widget, 'check_unsaved_changes'):
                    if not current_widget.check_unsaved_changes():
                        # 用户选择取消，阻止切换
                        logger.info(f"❌ 用户取消切换，保持在当前页面")
                        return True  # 拦截事件，阻止切换
                
                # 允许切换，更新索引
                self.current_tab_index = clicked_index
                
        except Exception as e:
            logger.error(f"事件过滤器处理失败: {e}")
        
        return super().eventFilter(obj, event)
    
    def _on_tab_changed_backup(self, index):
        """标签页切换后的备用检查（双重保护）"""
        try:
            # 如果索引不同，说明事件过滤器没有成功拦截
            if index != self.current_tab_index:
                # 再次检查是否有未保存的修改
                old_widget = self.main_tabs.widget(self.current_tab_index)
                
                # 检查是否有 check_unsaved_changes 方法和未保存标记
                if hasattr(old_widget, 'has_unsaved_changes') and old_widget.has_unsaved_changes:
                    # 有未保存修改，强制切换回去
                    logger.warning("⚠️ 检测到未保存修改，强制切换回原页面")
                    self.main_tabs.blockSignals(True)
                    self.main_tabs.setCurrentIndex(self.current_tab_index)
                    self.main_tabs.blockSignals(False)
                    
                    # 显示提示
                    if hasattr(old_widget, 'check_unsaved_changes'):
                        old_widget.check_unsaved_changes()
                    return
                
                # 正常切换，更新索引
                self.current_tab_index = index
        
        except Exception as e:
            logger.error(f"备用检查失败: {e}")
    
    def _on_register(self):
        """一键注册"""
        try:
            from gui.dialogs import AutoRegisterDialog
            
            self.current_panel.log("打开自动注册对话框...")
            
            dialog = AutoRegisterDialog(self)
            dialog.registration_completed.connect(self._on_registration_completed)
            
            result = dialog.exec()
            
            if result:
                self.current_panel.log("注册完成，刷新账号列表...")
                self.refresh_accounts(force_rebuild=True)
            
        except Exception as e:
            logger.error(f"一键注册功能错误: {e}")
            self.current_panel.log(f"错误: {e}")
    
    def _on_registration_completed(self, success_count: int):
        """
        注册完成回调
        """
        logger.info(f"✅ 收到注册完成信号，成功 {success_count} 个账号")
        self.current_panel.log(f"✅ 成功注册 {success_count} 个账号，正在刷新列表...")
        
        # 刷新账号列表
        self.refresh_accounts(force_rebuild=True)
        
        # 显示提示
        self.status_bar.show_message(f"✅ 成功注册 {success_count} 个账号", 5000)
    
    def _show_server_error_warning(self):
        """显示Cursor服务器错误警告"""
        try:
            # 显示工具栏中的警告标签
            if hasattr(self, 'server_error_label'):
                self.server_error_label.setVisible(True)
                logger.info("🚨 已显示服务器错误警告")
                
            # 关闭批量刷新对话框
            if hasattr(self, 'batch_refresh_dialog') and self.batch_refresh_dialog:
                try:
                    self.batch_refresh_dialog.update_progress(
                        self.batch_refresh_current,
                        "❌ Cursor服务器错误，已停止刷新"
                    )
                    # ⭐ 播放掉落动画后关闭
                    QTimer.singleShot(2000, self.batch_refresh_dialog.play_closing_animation)
                except:
                    pass
            
            # 显示消息框
            QTimer.singleShot(100, lambda: QMessageBox.warning(
                self,
                "🚨 Cursor服务器错误",
                "检测到 Cursor API 返回500错误\n\n"
                "这是Cursor服务器的问题，不是代码问题。\n\n"
                "建议操作：\n"
                "1. 等待5-10分钟\n"
                "2. 或重新登录Cursor编辑器\n"
                "3. 然后重启程序\n\n"
                "批量刷新已自动停止。"
            ))
        except Exception as e:
            logger.error(f"显示服务器错误警告失败: {e}")
    
    def _on_create_fingerprint_browser(self):
        """生成指纹浏览器"""
        try:
            from core.browser_manager import BrowserManager
            from core.machine_id_generator import generate_machine_id
            import tempfile
            
            self.current_panel.log("=" * 60)
            self.current_panel.log("🖐️ 开始生成指纹浏览器...")
            self.current_panel.log("=" * 60)
            
            # 1. 生成设备指纹
            self.current_panel.log("\n步骤1: 生成设备指纹...")
            machine_info = generate_machine_id()
            
            self.current_panel.log(f"✅ 设备指纹已生成:")
            self.current_panel.log(f"  machineId: {machine_info.get('telemetry.machineId', 'N/A')[:50]}...")
            self.current_panel.log(f"  macMachineId: {machine_info.get('telemetry.macMachineId', 'N/A')}")
            self.current_panel.log(f"  devDeviceId: {machine_info.get('telemetry.devDeviceId', 'N/A')}")
            self.current_panel.log(f"  sqmId: {machine_info.get('telemetry.sqmId', 'N/A')}")
            self.current_panel.log(f"  machineGuid: {machine_info.get('system.machineGuid', 'N/A')}")
            
            # 2. 创建独立的用户数据目录
            self.current_panel.log("\n步骤2: 创建浏览器实例...")
            temp_dir = tempfile.mkdtemp(prefix="fingerprint_browser_")
            self.current_panel.log(f"  用户数据目录: {temp_dir}")
            
            # 3. 初始化浏览器
            browser_manager = BrowserManager()
            browser = browser_manager.init_browser(
                incognito=False,  # 不使用无痕模式，保留指纹
                headless=False,   # 可见模式
                user_data_dir=temp_dir
            )
            
            self.current_panel.log("✅ 浏览器实例已创建")
            
            # 4. 访问测试页面
            self.current_panel.log("\n步骤3: 访问 Cursor 主页...")
            tab = browser.latest_tab
            tab.get("https://www.cursor.com")
            
            self.current_panel.log("✅ 已访问 Cursor 主页")
            self.current_panel.log(f"  当前URL: {tab.url}")
            
            # 5. 显示完成信息
            self.current_panel.log("\n" + "=" * 60)
            self.current_panel.log("✅ 指纹浏览器生成完成！")
            self.current_panel.log("=" * 60)
            self.current_panel.log("\n💡 提示:")
            self.current_panel.log("  • 浏览器已打开并保持运行")
            self.current_panel.log("  • 已生成独立的设备指纹")
            self.current_panel.log("  • 可以手动进行任何操作")
            self.current_panel.log("  • 关闭浏览器后数据不会保留")
            self.current_panel.log(f"  • 用户数据目录: {temp_dir}")
            
            # Toast通知
            from gui.widgets.toast_notification import show_toast
            show_toast(self, "✅ 指纹浏览器已生成！", duration=3000)
            
        except Exception as e:
            logger.error(f"生成指纹浏览器失败: {e}", exc_info=True)
            self.current_panel.log(f"\n❌ 生成失败: {e}")
            QMessageBox.critical(
                self,
                "生成失败",
                f"生成指纹浏览器时出错：\n\n{e}\n\n请查看日志获取详细信息。"
            )
    
    def _on_about(self):
        """关于"""
        QMessageBox.about(
            self,
            "关于",
            "🎯 Zzx Cursor Auto Manager v3.2\n\n"
            "功能:\n"
            "✅ 账号管理\n"
            "✅ 增量刷新（提速9倍）⚡\n"
            "✅ 当前账号检测\n"
            "✅ 霸气批量刷新 🦆🔫\n"
            "✅ 一键切换\n\n"
            "© 2025 Zzx Dev"
        )
    
    def _start_auto_detection(self):
        """启动自动检测"""
        # 从配置读取检测间隔
        detect_interval = self.config.get('cursor', {}).get('detect_interval', 30)
        auto_detect = self.config.get('cursor', {}).get('auto_detect', True)
        
        if not auto_detect:
            logger.info("自动检测已禁用")
            return
        
        # 首次检测（延迟 2 秒启动）
        QTimer.singleShot(2000, self._auto_detect_account)
        
        # 启动定时器
        self.auto_detect_timer.start(detect_interval * 1000)  # 转换为毫秒
        logger.info(f"自动检测已启动，间隔: {detect_interval} 秒")
    
    def _auto_detect_account(self):
        """自动检测当前账号（后台静默检测）"""
        try:
            # 检查是否已经在检测中
            if (hasattr(self.current_panel, 'detection_thread') and 
                self.current_panel.detection_thread and 
                self.current_panel.detection_thread.isRunning()):
                logger.debug("检测正在进行中，跳过本次自动检测")
                return
            
            # 触发静默检测（不输出日志，不禁用按钮）
            self.current_panel.start_detection(silent=True)
            
        except Exception as e:
            logger.error(f"自动检测失败: {e}")
    
    def _on_account_detected(self, account_data: dict):
        """账号检测完成回调"""
        detected_email = account_data.get('email', '未知')
        logger.info(f"检测到账号: {detected_email}")
        
        # 更新当前登录邮箱
        self.current_login_email = detected_email
        
        try:
            # ⚠️ 过滤掉构造的 session_token，设为空字符串
            access_token = account_data.get('access_token')
            refresh_token = account_data.get('refresh_token')
            
            # ⭐ 如果 refresh_token 为空，用 access_token 填充（通常相同）
            if not refresh_token and access_token:
                refresh_token = access_token
            
            # ⭐ 将模型费用转为JSON
            model_usage_json = None
            if 'model_usage' in account_data and account_data['model_usage']:
                import json
                try:
                    model_usage_json = json.dumps(account_data['model_usage'])
                except:
                    pass
            
            filtered_data = {
                'email': account_data.get('email'),
                'access_token': access_token,
                'refresh_token': refresh_token,  # ⭐ 确保有值
                'session_token': '',  # ⭐ 空字符串（导出时转为 null）
                'user_id': account_data.get('user_id'),
                'membership_type': account_data.get('membership_type'),
                'usage_percent': account_data.get('usage_percent'),
                'used': account_data.get('used'),
                'limit': account_data.get('limit'),
                'days_remaining': account_data.get('days_remaining', 0),
                'subscription_status': account_data.get('subscription_status'),  # ⭐ 订阅状态
                'total_cost': account_data.get('total_cost'),  # ⭐ 真实费用
                'total_tokens': account_data.get('total_tokens'),  # ⭐ 总tokens
                'unpaid_amount': account_data.get('unpaid_amount'),  # ⭐ 欠费金额
                'model_usage_json': model_usage_json,  # ⭐ 模型费用详情
                'last_used': account_data.get('last_used'),  # ⭐ 最后使用时间
                'machine_info': account_data.get('machine_info')  # ⭐ 保留机器码
            }
            
            logger.debug("保存数据：refresh_token 已填充, session_token 设为空, machine_info 已保留")
            
            # 保存账号到数据库（使用 upsert）
            account_id = self.storage.upsert_account(filtered_data)
            
            if account_id:
                logger.info(f"✅ 账号已保存到数据库 (ID: {account_id})")
                
                # ⭐ 当前登录账号检测完成后，必须重建列表以实现置顶功能
                logger.info(f"🔄 当前登录账号检测完成，重建列表以置顶: {detected_email}")
                QTimer.singleShot(500, lambda: self.refresh_accounts(force_rebuild=True))
                
                # ⭐ 静默提示（仅状态栏，无弹窗）
                email = filtered_data.get('email', '')
                plan = filtered_data.get('membership_type', 'free').upper()
                usage = filtered_data.get('usage_percent', 0)
                
                self.status_bar.show_message(
                    f"✅ 检测成功: {email} | {plan} | 使用率 {usage}%", 
                    5000
                )
                
                logger.info(f"账号信息: 套餐={plan}, 使用率={usage}%")
            else:
                logger.warning("保存账号失败")
                # ⭐ 静默提示（仅状态栏和日志，无弹窗）
                self.status_bar.show_message(
                    f"⚠️ 保存失败: {account_data.get('email', 'unknown')}", 
                    5000
                )
        except Exception as e:
            logger.error(f"处理检测到的账号时出错: {e}", exc_info=True)
            # ⭐ 静默提示（仅状态栏和日志，无弹窗）
            self.status_bar.show_message(f"❌ 检测错误: {str(e)[:50]}", 5000)
    
    def _on_filter_changed(self, filter_dict: dict):
        """筛选条件改变（使用防抖，避免闪烁）"""
        self.current_filter = filter_dict
        logger.info(f"筛选条件改变: {filter_dict}")
        
        # ⭐ 使用防抖定时器（避免频繁重建）
        if hasattr(self, 'filter_debounce_timer'):
            self.filter_debounce_timer.stop()
            self.filter_debounce_timer.start(150)  # 150ms延迟
        else:
            self.refresh_accounts(force_rebuild=True)
    
    def _on_sort_changed(self, sort_by: str, ascending: bool):
        """排序改变（使用防抖，避免闪烁）"""
        self.current_sort = (sort_by, ascending)
        logger.info(f"排序条件改变: {sort_by} ({'升序' if ascending else '降序'})")
        
        # ⭐ 使用防抖定时器（避免频繁重建）
        if hasattr(self, 'sort_debounce_timer'):
            self.sort_debounce_timer.stop()
            self.sort_debounce_timer.start(150)  # 150ms延迟
        else:
            self.refresh_accounts(force_rebuild=True)
    
    def _on_search_changed(self, text: str):
        """搜索文本改变（使用防抖，避免频繁刷新）"""
        # ⭐ 重启防抖定时器（300ms 后才真正刷新）
        self.search_debounce_timer.stop()
        self.search_debounce_timer.start(300)
    
    def _can_use_visibility_filter(self) -> bool:
        """
        判断是否可以使用可见性筛选（不重建卡片）
        
        Returns:
            bool: True表示可以使用可见性筛选
        """
        # 条件1：必须已有卡片
        if not self.account_cards:
            return False
        
        # 条件2：不能有搜索条件（搜索需要重建）
        if hasattr(self, 'toolbar') and self.toolbar.search_box.text():
            return False
        
        # 条件3：必须是纯筛选操作（不改变排序）
        # 如果有排序变化，返回False
        
        return True
    
    def _apply_filter_by_visibility(self):
        """
        通过可见性应用筛选（不删除卡片，无闪烁）
        """
        try:
            logger.info("🎯 使用智能筛选（隐藏/显示模式，无闪烁）")
            
            # ⭐ 禁用界面更新
            self.account_list_widget.setUpdatesEnabled(False)
            
            # 获取符合筛选条件的账号
            sort_by, ascending = self.current_sort
            filtered_accounts = self.storage.get_all_accounts(
                filter_type=self.current_filter.get('type'),
                filter_status=self.current_filter.get('status'),
                filter_month=self.current_filter.get('month'),
                sort_by=sort_by,
                ascending=ascending
            )
            
            # 构建符合条件的账号ID集合
            filtered_ids = {acc['id'] for acc in filtered_accounts}
            
            # 只改变卡片的可见性（不删除不创建）
            visible_count = 0
            hidden_count = 0
            for account_id, card in self.account_cards.items():
                if account_id in filtered_ids:
                    if not card.isVisible():
                        card.setVisible(True)
                        visible_count += 1
                else:
                    if card.isVisible():
                        card.setVisible(False)
                        hidden_count += 1
                    
                    # ⭐ 隐藏卡片时，自动取消选中（避免状态混乱）
                    if account_id in self.selected_account_ids:
                        card.set_selected(False)
                        self.selected_account_ids.discard(account_id)
                        logger.debug(f"取消隐藏账号的选中状态: {card.account_data.get('email')}")
            
            logger.info(f"✅ 筛选完成：显示 {len(filtered_ids)} 个，隐藏 {len(self.account_cards) - len(filtered_ids)} 个")
            
            # ⭐ 重新启用界面更新
            self.account_list_widget.setUpdatesEnabled(True)
            self.account_list_widget.update()
            
            # 更新工具栏计数
            if hasattr(self, 'toolbar'):
                total_count = len(self.account_cards)  # 总账号数
                visible_count = len(filtered_ids)  # 可见账号数
                selected_count = len(self.selected_account_ids)  # 选中数
                self.toolbar.update_counts(selected_count, total_count, visible_count)
            
            # 更新状态栏
            self.status_bar.update_account_count(len(filtered_ids))
            
        except Exception as e:
            logger.error(f"智能筛选失败，回退到重建模式: {e}")
            self.refresh_accounts(force_rebuild=True)
    
    def _do_search_refresh(self):
        """执行搜索刷新（防抖后的实际操作）"""
        self.refresh_accounts(force_rebuild=True)  # 搜索需要重建（内部也会检测）
    
    def _do_filter_refresh(self):
        """执行筛选刷新（防抖后的实际操作）- 使用智能筛选"""
        logger.info(f"⏰ 防抖完成，应用筛选: {self.current_filter}")
        
        # ⭐ 智能筛选：优先使用隐藏/显示，避免重建
        if self._can_use_visibility_filter():
            self._apply_filter_by_visibility()
        else:
            self.refresh_accounts(force_rebuild=True)
    
    def _do_sort_refresh(self):
        """执行排序刷新（防抖后的实际操作）"""
        sort_by, ascending = self.current_sort
        logger.info(f"⏰ 防抖完成，应用排序: {sort_by} ({'升序' if ascending else '降序'})")
        self.refresh_accounts(force_rebuild=True)  # 排序需要重建（因为顺序变化）
    
    def _on_card_selection_changed(self, account_id: int, selected: bool):
        """账号卡片选择状态改变"""
        if selected:
            self.selected_account_ids.add(account_id)
        else:
            self.selected_account_ids.discard(account_id)
        
        # 更新工具栏计数
        if hasattr(self, 'toolbar'):
            total = len(self.account_cards)
            visible_count = sum(1 for card in self.account_cards.values() if card.isVisible())
            self.toolbar.update_counts(len(self.selected_account_ids), total, visible_count)
    
    def _on_select_all(self, select: bool):
        """全选/取消全选（只选择当前可见的卡片）"""
        visible_count = 0
        
        for account_id, card in self.account_cards.items():
            # ⭐ 只操作可见的卡片（筛选后显示的）
            if card.isVisible():
                card.set_selected(select)
                visible_count += 1
                # 手动更新选中状态集合（因为 set_selected 阻塞了信号）
                if select:
                    self.selected_account_ids.add(account_id)
                else:
                    self.selected_account_ids.discard(account_id)
        
        logger.info(f"{'✅ 全选' if select else '❌ 取消全选'} {visible_count} 个可见账号")
        
        # 更新工具栏计数
        if hasattr(self, 'toolbar'):
            total_count = len(self.account_cards)  # 总账号数
            self.toolbar.update_counts(
                len(self.selected_account_ids),  # 选中数
                total_count,  # 总数
                visible_count  # 可见数（用于判断全选状态）
            )
    
    def _on_add_account(self):
        """添加账号"""
        from gui.dialogs.add_account_dialog import AddAccountDialog
        
        dialog = AddAccountDialog(self)
        
        # ⚡ 连接账号添加信号，实时刷新列表
        dialog.account_added.connect(self.refresh_accounts)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 获取账号数据
            account_data = dialog.get_account_data()
            
            if account_data:
                try:
                    # 添加到数据库
                    account_id = self.storage.add_account(account_data)
                    
                    if account_id:
                        # ⭐ 不弹窗，直接刷新账号列表
                        logger.info(f"✅ 账号添加成功: {account_data['email']}")
                        
                        # 刷新账号列表（新账号，需要重建）
                        self.refresh_accounts(force_rebuild=True)
                    else:
                        QMessageBox.warning(
                            self,
                            "警告",
                            "账号可能已存在"
                        )
                
                except Exception as e:
                    logger.error(f"添加账号失败: {e}")
                    QMessageBox.critical(
                        self,
                        "错误",
                        f"添加账号失败: {str(e)}"
                    )
    
    def _on_import_accounts(self):
        """导入账号"""
        from PyQt6.QtWidgets import QFileDialog
        from core.account_exporter import get_exporter
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入账号",
            "",
            "JSON 文件 (*.json);;所有文件 (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            exporter = get_exporter()
            
            # 尝试 Zzx 格式
            accounts = exporter.import_from_json(file_path)
            
            # 如果失败，尝试 FlyCursor 格式
            if not accounts:
                accounts = exporter.import_from_flycursor(file_path)
            
            if not accounts:
                QMessageBox.warning(self, "导入失败", "无法识别文件格式")
                return
            
            # 导入到数据库
            success_count = 0
            for account in accounts:
                account_id = self.storage.add_account(account)
                if account_id:
                    success_count += 1
            
            QMessageBox.information(
                self,
                "导入完成",
                f"成功导入 {success_count}/{len(accounts)} 个账号"
            )
            
            self.refresh_accounts(force_rebuild=True)  # 导入新账号，需要重建
            
        except Exception as e:
            logger.error(f"导入账号失败: {e}")
            QMessageBox.critical(self, "错误", f"导入失败: {str(e)}")
    
    def _on_export_selected(self):
        """导出选中的账号"""
        from PyQt6.QtWidgets import QFileDialog
        from core.account_exporter import get_exporter
        
        if not self.selected_account_ids:
            QMessageBox.warning(self, "提示", "请先选择要导出的账号")
            return
        
        # 获取选中的账号数据
        selected_accounts = []
        for account_id in self.selected_account_ids:
            account = self.storage.get_account_by_id(account_id)
            if account:
                selected_accounts.append(account)
        
        if not selected_accounts:
            return
        
        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出账号",
            f"accounts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON 文件 (*.json);;CSV 文件 (*.csv)"
        )
        
        if not file_path:
            return
        
        try:
            exporter = get_exporter()
            
            if file_path.endswith('.csv'):
                success = exporter.export_to_csv(selected_accounts, file_path)
            else:
                success = exporter.export_to_json(selected_accounts, file_path)
            
            if success:
                QMessageBox.information(
                    self,
                    "导出成功",
                    f"已导出 {len(selected_accounts)} 个账号到:\n{file_path}"
                )
            else:
                QMessageBox.warning(self, "导出失败", "导出过程中发生错误")
                
        except Exception as e:
            logger.error(f"导出账号失败: {e}")
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
    
    # ⭐ 已移除查看加密文件功能 - 不让用户知道导出的是加密文件
    # def _on_view_encrypted_file(self):
    #     """查看加密的导出文件"""
    #     pass
    
    def _on_batch_delete(self):
        """批量删除账号"""
        if not self.selected_account_ids:
            return
        
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除选中的 {len(self.selected_account_ids)} 个账号吗？\n\n此操作不可撤销！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success_count = 0
            for account_id in list(self.selected_account_ids):
                if self.storage.delete_account(account_id):
                    success_count += 1
            
            QMessageBox.information(
                self,
                "删除完成",
                f"成功删除 {success_count}/{len(self.selected_account_ids)} 个账号"
            )
            
            self.selected_account_ids.clear()
            self.refresh_accounts(force_rebuild=True)  # 删除账号，需要重建
    
    def _on_batch_refresh(self):
        """批量刷新账号（智能并发控制版）"""
        if not self.selected_account_ids:
            return
        
        # 初始化批量刷新状态
        self.batch_refresh_queue = list(self.selected_account_ids)
        self.batch_refresh_total = len(self.batch_refresh_queue)
        self.batch_refresh_current = 0
        self.batch_refresh_active = 0  # 当前正在刷新的数量
        self.batch_refresh_success = 0  # ⭐ 成功数量
        self.batch_refresh_failed = 0  # ⭐ 失败数量
        
        # ⭐ 从配置读取并发数（用于对话框显示）
        performance_config = self.config.get('performance', {})
        concurrent = performance_config.get('batch_concurrent', 2)
        
        # ⭐ 显示霸气的批量刷新对话框（传入并发数）
        from gui.dialogs.batch_refresh_dialog import BatchRefreshDialog
        
        self.batch_refresh_dialog = BatchRefreshDialog(self.batch_refresh_total, concurrent, self)
        
        # 连接信号：用户点击"开始刷新"时启动刷新
        self.batch_refresh_dialog.start_refresh_signal.connect(self._start_batch_refresh_process)
        
        # 显示对话框（非阻塞）
        self.batch_refresh_dialog.show()
    
    def _start_batch_refresh_process(self):
        """用户点击"开始刷新"后，真正启动批量刷新"""
        # ⭐ 从配置读取并发数（默认2个，最稳定）
        performance_config = self.config.get('performance', {})
        self.batch_refresh_max_concurrent = performance_config.get('batch_concurrent', 2)
        
        logger.info("="*60)
        logger.info(f"📊 开始批量刷新 {self.batch_refresh_total} 个账号（并发数: {self.batch_refresh_max_concurrent}）")
        logger.info("="*60)
        
        # 安全输出日志
        try:
            if self.current_panel:
                self.current_panel.log("="*40)
                self.current_panel.log(f"📊 批量刷新 {self.batch_refresh_total} 个账号")
                self.current_panel.log(f"⚡ 并发数: {self.batch_refresh_max_concurrent}")
                self.current_panel.log("="*40)
        except Exception as e:
            logger.debug(f"输出批量刷新日志失败: {e}")
        
        self.status_bar.show_message(f"🔄 批量刷新中 (0/{self.batch_refresh_total})...", 0)
        
        # 启动初始批次（启动多个并发任务）
        for _ in range(min(self.batch_refresh_max_concurrent, len(self.batch_refresh_queue))):
            self._start_next_batch_refresh()
    
    def _start_next_batch_refresh(self):
        """启动下一个批量刷新任务（优化版：添加关闭检查）"""
        try:
            # ⭐ 检查是否正在关闭
            if hasattr(self, '_is_closing') and self._is_closing:
                logger.info("窗口正在关闭，停止批量刷新")
                return
            
            if not hasattr(self, 'batch_refresh_queue') or not self.batch_refresh_queue:
                # 队列为空，检查是否全部完成
                if hasattr(self, 'batch_refresh_active') and self.batch_refresh_active == 0:
                    # 没有正在运行的任务了，完成
                    if hasattr(self, 'batch_refresh_total'):
                        success_count = getattr(self, 'batch_refresh_success', 0)
                        failed_count = getattr(self, 'batch_refresh_failed', 0)
                        
                        logger.info(f"✅ 批量刷新完成，共 {self.batch_refresh_total} 个账号（成功: {success_count}, 失败: {failed_count}）")
                        logger.info("="*60)
                        
                        # ⭐ 更新对话框为完成状态
                        if hasattr(self, 'batch_refresh_dialog') and self.batch_refresh_dialog:
                            try:
                                self.batch_refresh_dialog.update_progress(
                                    self.batch_refresh_total,
                                    f"✅ 刷新完成！成功: {success_count}, 失败: {failed_count}"
                                )
                                # ⭐ 3秒后播放掉落动画关闭对话框
                                QTimer.singleShot(3000, self.batch_refresh_dialog.play_closing_animation)
                            except Exception as e:
                                logger.debug(f"关闭对话框失败: {e}")
                        
                        # 安全调用日志输出
                        try:
                            if hasattr(self, 'current_panel') and self.current_panel:
                                self.current_panel.log(f"✅ 批量刷新完成 (成功:{success_count}/失败:{failed_count})")
                        except Exception as e:
                            logger.debug(f"输出日志失败: {e}")
                        
                        try:
                            if hasattr(self, 'status_bar') and self.status_bar:
                                self.status_bar.show_message(f"✅ 批量刷新完成 (成功:{success_count}/失败:{failed_count})", 5000)
                        except Exception as e:
                            logger.debug(f"更新状态栏失败: {e}")
                return
            
            # 获取下一个账号
            account_id = self.batch_refresh_queue.pop(0)
            self.batch_refresh_current += 1
            self.batch_refresh_active += 1
            
            account = self.storage.get_account_by_id(account_id)
            
            # 如果账号不存在，直接跳过
            if not account:
                logger.warning(f"账号 ID {account_id} 不存在，跳过")
                self.batch_refresh_active -= 1
                self._start_next_batch_refresh()
                return
            
            email = account.get('email', 'unknown')
            
            logger.info(f"[{self.batch_refresh_current}/{self.batch_refresh_total}] 刷新 {email} (并发: {self.batch_refresh_active})")
            
            # 安全调用日志输出
            try:
                if hasattr(self, 'current_panel') and self.current_panel:
                    self.current_panel.log(f"[{self.batch_refresh_current}/{self.batch_refresh_total}] {email}")
            except Exception as e:
                logger.debug(f"输出日志失败: {e}")
            
            try:
                if hasattr(self, 'status_bar') and self.status_bar:
                    self.status_bar.show_message(
                        f"🔄 批量刷新中 ({self.batch_refresh_current}/{self.batch_refresh_total}, 并发: {self.batch_refresh_active})...", 
                        0
                    )
            except Exception as e:
                logger.debug(f"更新状态栏失败: {e}")
            
            # ⭐ 启动刷新（批量模式 - 快速）
            # 现在 _on_refresh_finished 会在主线程中执行，所以回调也会在主线程执行
            self._on_refresh_account_with_callback(account_id, self._on_batch_refresh_item_finished, is_batch=True)
            
        except Exception as e:
            logger.error(f"启动批量刷新任务异常: {e}", exc_info=True)
            # 确保继续处理
            if hasattr(self, 'batch_refresh_active'):
                self.batch_refresh_active = max(0, self.batch_refresh_active - 1)
            # 尝试继续下一个
            try:
                QTimer.singleShot(100, self._start_next_batch_refresh)
            except:
                pass
    
    def _safe_update_current_panel(self, account_data: dict):
        """安全更新右侧当前账号面板"""
        try:
            if hasattr(self, 'current_panel') and self.current_panel and account_data:
                self.current_panel.update_account_info(account_data)
        except Exception as e:
            logger.debug(f"更新当前面板失败: {e}")
    
    def _on_batch_refresh_item_finished(self, account_id: int, success: bool):
        """单个批量刷新任务完成的回调（优化版：增强日志和错误处理）"""
        logger.info("=" * 40)
        logger.info(f"🔔 回调触发: account_id={account_id}, success={success}")
        logger.info("=" * 40)
        
        try:
            # ⭐ 检查是否遇到服务器错误，如果是，停止后续刷新
            if hasattr(self, 'batch_refresh_queue') and len(self.batch_refresh_queue) == 0 and not success:
                logger.warning("检测到服务器错误或队列已清空，停止批量刷新")
            
            # 检查窗口是否还存在
            if not self or not hasattr(self, 'batch_refresh_active'):
                logger.warning("窗口已关闭，停止批量刷新")
                return
            
            # ⭐ 确保计数不会出错
            logger.info(f"当前状态: active={self.batch_refresh_active}, current={self.batch_refresh_current}, total={self.batch_refresh_total}")
            
            if self.batch_refresh_active > 0:
                self.batch_refresh_active -= 1
            else:
                logger.warning(f"批量刷新计数异常: active={self.batch_refresh_active}")
                self.batch_refresh_active = 0
            
            # ⭐ 记录刷新结果
            if success:
                self.batch_refresh_success = getattr(self, 'batch_refresh_success', 0) + 1
            else:
                self.batch_refresh_failed = getattr(self, 'batch_refresh_failed', 0) + 1
            
            # ⭐ 获取账号信息用于日志
            account = self.storage.get_account_by_id(account_id)
            email = account.get('email', 'unknown') if account else 'unknown'
            status_text = "✅ 成功" if success else "❌ 失败"
            
            logger.info(f"[{self.batch_refresh_current}/{self.batch_refresh_total}] {email} 刷新{status_text} (active={self.batch_refresh_active})")
            
            # ⭐ 更新批量刷新对话框的进度
            if hasattr(self, 'batch_refresh_dialog') and self.batch_refresh_dialog:
                try:
                    self.batch_refresh_dialog.update_progress(
                        self.batch_refresh_current,
                        f"正在刷新: {self.batch_refresh_current}/{self.batch_refresh_total} - {email}"
                    )
                except Exception as e:
                    logger.debug(f"更新对话框进度失败: {e}")
            
            # ⭐ 无论成功失败都立即启动下一个（关键：确保第5个账号能开始）
            logger.info(f"准备启动下一个任务，队列剩余: {len(self.batch_refresh_queue)}")
            self._start_next_batch_refresh()
            
        except Exception as e:
            logger.error(f"批量刷新回调异常: {e}", exc_info=True)
            # ⭐ 确保即使出错也继续下一个（防止队列卡死）
            try:
                if hasattr(self, 'batch_refresh_active'):
                    self.batch_refresh_active = max(0, self.batch_refresh_active - 1)
                QTimer.singleShot(100, self._start_next_batch_refresh)
            except Exception as e2:
                logger.error(f"恢复处理失败: {e2}")
    
    def _on_batch_payment(self):
        """批量绑卡"""
        if not self.selected_account_ids:
            QMessageBox.warning(self, "提示", "请先选择要绑卡的账号")
            return
        
        # 获取选中的账号信息
        selected_accounts = []
        for account_id in self.selected_account_ids:
            account = self.storage.get_account_by_id(account_id)
            if account:
                selected_accounts.append(account)
        
        if not selected_accounts:
            QMessageBox.warning(self, "提示", "未找到有效的账号")
            return
        
        # 检查是否有可用的Token
        valid_accounts = [acc for acc in selected_accounts if acc.get('session_token')]
        if not valid_accounts:
            QMessageBox.warning(
                self, 
                "提示", 
                f"选中的 {len(selected_accounts)} 个账号都没有有效的Token，\n"
                "请先刷新账号获取Token后再进行绑卡。"
            )
            return
        
        # 如果有部分账号没有Token，提示用户
        if len(valid_accounts) < len(selected_accounts):
            reply = QMessageBox.question(
                self,
                "确认",
                f"选中的 {len(selected_accounts)} 个账号中：\n"
                f"• {len(valid_accounts)} 个有有效Token\n"
                f"• {len(selected_accounts) - len(valid_accounts)} 个无Token（将跳过）\n\n"
                f"是否继续对有Token的账号进行绑卡？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # 显示批量绑卡对话框
        from gui.dialogs.batch_payment_dialog import BatchPaymentDialog
        
        dialog = BatchPaymentDialog(valid_accounts, self)
        dialog.exec()
        
        # 刷新账号列表以显示更新的绑卡状态
        self.refresh_accounts()
    
    def _get_theme_icon(self) -> str:
        """获取主题切换按钮的图标"""
        if hasattr(self, 'theme_manager') and self.theme_manager.is_dark_theme():
            return "☀️ 浅色"
        else:
            return "🌙 深色"
    
    def _on_theme_toggle(self):
        """主题切换按钮点击事件（流畅过渡版）"""
        try:
            # ⭐ 懒加载过渡组件
            if not self.theme_transition:
                from gui.widgets.theme_transition import ThemeTransitionWidget
                self.theme_transition = ThemeTransitionWidget(self)
            
            # ⭐ 定义主题切换回调（在黑屏期间执行）
            def do_theme_switch():
                try:
                    # 切换主题
                    self.theme_manager.switch_theme(manual=True)  # ⭐ 标记为手动切换
                    
                    # 更新按钮图标
                    self.theme_toggle_action.setText(self._get_theme_icon())
                    
                    # 显示状态信息
                    current_theme = "深色模式" if self.theme_manager.is_dark_theme() else "浅色模式"
                    auto_switch_status = "（自动切换已禁用）" if not self.theme_manager.is_auto_switch_enabled() else ""
                    self.status_bar.show_message(f"✨ 已切换到{current_theme} {auto_switch_status}", 3000)
                    
                except Exception as e:
                    logger.error(f"主题切换回调失败: {e}")
            
            # ⭐ 播放过渡动画（淡入→切换→淡出）
            self.theme_transition.play_transition(do_theme_switch)
            
        except Exception as e:
            logger.error(f"切换主题失败: {e}")
            # 降级方案：直接切换（无动画）
            try:
                self.theme_manager.switch_theme(manual=True)  # ⭐ 标记为手动切换
                self.theme_toggle_action.setText(self._get_theme_icon())
                
                current_theme = "深色模式" if self.theme_manager.is_dark_theme() else "浅色模式"
                auto_switch_status = "（自动切换已禁用）" if not self.theme_manager.is_auto_switch_enabled() else ""
                self.status_bar.show_message(f"✨ 已切换到{current_theme} {auto_switch_status}", 2000)
            except:
                pass
                self.status_bar.show_message("❌ 主题切换失败", 3000)
    
    def _on_theme_changed(self, theme_name: str):
        """主题改变事件（分阶段渲染优化版）"""
        try:
            logger.debug(f"主题切换信号触发: {theme_name}")
            
            # ⭐ 阶段1：立即更新关键UI组件（用户最先看到的）
            # 更新按钮图标
            if hasattr(self, 'theme_toggle_action'):
                self.theme_toggle_action.setText(self._get_theme_icon())
            
            # 更新当前账号面板
            if hasattr(self, 'current_panel'):
                try:
                    self.current_panel._apply_theme_styles()
                    logger.debug("当前账号面板已更新")
                except Exception as e:
                    logger.warning(f"更新当前账号面板失败: {e}")
            
            # ⭐ 阶段2：延迟50ms更新账号卡片（分批处理）
            QTimer.singleShot(50, lambda: self._update_cards_theme_staged(theme_name))
            
            logger.info(f"主题切换准备完成: {theme_name}")
            
        except Exception as e:
            logger.error(f"主题切换失败: {e}")
    
    def _update_cards_theme_staged(self, theme_name: str):
        """分阶段更新卡片主题（优先渲染可见卡片）"""
        try:
            if not hasattr(self, 'account_cards') or not self.account_cards:
                return
            
            cards_list = list(self.account_cards.values())
            total_cards = len(cards_list)
            
            logger.debug(f"分阶段更新 {total_cards} 个卡片主题")
            
            # ⭐ 冻结布局（防止中途重排）
            if hasattr(self, 'account_list_layout'):
                self.account_list_layout.freeze()
            
            if hasattr(self, 'account_list_widget'):
                self.account_list_widget.setUpdatesEnabled(False)
            
            # ⭐ 第一批：前20个卡片（可见区域）立即更新
            batch1 = cards_list[:20]
            for card in batch1:
                if card:
                    card._update_style_silent()
            
            if total_cards <= 20:
                # 卡片不多，直接完成
                QTimer.singleShot(50, self._theme_update_complete)
            else:
                # ⭐ 第二批：剩余卡片延迟50ms更新
                def update_remaining():
                    try:
                        batch2 = cards_list[20:]
                        for card in batch2:
                            if card:
                                card._update_style_silent()
                        logger.debug(f"第二批 {len(batch2)} 个卡片已更新")
                        
                        # 再延迟50ms完成
                        QTimer.singleShot(50, self._theme_update_complete)
                    except Exception as e:
                        logger.error(f"更新第二批卡片失败: {e}")
                        self._theme_update_complete()
                
                QTimer.singleShot(50, update_remaining)
            
        except Exception as e:
            logger.error(f"分阶段更新卡片失败: {e}")
            # 确保解冻
            self._theme_update_complete()
    
    def _theme_update_complete(self):
        """主题更新完成回调（解冻并一次性重绘）"""
        try:
            # ⭐ 解冻布局并标记为脏
            if hasattr(self, 'account_list_layout'):
                self.account_list_layout.unfreeze()
            
            # ⭐ 恢复渲染（一次性重绘）
            if hasattr(self, 'account_list_widget'):
                self.account_list_widget.setUpdatesEnabled(True)
                self.account_list_widget.update()
            
            logger.debug("主题更新完成")
            
        except Exception as e:
            logger.error(f"主题更新完成回调失败: {e}")
            # 确保恢复状态
            if hasattr(self, 'account_list_widget'):
                self.account_list_widget.setUpdatesEnabled(True)
    
    def _load_stylesheet(self):
        """加载样式表（已被主题管理器替代，保留以兼容）"""
        # 此方法已被主题管理器替代，不再使用
        pass
    
    def eventFilter(self, obj, event):
        """
        事件过滤器 - 捕获键盘事件和鼠标事件（用于拖动多选）
        
        Args:
            obj: 事件对象
            event: 事件
            
        Returns:
            bool: 是否拦截事件
        """
        from PyQt6.QtCore import QEvent
        
        # ⭐ 处理键盘事件
        if event.type() == QEvent.Type.KeyPress:
            # Delete 键 - 删除选中的账号
            if event.key() == Qt.Key.Key_Delete:
                if self.selected_account_ids:
                    self._on_batch_delete()
                return True  # 拦截事件
            
            # Ctrl+A - 全选
            if event.key() == Qt.Key.Key_A and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self._on_select_all(True)
                return True  # 拦截事件
            
            # Escape - 取消全选
            if event.key() == Qt.Key.Key_Escape:
                self._on_select_all(False)
                return True  # 拦截事件
        
        # ⭐ 处理拖动多选功能
        if isinstance(obj, AccountCard):
            if event.type() == QEvent.Type.MouseButtonPress:
                return self._handle_card_mouse_press(obj, event)
            elif event.type() == QEvent.Type.MouseMove:
                return self._handle_card_mouse_move(obj, event)
            elif event.type() == QEvent.Type.MouseButtonRelease:
                return self._handle_card_mouse_release(obj, event)
        
        # 其他事件正常传递
        return super().eventFilter(obj, event)
    
    def _on_drag_select_start(self, card):
        """拖动多选开始"""
        self.is_drag_selecting = True
        self.drag_start_card = card
        
        # 更新选中集合
        if card.is_selected():
            self.selected_account_ids.add(card.account_id)
        else:
            self.selected_account_ids.discard(card.account_id)
        
        # 更新工具栏计数
        if hasattr(self, 'toolbar'):
            visible_count = sum(1 for c in self.account_cards.values() if c.isVisible())
            self.toolbar.update_counts(len(self.selected_account_ids), len(self.account_cards), visible_count)
        
        logger.info(f"✅ 开始拖动多选，起始卡片: {card.account_data.get('email')}")
    
    def _on_drag_select_move(self, card, event):
        """拖动多选移动（优化版：添加详细日志和简化逻辑）"""
        if not self.is_drag_selecting:
            return
        
        # 获取鼠标全局位置
        global_pos = card.mapToGlobal(event.pos())
        logger.debug(f"拖动移动 - 鼠标全局位置: {global_pos}")
        
        # 统计经过的卡片数量
        selected_count = 0
        
        # 遍历所有卡片，判断鼠标是否经过
        for account_id, other_card in self.account_cards.items():
            try:
                # ⭐ 简化：直接使用 geometry 获取卡片矩形
                card_rect = other_card.geometry()
                
                # 获取卡片在父容器中的位置
                card_parent_pos = other_card.pos()
                
                # 转换为全局坐标
                card_global_pos = other_card.parentWidget().mapToGlobal(card_parent_pos)
                
                # 创建全局矩形
                from PyQt6.QtCore import QRect
                card_global_rect = QRect(card_global_pos, card_rect.size())
                
                # 判断鼠标是否在这个卡片内
                if card_global_rect.contains(global_pos):
                    # 如果这个卡片还没有被选中，则选中它
                    if not other_card.is_selected():
                        other_card.set_selected(True)
                        self.selected_account_ids.add(account_id)
                        selected_count += 1
                        
                        logger.info(f"✅ 拖动经过并选中: {other_card.account_data.get('email')}")
            except Exception as e:
                logger.error(f"处理卡片鼠标移动异常: {e}", exc_info=True)
                continue
        
        # 更新工具栏计数（批量更新，避免频繁刷新）
        if selected_count > 0 and hasattr(self, 'toolbar'):
            visible_count = sum(1 for c in self.account_cards.values() if c.isVisible())
            self.toolbar.update_counts(len(self.selected_account_ids), len(self.account_cards), visible_count)
    
    def _on_drag_select_end(self, card):
        """拖动多选结束"""
        if not self.is_drag_selecting:
            return
        
        self.is_drag_selecting = False
        self.drag_start_card = None
        
        logger.info(f"拖动多选完成，共选中 {len(self.selected_account_ids)} 个账号")
    
    def _handle_card_mouse_press(self, card, event):
        """
        处理卡片上的鼠标按下事件（拖动多选起始）
        
        Args:
            card: AccountCard 对象
            event: 鼠标事件
            
        Returns:
            bool: 是否拦截事件
        """
        from PyQt6.QtCore import Qt
        
        # 只处理左键
        if event.button() != Qt.MouseButton.LeftButton:
            return False
        
        # 检查是否在复选框区域（左上角约30x30像素）
        pos = event.pos()
        checkbox_rect = card.checkbox.geometry()
        
        # ⭐ 调试日志
        logger.debug(f"鼠标按下位置: {pos}, 复选框区域: {checkbox_rect}")
        
        # 扩大复选框的可点击区域（更容易触发）
        checkbox_rect.adjust(-5, -5, 5, 5)
        
        if checkbox_rect.contains(pos):
            # 在复选框区域按下，启动拖动多选
            self.is_drag_selecting = True
            self.drag_start_card = card
            
            # 切换当前卡片的选中状态
            current_state = card.is_selected()
            card.set_selected(not current_state)
            
            # 手动更新选中集合
            if not current_state:
                self.selected_account_ids.add(card.account_id)
            else:
                self.selected_account_ids.discard(card.account_id)
            
            # 更新工具栏计数
            if hasattr(self, 'toolbar'):
                visible_count = sum(1 for c in self.account_cards.values() if c.isVisible())
                self.toolbar.update_counts(len(self.selected_account_ids), len(self.account_cards), visible_count)
            
            logger.info(f"✅ 开始拖动多选，起始卡片: {card.account_data.get('email')}")
            return True  # 拦截事件，防止触发复选框的默认行为
        else:
            logger.debug(f"点击位置不在复选框区域")
        
        return False
    
    def _handle_card_mouse_move(self, card, event):
        """
        处理卡片上的鼠标移动事件（拖动多选中）
        
        Args:
            card: AccountCard 对象
            event: 鼠标事件
            
        Returns:
            bool: 是否拦截事件
        """
        if not self.is_drag_selecting:
            return False
        
        # 获取鼠标全局位置
        global_pos = event.globalPosition().toPoint()
        
        # 遍历所有卡片，判断鼠标是否经过
        for account_id, other_card in self.account_cards.items():
            try:
                # ⭐ 修复：直接使用卡片的全局矩形
                card_top_left = other_card.mapToGlobal(other_card.rect().topLeft())
                card_bottom_right = other_card.mapToGlobal(other_card.rect().bottomRight())
                
                # 创建全局矩形
                from PyQt6.QtCore import QRect
                card_global_rect = QRect(card_top_left, card_bottom_right)
                
                # 判断鼠标是否在这个卡片内
                if card_global_rect.contains(global_pos):
                    # 如果这个卡片还没有被选中，则选中它
                    if not other_card.is_selected():
                        other_card.set_selected(True)
                        self.selected_account_ids.add(account_id)
                        
                        # 更新工具栏计数
                        if hasattr(self, 'toolbar'):
                            visible_count = sum(1 for c in self.account_cards.values() if c.isVisible())
                            self.toolbar.update_counts(len(self.selected_account_ids), len(self.account_cards), visible_count)
                        
                        logger.debug(f"拖动经过卡片: {other_card.account_data.get('email')}")
            except Exception as e:
                logger.debug(f"处理卡片鼠标移动异常: {e}")
                continue
        
        return True  # 拦截事件
    
    def _handle_card_mouse_release(self, card, event):
        """
        处理卡片上的鼠标释放事件（拖动多选结束）
        
        Args:
            card: AccountCard 对象
            event: 鼠标事件
            
        Returns:
            bool: 是否拦截事件
        """
        from PyQt6.QtCore import Qt
        
        if not self.is_drag_selecting:
            return False
        
        # 只处理左键释放
        if event.button() != Qt.MouseButton.LeftButton:
            return False
        
        # 结束拖动多选
        self.is_drag_selecting = False
        self.drag_start_card = None
        
        logger.info(f"拖动多选完成，共选中 {len(self.selected_account_ids)} 个账号")
        
        return True  # 拦截事件
    
    def keyPressEvent(self, event):
        """
        键盘事件处理（备用）
        
        Args:
            event: 键盘事件
        """
        
        # Delete 键 - 删除选中的账号
        if event.key() == Qt.Key.Key_Delete:
            if self.selected_account_ids:
                self._on_batch_delete()
            event.accept()
            return
        
        # Ctrl+A - 全选
        if event.key() == Qt.Key.Key_A and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._on_select_all(True)
            event.accept()
            return
        
        # Escape - 取消全选
        if event.key() == Qt.Key.Key_Escape:
            self._on_select_all(False)
            event.accept()
            return
        
        # 其他按键传递给父类处理
        super().keyPressEvent(event)
    
    def resizeEvent(self, event):
        """窗口大小调整事件 - 动态调整分割器比例"""
        super().resizeEvent(event)
        
        # 只在分割器已创建后才调整
        if hasattr(self, 'main_splitter'):
            # 获取窗口宽度
            window_width = self.width()
            
            # 只在窗口宽度变化超过50px时才调整（避免用户拖动分割器时被重置）
            if abs(window_width - self.last_window_width) > 50:
                # 智能动态计算分割器尺寸：根据窗口大小自适应调整比例
                # 目标：确保左侧能显示目标列数，右侧有充足空间
                
                # 计算4列所需最小宽度：4×270 + 3×6 + 20(边距) + 12(滚动条) = 1120px
                four_cols_min = 1120
                # 计算3列所需最小宽度：3×270 + 2×6 + 20 + 12 = 854px
                three_cols_min = 854
                # 计算2列所需最小宽度：2×270 + 1×6 + 20 + 12 = 578px
                two_cols_min = 578
                
                # 根据窗口宽度智能分配
                if window_width >= 1800:
                    # 大窗口：左侧留足够空间显示4列，右侧也要宽敞
                    left_width = four_cols_min + 200  # 4列 + 200px舒适余白
                elif window_width >= 1400:
                    # 中大窗口：左侧争取显示4列
                    left_width = four_cols_min + 100  # 4列 + 100px余白
                elif window_width >= 1100:
                    # 中窗口：左侧显示3列
                    left_width = three_cols_min + 100  # 3列 + 100px余白
                else:
                    # 小窗口：左侧显示2列，按60%分配，确保至少600px
                    left_width = max(600, int(window_width * 0.60))
                
                # 确保右侧至少有450px
                right_width = window_width - left_width
                if right_width < 450:
                    right_width = 450
                    left_width = window_width - 450
                
                # 应用新尺寸
                self.main_splitter.setSizes([left_width, right_width])
                
                # 更新记录
                self.last_window_width = window_width
                
                # 计算实际比例
                ratio = f"{left_width}:{right_width} ({left_width/window_width*100:.1f}%:{right_width/window_width*100:.1f}%)"
                logger.info(f"🔧 窗口调整: {window_width}px → 分割器: [{left_width}, {right_width}] = {ratio}")
    
    def _collect_card_update(self, account_id: int, account_data: dict):
        """
        收集卡片更新请求（防抖）
        
        Args:
            account_id: 账号ID
            account_data: 账号数据
        """
        # 加入待更新队列
        self._batch_update_manager['pending_cards'][account_id] = account_data
        
        # ⭐ 从配置读取防抖延迟（默认200ms）
        performance_config = self.config.get('performance', {})
        debounce_delay = performance_config.get('debounce_delay', 200)
        
        # 重启定时器（延迟内的更新会被合并）
        timer = self._batch_update_manager['timer']
        timer.stop()
        timer.start(debounce_delay)
    
    def _flush_card_updates(self):
        """
        刷新所有待更新的卡片（批量一次性处理）
        """
        pending = self._batch_update_manager['pending_cards']
        
        if not pending:
            return
        
        try:
            logger.debug(f"批量更新 {len(pending)} 个卡片")
            
            # ⭐ 三重防护：冻结布局+暂停渲染+禁用更新
            if hasattr(self, 'account_list_layout'):
                self.account_list_layout.freeze()
            
            if hasattr(self, 'account_list_widget'):
                self.account_list_widget.setUpdatesEnabled(False)
            
            # ⭐ 批量更新所有卡片（静默模式）
            for account_id, account_data in pending.items():
                card = self.account_cards.get(account_id)
                if card and account_data:
                    card.update_account_data_silent(account_data)
            
            # 清空队列
            pending.clear()
            
            # ⭐ 解冻布局并标记为脏（准备重新计算）
            if hasattr(self, 'account_list_layout'):
                self.account_list_layout.unfreeze()
            
            # ⭐ 恢复渲染（一次性重绘）
            if hasattr(self, 'account_list_widget'):
                self.account_list_widget.setUpdatesEnabled(True)
                self.account_list_widget.update()
            
            logger.debug("批量更新完成")
            
        except Exception as e:
            logger.error(f"批量更新失败: {e}")
            # 确保恢复状态
            if hasattr(self, 'account_list_layout'):
                try:
                    self.account_list_layout.unfreeze()
                except:
                    pass
            if hasattr(self, 'account_list_widget'):
                self.account_list_widget.setUpdatesEnabled(True)
    
    def closeEvent(self, event):
        """窗口关闭（优化版：确保所有线程正确清理）"""
        try:
            # 检查所有配置面板是否有未保存的修改
            config_panels = [
                (self.email_panel, '邮箱配置'),
                (self.phone_panel, '手机验证'),
                (self.payment_panel, '绑卡配置')
            ]
            
            for panel, name in config_panels:
                if hasattr(self, panel.__class__.__name__.replace('Panel', '').lower() + '_panel'):
                    if hasattr(panel, 'check_unsaved_changes'):
                        if not panel.check_unsaved_changes():
                            # 用户选择取消，不关闭窗口
                            logger.info(f"❌ 用户取消关闭（{name}页面有未保存修改）")
                            event.ignore()
                            return
            
            logger.info("开始关闭主窗口...")
            
            # ⭐ 设置关闭标志，防止新线程启动
            self._is_closing = True
            
            # 停止自动检测定时器
            if hasattr(self, 'auto_detect_timer') and self.auto_detect_timer:
                try:
                    self.auto_detect_timer.stop()
                    logger.debug("自动检测定时器已停止")
                except:
                    pass
            
            # 停止防抖定时器
            if hasattr(self, 'search_debounce_timer') and self.search_debounce_timer:
                try:
                    self.search_debounce_timer.stop()
                    logger.debug("搜索防抖定时器已停止")
                except:
                    pass
            
            # 停止系统监控定时器（已删除）
            # 系统监控功能已移除
            
            # ⭐ 停止线程管理器
            if hasattr(self, 'thread_manager') and self.thread_manager:
                try:
                    running_tasks = self.thread_manager.get_running_tasks()
                    if running_tasks:
                        logger.info(f"正在停止 {len(running_tasks)} 个运行中的任务...")
                    
                    # 关闭线程管理器（不等待任务完成，快速关闭）
                    self.thread_manager.shutdown(wait=False)
                    logger.info("线程管理器已停止")
                except Exception as e:
                    logger.error(f"停止线程管理器失败: {e}")
            
            # 停止检测线程
            if (hasattr(self, 'current_panel') and 
                hasattr(self.current_panel, 'detection_thread') and
                self.current_panel.detection_thread):
                try:
                    thread = self.current_panel.detection_thread
                    if thread.isRunning():
                        logger.debug("停止检测线程")
                        thread.quit()
                        if not thread.wait(2000):
                            logger.warning("检测线程未能正常退出，强制终止")
                            thread.terminate()
                            thread.wait(500)
                        thread.deleteLater()
                except Exception as e:
                    logger.error(f"停止检测线程失败: {e}")
            
            logger.info("主窗口关闭完成")
            event.accept()
            
        except Exception as e:
            logger.error(f"关闭窗口时出错: {e}", exc_info=True)
            event.accept()

