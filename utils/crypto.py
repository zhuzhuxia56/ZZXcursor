#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
加密工具模块
使用 cryptography 库实现数据加密
"""

import base64
import os
import sys
from cryptography.fernet import Fernet
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.app_paths import get_key_file


class CryptoManager:
    """加密管理器（使用固定通用密钥）"""
    
    # 固定的通用加密密钥（所有用户共享）
    # 这样导出的账号数据可以在任何安装了软件的电脑上导入使用
    UNIVERSAL_KEY = b'ZZX-CURSOR-AUTO-2025-UNIVERSAL-ENCRYPTION-KEY-FOR-DATA-SHARING=='
    
    def __init__(self, key_file: str = None):
        """
        初始化加密管理器
        
        Args:
            key_file: 密钥文件路径（可选，使用固定密钥）
        """
        # 使用用户目录的密钥文件路径
        if key_file:
            self.key_file = Path(key_file)
        else:
            self.key_file = get_key_file()
        
        self.key = self._get_universal_key()
        self.fernet = Fernet(self.key)
    
    def _get_universal_key(self) -> bytes:
        """
        获取通用加密密钥
        
        使用固定的通用密钥，确保所有用户的加密数据可以互相导入
        
        Returns:
            bytes: 加密密钥
        """
        # 使用固定的通用密钥（Base64 URL-safe 格式）
        import hashlib
        
        # 从固定字符串生成 Fernet 兼容的密钥
        key_source = "ZZX-CURSOR-AUTO-2025-UNIVERSAL-KEY"
        key_hash = hashlib.sha256(key_source.encode()).digest()
        key = base64.urlsafe_b64encode(key_hash)
        
        return key
    
    def encrypt(self, data: str) -> str:
        """
        加密数据
        
        Args:
            data: 明文数据
            
        Returns:
            str: 加密后的数据（Base64 编码）
        """
        if not data:
            return ""
        
        encrypted = self.fernet.encrypt(data.encode('utf-8'))
        return base64.b64encode(encrypted).decode('utf-8')
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        解密数据
        
        Args:
            encrypted_data: 加密的数据（Base64 编码）
            
        Returns:
            str: 解密后的明文
        """
        if not encrypted_data:
            return ""
        
        try:
            encrypted = base64.b64decode(encrypted_data.encode('utf-8'))
            decrypted = self.fernet.decrypt(encrypted)
            return decrypted.decode('utf-8')
        except Exception as e:
            raise ValueError(f"解密失败: {e}")
    
    def encrypt_dict(self, data: dict, fields: list) -> dict:
        """
        加密字典中的指定字段
        
        Args:
            data: 数据字典
            fields: 需要加密的字段列表
            
        Returns:
            dict: 加密后的字典
        """
        result = data.copy()
        for field in fields:
            if field in result and result[field]:
                result[field] = self.encrypt(str(result[field]))
        return result
    
    def decrypt_dict(self, data: dict, fields: list) -> dict:
        """
        解密字典中的指定字段
        
        Args:
            data: 数据字典
            fields: 需要解密的字段列表
            
        Returns:
            dict: 解密后的字典
        """
        result = data.copy()
        for field in fields:
            if field in result and result[field]:
                try:
                    result[field] = self.decrypt(result[field])
                except:
                    pass  # 解密失败时保留原值
        return result


# 全局加密管理器实例
_crypto_manager = None


def get_crypto_manager() -> CryptoManager:
    """
    获取全局加密管理器实例（单例）
    
    Returns:
        CryptoManager: 加密管理器实例
    """
    global _crypto_manager
    if _crypto_manager is None:
        _crypto_manager = CryptoManager()
    return _crypto_manager


def encrypt_data(data: str) -> str:
    """
    加密数据（便捷函数）
    
    Args:
        data: 明文数据
        
    Returns:
        str: 加密后的数据
    """
    return get_crypto_manager().encrypt(data)


def decrypt_data(encrypted_data: str) -> str:
    """
    解密数据（便捷函数）
    
    Args:
        encrypted_data: 加密的数据
        
    Returns:
        str: 解密后的明文
    """
    return get_crypto_manager().decrypt(encrypted_data)

