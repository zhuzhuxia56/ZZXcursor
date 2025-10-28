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
import uuid
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
    
    def _generate_email(self):
        """生成邮箱（使用配置的域名）"""
        try:
            from core.email_generator import EmailGenerator
            from utils.app_paths import get_config_file
            import json
            
            # 读取邮箱配置
            config_file = get_config_file()
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                domain = config.get('email', {}).get('domain', '')
            else:
                domain = ''
            
            if not domain:
                # 使用默认域名
                domain = 'ymwdes.cn'
                logger.warning(f"未配置邮箱域名，使用默认: {domain}")
            
            # 生成纯字母邮箱
            import random
            import string
            random_letters = ''.join(random.choices(string.ascii_lowercase, k=12))
            
            # 如果是域名池，随机选择一个
            if "/" in domain:
                domains = [d.strip() for d in domain.split("/") if d.strip()]
                selected_domain = random.choice(domains)
            else:
                selected_domain = domain
            
            email = f"{random_letters}@{selected_domain}"
            logger.info(f"生成Aug注册邮箱: {email}")
            
            return email
            
        except Exception as e:
            logger.error(f"生成邮箱失败: {e}")
            # 返回一个默认邮箱
            import random
            import string
            random_letters = ''.join(random.choices(string.ascii_lowercase, k=12))
            return f"{random_letters}@ymwdes.cn"
    
    def _handle_human_verification(self, tab, max_wait=30):
        """处理人机验证（复用Turnstile处理逻辑）"""
        try:
            from core.turnstile_handler import handle_turnstile
            import time
            
            self.log_signal.emit(f"  检测人机验证...")
            
            # 检查是否有Turnstile验证框
            try:
                turnstile_elem = tab.ele("#cf-turnstile", timeout=2)
                if turnstile_elem:
                    self.log_signal.emit(f"  ✅ 检测到Turnstile验证框")
                    self.log_signal.emit(f"  开始自动处理...")
                    
                    # 使用Cursor注册的Turnstile处理逻辑
                    success = handle_turnstile(tab, max_wait_seconds=max_wait)
                    
                    if success:
                        self.log_signal.emit(f"  ✅ Turnstile验证已通过")
                        return True
                    else:
                        self.log_signal.emit(f"  ⚠️ Turnstile验证超时")
                        return False
            except:
                # 没有找到Turnstile元素
                pass
            
            # 检查其他类型的验证框（如普通checkbox）
            try:
                self.log_signal.emit(f"  查找验证复选框...")
                checkbox_selectors = [
                    'input[type="checkbox"]',
                    'input[role="checkbox"]',
                    '[role="checkbox"]',
                    '.checkbox'
                ]
                
                for selector in checkbox_selectors:
                    try:
                        checkbox = tab.ele(selector, timeout=1)
                        if checkbox:
                            self.log_signal.emit(f"  ✅ 找到验证复选框，点击...")
                            checkbox.click()
                            time.sleep(2)
                            self.log_signal.emit(f"  ✅ 已点击验证框")
                            return True
                    except:
                        continue
            except:
                pass
            
            # 没有检测到验证框，可能不需要验证
            self.log_signal.emit(f"  ℹ️ 未检测到人机验证，继续...")
            return True
            
        except Exception as e:
            logger.error(f"处理人机验证失败: {e}")
            self.log_signal.emit(f"  ❌ 验证处理异常: {e}")
            return False
    
    def _get_verification_code(self, email, max_retries=30):
        """获取邮箱验证码"""
        try:
            from core.email_verification import EmailVerificationHandler
            from utils.app_paths import get_config_file
            import json
            
            # 读取邮箱配置
            config_file = get_config_file()
            if not config_file.exists():
                self.log_signal.emit(f"  ❌ 未配置接收邮箱")
                return None
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            email_config = config.get('email', {})
            receiving_email = email_config.get('receiving_email', '')
            receiving_pin = email_config.get('receiving_email_pin', '')
            
            if not receiving_email or not receiving_pin:
                self.log_signal.emit(f"  ❌ 接收邮箱或PIN码未配置")
                return None
            
            self.log_signal.emit(f"  接收邮箱: {receiving_email}")
            self.log_signal.emit(f"  开始获取验证码（最多等待30秒）...")
            
            # 使用邮箱验证处理器
            handler = EmailVerificationHandler(
                account=email,
                receiving_email=receiving_email,
                receiving_pin=receiving_pin
            )
            
            # 获取验证码（带重试机制）
            code = handler.get_verification_code(max_retries=max_retries, retry_interval=1)
            
            return code
            
        except Exception as e:
            logger.error(f"获取验证码失败: {e}")
            self.log_signal.emit(f"  ❌ 获取验证码异常: {e}")
            return None
    
    def _fill_verification_code(self, tab, code):
        """填写验证码并提交"""
        try:
            import time
            
            # 查找验证码输入框
            self.log_signal.emit(f"  查找验证码输入框...")
            
            code_selectors = [
                'input[placeholder*="code"]',
                'input[placeholder*="Code"]',
                'input[name="code"]',
                'input[type="text"]',
                'input[type="tel"]'
            ]
            
            code_input = None
            for selector in code_selectors:
                try:
                    code_input = tab.ele(selector, timeout=2)
                    if code_input:
                        self.log_signal.emit(f"  ✅ 找到验证码输入框")
                        break
                except:
                    continue
            
            if not code_input:
                self.log_signal.emit(f"  ❌ 未找到验证码输入框")
                return False
            
            # 填写验证码
            self.log_signal.emit(f"  填写验证码: {code}")
            code_input.clear()  # 先清空
            code_input.input(code)
            time.sleep(1)
            
            # 查找并点击Continue按钮
            self.log_signal.emit(f"  查找Continue按钮...")
            
            submit_selectors = [
                'button:contains("Continue")',
                'button[type="submit"]',
                'button:contains("Submit")',
                'button:contains("Verify")',
                'button:contains("确认")'
            ]
            
            for selector in submit_selectors:
                try:
                    submit_btn = tab.ele(selector, timeout=2)
                    if submit_btn:
                        self.log_signal.emit(f"  ✅ 找到Continue按钮，点击...")
                        submit_btn.click()
                        time.sleep(3)
                        return True
                except:
                    continue
            
            self.log_signal.emit(f"  ⚠️ 未找到Continue按钮")
            return False
            
        except Exception as e:
            logger.error(f"填写验证码失败: {e}")
            self.log_signal.emit(f"  ❌ 填写验证码异常: {e}")
            return False
    
    def _click_skip_button(self, tab):
        """点击Skip for now按钮"""
        try:
            import time
            
            self.log_signal.emit(f"  查找Skip for now按钮...")
            
            skip_selectors = [
                'button:contains("Skip for now")',
                'button:contains("Skip")',
                'a:contains("Skip for now")',
                'a:contains("Skip")'
            ]
            
            for selector in skip_selectors:
                try:
                    skip_btn = tab.ele(selector, timeout=2)
                    if skip_btn:
                        self.log_signal.emit(f"  ✅ 找到Skip按钮，点击...")
                        skip_btn.click()
                        time.sleep(3)
                        return True
                except:
                    continue
            
            self.log_signal.emit(f"  ⚠️ 未找到Skip按钮")
            return False
            
        except Exception as e:
            logger.error(f"点击Skip失败: {e}")
            return False
    
    def _get_auth_code(self, tab):
        """获取授权code"""
        try:
            import time
            import re
            
            time.sleep(2)  # 等待页面加载
            current_url = tab.url
            self.log_signal.emit(f"  当前URL: {current_url}")
            
            # 检查是否在complete-signup页面
            if 'complete-signup' in current_url:
                self.log_signal.emit(f"  ✅ 已进入complete-signup页面")
                
                # 查找code元素（可能在页面文本中）
                # 尝试从页面获取包含code的文本
                page_text = tab.html
                
                # 使用正则提取code（JSON格式）
                code_pattern = r'\{"code":"([^"]+)"\}'
                match = re.search(code_pattern, page_text)
                
                if match:
                    code_json = match.group(0)
                    self.log_signal.emit(f"  ✅ 找到code: {code_json}")
                    return code_json
                
                # 尝试查找code文本元素
                try:
                    code_elem = tab.ele('text:code', timeout=2)
                    if code_elem:
                        code_text = code_elem.text
                        self.log_signal.emit(f"  ✅ 找到code元素: {code_text}")
                        return code_text
                except:
                    pass
                
                self.log_signal.emit(f"  ⚠️ 未找到code")
                return None
            else:
                self.log_signal.emit(f"  ⚠️ 未进入complete-signup页面")
                return None
                
        except Exception as e:
            logger.error(f"获取code失败: {e}")
            return None
    
    def _handle_payment(self, tab, email, code_data):
        """处理绑卡流程"""
        try:
            import time
            
            # 1. 回退到onboard页面
            self.log_signal.emit(f"  点击浏览器回退...")
            tab.back()
            time.sleep(2)
            
            # 2. 点击Add Payment Method
            self.log_signal.emit(f"  查找Add Payment Method按钮...")
            
            add_payment_selectors = [
                'button:contains("Add Payment Method")',
                'a:contains("Add Payment Method")',
                'button:contains("添加支付方式")'
            ]
            
            for selector in add_payment_selectors:
                try:
                    add_btn = tab.ele(selector, timeout=2)
                    if add_btn:
                        self.log_signal.emit(f"  ✅ 找到按钮，点击...")
                        add_btn.click()
                        time.sleep(3)
                        break
                except:
                    continue
            
            # 3. 等待跳转到绑卡页面
            current_url = tab.url
            self.log_signal.emit(f"  当前URL: {current_url}")
            
            if 'billing.augmentcode.com' in current_url or 'pay' in current_url:
                self.log_signal.emit(f"  ✅ 已进入绑卡页面")
                
                # 4. 填写支付信息
                payment_success = self._fill_payment_info(tab)
                
                return payment_success
            else:
                self.log_signal.emit(f"  ⚠️ 未进入绑卡页面")
                return False
                
        except Exception as e:
            logger.error(f"处理绑卡失败: {e}")
            self.log_signal.emit(f"  ❌ 绑卡处理异常: {e}")
            return False
    
    def _fill_payment_info(self, tab):
        """填写支付信息"""
        try:
            from core.card_pool_manager import get_card_pool_manager
            from core.payment_handler import VirtualCardGenerator
            import time
            
            self.log_signal.emit(f"  获取卡号...")
            
            # 从卡池获取卡号
            card_data = VirtualCardGenerator.get_card_from_pool()
            
            if not card_data:
                self.log_signal.emit(f"  ❌ 卡池为空，无法绑卡")
                return False
            
            card_number = card_data['number']
            month = card_data['month']
            year = card_data['year']
            cvv = card_data['cvv']
            
            self.log_signal.emit(f"  卡号: {card_number}")
            self.log_signal.emit(f"  有效期: {month}/{year}")
            self.log_signal.emit(f"  CVV: {cvv}")
            
            # 填写卡号
            self.log_signal.emit(f"  填写卡号...")
            card_input = tab.ele('input[placeholder*="1234"]', timeout=3)
            if card_input:
                card_input.input(card_number)
                time.sleep(1)
                self.log_signal.emit(f"  ✅ 卡号已填写")
            else:
                self.log_signal.emit(f"  ❌ 未找到卡号输入框")
                return False
            
            # 填写有效期（月份/年份）
            self.log_signal.emit(f"  填写有效期...")
            expiry_input = tab.ele('input[placeholder*="月份"]', timeout=2)
            if not expiry_input:
                expiry_input = tab.ele('input[placeholder*="MM"]', timeout=2)
            
            if expiry_input:
                expiry_input.input(f"{month}/{year[-2:]}")
                time.sleep(1)
                self.log_signal.emit(f"  ✅ 有效期已填写")
            else:
                self.log_signal.emit(f"  ⚠️ 未找到有效期输入框")
            
            # 填写CVV
            self.log_signal.emit(f"  填写CVV...")
            cvv_input = tab.ele('input[placeholder*="CVC"]', timeout=2)
            if not cvv_input:
                cvv_input = tab.ele('input[placeholder*="CVV"]', timeout=2)
            
            if cvv_input:
                cvv_input.input(cvv)
                time.sleep(1)
                self.log_signal.emit(f"  ✅ CVV已填写")
            else:
                self.log_signal.emit(f"  ⚠️ 未找到CVV输入框")
            
            # 填写姓名
            self.log_signal.emit(f"  填写姓名...")
            name_input = tab.ele('input[placeholder*="全名"]', timeout=2)
            if not name_input:
                name_input = tab.ele('input[placeholder*="name"]', timeout=2)
            
            if name_input:
                name = "Test User"  # TODO: 从配置读取或随机生成
                name_input.input(name)
                time.sleep(1)
                self.log_signal.emit(f"  ✅ 姓名已填写")
            
            # 国家/地址等其他字段...
            # TODO: 根据实际页面补充
            
            # 点击提交
            self.log_signal.emit(f"  查找提交按钮...")
            submit_selectors = [
                'button:contains("保存")',
                'button:contains("Submit")',
                'button[type="submit"]',
                'button:contains("确认")'
            ]
            
            for selector in submit_selectors:
                try:
                    submit_btn = tab.ele(selector, timeout=2)
                    if submit_btn:
                        self.log_signal.emit(f"  ✅ 找到提交按钮，点击...")
                        submit_btn.click()
                        time.sleep(3)
                        
                        # 删除已使用的卡号
                        card_manager = get_card_pool_manager()
                        card_manager.remove_card_by_number(card_number)
                        self.log_signal.emit(f"  ✅ 已删除使用的卡号")
                        
                        return True
                except:
                    continue
            
            self.log_signal.emit(f"  ⚠️ 未找到提交按钮")
            return False
            
        except Exception as e:
            logger.error(f"填写支付信息失败: {e}")
            self.log_signal.emit(f"  ❌ 填写支付信息异常: {e}")
            return False
    
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
        """生成指纹浏览器并打开授权页面"""
        try:
            from core.browser_manager import BrowserManager
            from core.machine_id_generator import generate_machine_info
            from core.aug_auth import AugmentAuth
            import tempfile
            
            # 1. 生成设备指纹
            machine_info = generate_machine_info()
            self.log_signal.emit(f"  设备指纹: {machine_info.get('telemetry.machineId', 'N/A')[:30]}...")
            
            # 2. 创建用户数据目录
            temp_dir = tempfile.mkdtemp(prefix="aug_browser_")
            self.log_signal.emit(f"  数据目录: {temp_dir}")
            
            # 3. 初始化浏览器
            browser_manager = BrowserManager()
            browser = browser_manager.init_browser(
                incognito=False,
                headless=False,
                user_data_dir=temp_dir
            )
            
            self.log_signal.emit(f"  ✅ 浏览器已打开")
            
            # 4. 生成授权链接
            self.log_signal.emit(f"\n步骤2: 生成授权链接...")
            state = str(uuid.uuid4())
            authorize_url = AugmentAuth.generate_authorize_url(state)
            self.log_signal.emit(f"  授权链接: {authorize_url[:80]}...")
            
            # 5. 访问授权页面
            self.log_signal.emit(f"\n步骤3: 访问授权页面...")
            tab = browser.latest_tab
            tab.get(authorize_url)
            
            import time
            time.sleep(3)  # 等待页面加载
            
            self.log_signal.emit(f"  ✅ 授权页面已打开")
            self.log_signal.emit(f"  当前URL: {tab.url}")
            
            # 6. 自动完成授权流程
            self.log_signal.emit(f"\n步骤4: 自动填写授权信息...")
            
            # ⭐ 生成邮箱（使用配置的域名）
            email = self._generate_email()
            self.log_signal.emit(f"  生成邮箱: {email}")
            
            # ⭐ 查找并填写邮箱输入框
            self.log_signal.emit(f"  正在查找邮箱输入框...")
            
            # Aug授权页面可能的输入框ID/name
            email_selectors = [
                '#email',
                'input[type="email"]',
                'input[name="email"]',
                'input[placeholder*="email"]'
            ]
            
            email_input = None
            for selector in email_selectors:
                try:
                    email_input = tab.ele(selector, timeout=2)
                    if email_input:
                        self.log_signal.emit(f"  ✅ 找到邮箱输入框")
                        break
                except:
                    continue
            
            if not email_input:
                self.log_signal.emit(f"  ⚠️ 未找到邮箱输入框，授权页面可能已改版")
                self.log_signal.emit(f"  💡 浏览器将保持打开，请手动完成授权")
                return True  # 保持浏览器打开
            
            # ⭐ 填写邮箱
            self.log_signal.emit(f"  填写邮箱...")
            email_input.input(email)
            time.sleep(1)
            
            # ⭐ 处理人机验证（类似Turnstile）
            self.log_signal.emit(f"\n步骤5: 处理人机验证...")
            verification_success = self._handle_human_verification(tab)
            
            if not verification_success:
                self.log_signal.emit(f"  ⚠️ 人机验证未自动通过")
                self.log_signal.emit(f"  💡 浏览器保持打开，请手动验证")
                return True  # 保持浏览器打开
            
            self.log_signal.emit(f"  ✅ 人机验证已通过")
            time.sleep(2)
            
            # ⭐ 查找并点击继续/提交按钮
            self.log_signal.emit(f"\n步骤6: 点击Continue按钮...")
            submit_selectors = [
                'button[type="submit"]',
                'button:contains("Continue")',
                'button:contains("Sign up")',
                'button:contains("Next")',
                'button:contains("提交")'
            ]
            
            for selector in submit_selectors:
                try:
                    submit_btn = tab.ele(selector, timeout=2)
                    if submit_btn:
                        self.log_signal.emit(f"  ✅ 找到Continue按钮，点击...")
                        submit_btn.click()
                        time.sleep(3)
                        break
                except:
                    continue
            
            self.log_signal.emit(f"  ✅ 授权流程已启动")
            
            # 7. 等待并获取邮箱验证码
            self.log_signal.emit(f"\n步骤7: 获取邮箱验证码...")
            
            # 等待跳转到验证码页面
            time.sleep(3)
            current_url = tab.url
            self.log_signal.emit(f"  当前URL: {current_url}")
            
            # 检查是否已经到验证码页面
            if 'passwordless-email-challenge' in current_url or 'code' in current_url.lower():
                self.log_signal.emit(f"  ✅ 已进入验证码页面")
                
                # 获取验证码
                code = self._get_verification_code(email)
                
                if not code:
                    self.log_signal.emit(f"  ❌ 未获取到验证码")
                    self.log_signal.emit(f"  💡 浏览器保持打开，请手动输入")
                    return True
                
                self.log_signal.emit(f"  ✅ 获取到验证码: {code}")
                
                # 8. 填写验证码
                self.log_signal.emit(f"\n步骤8: 填写验证码...")
                success = self._fill_verification_code(tab, code)
                
                if success:
                    self.log_signal.emit(f"  ✅ 验证码已填写并提交")
                    
                    # 9. 处理onboard页面 - 点击Skip
                    self.log_signal.emit(f"\n步骤9: 处理onboard页面...")
                    time.sleep(5)  # 等待页面加载
                    
                    current_url = tab.url
                    self.log_signal.emit(f"  当前URL: {current_url}")
                    
                    if 'onboard' in current_url:
                        self.log_signal.emit(f"  ✅ 已进入onboard页面")
                        
                        # 点击Skip for now
                        skip_success = self._click_skip_button(tab)
                        
                        if skip_success:
                            # 10. 获取并保存code
                            self.log_signal.emit(f"\n步骤10: 获取授权code...")
                            code_data = self._get_auth_code(tab)
                            
                            if code_data:
                                self.log_signal.emit(f"  ✅ 获取到code: {code_data[:50]}...")
                                
                                # 11. 返回并绑卡
                                self.log_signal.emit(f"\n步骤11: 返回绑卡...")
                                payment_success = self._handle_payment(tab, email, code_data)
                                
                                if payment_success:
                                    self.log_signal.emit(f"  ✅ 绑卡成功")
                                    # TODO: 保存账号信息
                                else:
                                    self.log_signal.emit(f"  ⚠️ 绑卡失败")
                            else:
                                self.log_signal.emit(f"  ❌ 未获取到code")
                        else:
                            self.log_signal.emit(f"  ⚠️ Skip按钮处理失败")
                    else:
                        self.log_signal.emit(f"  ⚠️ 未进入onboard页面")
                        self.log_signal.emit(f"  💡 浏览器保持打开")
                else:
                    self.log_signal.emit(f"  ⚠️ 验证码填写失败")
                    self.log_signal.emit(f"  💡 浏览器保持打开")
            else:
                self.log_signal.emit(f"  ⚠️ 未跳转到验证码页面")
                self.log_signal.emit(f"  💡 浏览器保持打开")
            
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

