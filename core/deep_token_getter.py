#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深度Token获取器
通过 SessionToken 获取 accessToken (type=session)
深度登录方法实现
"""

import time
import uuid
import secrets
import hashlib
import base64
import requests
from utils.logger import get_logger

logger = get_logger("deep_token_getter")


class DeepTokenGetter:
    """深度Token获取器"""
    
    @staticmethod
    def _generate_pkce_pair():
        """
        生成PKCE验证对
        
        Returns:
            tuple: (code_verifier, code_challenge)
        """
        code_verifier = secrets.token_urlsafe(43)
        code_challenge_digest = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        code_challenge = base64.urlsafe_b64encode(code_challenge_digest).decode('utf-8').rstrip('=')
        return code_verifier, code_challenge
    
    @staticmethod
    def get_access_token_from_session_token(tab, session_token: str, max_attempts: int = 3) -> str:
        """
        通过 SessionToken 获取 accessToken
        
        Args:
            tab: DrissionPage 的 tab 对象
            session_token: WorkosCursorSessionToken 的值（格式：user_xxx::eyJhbGci...）
            max_attempts: 最大尝试次数
            
        Returns:
            str: accessToken 或 None
        """
        logger.info("="*60)
        logger.info("开始深度登录获取 accessToken")
        logger.info("="*60)
        
        attempts = 0
        while attempts < max_attempts:
            try:
                # 生成 PKCE 验证对
                verifier, challenge = DeepTokenGetter._generate_pkce_pair()
                uuid_str = str(uuid.uuid4())
                
                logger.info(f"尝试 {attempts + 1}/{max_attempts}")
                logger.info(f"UUID: {uuid_str}")
                logger.info(f"Challenge: {challenge[:30]}...")
                
                # 构造深度登录URL
                login_url = f"https://www.cursor.com/cn/loginDeepControl?challenge={challenge}&uuid={uuid_str}&mode=login"
                
                logger.info(f"\n步骤1: 设置 SessionToken 到 Cookie...")
                
                # ⚡ 使用 DrissionPage 的 Cookie API 设置
                try:
                    # 先访问 cursor.com 建立会话
                    tab.get("https://www.cursor.com")
                    time.sleep(1)
                    
                    # ⚡ 使用 DrissionPage 的 set_session_storage 或 set.cookies
                    # 构造Cookie对象
                    cookie_data = {
                        'name': 'WorkosCursorSessionToken',
                        'value': session_token,
                        'domain': '.cursor.com',
                        'path': '/',
                        'secure': True,
                        'httpOnly': False,
                        'sameSite': 'None'
                    }
                    
                    # 设置Cookie（使用DrissionPage API）
                    tab.set.cookies(cookie_data)
                    logger.info(f"✅ SessionToken 已通过 API 设置到 Cookie")
                    
                    # 验证Cookie
                    cookies = tab.cookies()
                    found = False
                    for c in cookies:
                        if c.get('name') == 'WorkosCursorSessionToken':
                            found = True
                            logger.info(f"✅ Cookie 验证成功: {c.get('value')[:30]}...")
                            break
                    
                    if not found:
                        logger.warning(f"⚠️ Cookie 未找到，尝试备用方法...")
                        # 备用：使用 JavaScript 设置
                        cookie_value = session_token.replace('"', '\\"')
                        cookie_js = f"document.cookie = 'WorkosCursorSessionToken={cookie_value}; path=/; domain=.cursor.com; Secure';"
                        tab.run_js(cookie_js)
                        
                except Exception as e:
                    logger.warning(f"设置 Cookie API 失败: {e}，尝试JS方法...")
                    try:
                        cookie_value = session_token.replace('"', '\\"')
                        cookie_js = f"document.cookie = 'WorkosCursorSessionToken={cookie_value}; path=/; domain=.cursor.com';"
                        tab.run_js(cookie_js)
                    except:
                        pass
                
                logger.info(f"\n步骤2: 访问深度登录页面...")
                logger.info(f"URL: {login_url}")
                
                # 访问深度登录页面（现在Cookie中已有 SessionToken）
                tab.get(login_url)
                time.sleep(3)
                
                logger.info(f"当前页面: {tab.url}")
                
                # 步骤1.5: 检测并处理 Data Sharing 页面（可能出现）
                logger.info("\n步骤1.5: 检测 Data Sharing 页面...")
                try:
                    from .registration_steps import RegistrationSteps
                    RegistrationSteps.handle_data_sharing_page(tab)
                except Exception as e:
                    logger.warning(f"检测 Data Sharing 页面时出错: {e}")
                
                # 步骤2: 查找"Yes, Log In"按钮
                logger.info("\n步骤2: 查找确认登录按钮...")
                
                try:
                    # 等待按钮出现（最多5秒）
                    login_button = None
                    for i in range(10):
                        login_button = tab.ele("xpath://span[contains(text(), 'Yes, Log In')]", timeout=0.5)
                        if not login_button:
                            login_button = tab.ele("xpath://button[contains(text(), 'Yes')]", timeout=0.5)
                        
                        if login_button:
                            logger.info(f"✅ 找到确认按钮（等待{i}秒）")
                            break
                        
                        if i % 2 == 0:
                            logger.info(f"等待按钮出现... ({i}/10秒)")
                        time.sleep(1)
                    
                    if not login_button:
                        logger.warning("⚠️ 未找到确认按钮")
                        logger.warning("   可能原因：")
                        logger.warning("   1. SessionToken 无效或已过期")
                        logger.warning("   2. 页面结构已改变")
                        logger.warning("   3. 需要用户手动确认")
                        
                        attempts += 1
                        if attempts < max_attempts:
                            logger.info(f"3秒后重试...")
                            time.sleep(3)
                        continue
                    
                    # 步骤3: 点击确认按钮
                    logger.info("\n步骤3: 点击确认登录...")
                    login_button.click()
                    time.sleep(2)
                    
                    logger.info("✅ 已点击确认")
                    
                    # 步骤4: 轮询API获取accessToken
                    logger.info("\n步骤4: 轮询API获取 accessToken...")
                    
                    poll_url = f"https://api2.cursor.sh/auth/poll?uuid={uuid_str}&verifier={verifier}"
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Cursor/0.48.6 Chrome/132.0.6834.210 Electron/34.3.4 Safari/537.36",
                        "Accept": "*/*"
                    }
                    
                    logger.info(f"轮询URL: {poll_url}")
                    
                    response = requests.get(poll_url, headers=headers, timeout=10)
                    
                    logger.info(f"响应状态码: {response.status_code}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        access_token = data.get("accessToken")
                        auth_id = data.get("authId", "")
                        
                        if access_token:
                            logger.info("\n" + "="*60)
                            logger.info("✅ 成功获取 accessToken！")
                            logger.info("="*60)
                            logger.info(f"accessToken: {access_token[:50]}...")
                            logger.info(f"authId: {auth_id}")
                            logger.info(f"Token长度: {len(access_token)} 字符")
                            
                            # 解析JWT查看type
                            try:
                                import json
                                parts = access_token.split('.')
                                if len(parts) >= 2:
                                    payload = parts[1]
                                    padding = len(payload) % 4
                                    if padding:
                                        payload += '=' * (4 - padding)
                                    
                                    decoded = base64.urlsafe_b64decode(payload)
                                    token_data = json.loads(decoded)
                                    
                                    token_type = token_data.get('type')
                                    logger.info(f"Token Type: {token_type}")
                                    
                                    if token_type == 'session':
                                        logger.info("✅ 这是正确的 accessToken (type=session)！")
                                    else:
                                        logger.warning(f"⚠️ Token type 不是 session: {token_type}")
                            except:
                                pass
                            
                            logger.info("="*60)
                            
                            return access_token
                        else:
                            logger.error("❌ 响应中没有 accessToken")
                    else:
                        logger.error(f"❌ API请求失败，状态码: {response.status_code}")
                        logger.error(f"响应内容: {response.text}")
                
                except Exception as e:
                    logger.error(f"处理过程出错: {e}")
                
                attempts += 1
                if attempts < max_attempts:
                    wait_time = 3 * attempts
                    logger.warning(f"\n第 {attempts} 次尝试失败，{wait_time}秒后重试...")
                    time.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"深度登录失败: {e}")
                attempts += 1
                if attempts < max_attempts:
                    time.sleep(3 * attempts)
        
        logger.error(f"\n在 {max_attempts} 次尝试后仍未获取到 accessToken")
        return None
    
    @staticmethod
    def get_session_token_from_cookies(tab) -> str:
        """
        从浏览器 Cookie 中获取 SessionToken
        
        Args:
            tab: DrissionPage 的 tab 对象
            
        Returns:
            str: SessionToken 或 None
        """
        try:
            cookies = tab.cookies()
            
            for cookie in cookies:
                if cookie.get("name") == "WorkosCursorSessionToken":
                    token_value = cookie["value"]
                    logger.info(f"✅ 从 Cookie 获取到 SessionToken")
                    logger.info(f"   Token: {token_value[:50]}...")
                    return token_value
            
            logger.warning("⚠️ Cookie 中未找到 WorkosCursorSessionToken")
            return None
            
        except Exception as e:
            logger.error(f"获取 SessionToken 失败: {e}")
            return None



