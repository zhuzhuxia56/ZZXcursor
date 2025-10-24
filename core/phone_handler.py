#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手机验证处理模块
负责处理 Cursor 的手机验证步骤
"""

import time
import random
from utils.logger import get_logger

logger = get_logger("phone_handler")


class PhoneHandler:
    """手机验证处理器"""
    
    @staticmethod
    def generate_us_phone():
        """
        生成随机美国手机号
        
        Returns:
            str: 10位手机号（不含+1）
        """
        area_code = random.randint(200, 999)
        if area_code == 555:  # 跳过保留号段
            area_code = 556
        
        exchange = random.randint(200, 999)
        subscriber = random.randint(1000, 9999)
        
        return f"{area_code}{exchange}{subscriber}"
    
    @staticmethod
    def call_user_custom_code(tab, custom_code: str) -> bool:
        """
        调用用户自定义的手机验证代码
        
        Args:
            tab: DrissionPage 的 tab 对象
            custom_code: 用户编写的 Python 代码
            
        Returns:
            bool: 是否成功
        """
        try:
            phone_number = PhoneHandler.generate_us_phone()
            logger.info(f"生成手机号: +1{phone_number}")
            
            # 创建执行环境
            exec_globals = {
                'tab': tab,
                'phone_number': phone_number,
                'time': time,
                'logger': logger
            }
            exec_locals = {}
            
            # 执行用户代码
            exec(custom_code, exec_globals, exec_locals)
            
            # 调用用户定义的函数
            if 'verify_phone' in exec_locals:
                verify_func = exec_locals['verify_phone']
                result = verify_func(tab, phone_number)
                return bool(result)
            else:
                logger.error("用户代码中未找到 verify_phone 函数")
                return False
                
        except Exception as e:
            logger.error(f"执行用户代码失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def handle_manual_phone_verification(tab) -> bool:
        """
        手动模式：完全由用户手动操作，程序只检测是否完成
        
        Args:
            tab: DrissionPage 的 tab 对象
            
        Returns:
            bool: 是否成功
        """
        logger.info("="*60)
        logger.info("⚠️ 未配置自动过手机号")
        logger.info("="*60)
        logger.info("")
        logger.info("💡 请按照以下步骤手动操作：")
        logger.info("   1. 在浏览器中输入您的手机号")
        logger.info("   2. 点击发送验证码")
        logger.info("   3. 接收短信验证码并输入")
        logger.info("   4. 点击提交")
        logger.info("")
        logger.info("💡 想要自动化？请前往：设置 → 📱手机验证 配置自动接码")
        logger.info("")
        logger.info("程序每3秒自动检测验证是否完成...")
        logger.info("检测到页面跳转后会自动继续下一步")
        logger.info("="*60)
        
        # 每3秒检测是否验证完成
        manual_wait = 120  # 2分钟
        start_url = tab.url  # 记录起始URL
        
        for i in range(manual_wait):
            try:
                new_url = tab.url
                
                # ✅ 修复判断逻辑：必须满足以下条件之一才算完成
                # 1. 跳转到真正的 cursor.com（不是 authenticator.cursor.sh）
                # 2. 离开了所有验证相关页面（phone/radar/magic-code）
                
                is_verified = False
                
                # 条件1: 跳转到 cursor.com 主站（不含 authenticator）
                if "cursor.com" in new_url and "authenticator" not in new_url:
                    if "phone" not in new_url and "radar" not in new_url:
                        is_verified = True
                        logger.info("")
                        logger.info("="*60)
                        logger.info(f"✅ 手机验证完成！已跳转到主站（耗时 {i+1} 秒）")
                        logger.info(f"   新URL: {new_url}")
                        logger.info("="*60)
                        return True
                
                # ⚠️ 检测二次验证：从radar返回到magic-code页面
                if "magic-code" in new_url and "radar_auth_attempt_id" in new_url:
                    if new_url != start_url:  # URL确实变化了
                        logger.info("")
                        logger.info("="*60)
                        logger.info(f"⚠️ 检测到从手机验证返回（耗时 {i+1} 秒）")
                        logger.info("   需要重新输入验证码...")
                        logger.info("="*60)
                        return True  # 返回True，让主流程处理二次验证
                        
            except:
                pass
            
            # 每10秒显示一次进度（减少日志噪音）
            if (i + 1) % 10 == 0:
                logger.info(f"⏳ 等待手动验证... ({i+1}/{manual_wait}秒)")
            
            time.sleep(1)
        
        logger.error("="*60)
        logger.error("❌ 手机验证超时（2分钟）")
        logger.error("="*60)
        return False

