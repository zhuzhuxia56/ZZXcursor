#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Augment Code 授权处理模块
使用PKCE (Proof Key for Code Exchange) 流程
"""

import hashlib
import base64
import secrets
import random
import string
import urllib.parse
from utils.logger import get_logger

logger = get_logger("aug_auth")


class AugmentAuth:
    """Augment授权处理器"""
    
    @staticmethod
    def generate_code_verifier():
        """
        生成code_verifier（PKCE）
        
        Returns:
            str: code_verifier (43-128位随机字符串)
        """
        # 生成43位随机字符串（base64url安全字符）
        verifier = secrets.token_urlsafe(32)  # 生成43个字符
        return verifier
    
    @staticmethod
    def generate_code_challenge(code_verifier):
        """
        生成code_challenge（PKCE）
        
        Args:
            code_verifier: code_verifier字符串
            
        Returns:
            str: code_challenge (SHA256后base64url编码)
        """
        # SHA256哈希
        digest = hashlib.sha256(code_verifier.encode('ascii')).digest()
        
        # Base64 URL编码（去除padding）
        challenge = base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')
        
        return challenge
    
    @staticmethod
    def generate_short_state():
        """
        生成短state字符串
        
        Returns:
            str: 短随机state (如 8N20W8_xzj4)
        """
        # 生成11位随机字符串（字母+数字+下划线）
        chars = string.ascii_letters + string.digits + '_'
        state = ''.join(random.choices(chars, k=11))
        return state
    
    @staticmethod
    def generate_authorize_url():
        """
        生成Augment授权链接（PKCE流程）
        
        Returns:
            tuple: (授权URL, code_verifier, state)
        """
        # 1. 生成code_verifier
        code_verifier = AugmentAuth.generate_code_verifier()
        
        # 2. 计算code_challenge
        code_challenge = AugmentAuth.generate_code_challenge(code_verifier)
        
        # 3. 生成短state
        state = AugmentAuth.generate_short_state()
        
        logger.info(f"生成PKCE参数:")
        logger.info(f"  code_verifier: {code_verifier[:20]}...")
        logger.info(f"  code_challenge: {code_challenge}")
        logger.info(f"  state: {state}")
        
        # 4. 构建授权参数
        params = {
            'response_type': 'code',
            'code_challenge': code_challenge,
            'client_id': 'v',  # Aug使用的client_id是'v'
            'state': state,
            'prompt': 'login'
        }
        
        # 5. 构建URL
        base_url = 'https://auth.augmentcode.com/authorize'
        query_string = urllib.parse.urlencode(params)
        authorize_url = f"{base_url}?{query_string}"
        
        logger.info(f"生成授权链接: {authorize_url}")
        
        return authorize_url, code_verifier, state
    
    @staticmethod
    def generate_push_login_uri(tenant_url, access_token):
        """
        生成VSCode深链接（用于推送登录）
        
        Args:
            tenant_url: 租户URL（如：https://d5.api.augmentcode.com/）
            access_token: 访问令牌
            
        Returns:
            str: VSCode深链接
        """
        # 编码参数
        params = {
            'url': tenant_url,
            'token': access_token
        }
        
        query_string = urllib.parse.urlencode(params)
        deep_link = f"vscode://augment.augment-vscode/autoAuth/push-login?{query_string}"
        
        logger.info(f"生成推送登录链接: {deep_link}")
        
        return deep_link
    
    @staticmethod
    def parse_callback_url(callback_url):
        """
        解析授权回调URL
        
        Args:
            callback_url: 回调URL
            
        Returns:
            dict: 包含code、state等参数
        """
        try:
            # 解析URL
            parsed = urllib.parse.urlparse(callback_url)
            params = urllib.parse.parse_qs(parsed.query)
            
            result = {
                'code': params.get('code', [None])[0],
                'state': params.get('state', [None])[0],
                'error': params.get('error', [None])[0],
                'error_description': params.get('error_description', [None])[0]
            }
            
            logger.info(f"解析回调URL: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"解析回调URL失败: {e}")
            return {}
    
    @staticmethod
    def get_tenant_url_from_api_domain(api_domain):
        """
        从API域名获取租户URL
        
        Args:
            api_domain: API域名（如：d14.api.augmentcode.com）
            
        Returns:
            str: 租户URL
        """
        # 确保有协议
        if not api_domain.startswith('http'):
            api_domain = f"https://{api_domain}"
        
        # 确保以/结尾
        if not api_domain.endswith('/'):
            api_domain += '/'
        
        return api_domain

