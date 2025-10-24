#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量刷新对话框
带动图、进度条和霸气提示
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QProgressBar, QFrame, QMessageBox,
    QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QMovie, QFont

from utils.logger import get_logger
from utils.resource_path import get_gui_resource

logger = get_logger("batch_refresh_dialog")


class BatchRefreshDialog(QDialog):
    """批量刷新确认对话框（霸气版）"""
    
    # 信号
    start_refresh_signal = pyqtSignal()  # 开始刷新
    
    def __init__(self, total_count: int, concurrent: int = 2, parent=None):
        super().__init__(parent)
        self.total_count = total_count
        self.concurrent = concurrent  # ⭐ 并发数
        self.current_count = 0
        self.is_completed = False  # ⭐ 标记是否已完成
        self._is_closing_animation = False  # ⭐ 标记是否正在播放关闭动画
        self.setup_ui()
    
    def setup_ui(self):
        """初始化UI"""
        self.setWindowTitle("批量刷新")
        self.setModal(True)
        self.setMinimumWidth(650)
        self.setMinimumHeight(450)
        
        # 深色模式背景
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
        """)
        
        # 主布局 - 左右布局
        main_layout = QHBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # ========== 左侧：动图和进度区域 ==========
        left_widget = QFrame()
        left_widget.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 8px;
                border: 2px solid #FF6B6B;
            }
        """)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)
        left_layout.setContentsMargins(20, 20, 20, 20)
        
        # 霸气标题
        title_label = QLabel("别乱动，刷新呢！！！")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #FF6B6B; background: transparent; padding: 0;")
        left_layout.addWidget(title_label)
        
        # 动图（变大填充）
        self.movie_label = QLabel()
        self.movie_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.movie_label.setMinimumSize(280, 280)  # 变大
        
        # 加载动图
        try:
            from pathlib import Path
            gif_path = get_gui_resource("A17.gif")
            if gif_path.exists():
                self.movie = QMovie(str(gif_path))
                # ⭐ 放大到280x280填充左侧
                self.movie.setScaledSize(QSize(280, 280))
                self.movie_label.setMovie(self.movie)
                self.movie.start()
            else:
                self.movie_label.setText("🔫")
                self.movie_label.setStyleSheet("font-size: 120px; background: transparent;")
        except Exception as e:
            logger.warning(f"加载动图失败: {e}")
            self.movie_label.setText("🔫")
            self.movie_label.setStyleSheet("font-size: 120px; background: transparent;")
        
        left_layout.addWidget(self.movie_label)
        
        # 进度区域
        progress_widget = QFrame()
        progress_widget.setStyleSheet("background: transparent;")
        progress_layout = QVBoxLayout(progress_widget)
        progress_layout.setSpacing(8)
        
        self.progress_label = QLabel(f"准备刷新 {self.total_count} 个账号...")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setStyleSheet("color: #e0e0e0; font-size: 12px; background: transparent;")
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(self.total_count)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v / %m")
        self.progress_bar.setFixedHeight(30)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #555;
                border-radius: 5px;
                text-align: center;
                background-color: #3a3a3a;
                color: white;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4CAF50, stop:1 #45a049
                );
                border-radius: 3px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        
        left_layout.addWidget(progress_widget)
        
        # ========== 右侧：信息和按钮 ==========
        right_widget = QFrame()
        right_widget.setStyleSheet("background: transparent;")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(20)
        
        # ⭐ 根据并发数显示不同提示
        concurrent_text = f"同时{self.concurrent}个"
        if self.concurrent > 2:
            concurrent_warning = f"<p style='color: #FF6B6B; font-weight: bold; font-size: 13px;'>⚠️ 并发数已设为{self.concurrent}个，可能触发限流！</p>"
        else:
            concurrent_warning = ""
        
        # 信息文本
        info_label = QLabel(
            f"<h2 style='color: #e0e0e0;'>批量刷新 {self.total_count} 个账号</h2>"
            "<p style='color: #b0b0b0; font-size: 13px;'>• 获取完整信息（金额、使用记录等）</p>"
            "<p style='color: #b0b0b0; font-size: 13px;'>• 增量刷新模式（已刷新过的会很快）⚡</p>"
            f"<p style='color: #b0b0b0; font-size: 13px;'>• 预计耗时：{self.total_count * 2} - {self.total_count * 20} 秒</p>"
            f"<p style='color: #b0b0b0; font-size: 13px;'>• 并发数：{concurrent_text}</p>"
            f"{concurrent_warning}"
            "<br>"
            "<p style='color: #FFA500; font-weight: bold; font-size: 14px;'>⚠️ 刷新期间请勿关闭程序！</p>"
        )
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        right_layout.addWidget(info_label)
        
        right_layout.addStretch()
        
        # 按钮区域
        button_layout = QVBoxLayout()
        button_layout.setSpacing(12)
        
        # 开始刷新按钮
        self.refresh_btn = QPushButton("🔫 开始刷新")
        self.refresh_btn.setMinimumHeight(55)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #999;
            }
        """)
        self.refresh_btn.clicked.connect(self.on_start_refresh)
        button_layout.addWidget(self.refresh_btn)
        
        # 关闭按钮
        self.cancel_btn = QPushButton("❌ 关闭")
        self.cancel_btn.setMinimumHeight(55)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:pressed {
                background-color: #c1170a;
            }
        """)
        self.cancel_btn.clicked.connect(self.on_cancel)
        button_layout.addWidget(self.cancel_btn)
        
        right_layout.addLayout(button_layout)
        
        # 添加到主布局
        main_layout.addWidget(left_widget, 2)  # 左侧占2份
        main_layout.addWidget(right_widget, 3)  # 右侧占3份
        
        self.setLayout(main_layout)
    
    def on_start_refresh(self):
        """开始刷新"""
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("🔄 刷新中...")
        self.cancel_btn.setEnabled(False)
        self.start_refresh_signal.emit()
        # ⭐ 不要关闭对话框，保持打开显示进度
    
    def on_cancel(self):
        """取消/完成按钮点击"""
        # ⭐ 如果未开始刷新，关闭并显示掉落Toast
        if not self.is_completed and self.refresh_btn.isEnabled():
            # 先关闭对话框
            self.accept()
            
            # ⭐ 然后显示掉落Toast（无声警告）
            from gui.widgets.drop_toast import show_drop_toast
            show_drop_toast("你不刷新，你点开干什么！枪毙！", self.parent())
        elif self.is_completed:
            # ⭐ 已完成，播放掉落动画后关闭
            self.play_closing_animation()
        else:
            # 正在刷新中，显示Toast警告
            from gui.widgets.drop_toast import show_drop_toast
            show_drop_toast("刷新进行中，不许关闭！！！\n老实等着！", self.parent())
    
    def update_progress(self, current: int, status_text: str = ""):
        """更新进度"""
        self.current_count = current
        self.progress_bar.setValue(current)
        if status_text:
            self.progress_label.setText(status_text)
        else:
            self.progress_label.setText(f"正在刷新: {current}/{self.total_count}")
        
        # ⭐ 如果完成了，更新按钮状态
        if current >= self.total_count:
            self.set_completed()
    
    def set_completed(self):
        """设置为完成状态"""
        try:
            # ⭐ 标记为已完成
            self.is_completed = True
            
            # 更新按钮为完成状态
            self.refresh_btn.setText("✅ 刷新完成")
            self.refresh_btn.setEnabled(False)
            
            # 启用关闭按钮，允许用户手动关闭
            self.cancel_btn.setEnabled(True)
            self.cancel_btn.setText("✅ 完成")
            
            # 停止动图
            if hasattr(self, 'movie') and self.movie:
                self.movie.stop()
            
            logger.debug("批量刷新对话框已设置为完成状态")
        except Exception as e:
            logger.error(f"设置完成状态失败: {e}")
    
    def play_closing_animation(self):
        """播放关闭掉落动画（自由掉落效果）"""
        try:
            # ⭐ 标记正在播放关闭动画
            self._is_closing_animation = True
            
            # 获取当前位置和屏幕高度
            current_geometry = self.geometry()
            screen_height = self.screen().size().height()
            
            # 计算掉落的目标位置（屏幕底部以下）
            target_y = screen_height + 100
            target_geometry = QRect(
                current_geometry.x(),
                target_y,
                current_geometry.width(),
                current_geometry.height()
            )
            
            # ⭐ 创建位置动画（自由掉落）
            self.drop_animation = QPropertyAnimation(self, b"geometry")
            self.drop_animation.setDuration(800)  # 0.8秒掉落时间
            self.drop_animation.setStartValue(current_geometry)
            self.drop_animation.setEndValue(target_geometry)
            self.drop_animation.setEasingCurve(QEasingCurve.Type.InQuad)  # 加速掉落（自由落体）
            
            # ⭐ 创建透明度动画（同时淡出）
            self.opacity_effect = QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(self.opacity_effect)
            
            self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
            self.fade_animation.setDuration(800)
            self.fade_animation.setStartValue(1.0)
            self.fade_animation.setEndValue(0.0)
            self.fade_animation.setEasingCurve(QEasingCurve.Type.InQuad)
            
            # ⭐ 动画完成后真正关闭对话框
            self.drop_animation.finished.connect(self._really_close)
            
            # 启动动画
            self.drop_animation.start()
            self.fade_animation.start()
            
            logger.debug("开始播放掉落关闭动画")
            
        except Exception as e:
            logger.error(f"播放关闭动画失败: {e}")
            # 如果动画失败，直接关闭
            self._really_close()
    
    def _really_close(self):
        """真正关闭对话框（动画完成后）"""
        try:
            # 清理动画对象
            if hasattr(self, 'drop_animation'):
                self.drop_animation.deleteLater()
            if hasattr(self, 'fade_animation'):
                self.fade_animation.deleteLater()
            
            # 调用父类的关闭方法
            super().accept()
            
        except Exception as e:
            logger.error(f"关闭对话框失败: {e}")
    
    def closeEvent(self, event):
        """关闭事件（根据状态决定行为）"""
        # ⭐ 如果正在播放关闭动画，允许关闭
        if self._is_closing_animation:
            event.accept()
            return
        
        # ⭐ 如果已完成，播放掉落动画后关闭
        if self.is_completed:
            event.ignore()  # 先阻止关闭
            self.play_closing_animation()  # 播放动画，动画完成后会真正关闭
            return
        
        # 如果正在刷新，阻止关闭
        if self.refresh_btn.isEnabled() == False and not self.is_completed:
            event.ignore()
            # 显示Toast警告
            from gui.widgets.drop_toast import show_drop_toast
            show_drop_toast("刷新进行中，不许关闭！！！\n老实等着！", self.parent())
        else:
            # ⭐ 未开始刷新就关闭，显示掉落Toast
            event.accept()  # 允许关闭
            # 关闭后显示Toast
            from gui.widgets.drop_toast import show_drop_toast
            show_drop_toast("你不刷新，你点开干什么！枪毙！", self.parent())
