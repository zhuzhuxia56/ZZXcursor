#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动画面 - 类似于 IntelliJ IDEA 的启动弹窗
在软件完全加载前显示，提供更好的用户体验
"""

import sys
import time
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QProgressBar, QFrame, QApplication, QGraphicsOpacityEffect
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, 
    QEasingCurve, QRect
)
from PyQt6.QtGui import (
    QPixmap, QFont, QPainter, QColor, QBrush, 
    QPen, QLinearGradient, QPainterPath
)

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.logger import get_logger

logger = get_logger("splash_screen")


class InitializationWorker(QThread):
    """初始化工作线程"""
    
    progress_updated = pyqtSignal(int, str)  # 进度, 状态文本
    finished = pyqtSignal(object)  # 传递检测到的账号信息
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.should_stop = False
        self.detected_account = None  # 存储检测到的账号
    
    def stop(self):
        """停止初始化"""
        self.should_stop = True
        self.quit()
        self.wait()
    
    def run(self):
        """执行初始化任务"""
        try:
            # 实际的初始化步骤
            self._init_step(10, "初始化日志系统...", self._init_logging)
            self._init_step(20, "加载配置文件...", self._load_config)
            self._init_step(30, "初始化数据库连接...", self._init_database)
            self._init_step(40, "检测浏览器环境...", self._check_browser)
            self._init_step(50, "加载邮箱配置...", self._init_email)
            self._init_step(60, "初始化 Cursor API...", self._init_api)
            self._init_step(70, "初始化线程管理器...", self._init_thread_manager)
            # ⭐ 启动检测改为可选（失败不影响程序启动）
            try:
                self._init_step(75, "检测当前登录账号...", self._detect_current_account)
            except Exception as e:
                logger.warning(f"启动检测失败（跳过）: {e}")
                self.progress_updated.emit(75, "启动检测失败（已跳过）")
            self._init_step(85, "准备UI组件...", self._prepare_ui)
            self._init_step(95, "应用主题样式...", self._apply_theme)
            self._init_step(100, "启动完成!", lambda: None)
            
            # 额外等待一小段时间，让用户看到"启动完成"
            time.sleep(0.5)
            
            # 传递检测到的账号信息
            self.finished.emit(self.detected_account)
            
        except Exception as e:
            logger.error(f"初始化过程中发生错误: {e}")
            self.error_occurred.emit(str(e))
    
    def _init_step(self, progress: int, status: str, init_func: callable):
        """执行单个初始化步骤"""
        if self.should_stop:
            return
        
        self.progress_updated.emit(progress, status)
        
        try:
            init_func()
        except Exception as e:
            logger.error(f"初始化步骤失败 [{status}]: {e}")
            # 继续执行，不因为单个步骤失败而停止整个初始化
        
        # 短暂延迟，让用户看到进度更新
        time.sleep(0.2)
    
    def _init_logging(self):
        """初始化日志系统"""
        from utils.logger import setup_logger
        setup_logger()
        logger.info("日志系统初始化完成")
    
    def _load_config(self):
        """加载配置文件"""
        import json
        from pathlib import Path
        import sys
        # 导入 get_config_file
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from utils.app_paths import get_config_file
        
        config_path = get_config_file()
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"配置文件加载完成: {len(config)} 个配置项")
        else:
            logger.warning("配置文件不存在，将使用默认配置")
    
    def _init_database(self):
        """初始化数据库连接"""
        from core.account_storage import get_storage
        self.storage = get_storage()  # ⭐ 保存到实例变量
        # 测试数据库连接
        accounts = self.storage.get_all_accounts()
        logger.info(f"数据库连接成功，当前账号数: {len(accounts)}")
    
    def _check_browser(self):
        """检测浏览器环境（已禁用，等待重新实现）"""
        # 浏览器管理器已删除，等待重新实现
        logger.info("浏览器检测已跳过（等待重新实现）")
    
    def _init_email(self):
        """加载邮箱配置"""
        try:
            from core.email_generator import init_email_generator
            init_email_generator("sakuna.top")  # 使用默认域名
            logger.info("邮箱配置加载完成")
        except Exception as e:
            logger.warning(f"邮箱配置加载失败: {e}")
    
    def _init_api(self):
        """初始化 Cursor API"""
        try:
            from core.cursor_api import get_api_client
            api = get_api_client()
            logger.info("Cursor API 客户端初始化完成")
        except Exception as e:
            logger.warning(f"API 客户端初始化失败: {e}")
    
    def _init_thread_manager(self):
        """初始化线程管理器"""
        try:
            from core.thread_manager import get_thread_manager
            thread_manager = get_thread_manager()
            logger.info("线程管理器初始化完成")
        except Exception as e:
            logger.warning(f"线程管理器初始化失败: {e}")
    
    def _prepare_ui(self):
        """准备UI组件"""
        # 预加载一些UI资源
        logger.info("UI组件准备完成")
    
    def _detect_current_account(self):
        """检测当前登录账号"""
        try:
            from core.current_account_detector import get_detector
            
            # ⭐ 传递storage实例，让detector可以读取增量刷新信息
            storage = getattr(self, 'storage', None)
            if not storage:
                logger.warning("storage 未初始化，无法使用增量刷新")
            
            detector = get_detector(storage=storage)
            account = detector.detect_current_account()
            
            if account and account.get('status') == 'active':
                self.detected_account = account
                email = account.get('email', '未知')
                plan = account.get('membership_type', 'free').upper()
                logger.info(f"检测到当前账号: {email} ({plan})")
            else:
                logger.warning("未检测到活跃账号")
                self.detected_account = None
                
        except Exception as e:
            logger.warning(f"账号检测失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            self.detected_account = None
    
    def _apply_theme(self):
        """应用主题样式"""
        # 预加载样式表等
        logger.info("主题样式应用完成")


class SplashScreen(QDialog):
    """启动画面对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.init_worker = None
        self._fade_animation = None
        self.detected_account_data = None  # 存储检测到的账号信息
        
        self._setup_ui()
        self._setup_animations()
        self._start_initialization()
    
    def _setup_ui(self):
        """设置用户界面"""
        # 设置对话框属性
        self.setWindowFlags(
            Qt.WindowType.Dialog | 
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setModal(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 设置固定大小（增加宽度和高度）
        self.setFixedSize(500, 350)
        
        # 居中显示
        if QApplication.primaryScreen():
            screen_center = QApplication.primaryScreen().availableGeometry().center()
            self.move(screen_center - self.rect().center())
        
        # 创建主容器
        self.main_frame = QFrame()
        self.main_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #ffffff, stop: 1 #f8f9fa);
                border: 2px solid #e0e6ed;
                border-radius: 15px;
            }
        """)
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.main_frame)
        
        # 内容布局
        content_layout = QVBoxLayout(self.main_frame)
        content_layout.setContentsMargins(40, 35, 40, 35)
        content_layout.setSpacing(15)
        
        # Logo 区域
        logo_layout = QHBoxLayout()
        logo_layout.addStretch()
        
        # Logo 图标（使用文字代替，可以替换为实际图标）
        self.logo_label = QLabel("🎯")
        self.logo_label.setFont(QFont("Segoe UI Emoji", 32))
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_layout.addWidget(self.logo_label)
        
        logo_layout.addStretch()
        content_layout.addLayout(logo_layout)
        
        # 标题
        self.title_label = QLabel("Zzx Cursor Auto Manager")
        self.title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                margin: 8px 0;
                padding: 0px;
            }
        """)
        self.title_label.setWordWrap(True)  # 允许文字换行
        content_layout.addWidget(self.title_label)
        
        # 版本信息
        self.version_label = QLabel("v2.5 - Cursor 账号自动化管理系统")
        self.version_label.setFont(QFont("Microsoft YaHei", 10))
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.version_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                margin-bottom: 15px;
                padding: 0px;
            }
        """)
        self.version_label.setWordWrap(True)  # 允许文字换行
        content_layout.addWidget(self.version_label)
        
        # 进度条容器
        progress_container = QVBoxLayout()
        progress_container.setSpacing(8)
        
        # 状态文本
        self.status_label = QLabel("正在启动...")
        self.status_label.setFont(QFont("Microsoft YaHei", 9))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #5d6d7e;
                padding: 0px;
            }
        """)
        self.status_label.setWordWrap(True)  # 允许文字换行
        progress_container.addWidget(self.status_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 4px;
                background-color: #ecf0f1;
            }
            QProgressBar::chunk {
                border-radius: 4px;
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #3498db, stop: 1 #2980b9);
            }
        """)
        progress_container.addWidget(self.progress_bar)
        
        content_layout.addLayout(progress_container)
        
        # 底部版权信息
        content_layout.addStretch()
        
        self.copyright_label = QLabel("© 2025 Zzx Dev - All Rights Reserved")
        self.copyright_label.setFont(QFont("Microsoft YaHei", 8))
        self.copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.copyright_label.setStyleSheet("""
            QLabel {
                color: #95a5a6;
                padding: 0px;
            }
        """)
        self.copyright_label.setWordWrap(True)  # 允许文字换行
        content_layout.addWidget(self.copyright_label)
    
    def _setup_animations(self):
        """设置动画效果"""
        # 淡入动画
        self.fade_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.fade_effect)
        
        self.fade_in_animation = QPropertyAnimation(self.fade_effect, b"opacity")
        self.fade_in_animation.setDuration(500)
        self.fade_in_animation.setStartValue(0.0)
        self.fade_in_animation.setEndValue(1.0)
        self.fade_in_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # 淡出动画
        self.fade_out_animation = QPropertyAnimation(self.fade_effect, b"opacity")
        self.fade_out_animation.setDuration(400)
        self.fade_out_animation.setStartValue(1.0)
        self.fade_out_animation.setEndValue(0.0)
        self.fade_out_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade_out_animation.finished.connect(self.accept)
    
    def _start_initialization(self):
        """开始初始化过程"""
        # 播放淡入动画
        self.fade_in_animation.start()
        
        # 创建并启动初始化线程
        self.init_worker = InitializationWorker()
        self.init_worker.progress_updated.connect(self._on_progress_updated)
        self.init_worker.finished.connect(self._on_initialization_finished)
        self.init_worker.error_occurred.connect(self._on_initialization_error)
        
        # 延迟启动，让淡入动画先播放
        QTimer.singleShot(200, self.init_worker.start)
    
    def _on_progress_updated(self, progress: int, status: str):
        """更新进度"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(status)
        logger.debug(f"启动进度: {progress}% - {status}")
    
    def _on_initialization_finished(self, detected_account):
        """初始化完成"""
        self.detected_account_data = detected_account
        
        if detected_account:
            email = detected_account.get('email', '未知')
            plan = detected_account.get('membership_type', 'free').upper()
            logger.info(f"启动初始化完成，检测到账号: {email} ({plan})")
        else:
            logger.info("启动初始化完成，未检测到活跃账号")
        
        # 延迟一下再关闭，让用户看到完成状态
        QTimer.singleShot(800, self._close_with_animation)
    
    def _on_initialization_error(self, error_message: str):
        """初始化错误"""
        logger.error(f"启动初始化失败: {error_message}")
        
        self.status_label.setText(f"初始化失败: {error_message}")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #e74c3c;
            }
        """)
        
        # 3秒后自动关闭
        QTimer.singleShot(3000, self.accept)
    
    def _close_with_animation(self):
        """带动画的关闭"""
        self.fade_out_animation.start()
    
    def closeEvent(self, event):
        """处理关闭事件"""
        if self.init_worker and self.init_worker.isRunning():
            self.init_worker.stop()
        
        super().closeEvent(event)
    
    def keyPressEvent(self, event):
        """处理按键事件"""
        # 禁用 Escape 键关闭
        if event.key() == Qt.Key.Key_Escape:
            event.ignore()
            return
        
        super().keyPressEvent(event)


def show_splash_screen(parent=None) -> tuple:
    """
    显示启动画面
    
    Args:
        parent: 父窗口
    
    Returns:
        tuple: (是否成功初始化, 检测到的账号数据)
    """
    try:
        splash = SplashScreen(parent)
        result = splash.exec()
        success = result == QDialog.DialogCode.Accepted
        detected_account = splash.detected_account_data
        return success, detected_account
    except Exception as e:
        logger.error(f"显示启动画面失败: {e}")
        return True, None  # 即使启动画面失败也继续启动程序


if __name__ == "__main__":
    # 测试启动画面
    app = QApplication(sys.argv)
    
    success = show_splash_screen()
    print(f"启动画面结果: {success}")
    
    sys.exit(0)
