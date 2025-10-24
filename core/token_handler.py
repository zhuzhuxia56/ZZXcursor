#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Token 处理模块
负责从页面获取 Token 并保存到数据库
"""

from typing import Optional
from .deep_token_getter import DeepTokenGetter
from utils.logger import get_logger

logger = get_logger("token_handler")


class TokenHandler:
    """Token 处理器"""
    
    @staticmethod
    def get_access_token(tab) -> Optional[str]:
        """
        获取 accessToken（深度登录方法）
        
        Args:
            tab: DrissionPage 的 tab 对象
            
        Returns:
            Optional[str]: accessToken 或 None
        """
        logger.info("\n" + "="*60)
        logger.info("开始获取 accessToken（深度登录）")
        logger.info("="*60)
        
        # 通过深度登录获取（使用 SessionToken）
        logger.info("\n首先获取 SessionToken...")
        
        session_token = DeepTokenGetter.get_session_token_from_cookies(tab)
        if not session_token:
            logger.error("❌ 未找到 SessionToken，无法继续")
            return None
        
        logger.info("开始深度登录流程...")
        access_token = DeepTokenGetter.get_access_token_from_session_token(
            tab,
            session_token,
            max_attempts=3
        )
        
        if access_token:
            logger.info("✅ 深度登录成功：获取到 accessToken (type=session)")
            return access_token
        
        logger.error("❌ 深度登录失败：未获取到 accessToken")
        return None
    
    @staticmethod
    def save_to_database(email: str, access_token: str, session_token: str = None):
        """
        保存账号到数据库（保存 accessToken 和 SessionToken）
        
        Args:
            email: 邮箱地址
            access_token: accessToken (type=session)
            session_token: SessionToken (type=web, 可选)
        """
        try:
            from core.account_storage import get_storage
            from datetime import datetime
            
            storage = get_storage()
            
            # 提取 User ID
            user_id = ''
            try:
                import base64
                import json
                parts = access_token.split('.')
                if len(parts) >= 2:
                    payload = parts[1]
                    padding = len(payload) % 4
                    if padding:
                        payload += '=' * (4 - padding)
                    decoded = base64.urlsafe_b64decode(payload)
                    token_data = json.loads(decoded)
                    user_id = token_data.get('sub', '').replace('auth0|', '')
                    logger.info(f"从 JWT 提取 User ID: {user_id}")
            except:
                pass
            
            # 生成机器码
            machine_info = None
            try:
                from core.machine_id_generator import generate_machine_info
                machine_info = generate_machine_info(platform='win32', user_id=user_id)
                logger.info(f"已生成机器码信息")
            except Exception as e:
                logger.warning(f"生成机器码失败: {e}")
            
            account_data = {
                'email': email,
                'password': '',
                'access_token': access_token,  # 保存 accessToken (加密)
                'refresh_token': access_token,  # 使用相同的 token (加密)
                'session_token': session_token or '',  # 保存 SessionToken (会被加密) ⭐
                'user_id': user_id,
                'machine_info': machine_info,  # 保存机器码 (加密)
                'membership_type': 'free',
                'days_remaining': 14,
                'usage_percent': 0.0,
                'used': 0,
                'limit_value': 1000,
                'status': 'active',
                'notes': f"自动注册于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
            
            account_id = storage.upsert_account(account_data)
            
            if account_id:
                logger.info(f"✅ 账号已保存 (ID: {account_id})")
                logger.info(f"   Email: {email}")
                logger.info(f"   User ID: {user_id}")
                logger.info(f"   accessToken: 已加密保存")
                if session_token:
                    logger.info(f"   SessionToken: 已明文保存")
                if machine_info:
                    logger.info(f"   机器码: 已加密保存（5个字段）")
            else:
                logger.warning("保存账号失败")
                
        except Exception as e:
            logger.error(f"保存失败: {e}")

