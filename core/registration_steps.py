#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
注册步骤实现模块
包含各个具体注册步骤的实现
"""

import time
import random
from .turnstile_handler import handle_turnstile
from utils.logger import get_logger

logger = get_logger("registration_steps")


class RegistrationSteps:
    """注册步骤实现类"""
    
    @staticmethod
    def input_email(tab, email: str) -> bool:
        """
        步骤3: 输入邮箱
        
        Args:
            tab: DrissionPage 的 tab 对象
            email: 邮箱地址
            
        Returns:
            bool: 是否成功
        """
        logger.info(f"\n步骤3: 输入邮箱: {email}")
        
        try:
            # ⚡ 快速检测邮箱输入框（减少timeout，加快响应）
            logger.info("快速检测邮箱输入框...")
            email_input = None
            max_wait = 10  # 降低到10秒
            
            for attempt in range(max_wait):
                try:
                    # 快速查找，timeout只设0.5秒
                    email_input = tab.ele("@name=email", timeout=0.5)
                    if not email_input:
                        email_input = tab.ele("@type=email", timeout=0.5)
                    
                    if email_input:
                        logger.info(f"✅ 检测到输入框 ({attempt+1}秒)")
                        break
                except:
                    pass
                
                if attempt % 3 == 2:  # 每3秒报告一次
                    logger.info(f"  等待... ({attempt+1}/{max_wait}秒)")
                time.sleep(1)
            
            
            if not email_input:
                logger.error("❌ 未找到邮箱输入框")
                logger.error(f"当前URL: {tab.url}")
                return False
            
            logger.info("找到邮箱输入框，开始输入...")
            
            # ⚡ 确保输入框可交互
            time.sleep(0.3)
            
            # ⚡ 快速输入（减少验证，避免卡死）
            try:
                email_input.clear()
                time.sleep(0.2)
                email_input.input(email)
                logger.info("✅ 邮箱已输入")
                time.sleep(0.5)
                return True
            except Exception as e:
                logger.warning(f"⚠️ 输入失败，重试一次: {e}")
                try:
                    # 重试一次
                    email_input.input(email)
                    logger.info("✅ 邮箱已输入（重试成功）")
                    return True
                except:
                    logger.error("❌ 邮箱输入失败")
                    return False
            
        except Exception as e:
            logger.error(f"输入邮箱时出错: {e}")
            return False
    
    @staticmethod
    def click_continue(tab) -> bool:
        """
        步骤4: 点击继续按钮
        
        Args:
            tab: DrissionPage 的 tab 对象
            
        Returns:
            bool: 是否成功
        """
        logger.info("\n步骤4: 点击继续...")
        
        # ⚡ 快速查找继续按钮
        submit_btn = tab.ele("@type=submit", timeout=2)
        if not submit_btn:
            logger.error("❌ 未找到继续按钮")
            return False
        
        time.sleep(0.3)  # 短暂等待
        start_url = tab.url
        
        # ⚡ 持续点击直到跳转（最多30秒，每2秒点一次）
        max_wait = 30
        start_time = time.time()
        click_count = 0
        
        while time.time() - start_time < max_wait:
            # 快速检查是否已跳转
            try:
                if "password" in tab.url or "magic-code" in tab.url:
                    logger.info(f"✅ 已跳转！({int(time.time()-start_time)}秒)")
                    return True
            except:
                pass
            
            # 每2秒点击一次
            if int(time.time() - start_time) % 2 == 0 and int(time.time() - start_time) != click_count * 2:
                click_count += 1
                try:
                    btn = tab.ele("@type=submit", timeout=0.5)
                    if btn:
                        btn.click()
                        logger.info(f"🔄 第{click_count}次点击")
                except:
                    pass
            
            time.sleep(0.5)  # 快速轮询
        
        # 最终检查
        if "password" in tab.url or "magic-code" in tab.url:
            return True
        
        logger.warning(f"⚠️ 超时，但继续执行")
        return True
    
    @staticmethod
    def click_email_code_button(tab) -> bool:
        """
        步骤5: 点击"邮箱验证码"按钮（带重试机制）
        
        Args:
            tab: DrissionPage 的 tab 对象
            
        Returns:
            bool: 是否成功
        """
        logger.info(f"\n步骤5: 选择邮箱验证码登录")
        
        if "password" not in tab.url:
            logger.warning(f"未在password页面: {tab.url}")
        
        max_attempts = 3
        button_clicked_success = False
        
        for attempt in range(max_attempts):
            logger.info(f"\n尝试点击 (第{attempt+1}/{max_attempts}次)")
            
            code_buttons = tab.eles("tag:button")
            button_clicked = False
            
            for btn in code_buttons:
                btn_text = btn.text
                if btn_text and ("邮箱" in btn_text or "code" in btn_text.lower() or "验证码" in btn_text):
                    logger.info(f"点击按钮: {btn_text}")
                    current_url = tab.url
                    btn.click()
                    button_clicked = True
                    
                    # 等待页面响应（边等待边检查 Turnstile）
                    logger.info("等待页面响应...")
                    max_wait = 20
                    turnstile_handled = False
                    
                    for i in range(max_wait):
                        time.sleep(1)
                        
                        # 检查1: 是否已跳转？
                        if tab.url != current_url:
                            logger.info(f"✅ 页面已跳转！(等待{i+1}秒)")
                            button_clicked_success = True
                            break
                        
                        # 检查2: 是否出现 Turnstile 验证框？
                        if not turnstile_handled:
                            try:
                                turnstile_elem = tab.ele("#cf-turnstile", timeout=0.5)
                                if turnstile_elem:
                                    logger.info(f"\n⚠️ 检测到 Turnstile 验证框！({i+1}秒)")
                                    logger.info("立即处理验证...")
                                    turnstile_handled = True
                                    
                                    # 立即处理验证
                                    verification_passed = handle_turnstile(tab, max_wait_seconds=30)
                                    
                                    # 验证后检查是否跳转
                                    if tab.url != current_url:
                                        logger.info(f"✅ 验证后页面已跳转！")
                                        button_clicked_success = True
                                        break
                            except:
                                pass
                        
                        # 每5秒显示进度
                        if (i + 1) % 5 == 0:
                            logger.info(f"   等待跳转... ({i+1}/{max_wait}秒)")
                    
                    if button_clicked_success:
                        break
                    
                    if tab.url != current_url:
                        logger.info(f"✅ 验证后页面已跳转！")
                        button_clicked_success = True
                        break
                    
                    if attempt < max_attempts - 1:
                        logger.info("3秒后重试...")
                        time.sleep(3)
                    
                    break
            
            if button_clicked_success:
                break
        
        if "password" in tab.url:
            logger.error("无法进入验证码页面")
            return False
        
        logger.info(f"✅ 成功离开password页面")
        return True
    
    @staticmethod
    def input_verification_code(tab, code: str) -> bool:
        """
        步骤8: 输入验证码
        
        Args:
            tab: DrissionPage 的 tab 对象
            code: 验证码
            
        Returns:
            bool: 是否成功
        """
        logger.info("\n步骤8: 输入验证码...")
        
        # ⚡ 快速检测输入框（timeout减小）
        code_inputs = None
        for attempt in range(8):  # 最多等8秒
            try:
                code_inputs = tab.eles("@class=rt-reset rt-TextFieldInput", timeout=0.5)
                if code_inputs and len(code_inputs) >= 6:
                    logger.info(f"✅ 检测到输入框 ({attempt+1}秒)")
                    break
            except:
                pass
            time.sleep(1)
        
        if not code_inputs or len(code_inputs) < 6:
            logger.error(f"❌ 未找到输入框")
            return False
        
        # ⚡ 快速输入验证码（减少延迟）
        logger.info("输入验证码...")
        for i, digit in enumerate(code[:6]):
            try:
                if i < len(code_inputs):
                    code_inputs[i].input(digit)
                    time.sleep(0.1)  # 减少延迟
            except:
                pass
        
        logger.info("✅ 验证码已输入")
        
        # ⚡ 快速检测跳转（3秒）
        for i in range(6):
            try:
                if "cursor.com" in tab.url or "phone" in tab.url or "radar" in tab.url:
                    logger.info(f"  页面已跳转 ({i*0.5}秒)")
                    break
            except:
                pass
            time.sleep(0.5)
        
        return True
    
    @staticmethod
    def wait_for_cursor_com(tab, max_wait=30) -> bool:
        """
        等待跳转到 cursor.com 主站
        
        Args:
            tab: DrissionPage 的 tab 对象
            max_wait: 最大等待时间（秒）
            
        Returns:
            bool: 是否成功
        """
        logger.info("\n等待最终跳转到 cursor.com...")
        
        login_success = False
        
        for i in range(max_wait):
            try:
                current_url = tab.url
                
                if current_url.startswith("https://cursor.com") or current_url.startswith("https://www.cursor.com"):
                    if "authenticator" not in current_url and "radar" not in current_url and "phone" not in current_url:
                        logger.info(f"✅ 已跳转到 cursor.com 主站！")
                        login_success = True
                        break
                
                if (i + 1) % 5 == 0:
                    logger.info(f"⏳ 等待跳转... ({i+1}/{max_wait}秒)")
            except:
                pass
            
            time.sleep(1)
        
        if not login_success:
            logger.warning(f"⚠️ 未检测到跳转，尝试获取Token...")
        
        return True  # 即使未跳转也继续尝试获取Token
    
    @staticmethod
    def handle_data_sharing_page(tab, max_wait=10) -> bool:
        """
        处理 Data Sharing 页面（可能出现在登录后）
        
        Args:
            tab: DrissionPage 的 tab 对象
            max_wait: 最大等待时间（秒）
            
        Returns:
            bool: 是否成功处理（页面不存在也返回True）
        """
        logger.info("\n检测 Data Sharing 页面...")
        
        try:
            # 等待页面加载
            time.sleep(2)
            
            # 检测是否存在 Data Sharing 页面的特征元素
            # 检查是否包含 "Data Sharing" 标题
            page_text = tab.html.lower()
            
            if "data sharing" not in page_text and "help improve cursor" not in page_text:
                logger.info("✅ 未出现 Data Sharing 页面，继续流程")
                return True
            
            logger.info("🔍 检测到 Data Sharing 页面，开始自动处理...")
            
            # 方法1: 尝试勾选复选框（使用JS点击，因为普通click不生效）
            checkbox_clicked = False
            try:
                # 查找包含特定文本的复选框
                checkbox = tab.ele("@type=checkbox", timeout=5)
                if checkbox:
                    # 检查是否已勾选
                    if not checkbox.states.is_checked:
                        # ⚡ 使用JS点击（普通click对这个checkbox不生效）
                        tab.run_js("arguments[0].click();", checkbox)
                        logger.info("✅ 已勾选同意复选框")
                    else:
                        logger.info("✅ 复选框已勾选")
                    checkbox_clicked = True
                    time.sleep(1)
            except Exception as e:
                logger.debug(f"方法1失败: {e}")
            
            # 方法2: 如果方法1失败，尝试直接点击包含文本的区域
            if not checkbox_clicked:
                try:
                    # 查找包含 "I'm fine" 文本的元素并点击
                    text_elem = tab.ele("text:I'm fine", timeout=3)
                    if text_elem:
                        text_elem.click()
                        logger.info("✅ 已点击同意选项")
                        checkbox_clicked = True
                        time.sleep(1)
                except Exception as e:
                    logger.debug(f"方法2失败: {e}")
            
            # 点击 Continue 按钮
            continue_clicked = False
            
            # 方法1: 查找包含 Continue 文本的按钮
            try:
                continue_btn = tab.ele("text:Continue", timeout=5)
                if continue_btn:
                    continue_btn.click()
                    logger.info("✅ 已点击 Continue 按钮")
                    continue_clicked = True
                    time.sleep(2)
            except Exception as e:
                logger.debug(f"Continue按钮方法1失败: {e}")
            
            # 方法2: 查找 button 标签
            if not continue_clicked:
                try:
                    buttons = tab.eles("tag:button")
                    for btn in buttons:
                        if "continue" in btn.text.lower():
                            btn.click()
                            logger.info("✅ 已点击 Continue 按钮")
                            continue_clicked = True
                            time.sleep(2)
                            break
                except Exception as e:
                    logger.debug(f"Continue按钮方法2失败: {e}")
            
            if continue_clicked:
                logger.info("✅ Data Sharing 页面已处理")
                return True
            else:
                logger.warning("⚠️ 未能点击 Continue 按钮，尝试继续...")
                return True  # 即使失败也继续流程
                
        except Exception as e:
            logger.warning(f"处理 Data Sharing 页面时出错: {e}")
            return True  # 出错也继续流程

