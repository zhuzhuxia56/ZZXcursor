#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量绑卡对话框
对选中的账号批量执行绑卡操作
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QGroupBox, QCheckBox, QMessageBox,
    QApplication
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from datetime import datetime
import time
import tempfile
import traceback

from core.browser_manager import BrowserManager
from core.payment_handler import PaymentHandler
from utils.logger import get_logger

logger = get_logger("batch_payment")


class PaymentWorker(QThread):
    """批量绑卡工作线程"""
    
    # 信号
    progress_updated = pyqtSignal(int, int)  # 当前索引, 总数
    log_message = pyqtSignal(str)
    status_updated = pyqtSignal(int, int, int)  # 成功, 警告, 失败
    account_processed = pyqtSignal(str, bool, bool)  # 邮箱, 是否成功, 是否有警告
    finished_all = pyqtSignal()
    
    def __init__(self, accounts, settings):
        super().__init__()
        self.accounts = accounts
        self.settings = settings
        self.is_running = True
        self.warning_browsers = []  # 保存有警告的浏览器
        self.current_browser = None  # 当前正在使用的浏览器
        
        # 统计
        self.success_count = 0
        self.warning_count = 0
        self.fail_count = 0
        
    def run(self):
        """执行批量绑卡"""
        total = len(self.accounts)
        from core.account_storage import get_storage
        storage = get_storage()
        
        for index, account in enumerate(self.accounts, 1):
            if not self.is_running:
                break
            
            # 更新进度
            self.progress_updated.emit(index, total)
            
            # 检查是否跳过
            if self.settings['skip_bound'] and account.get('payment_bound'):
                self.log(f"⏭ 跳过已绑卡: {account['email']}")
                continue
            
            # 检查Token
            if not account.get('session_token'):
                self.log(f"⚠️ 跳过无Token: {account['email']}")
                self.fail_count += 1
                continue
            
            self.log(f"\n{'='*60}")
            self.log(f"处理账号 {index}/{total}: {account['email']}")
            self.log(f"{'='*60}")
            
            browser = None
            try:
                # 1. 创建浏览器并登录
                browser = self._create_browser_with_token(account)
                self.current_browser = browser  # 记录当前浏览器
                
                # 2. 执行绑卡
                success, has_warning = self._bind_payment_for_account(browser, account)
                
                # 3. 根据结果处理浏览器
                if has_warning:
                    self._handle_warning_browser(browser, account)
                    self.warning_count += 1
                elif success:
                    self._handle_success_browser(browser, account)
                    self.success_count += 1
                    
                    # 更新账号信息
                    account['payment_bound'] = True
                    account['payment_date'] = datetime.now().isoformat()
                    storage.update_account(account['email'], account)
                else:
                    self._close_browser_safely(browser)
                    self.fail_count += 1
                
                # 发送处理结果
                self.account_processed.emit(account['email'], success, has_warning)
                
            except Exception as e:
                self.log(f"❌ {account['email']} 处理失败: {e}")
                logger.error(f"批量绑卡失败: {e}", exc_info=True)
                self._close_browser_safely(browser)
                self.fail_count += 1
            finally:
                # 清空当前浏览器引用
                self.current_browser = None
            
            # 更新统计
            self.status_updated.emit(self.success_count, self.warning_count, self.fail_count)
            
            # 延时避免操作过快
            if index < total and self.is_running:
                self.log("等待 5 秒后处理下一个账号...")
                for i in range(5):
                    if not self.is_running:
                        break
                    time.sleep(1)
        
        self.finished_all.emit()
    
    def _create_browser_with_token(self, account):
        """创建带有SessionToken的浏览器"""
        self.log(f"创建浏览器实例...")
        
        # 创建独立的用户数据目录（指纹隔离）
        email_prefix = account['email'].split('@')[0]
        temp_dir = tempfile.mkdtemp(prefix=f"cursor_bind_{email_prefix}_")
        self.log(f"  用户数据目录: {temp_dir}")
        
        # 初始化浏览器
        browser_manager = BrowserManager()
        browser = browser_manager.init_browser(
            incognito=True,  # 无痕模式
            headless=False,  # 需要可见
            user_data_dir=temp_dir
        )
        
        tab = browser.latest_tab
        
        try:
            # 解密SessionToken
            self.log("准备 SessionToken...")
            session_token = account['session_token']
            
            from utils.crypto import get_crypto_manager
            crypto = get_crypto_manager()
            try:
                decrypted_token = crypto.decrypt(session_token)
                if decrypted_token:
                    session_token = decrypted_token
                    self.log(f"  Token已解密: {session_token[:20]}...")
                else:
                    self.log("  Token解密失败，使用原始值")
            except Exception as e:
                self.log(f"  Token解密异常: {e}，使用原始值")
            
            # 1. 先访问cursor.com建立会话
            self.log("访问 Cursor 主页建立会话...")
            tab.get("https://www.cursor.com")
            time.sleep(1)
            
            # 2. 使用DrissionPage API设置SessionToken
            self.log("设置 SessionToken...")
            cookie_data = {
                'name': 'WorkosCursorSessionToken',
                'value': session_token,
                'domain': '.cursor.com',
                'path': '/',
                'secure': True,
                'httpOnly': False,
                'sameSite': 'None'
            }
            
            try:
                # 设置Cookie（使用DrissionPage API）
                tab.set.cookies(cookie_data)
                self.log(f"✅ SessionToken 已通过 API 设置到 Cookie")
                
                # 验证Cookie
                cookies = tab.cookies()
                found = False
                for c in cookies:
                    if c.get('name') == 'WorkosCursorSessionToken':
                        found = True
                        self.log(f"✅ Cookie 验证成功: {c.get('value')[:30]}...")
                        break
                
                if not found:
                    self.log(f"⚠️ Cookie 未找到，尝试备用方法...")
                    # 备用：使用 JavaScript 设置
                    cookie_value = session_token.replace('"', '\\"')
                    cookie_js = f"document.cookie = 'WorkosCursorSessionToken={cookie_value}; path=/; domain=.cursor.com; Secure';"
                    tab.run_js(cookie_js)
                    
            except Exception as e:
                self.log(f"设置 Cookie API 失败: {e}，尝试JS方法...")
                cookie_value = session_token.replace('"', '\\"')
                cookie_js = f"document.cookie = 'WorkosCursorSessionToken={cookie_value}; path=/; domain=.cursor.com';"
                tab.run_js(cookie_js)
            
            # 3. 验证登录状态（访问简单页面即可）
            self.log("验证登录状态...")
            tab.get("https://cursor.com/")
            time.sleep(2)
            
            current_url = tab.url
            self.log(f"当前页面: {current_url}")
            
            # 如果被重定向到认证页面，说明登录失败
            if "authenticator" in current_url or "sign-in" in current_url or "login" in current_url:
                raise Exception(f"Token无效或过期，无法登录")
            
            self.log(f"✅ 登录成功: {account['email']}")
            
            # ⭐ 批量绑卡不需要处理 Data Sharing（账号已登录过）
            # Data Sharing 只在新注册账号第一次登录时出现
            
            return browser
            
        except Exception as e:
            self.log(f"❌ 登录失败: {e}")
            browser.quit()
            raise
    
    def _bind_payment_for_account(self, browser, account):
        """对单个账号执行绑卡"""
        tab = browser.latest_tab
        
        try:
            # ⭐ 优化：直接获取并访问绑卡页面（API 会自动处理）
            self.log("获取 Stripe 绑卡页面...")
            if not PaymentHandler.click_start_trial_button(tab):
                self.log(f"⚠️ 无法获取绑卡页面（可能已绑卡或已使用试用）")
                return (False, False)
            
            # 3. 填写Stripe支付信息（复用现有方法，返回元组）
            self.log("填写支付信息...")
            result = PaymentHandler.fill_stripe_payment(tab, browser)
            
            # 处理返回值（可能是元组或bool）
            if isinstance(result, tuple):
                success, has_warning = result
                
                if has_warning:
                    self.log(f"⚠️ 绑卡完成但有支付警告")
                    self.log("⚠️ Your payment method is not eligible for a free trial")
                    self.log("⚠️ 保持浏览器打开供手动处理")
                elif success:
                    self.log(f"✅ 绑卡成功，无警告")
                else:
                    self.log(f"❌ 绑卡失败")
                
                return (success, has_warning)
            else:
                # 兼容旧版返回
                if result:
                    self.log(f"✅ 绑卡成功")
                    return (True, False)
                else:
                    self.log(f"❌ 绑卡失败")
                    return (False, False)
                
        except Exception as e:
            self.log(f"❌ 绑卡流程异常: {e}")
            logger.error(f"绑卡异常: {e}", exc_info=True)
            return (False, False)
    
    def _handle_warning_browser(self, browser, account):
        """处理有警告的浏览器"""
        self.log(f"\n🔶 检测到支付警告，保持浏览器打开")
        self.log(f"   账号: {account['email']}")
        self.log(f"   请手动处理支付问题")
        
        # 记录有警告的浏览器
        self.warning_browsers.append({
            'browser': browser,
            'account': account['email'],
            'timestamp': datetime.now()
        })
        
        # 不关闭浏览器
    
    def _handle_success_browser(self, browser, account):
        """处理成功的浏览器"""
        if self.settings['auto_close']:
            self.log(f"\n✅ 绑卡成功且无警告，关闭浏览器")
            self._close_browser_safely(browser)
        else:
            self.log(f"\n✅ 绑卡成功，保持浏览器打开")
    
    def _close_browser_safely(self, browser):
        """安全关闭浏览器"""
        try:
            if browser:
                browser.quit()
                self.log("   浏览器已关闭")
        except Exception as e:
            self.log(f"   关闭浏览器时出错: {e}")
    
    def log(self, message):
        """发送日志消息"""
        self.log_message.emit(message)
        logger.info(message)
    
    def stop(self):
        """停止执行（只暂停任务，不关闭浏览器）"""
        self.is_running = False
    
    def force_stop(self):
        """强制停止执行并关闭所有浏览器"""
        self.is_running = False
        self._close_all_browsers()
    
    def _close_all_browsers(self):
        """强制关闭所有打开的浏览器"""
        closed_count = 0
        
        # 1. 关闭当前正在使用的浏览器
        if self.current_browser:
            try:
                self.log("⚠️ 正在关闭当前浏览器...")
                self.current_browser.quit()
                closed_count += 1
            except Exception as e:
                logger.error(f"关闭当前浏览器失败: {e}")
            finally:
                self.current_browser = None
        
        # 2. 关闭所有警告浏览器
        if self.warning_browsers:
            self.log(f"⚠️ 正在关闭 {len(self.warning_browsers)} 个警告浏览器...")
            for browser in self.warning_browsers:
                try:
                    browser.quit()
                    closed_count += 1
                except Exception as e:
                    logger.error(f"关闭警告浏览器失败: {e}")
            self.warning_browsers.clear()
        
        if closed_count > 0:
            self.log(f"✅ 已强制关闭 {closed_count} 个浏览器")
        else:
            self.log("ℹ️ 没有需要关闭的浏览器")


class BatchPaymentDialog(QDialog):
    """批量绑卡对话框"""
    
    def __init__(self, selected_accounts, parent=None):
        super().__init__(parent)
        self.accounts = selected_accounts
        self.worker = None
        self.start_time = None
        
        self.setWindowTitle(f"批量绑卡 - {len(selected_accounts)} 个账号")
        self.setMinimumSize(700, 600)
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # 标题
        title_label = QLabel(f"批量绑卡任务")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # 账号信息
        info_label = QLabel(f"已选择 {len(self.accounts)} 个账号进行绑卡")
        layout.addWidget(info_label)
        
        # 设置区域
        settings_group = QGroupBox("绑卡设置")
        settings_layout = QVBoxLayout()
        
        self.skip_bound_checkbox = QCheckBox("跳过已绑卡账号")
        self.skip_bound_checkbox.setChecked(True)
        
        self.auto_close_checkbox = QCheckBox("绑卡成功后自动关闭浏览器")
        self.auto_close_checkbox.setChecked(True)
        
        warning_info = QLabel("⚠️ 有支付警告的浏览器会自动保持打开")
        warning_info.setStyleSheet("color: orange; padding-left: 20px;")
        
        settings_layout.addWidget(self.skip_bound_checkbox)
        settings_layout.addWidget(self.auto_close_checkbox)
        settings_layout.addWidget(warning_info)
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)
        
        # 当前状态
        self.status_label = QLabel("准备开始...")
        layout.addWidget(self.status_label)
        
        # 统计信息
        self.stats_label = QLabel("成功: 0 | 警告: 0 | 失败: 0")
        self.stats_label.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(self.stats_label)
        
        # 日志区域
        log_group = QGroupBox("执行日志")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(250)
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("开始绑卡")
        self.start_btn.clicked.connect(self.start_binding)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        
        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self.stop_binding)
        self.stop_btn.setEnabled(False)
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)
        
        button_layout.addStretch()
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def start_binding(self):
        """开始批量绑卡"""
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.close_btn.setEnabled(False)
        
        # 清空日志
        self.log_text.clear()
        self.log("批量绑卡任务开始")
        self.log(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log("-" * 60)
        
        # 记录开始时间
        self.start_time = datetime.now()
        
        # 获取设置
        settings = {
            'skip_bound': self.skip_bound_checkbox.isChecked(),
            'auto_close': self.auto_close_checkbox.isChecked()
        }
        
        # 创建并启动工作线程
        self.worker = PaymentWorker(self.accounts, settings)
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.log_message.connect(self.log)
        self.worker.status_updated.connect(self.update_stats)
        self.worker.account_processed.connect(self.on_account_processed)
        self.worker.finished_all.connect(self.on_all_finished)
        
        self.worker.start()
    
    def stop_binding(self):
        """停止批量绑卡（只暂停任务，不关闭浏览器）"""
        if self.worker and self.worker.isRunning():
            self.log("\n⏸️ 用户暂停任务...")
            self.worker.stop()  # 只停止任务，不关闭浏览器
            self.stop_btn.setEnabled(False)
    
    def update_progress(self, current, total):
        """更新进度"""
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)
        self.status_label.setText(f"正在处理: 第 {current}/{total} 个账号")
    
    def update_stats(self, success, warning, fail):
        """更新统计"""
        self.stats_label.setText(
            f"✅ 成功: {success} | ⚠️ 警告: {warning} | ❌ 失败: {fail}"
        )
    
    def on_account_processed(self, email, success, has_warning):
        """账号处理完成"""
        if success:
            if has_warning:
                self.log(f"⚠️ {email}: 绑卡但有警告（浏览器保持打开）")
            else:
                self.log(f"✅ {email}: 绑卡成功")
        else:
            self.log(f"❌ {email}: 绑卡失败")
    
    def on_all_finished(self):
        """全部完成"""
        self.progress_bar.setValue(100)
        self.status_label.setText("任务完成")
        
        # 计算耗时
        if self.start_time:
            duration = datetime.now() - self.start_time
            minutes = int(duration.total_seconds() / 60)
            seconds = int(duration.total_seconds() % 60)
            time_str = f"{minutes}分{seconds}秒"
        else:
            time_str = "未知"
        
        # 显示完成报告
        self.log("\n" + "=" * 60)
        self.log("批量绑卡任务完成")
        self.log(f"总耗时: {time_str}")
        self.log("-" * 60)
        
        success = self.worker.success_count
        warning = self.worker.warning_count
        fail = self.worker.fail_count
        total = success + warning + fail
        
        self.log(f"处理账号总数: {total}")
        self.log(f"✅ 成功（无警告）: {success}")
        self.log(f"⚠️ 成功（有警告）: {warning}")
        self.log(f"❌ 失败: {fail}")
        
        if warning > 0:
            self.log("\n⚠️ 注意：")
            self.log(f"有 {warning} 个账号存在支付警告")
            self.log("相关浏览器已保持打开，请手动处理")
        
        self.log("=" * 60)
        
        # 启用按钮
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.close_btn.setEnabled(True)
        
        # 显示完成提示
        if warning > 0:
            QMessageBox.warning(
                self,
                "需要注意",
                f"批量绑卡完成！\n\n"
                f"成功: {success}\n"
                f"警告: {warning}\n"
                f"失败: {fail}\n\n"
                f"有 {warning} 个账号存在支付警告，\n"
                f"浏览器已保持打开，请手动处理。"
            )
        else:
            QMessageBox.information(
                self,
                "完成",
                f"批量绑卡完成！\n\n"
                f"成功: {success}\n"
                f"失败: {fail}\n\n"
                f"总耗时: {time_str}"
            )
    
    def log(self, message):
        """添加日志"""
        self.log_text.append(message)
        # 自动滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def closeEvent(self, event):
        """关闭事件"""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "确认",
                "绑卡任务正在进行中，确定要退出吗？\n将强制关闭所有浏览器！",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.log("\n⚠️ 用户强制关闭对话框，正在关闭所有浏览器...")
                self.worker.force_stop()  # 强制停止并关闭所有浏览器
                self.worker.wait(3000)  # 等待最多3秒
                event.accept()
            else:
                event.ignore()
        else:
            # 即使任务完成，也需要关闭可能残留的浏览器
            if self.worker:
                self.worker._close_all_browsers()
            event.accept()

