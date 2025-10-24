#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮箱生成器模块
基于用户域名和 Cloudflare 邮箱路由生成随机邮箱
"""

import re
import uuid
import random
import string
from typing import Optional


class EmailGenerator:
    """邮箱生成器类（支持域名池）"""
    
    def __init__(self, domain: str):
        """
        初始化邮箱生成器（支持多域名用 / 分隔）
        
        Args:
            domain: 邮箱域名（例如: yourdomain.com）
                   或多个域名用 / 分隔（例如: domain1.com/domain2.com/domain3.com）
        """
        # ========== 域名池支持（用 / 分隔多个域名）==========
        if "/" in domain:
            # 多个域名，分割成列表
            self.domain_pool = [d.strip().lstrip('@') for d in domain.split("/") if d.strip()]
            self.domain = self.domain_pool[0]  # 默认使用第一个
            print(f"✅ 检测到域名池（共 {len(self.domain_pool)} 个）: {', '.join(self.domain_pool)}")
        else:
            # 单个域名
            self.domain = domain.lstrip('@')
            self.domain_pool = [self.domain]
    
    def _get_random_domain(self) -> str:
        """从域名池中随机选择一个域名
        
        Returns:
            str: 随机选择的域名
        """
        if len(self.domain_pool) > 1:
            selected = random.choice(self.domain_pool)
            print(f"🎲 从域名池随机抽取: {selected} (共 {len(self.domain_pool)} 个可用)")
            return selected
        return self.domain_pool[0]
    
    def generate_random_email(self, prefix: str = "cursor", length: int = 8) -> str:
        """
        生成随机邮箱地址（从域名池中随机选择域名）
        
        Args:
            prefix: 邮箱前缀
            length: 随机字符串长度
            
        Returns:
            str: 邮箱地址
        """
        # ========== 从域名池中随机选择域名 ==========
        domain = self._get_random_domain()
        
        # 生成随机字符串
        random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
        
        # 组合邮箱
        email = f"{prefix}_{random_str}@{domain}"
        
        return email
    
    def generate_uuid_email(self, prefix: str = "cursor") -> str:
        """
        使用 UUID 生成邮箱地址（从域名池中随机选择域名）
        
        Args:
            prefix: 邮箱前缀
            
        Returns:
            str: 邮箱地址
        """
        # ========== 从域名池中随机选择域名 ==========
        domain = self._get_random_domain()
        
        # 使用 UUID 的前 8 位
        uuid_str = uuid.uuid4().hex[:8]
        
        return f"{prefix}_{uuid_str}@{domain}"
    
    def generate_timestamp_email(self, prefix: str = "cursor") -> str:
        """
        使用时间戳生成邮箱地址（从域名池中随机选择域名）
        
        Args:
            prefix: 邮箱前缀
            
        Returns:
            str: 邮箱地址
        """
        # ========== 从域名池中随机选择域名 ==========
        domain = self._get_random_domain()
        
        import time
        timestamp = str(int(time.time()))[-8:]  # 取时间戳后 8 位
        
        return f"{prefix}_{timestamp}@{domain}"
    
    def validate_email(self, email: str) -> bool:
        """
        验证邮箱地址格式
        
        Args:
            email: 邮箱地址
            
        Returns:
            bool: 是否有效
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def is_disposable_email(self, email: str) -> bool:
        """
        检查是否为临时邮箱
        
        Args:
            email: 邮箱地址
            
        Returns:
            bool: 是否为临时邮箱
        """
        # 常见的临时邮箱域名列表
        disposable_domains = [
            'tempmail.com', 'guerrillamail.com', '10minutemail.com',
            'mailinator.com', 'maildrop.cc', 'temp-mail.org'
        ]
        
        domain = email.split('@')[-1].lower()
        return domain in disposable_domains
    
    def parse_email(self, email: str) -> Optional[dict]:
        """
        解析邮箱地址
        
        Args:
            email: 邮箱地址
            
        Returns:
            dict: {'username': ..., 'domain': ...} 或 None
        """
        if not self.validate_email(email):
            return None
        
        parts = email.split('@')
        return {
            'username': parts[0],
            'domain': parts[1]
        }
    
    def generate_alias_email(self, base_email: str) -> str:
        """
        生成别名邮箱（Gmail 风格的 + 别名）
        
        Args:
            base_email: 基础邮箱地址
            
        Returns:
            str: 别名邮箱
        """
        parsed = self.parse_email(base_email)
        if not parsed:
            raise ValueError("无效的邮箱地址")
        
        # 生成随机别名
        alias = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        
        return f"{parsed['username']}+{alias}@{parsed['domain']}"


# 全局邮箱生成器实例
_email_generator = None


def init_email_generator(domain: str) -> EmailGenerator:
    """
    初始化全局邮箱生成器
    
    Args:
        domain: 邮箱域名
        
    Returns:
        EmailGenerator: 邮箱生成器实例
    """
    global _email_generator
    _email_generator = EmailGenerator(domain)
    return _email_generator


def get_email_generator() -> Optional[EmailGenerator]:
    """
    获取全局邮箱生成器实例
    
    Returns:
        EmailGenerator: 邮箱生成器实例或 None
    """
    return _email_generator


def generate_email(domain: str = None, prefix: str = "cursor") -> str:
    """
    生成邮箱地址（便捷函数）
    
    Args:
        domain: 邮箱域名（如果未设置全局生成器则必需）
        prefix: 邮箱前缀
        
    Returns:
        str: 邮箱地址
    """
    if domain:
        generator = EmailGenerator(domain)
    else:
        generator = get_email_generator()
        if not generator:
            raise ValueError("请先初始化邮箱生成器或提供域名")
    
    return generator.generate_random_email(prefix=prefix)

