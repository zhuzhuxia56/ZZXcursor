#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aug账号批量注册对话框
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QProgressBar, QTextEdit, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.logger import get_logger

logger = get_logger("aug_batch_register")


class AugRegisterWorker(QThread):
    """Aug账号注册工作线程"""
    
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(int, int)  # 成功数, 失败数
    
    def __init__(self, count: int, parent=None):
        super().__init__(parent)
        self.count = count
        self.is_running = True
        self.success_count = 0
        self.fail_count = 0
    
    def stop(self):
        """停止注册"""
        self.is_running = False
    
    def run(self):
        """执行批量注册"""
        self.log_signal.emit(f"开始批量注册 {self.count} 个Aug账号...\n")
        
        for i in range(self.count):
            if not self.is_running:
                self.log_signal.emit("\n⏸️ 用户停止注册")
                break
            
            try:
                self.log_signal.emit(f"\n{'='*60}")
                self.log_signal.emit(f"注册第 {i+1}/{self.count} 个账号")
                self.log_signal.emit(f"{'='*60}")
                
                # 步骤1: 生成指纹浏览器
                self.log_signal.emit("\n步骤1: 生成指纹浏览器...")
                success = self._create_fingerprint_browser()
                
                if success:
                    self.log_signal.emit("✅ 指纹浏览器生成成功")
                    
                    # 步骤2: 执行注册（待实现）
                    self.log_signal.emit("\n步骤2: 执行Aug账号注册...")
                    self.log_signal.emit("⚠️ 注册功能开发中...")
                    
                    self.success_count += 1
                else:
                    self.log_signal.emit("❌ 指纹浏览器生成失败")
                    self.fail_count += 1
                
                # 更新进度
                progress = int(((i + 1) / self.count) * 100)
                self.progress_signal.emit(progress)
                
                # 延时
                if i < self.count - 1 and self.is_running:
                    self.log_signal.emit("\n等待 2 秒后继续...")
                    import time
                    time.sleep(2)
                    
            except Exception as e:
                logger.error(f"注册第 {i+1} 个账号失败: {e}")
                self.log_signal.emit(f"\n❌ 注册失败: {e}")
                self.fail_count += 1
        
        # 完成
        self.finished_signal.emit(self.success_count, self.fail_count)
    
    def _create_fingerprint_browser(self):
        """生成指纹浏览器"""
        try:
            from core.browser_manager import BrowserManager
            from core.machine_id_generator import generate_machine_info
            import tempfile
            
            # 生成设备指纹
            machine_info = generate_machine_info()
            self.log_signal.emit(f"  设备指纹: {machine_info.get('telemetry.machineId', 'N/A')[:30]}...")
            
            # 创建用户数据目录
            temp_dir = tempfile.mkdtemp(prefix="aug_browser_")
            self.log_signal.emit(f"  数据目录: {temp_dir}")
            
            # 初始化浏览器
            browser_manager = BrowserManager()
            browser = browser_manager.init_browser(
                incognito=False,
                headless=False,
                user_data_dir=temp_dir
            )
            
            self.log_signal.emit(f"  ✅ 浏览器已打开")
            
            # TODO: 保存浏览器实例用于后续注册
            
            return True
            
        except Exception as e:
            logger.error(f"生成指纹浏览器失败: {e}")
            self.log_signal.emit(f"  ❌ 失败: {e}")
            return False


class AugBatchRegisterDialog(QDialog):
    """Aug账号批量注册对话框"""
    
    registration_completed = pyqtSignal(int)  # 发送成功数量
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("Aug账号批量注册")
        self.setMinimumSize(700, 500)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel("📝 Aug账号批量注册")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # 设置区域
        settings_row = QHBoxLayout()
        
        settings_row.addWidget(QLabel("注册数量:"))
        
        self.count_spin = QSpinBox()
        self.count_spin.setMinimum(1)
        self.count_spin.setMaximum(100)
        self.count_spin.setValue(5)
        self.count_spin.setSuffix(" 个")
        settings_row.addWidget(self.count_spin)
        
        settings_row.addStretch()
        layout.addLayout(settings_row)
        
        # 说明
        info_label = QLabel(
            "💡 批量注册流程：\n"
            "1. 生成指纹浏览器（每个账号独立指纹）\n"
            "2. 访问Aug注册页面\n"
            "3. 填写注册信息\n"
            "4. 验证邮箱\n"
            "5. 保存账号信息"
        )
        info_label.setStyleSheet("""
            background-color: rgba(52, 152, 219, 0.1);
            border: 1px solid #3498db;
            border-radius: 5px;
            padding: 10px;
            color: #2c3e50;
        """)
        layout.addWidget(info_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # 日志显示
        log_label = QLabel("注册日志:")
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setMinimumHeight(250)
        layout.addWidget(log_label)
        layout.addWidget(self.log_text)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("开始注册")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 8px 20px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        self.start_btn.clicked.connect(self._on_start)
        
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 8px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.stop_btn.clicked.connect(self._on_stop)
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)
        
        button_layout.addStretch()
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def _on_start(self):
        """开始注册"""
        count = self.count_spin.value()
        
        # 禁用控件
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.count_spin.setEnabled(False)
        
        # 清空日志
        self.log_text.clear()
        
        # 创建并启动工作线程
        self.worker = AugRegisterWorker(count)
        self.worker.log_signal.connect(self._append_log)
        self.worker.progress_signal.connect(self.progress_bar.setValue)
        self.worker.finished_signal.connect(self._on_finished)
        
        self.worker.start()
    
    def _on_stop(self):
        """停止注册"""
        if self.worker:
            self.worker.stop()
            self.stop_btn.setEnabled(False)
    
    def _on_finished(self, success, fail):
        """注册完成"""
        self.progress_bar.setValue(100)
        
        self._append_log("\n" + "="*60)
        self._append_log("✅ 批量注册完成！")
        self._append_log(f"成功: {success} 个")
        self._append_log(f"失败: {fail} 个")
        self._append_log("="*60)
        
        # 恢复控件
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.count_spin.setEnabled(True)
        
        # 显示完成对话框
        QMessageBox.information(
            self,
            "注册完成",
            f"批量注册完成！\n\n"
            f"✅ 成功: {success} 个\n"
            f"❌ 失败: {fail} 个"
        )
        
        # 发送完成信号
        if success > 0:
            self.registration_completed.emit(success)
    
    def _append_log(self, message):
        """添加日志"""
        self.log_text.append(message)
        # 自动滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

