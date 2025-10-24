#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动注册对话框
自动注册 Cursor 账号
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QSpinBox, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

import sys
import time
import json
from pathlib import Path

# 确保可以导入 core 模块
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.auto_register import CursorAutoRegister
from core.email_generator import EmailGenerator
from utils.logger import get_logger
from utils.app_paths import get_config_file

logger = get_logger("auto_register_dialog")


class RegisterWorker(QThread):
    """注册工作线程"""
    
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(int, int)  # 成功数, 失败数
    
    def __init__(self, count: int, parent=None):
        super().__init__(parent)
        self.count = count
        self.is_running = True
        self.success_count = 0
        self.fail_count = 0
        self.current_register = None  # ⭐ 保存当前的注册实例
    
    def stop(self):
        """停止注册（立即关闭浏览器）"""
        logger.info("收到停止信号...")
        self.is_running = False
        
        # ⭐ 立即强制关闭浏览器，不管什么步骤
        if self.current_register:
            try:
                # 先尝试优雅关闭
                if hasattr(self.current_register, 'browser_manager') and self.current_register.browser_manager:
                    logger.info("正在关闭浏览器...")
                    self.current_register.browser_manager.quit()
                    logger.info("✅ 浏览器已关闭")
            except Exception as e:
                logger.warning(f"关闭浏览器时出错: {e}")
        
        # 终止线程
        logger.info("请求终止线程...")
        self.quit()  # 请求线程退出
        
        # 等待线程结束（最多2秒）
        if not self.wait(2000):
            logger.warning("线程未能及时结束，强制终止")
            self.terminate()  # 强制终止
            self.wait(500)
    
    def run(self):
        """执行注册"""
        try:
            self.log_signal.emit("=" * 60)
            self.log_signal.emit("[START] 开始自动注册流程")
            self.log_signal.emit(f"目标: {self.count} 个账号")
            self.log_signal.emit("=" * 60)
            
            # 加载配置（使用用户目录）
            config_path = get_config_file()
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            email_config = config.get('email', {})
            receiving_email = email_config.get('receiving_email')
            receiving_pin = email_config.get('receiving_email_pin')
            domain = email_config.get('domain')
            
            if not all([receiving_email, receiving_pin, domain]):
                self.log_signal.emit("[ERROR] 邮箱配置缺失！")
                self.log_signal.emit("")
                self.log_signal.emit("请先进行邮箱配置：")
                self.log_signal.emit("1. 点击顶部的【邮箱配置】标签页")
                self.log_signal.emit("2. 填写以下信息：")
                self.log_signal.emit("   - 域名（例如：sharklasers.com）")
                self.log_signal.emit("   - 接收邮箱（例如：xxx@fexpost.com）")
                self.log_signal.emit("   - PIN码（例如：123456）")
                self.log_signal.emit("3. 点击【保存配置】")
                self.log_signal.emit("4. 返回账号管理页面，重新点击【自动注册】")
                self.log_signal.emit("")
                self.log_signal.emit("提示：访问 tempmail.plus 可以免费获取邮箱和PIN码")
                self.finished_signal.emit(0, 0)
                return
            
            # 初始化邮箱生成器
            email_gen = EmailGenerator(domain)
            
            for i in range(self.count):
                if not self.is_running:
                    self.log_signal.emit("\n[STOP] 用户中止注册")
                    break
                
                self.log_signal.emit(f"\n{'='*60}")
                self.log_signal.emit(f"[{i+1}/{self.count}] 开始注册第 {i+1} 个账号")
                self.log_signal.emit(f"{'='*60}")
                
                # 生成随机邮箱
                email = email_gen.generate_random_email(prefix="zzx", length=8)
                self.log_signal.emit(f"[INFO] 生成邮箱: {email}")
                
                # 注册（传递完整配置）
                success, result_message = self._register_one(email, config)
                
                if success:
                    self.success_count += 1
                    self.log_signal.emit(f"[SUCCESS] ✅ 第 {i+1} 个账号注册成功！")
                else:
                    self.fail_count += 1
                    self.log_signal.emit(f"[FAILED] ❌ 第 {i+1} 个账号注册失败")
                    
                    # ⭐ 检查是否是限制失败（今日额度用完）
                    if result_message and ("今日额度已用完" in result_message or "未激活" in result_message):
                        self.log_signal.emit("\n" + "=" * 60)
                        self.log_signal.emit(f"[LIMIT] 🚫 {result_message}")
                        self.log_signal.emit("[LIMIT] 今日注册已达上限，流程自动终止")
                        self.log_signal.emit("[HINT] 💡 请前往 [设置] 页面激活设备以解除限制")
                        self.log_signal.emit("=" * 60)
                        break  # 立即停止循环
                    
                    # ⭐ 检查是否是浏览器关闭
                    if result_message and "浏览器已关闭" in result_message:
                        self.log_signal.emit("\n" + "=" * 60)
                        self.log_signal.emit(f"[BROWSER] 🚫 {result_message}")
                        self.log_signal.emit("[BROWSER] 浏览器已被手动关闭，注册流程已终止")
                        self.log_signal.emit("[INFO] 💡 已成功注册的账号已保存")
                        self.log_signal.emit("=" * 60)
                        break  # 立即停止循环
                
                progress = int((i + 1) / self.count * 100)
                self.progress_signal.emit(progress)
                
                # 等待间隔
                if i < self.count - 1:
                    self.log_signal.emit("[WAIT] 等待 3 秒...")  # ⚡ 优化：5秒→3秒
                    time.sleep(3)
            
            # 完成
            self.log_signal.emit("\n" + "=" * 60)
            self.log_signal.emit("[DONE] 注册流程完成！")
            self.log_signal.emit(f"成功: {self.success_count} 个")
            self.log_signal.emit(f"失败: {self.fail_count} 个")
            self.log_signal.emit("=" * 60)
            
            self.finished_signal.emit(self.success_count, self.fail_count)
            
        except Exception as e:
            logger.error(f"注册线程异常: {e}")
            self.log_signal.emit(f"\n[ERROR] 注册过程出错: {e}")
            self.finished_signal.emit(self.success_count, self.fail_count)
    
    def _register_one(self, email: str, config: dict) -> tuple:
        """
        注册单个账号
        
        Returns:
            tuple: (是否成功, 错误消息)
        """
        try:
            # 定义进度回调
            def progress_callback(message, percent):
                self.log_signal.emit(f"[{percent}%] {message}")
                self.progress_signal.emit(percent)
            
            register = CursorAutoRegister()
            self.current_register = register  # ⭐ 保存实例供停止时使用
            
            result = register.register_account(email, config, progress_callback, check_limit=True)
            
            success = result.get('success', False)
            message = result.get('message', '')
            has_payment_warning = result.get('has_payment_warning', False)
            
            # ⭐ 智能关闭浏览器：无支付警告时关闭，有警告时保留
            if success and not has_payment_warning:
                # 绑卡成功且无警告，关闭浏览器
                try:
                    register.close()
                    self.log_signal.emit("[INFO] ✅ 绑卡成功，浏览器已关闭")
                except:
                    pass
            elif success and has_payment_warning:
                # 有支付警告，保留浏览器供用户查看
                self.log_signal.emit("[WARN] ⚠️ 检测到支付警告，浏览器保持打开供您查看")
                self.log_signal.emit("[INFO] 💡 请在浏览器中检查Dashboard页面的警告信息")
            
            self.current_register = None  # ⭐ 清除实例
            
            return (success, message)
        except Exception as e:
            logger.error(f"注册失败: {e}")
            self.log_signal.emit(f"[ERROR] {e}")
            self.current_register = None
            return (False, str(e))


class AutoRegisterDialog(QDialog):
    """自动注册对话框"""
    
    registration_completed = pyqtSignal(int)  # 发送成功数量
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.init_ui()
        # ⚡ 对话框显示时刷新配置状态
        self._update_payment_status()
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # ⭐ 关闭窗口时停止注册线程并关闭浏览器
        if self.worker and self.worker.isRunning():
            self._append_log("\n[CLOSE] 🛑 窗口关闭，正在停止注册...")
            
            # 停止worker线程
            self.worker.stop()
            
            # ⚡ 立即关闭浏览器（防止后台继续运行）
            try:
                if self.worker.current_register:
                    self._append_log("[CLOSE] 正在关闭浏览器...")
                    self.worker.current_register.close()
                    self._append_log("[CLOSE] ✅ 浏览器已关闭")
            except Exception as e:
                logger.debug(f"关闭浏览器失败: {e}")
            
            # 等待线程结束
            if not self.worker.wait(2000):
                self._append_log("[CLOSE] 强制终止线程...")
                self.worker.terminate()
                self.worker.wait()
            
            self._append_log("[CLOSE] ✅ 注册已停止")
        
        # 接受关闭事件
        event.accept()
    
    def showEvent(self, event):
        """对话框显示时触发 - 刷新配置状态"""
        super().showEvent(event)
        # ⚡ 每次显示对话框时刷新绑卡配置状态
        self._update_payment_status()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("自动注册")
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("自动注册 Cursor 账号")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # 数量选择
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("注册数量:"))
        self.count_spin = QSpinBox()
        self.count_spin.setMinimum(1)
        self.count_spin.setMaximum(100)
        self.count_spin.setValue(1)
        self.count_spin.setSuffix(" 个账号")
        self.count_spin.valueChanged.connect(self._on_count_changed)  # ⭐ 监听数量变化
        count_layout.addWidget(self.count_spin)
        count_layout.addStretch()
        layout.addLayout(count_layout)
        
        # ⭐ 数量警告标签（当超过限制时显示）
        self.count_warning_label = QLabel("")
        self.count_warning_label.setStyleSheet("color: #e74c3c; font-size: 11px; padding-left: 80px;")
        self.count_warning_label.setVisible(False)
        layout.addWidget(self.count_warning_label)
        
        # 手机验证状态显示
        phone_status_layout = QHBoxLayout()
        phone_status_layout.addWidget(QLabel("📱 自动过手机号:"))
        
        self.phone_status_label = QLabel()
        self._update_phone_status()
        phone_status_layout.addWidget(self.phone_status_label)
        
        phone_status_layout.addStretch()
        layout.addLayout(phone_status_layout)
        
        # 绑卡状态显示
        payment_status_layout = QHBoxLayout()
        payment_status_layout.addWidget(QLabel("💳 自动绑卡:"))
        
        self.payment_status_label = QLabel()
        self._update_payment_status()
        payment_status_layout.addWidget(self.payment_status_label)
        
        payment_status_layout.addStretch()
        layout.addLayout(payment_status_layout)
        
        # ⭐ 激活状态显示
        activation_status_layout = QHBoxLayout()
        activation_status_layout.addWidget(QLabel("🎫 设备激活:"))
        
        self.activation_status_label = QLabel()
        self._update_activation_status()
        activation_status_layout.addWidget(self.activation_status_label)
        
        activation_status_layout.addStretch()
        layout.addLayout(activation_status_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # 日志显示
        log_label = QLabel("注册日志:")
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
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
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.stop_btn.clicked.connect(self._on_stop)
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)
        
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def _update_phone_status(self):
        """更新手机验证状态显示"""
        try:
            config_path = get_config_file()
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            phone_config = config.get('phone_verification', {})
            enabled = phone_config.get('enabled', False)
            
            if enabled:
                self.phone_status_label.setText("✅ 已配置")
                self.phone_status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
            else:
                self.phone_status_label.setText("❌ 未配置")
                self.phone_status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        except:
            self.phone_status_label.setText("❌ 未配置")
            self.phone_status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
    
    def _on_count_changed(self, value):
        """注册数量改变时检查限制"""
        try:
            from core.activation_manager import get_activation_manager
            activation_mgr = get_activation_manager()
            
            # 如果已激活，无需检查
            if activation_mgr.is_activated():
                self.count_warning_label.setVisible(False)
                return
            
            # 获取剩余额度
            today_used = activation_mgr.get_today_registered_count()
            daily_limit = activation_mgr.get_daily_limit()
            remaining = daily_limit - today_used
            
            # 检查输入数量是否超过剩余额度
            if value > remaining:
                # 超过限制，显示警告
                self.count_warning_label.setText(
                    f"⚠️ 超过今日剩余额度！当前剩余：{remaining} 个，需要激活才能注册更多账号"
                )
                self.count_warning_label.setVisible(True)
                # ⭐ 开始按钮显示警告样式
                self.start_btn.setProperty("danger", True)
                self.start_btn.setStyleSheet("")
                self.start_btn.style().unpolish(self.start_btn)
                self.start_btn.style().polish(self.start_btn)
            else:
                # 在限制内，隐藏警告
                self.count_warning_label.setVisible(False)
                # 恢复正常样式
                self.start_btn.setProperty("danger", False)
                self.start_btn.setStyleSheet("")
                self.start_btn.style().unpolish(self.start_btn)
                self.start_btn.style().polish(self.start_btn)
        except Exception as e:
            logger.debug(f"检查数量限制失败: {e}")
    
    def _update_activation_status(self):
        """更新激活状态显示"""
        try:
            from core.activation_manager import get_activation_manager
            
            activation_mgr = get_activation_manager()
            
            if activation_mgr.is_activated():
                self.activation_status_label.setText("✅ 已激活（无限制）")
                self.activation_status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
            else:
                today_used = activation_mgr.get_today_registered_count()
                daily_limit = activation_mgr.get_daily_limit()
                remaining = daily_limit - today_used
                
                if remaining > 0:
                    self.activation_status_label.setText(f"❌ 未激活（今日剩余：{remaining}/{daily_limit}）")
                    self.activation_status_label.setStyleSheet("color: #ffa500; font-weight: bold;")
                else:
                    self.activation_status_label.setText(f"🚫 今日额度已用完（{daily_limit}/{daily_limit}）")
                    self.activation_status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
            
            # ⭐ 更新后触发一次数量检查
            self._on_count_changed(self.count_spin.value())
        except:
            self.activation_status_label.setText("❌ 未知")
            self.activation_status_label.setStyleSheet("color: #95a5a6; font-weight: bold;")
    
    def _update_payment_status(self):
        """更新绑卡状态显示"""
        try:
            config_path = get_config_file()
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            payment_config = config.get('payment_binding', {})
            enabled = payment_config.get('enabled', False)
            
            if enabled:
                # 检查卡号配置
                card_mode = payment_config.get('card_mode', 'import')
                imported_cards = payment_config.get('imported_cards', [])
                
                # 如果是导入模式且卡号为空，显示未配置
                if card_mode == 'import' and len(imported_cards) == 0:
                    self.payment_status_label.setText("❌ 未配置")
                    self.payment_status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
                else:
                    self.payment_status_label.setText("✅ 已启用")
                    self.payment_status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
            else:
                self.payment_status_label.setText("❌ 未启用")
                self.payment_status_label.setStyleSheet("color: #95a5a6; font-weight: bold;")
        except:
            self.payment_status_label.setText("❌ 未配置")
            self.payment_status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
    
    def _on_start(self):
        """开始注册"""
        # ⭐ 先检查激活限制
        try:
            from core.activation_manager import get_activation_manager
            activation_mgr = get_activation_manager()
            
            can_register, remaining, limit_msg = activation_mgr.can_register()
            
            if not can_register:
                QMessageBox.warning(
                    self,
                    "今日额度已用完",
                    f"🚫 {limit_msg}\n\n"
                    f"💡 解决方案：\n"
                    f"1. 前往 [设置] 页面激活设备\n"
                    f"2. 激活后可每天无限次注册\n"
                    f"3. 或等待明天自动重置额度"
                )
                return
        except Exception as e:
            logger.error(f"检查激活限制失败: {e}")
        
        count = self.count_spin.value()
        
        reply = QMessageBox.question(
            self,
            "确认",
            f"确定要开始注册吗？\n\n注册数量: {count} 个账号",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 禁用控件
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.count_spin.setEnabled(False)
        
        # 清空日志
        self.log_text.clear()
        self.progress_bar.setValue(0)
        
        # 创建并启动工作线程
        self.worker = RegisterWorker(count)
        self.worker.log_signal.connect(self._append_log)
        self.worker.progress_signal.connect(self._update_progress)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.start()
    
    def _on_stop(self):
        """停止注册（立即关闭浏览器，强制终止）"""
        if self.worker and self.worker.isRunning():
            self._append_log("\n[STOP] 🛑 立即停止注册...")
            
            # ⭐ 立即停止并关闭浏览器
            self.worker.stop()
            
            # ⭐ 不等待，直接强制终止线程（1秒超时）
            if not self.worker.wait(1000):
                self.worker.terminate()
                self.worker.wait()
            
            self._append_log("[STOP] ✅ 已停止")
            
            # 恢复按钮状态
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.count_spin.setEnabled(True)
    
    def _append_log(self, message: str):
        """添加日志"""
        self.log_text.append(message)
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _update_progress(self, value: int):
        """更新进度"""
        self.progress_bar.setValue(value)
    
    def _on_finished(self, success: int, failed: int):
        """注册完成"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.count_spin.setEnabled(True)
        
        # 通知主窗口刷新
        if success > 0:
            self.registration_completed.emit(success)
        
        # 显示结果
        QMessageBox.information(
            self,
            "注册完成",
            f"注册流程已完成！\n\n"
            f"成功: {success} 个\n"
            f"失败: {failed} 个"
        )

