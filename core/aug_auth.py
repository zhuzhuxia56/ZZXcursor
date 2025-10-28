#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Augment Code 授权处理模块
"""

import uuid
import urllib.parse
from utils.logger import get_logger

logger = get_logger("aug_auth")


class AugmentAuth:
    """Augment授权处理器"""
    
    @staticmethod
    def generate_authorize_url(state=None):
        """
        生成Augment授权链接
        
        Args:
            state: 状态参数（可选，用于防CSRF）
            
        Returns:
            str: 授权URL
        """
        # 生成随机state（如果未提供）
        if not state:
            state = str(uuid.uuid4())
        
        # Augment授权参数
        params = {
            'response_type': 'code',
            'client_id': 'augment',  # Augment的client_id
            'redirect_uri': 'vscode://augment.augment-vscode/callback',
            'scope': 'openid email profile',
            'state': state,
            'prompt': 'login'  # 强制显示登录页面
        }
        
        # 构建URL
        base_url = 'https://auth.augmentcode.com/authorize'
        query_string = urllib.parse.urlencode(params)
        authorize_url = f"{base_url}?{query_string}"
        
        logger.info(f"生成授权链接: {authorize_url}")
        
        return authorize_url
    
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

