#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动注册模块（主流程控制）
"""

import time
from typing import Dict, Any

from .browser_manager import BrowserManager
from .email_verification import EmailVerificationHandler
from .registration_steps import RegistrationSteps
from .phone_handler import PhoneHandler
from .token_handler import TokenHandler
from .payment_handler import PaymentHandler
from .activation_manager import get_activation_manager
from utils.logger import get_logger

logger = get_logger("auto_register")


class CursorAutoRegister:
    """Cursor 自动注册器"""
    
    def __init__(self):
        self.browser_manager = None
        self.browser = None
        self.tab = None
        self.progress_callback = None
        self.config = {}  # ⭐ 初始化配置字典
    
    def _log(self, message: str, percent: int = None):
        """统一日志输出"""
        logger.info(message)
        if self.progress_callback and percent is not None:
            try:
                self.progress_callback(message, percent)
            except:
                pass
    
    def _is_browser_alive(self) -> bool:
        """
        检测浏览器是否仍在运行
        
        Returns:
            bool: True 表示浏览器正常运行，False 表示已关闭
        """
        try:
            if not self.browser or not self.tab:
                return False
            
            # 尝试访问 tab 的 url 属性
            # 如果浏览器已关闭，这个操作会抛出异常
            _ = self.tab.url
            return True
            
        except Exception as e:
            logger.debug(f"浏览器状态检测异常: {e}")
            return False
    
    def _check_browser_or_abort(self):
        """
        检查浏览器状态，如果已关闭则抛出异常
        
        Raises:
            Exception: 浏览器已被关闭
        """
        if not self._is_browser_alive():
            raise Exception("浏览器已被用户关闭，注册流程终止")
            
    def register_account(self, email: str, config: Dict[str, Any], progress_callback=None, check_limit: bool = True) -> Dict[str, Any]:
        """
        注册单个账号
        
        Args:
            email: 邮箱地址
            config: 配置信息
            progress_callback: 进度回调函数 callback(message, percent)
            check_limit: 是否检查注册限制
        """
        self.browser_manager = BrowserManager()
        self.progress_callback = progress_callback
        self.config = config  # ⭐ 保存配置供后续使用
        
        try:
            # ⭐ 检查注册限制（未激活设备每天5个）
            if check_limit:
                activation_mgr = get_activation_manager()
                can_register, remaining, limit_msg = activation_mgr.can_register()
                
                if not can_register:
                    self._log(f"❌ {limit_msg}", 0)
                    return {'success': False, 'message': limit_msg, 'token': None}
                
                logger.info(f"✅ 注册限制检查通过: {limit_msg}")
            
            self._log("="*60, 0)
            self._log("开始注册流程", 0)
            self._log("="*60, 0)
            
            # 步骤0: 测试邮箱
            self._log("步骤0: 测试邮箱连接...", 5)
            if not self._test_email(email, config):
                return {'success': False, 'message': '邮箱测试失败', 'token': None}
            self._log("✅ 邮箱测试通过", 10)
            
            # 步骤1: 启动浏览器
            self._log("步骤1: 启动浏览器...", 15)
            if not self._init_browser():
                return {'success': False, 'message': '浏览器启动失败', 'token': None}
            self._log("✅ 浏览器已就绪", 25)
            
            # 步骤2: 访问登录页
            self._log("步骤2: 访问登录页...", 30)
            login_result = self._visit_login()
            if not login_result:
                return {'success': False, 'message': '访问登录页失败', 'token': None}
            self._log("✅ 登录页加载完成", 35)
            self._check_browser_or_abort()  # ⭐ 检查浏览器状态
            
            # 步骤3: 输入邮箱（已内置智能等待，无需额外sleep）
            self._log(f"步骤3: 输入邮箱 {email}", 40)
            email_result = RegistrationSteps.input_email(self.tab, email)
            if not email_result:
                self._log("❌ 输入邮箱失败", 0)
                return {'success': False, 'message': '输入邮箱失败', 'token': None}
            self._log("✅ 邮箱已输入", 45)
            self._check_browser_or_abort()  # ⭐ 检查浏览器状态
            
            # 步骤4: 点击继续
            self._log("步骤4: 点击继续...", 50)
            if not RegistrationSteps.click_continue(self.tab):
                return {'success': False, 'message': '点击继续失败', 'token': None}
            self._log("✅ 已跳转到密码页面", 55)
            self._check_browser_or_abort()  # ⭐ 检查浏览器状态
            
            # 步骤5: 点击邮箱验证码
            self._log("步骤5: 点击邮箱验证码按钮...", 60)
            if not RegistrationSteps.click_email_code_button(self.tab):
                return {'success': False, 'message': '进入验证码页面失败', 'token': None}
            
            # 步骤6: 智能检测验证码页面
            self._log("等待进入验证码页面...", 60)
            max_wait = 10
            for i in range(max_wait):
                self._check_browser_or_abort()
                if "magic-code" in self.tab.url:
                    self._log(f"✅ 已进入验证码页面 ({i+1}秒)", 65)
                    break
                time.sleep(1)
            else:
                self._log("⚠️ 未检测到验证码页面，尝试继续", 65)
            
            self._check_browser_or_abort()
            
            # 步骤7: 获取验证码
            self._log("步骤7: 获取邮箱验证码...", 70)
            code = self._get_code(email, config)
            if not code:
                return {'success': False, 'message': '获取验证码失败', 'token': None}
            self._log(f"✅ 获取到验证码: {code}", 75)
            self._check_browser_or_abort()  # ⭐ 检查浏览器状态
            
            # 步骤8: 输入验证码
            self._log("步骤8: 输入验证码...", 80)
            if not RegistrationSteps.input_verification_code(self.tab, code):
                return {'success': False, 'message': '输入验证码失败', 'token': None}
            self._log("✅ 验证码已输入", 85)
            self._check_browser_or_abort()  # ⭐ 检查浏览器状态
            
            # 步骤9: 处理手机验证
            self._log("步骤9: 检测手机验证...", 88)
            if not self._handle_phone(config):
                return {'success': False, 'message': '手机验证失败', 'token': None}
            self._log("✅ 手机验证完成", 92)
            self._check_browser_or_abort()
            
            # ⚡ 步骤9.5: 检测二次验证（radar验证后可能要求重新输入验证码）
            time.sleep(1)
            if "magic-code" in self.tab.url and "radar_auth_attempt_id" in self.tab.url:
                self._log("⚠️ 检测到二次验证要求，重新获取验证码...", 88)
                
                # 重新获取验证码
                code2 = self._get_code(email, config)
                if not code2:
                    return {'success': False, 'message': '二次验证码获取失败', 'token': None}
                self._log(f"✅ 获取到二次验证码: {code2}", 90)
                
                # 重新输入验证码
                self._log("输入二次验证码...", 91)
                if not RegistrationSteps.input_verification_code(self.tab, code2):
                    return {'success': False, 'message': '二次验证码输入失败', 'token': None}
                self._log("✅ 二次验证码已输入", 92)
                self._check_browser_or_abort()
            
            # 等待跳转到 cursor.com
            self._log("等待跳转到 cursor.com...", 94)
            RegistrationSteps.wait_for_cursor_com(self.tab)
            self._check_browser_or_abort()
            
            # 步骤9.5: 处理 Data Sharing 页面（可能出现）
            self._log("检测并处理 Data Sharing 页面...", 89)
            RegistrationSteps.handle_data_sharing_page(self.tab)
            self._check_browser_or_abort()  # ⭐ 检查浏览器状态
            
            # 步骤10: 获取Token
            self._log("步骤10: 获取Token...", 90)
            token = self._get_token(email)
            if not token:
                self._log("❌ 未获取到Token", 0)
                return {'success': False, 'message': '未获取到Token', 'token': None}
            
            self._log("✅ Token 已获取", 92)
            self._log("✅ 账号已保存到数据库", 94)
            self._check_browser_or_abort()  # ⭐ 检查浏览器状态
            
            # 步骤11: 绑卡（可选）
            payment_config = config.get('payment_binding', {})
            has_payment_warning = False  # 是否有支付警告
            
            if payment_config.get('enabled', False):
                self._log("步骤11: 开始绑卡流程...", 95)
                result = self._handle_payment_binding(payment_config)
                
                # ⭐ 处理返回值（可能是bool或tuple）
                if isinstance(result, tuple):
                    binding_success, has_payment_warning = result
                else:
                    binding_success = result
                    has_payment_warning = False
                
                if binding_success:
                    if has_payment_warning:
                        self._log("⚠️ 绑卡完成但有支付警告", 98)
                    else:
                        self._log("✅ 绑卡完成", 98)
                else:
                    self._log("⚠️ 绑卡失败或跳过", 98)
                    if not payment_config.get('skip_on_error', True):
                        return {'success': False, 'message': '绑卡失败', 'token': token, 'has_payment_warning': False}
                self._check_browser_or_abort()  # ⭐ 检查浏览器状态
            else:
                self._log("步骤11: 跳过绑卡（未启用）", 98)
            
            # ⭐ 注册成功，增加每日计数
            if check_limit:
                activation_mgr = get_activation_manager()
                activation_mgr.increment_daily_count()
                logger.info("✅ 已更新今日注册计数")
            
            self._log("="*60, 100)
            self._log("✅ 注册完成！", 100)
            self._log("="*60, 100)
            
            # ⭐ 返回包含警告信息
            return {
                'success': True, 
                'message': '注册成功', 
                'email': email, 
                'token': token,
                'has_payment_warning': has_payment_warning
            }
            
        except Exception as e:
            error_msg = str(e)
            
            # 区分浏览器关闭和其他错误
            if "浏览器已被用户关闭" in error_msg:
                logger.warning("⚠️ 浏览器已被用户手动关闭，注册流程已终止")
                self._log("⚠️ 浏览器已关闭，注册流程终止", 0)
                return {'success': False, 'message': '浏览器已关闭', 'token': None}
            else:
                logger.error(f"注册失败: {e}")
                return {'success': False, 'message': str(e), 'token': None}
        finally:
            pass  # 浏览器由外部决定是否关闭
    
    def _test_email(self, email, config):
        """测试邮箱连接"""
        email_config = config.get('email', {})  # ⭐ 先获取 'email' 子对象
        handler = EmailVerificationHandler(email, email_config.get('receiving_email'), email_config.get('receiving_email_pin'))
        success, msg = handler.test_connection()
        if not success:
            self._log(f"❌ 邮箱测试失败: {msg}", 0)
        return success
    
    def _init_browser(self):
        """启动浏览器（智能等待）"""
        # ⭐ 从配置读取无痕模式设置
        browser_config = self.config.get('browser', {})
        incognito_mode = browser_config.get('incognito_mode', True)  # 默认启用无痕模式
        
        self.browser = self.browser_manager.init_browser(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            headless=False,
            incognito=incognito_mode  # ⭐ 传递无痕模式配置
        )
        
        # ⚡ 智能等待：检测浏览器和tab是否就绪
        max_wait = 5
        for i in range(max_wait):
            try:
                self.tab = self.browser.latest_tab
                if self.tab:
                    logger.info(f"浏览器就绪 ({i+1}秒)")
                    return True
            except:
                pass
            time.sleep(1)
        
        # 超时但尝试继续
        self.tab = self.browser.latest_tab
        return True
    
    def _visit_login(self):
        """访问登录页（防卡死优化）"""
        login_url = "https://authenticator.cursor.sh/"
        logger.info(f"访问登录页: {login_url}")
        
        try:
            # ⚡ 直接导航
            logger.info("导航中...")
            self.tab.get(login_url)
            logger.info("导航完成，等待页面元素...")
            
            # ⚡ 简单等待2秒让页面稳定
            time.sleep(2)
            
            # 检测页面是否就绪
            try:
                test_input = self.tab.ele("tag:input@type=email", timeout=2)
                if test_input:
                    logger.info("✅ 页面就绪")
                    return True
            except:
                pass
            
            # 再等3秒
            logger.info("  页面未完全加载，再等待3秒...")
            time.sleep(3)
            
            logger.info("✅ 继续执行")
            return True
            
        except Exception as e:
            logger.error(f"访问失败: {e}")
            return False
    
    def _get_code(self, email, config):
        """获取验证码（快速轮询，防止卡死）"""
        email_config = config.get('email', {})
        handler = EmailVerificationHandler(email, email_config.get('receiving_email'), email_config.get('receiving_email_pin'))
        
        # ⚡ 快速轮询模式（最多30秒）
        max_wait = 30
        start_time = time.time()
        attempt = 0
        
        logger.info("开始获取验证码...")
        
        while time.time() - start_time < max_wait:
            # 检查浏览器状态
            if not self._is_browser_alive():
                raise Exception("浏览器已关闭")
            
            try:
                attempt += 1
                # ⚡ 快速获取验证码（使用短超时）
                verify_code, first_id = handler._get_latest_mail_code()
                if verify_code:
                    logger.info(f"✅ 获取到验证码: {verify_code}")
                    try:
                        handler._cleanup_mail(first_id)
                    except:
                        pass
                    return verify_code
                
                # 每5次报告一次
                if attempt % 5 == 0:
                    logger.info(f"  获取中... ({int(time.time()-start_time)}/{max_wait}秒)")
                
            except Exception as e:
                if attempt == 1:
                    logger.debug(f"获取验证码: {e}")
            
            time.sleep(1)
        
        self._log("❌ 获取验证码超时", 0)
        return None
    
    def _handle_phone(self, config):
        """处理手机验证（智能检测）"""
        # ⚡ 智能检测：最多等5秒看是否跳转到手机验证
        for i in range(5):
            if "phone" in self.tab.url or "radar" in self.tab.url:
                break
            time.sleep(1)
        
        if "phone" not in self.tab.url and "radar" not in self.tab.url:
            self._log("✅ 无需手机验证", 90)
            return True
        
        self._log("⚠️ 需要手机验证！", 88)
        
        phone_cfg = config.get('phone_verification', {})
        if phone_cfg.get('enabled'):
            self._log("调用用户自定义代码...", 88)
            success = PhoneHandler.call_user_custom_code(self.tab, phone_cfg.get('custom_code', ''))
            if success:
                self._log("✅ 自定义代码执行成功", 92)
                return True
            return False
        else:
            self._log("未配置自动过手机号，切换到手动模式", 88)
            self._log("💡 请在浏览器中手动完成手机验证", 88)
            return PhoneHandler.handle_manual_phone_verification(self.tab)
    
    def _get_token(self, email):
        """获取Token并保存（智能等待）"""
        # ⚡ 智能等待：检测页面是否稳定
        self._log("等待页面稳定...", 90)
        time.sleep(1)
        
        # 获取 accessToken（深度登录）
        access_token = TokenHandler.get_access_token(self.tab)
        if not access_token:
            return None
    
        # 获取 SessionToken（从Cookie）
        from .deep_token_getter import DeepTokenGetter
        session_token = DeepTokenGetter.get_session_token_from_cookies(self.tab)
        
        # 保存到数据库（accessToken 和 SessionToken 都保存）
        TokenHandler.save_to_database(email, access_token, session_token)
        
        return access_token
    
    def _handle_payment_binding(self, config):
        """
        处理绑卡流程（步骤11）
        
        Args:
            config: 配置信息
            
        Returns:
            tuple: (是否成功, 是否有支付警告) 或 bool（兼容旧版）
        """
        try:
            # ⭐ 优化：直接通过 API 获取绑卡页面，跳过 Dashboard
            # 不再需要 navigate_to_billing，API 会自动处理
            logger.info("\n" + "="*60)
            logger.info("步骤11: 获取并访问绑卡页面")
            logger.info("="*60)
            
            # 获取并访问 Stripe 绑卡页面（API 优先，自动包含 SessionToken 处理）
            if not PaymentHandler.click_start_trial_button(self.tab):
                logger.warning("未能获取或访问绑卡页面")
                return (False, False)
            
            # 填写 Stripe 支付信息（返回元组）
            result = PaymentHandler.fill_stripe_payment(self.tab, self.browser_manager.browser)
            
            # ⭐ 处理返回值（可能是bool或tuple）
            if isinstance(result, tuple):
                success, has_warning = result
                if success:
                    logger.info("✅ 绑卡流程完成")
                return (success, has_warning)
            else:
                # 兼容旧版返回bool
                if result:
                    logger.info("✅ 绑卡流程完成")
                    return (True, False)
                else:
                    logger.warning("Stripe 支付信息填写失败")
                    return (False, False)
                
        except Exception as e:
            logger.error(f"绑卡流程异常: {e}")
            return (False, False)
    
    def close(self):
        """关闭浏览器（立即关闭，不输出多余日志）"""
        if self.browser_manager:
            try:
                self.browser_manager.quit()
            except:
                pass
