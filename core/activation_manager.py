#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
激活管理器
本地激活码验证和注册限制管理
"""

import sys
import json
import hashlib
from datetime import datetime, date
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import get_logger
from utils.app_paths import get_config_file

logger = get_logger("activation")


class ActivationManager:
    """激活管理器"""
    
    def __init__(self, config_file: str = None):
        # 使用用户目录的配置文件路径
        if config_file:
            self.config_file = Path(config_file)
        else:
            self.config_file = get_config_file()
        
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """加载配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return {}
    
    def _save_config(self):
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def is_activated(self) -> bool:
        """
        检查是否已激活
        
        Returns:
            bool: True表示已激活
        """
        license_info = self.config.get('license', {})
        return license_info.get('activated', False)
    
    def get_daily_limit(self) -> int:
        """
        获取每日注册限制
        
        Returns:
            int: 每日限制数量（0表示无限制）
        """
        if self.is_activated():
            return 0  # 已激活，无限制
        else:
            return 5  # 未激活，每天5个
    
    def get_today_registered_count(self) -> int:
        """
        获取今天已注册数量
        
        Returns:
            int: 今天已注册的账号数量
        """
        license_info = self.config.get('license', {})
        usage = license_info.get('daily_usage', {})
        
        today_str = date.today().isoformat()
        return usage.get(today_str, 0)
    
    def get_today_payment_count(self) -> int:
        """
        获取今天已绑卡数量
        
        Returns:
            int: 今天已绑卡的账号数量
        """
        license_info = self.config.get('license', {})
        payment_usage = license_info.get('daily_payment_usage', {})
        
        today_str = date.today().isoformat()
        return payment_usage.get(today_str, 0)
    
    def get_payment_daily_limit(self) -> int:
        """
        获取每日绑卡限制
        
        Returns:
            int: 每日限制数量（0表示无限制）
        """
        if self.is_activated():
            return 0  # 已激活，无限制
        else:
            return 5  # 未激活，每天5个
    
    def increment_daily_count(self) -> bool:
        """
        增加今天的注册计数
        
        Returns:
            bool: 是否成功
        """
        try:
            if 'license' not in self.config:
                self.config['license'] = {}
            if 'daily_usage' not in self.config['license']:
                self.config['license']['daily_usage'] = {}
            
            today_str = date.today().isoformat()
            current_count = self.config['license']['daily_usage'].get(today_str, 0)
            self.config['license']['daily_usage'][today_str] = current_count + 1
            
            # 只保留最近7天的记录
            self._cleanup_old_records()
            
            return self._save_config()
        except Exception as e:
            logger.error(f"增加计数失败: {e}")
            return False
    
    def increment_payment_count(self) -> bool:
        """
        增加今天的绑卡计数
        
        Returns:
            bool: 是否成功
        """
        try:
            if 'license' not in self.config:
                self.config['license'] = {}
            if 'daily_payment_usage' not in self.config['license']:
                self.config['license']['daily_payment_usage'] = {}
            
            today_str = date.today().isoformat()
            current_count = self.config['license']['daily_payment_usage'].get(today_str, 0)
            self.config['license']['daily_payment_usage'][today_str] = current_count + 1
            
            # 只保留最近7天的记录
            self._cleanup_old_payment_records()
            
            return self._save_config()
        except Exception as e:
            logger.error(f"增加绑卡计数失败: {e}")
            return False
    
    def _cleanup_old_records(self):
        """清理7天前的旧记录"""
        try:
            from datetime import timedelta
            
            if 'license' not in self.config or 'daily_usage' not in self.config['license']:
                return
            
            usage = self.config['license']['daily_usage']
            today = date.today()
            cutoff = today - timedelta(days=7)
            
            # 删除7天前的记录
            old_dates = [d for d in usage.keys() if d < cutoff.isoformat()]
            for old_date in old_dates:
                del usage[old_date]
                
        except Exception as e:
            logger.debug(f"清理旧记录失败: {e}")
    
    def _cleanup_old_payment_records(self):
        """清理7天前的绑卡旧记录"""
        try:
            from datetime import timedelta
            
            if 'license' not in self.config or 'daily_payment_usage' not in self.config['license']:
                return
            
            usage = self.config['license']['daily_payment_usage']
            today = date.today()
            cutoff = today - timedelta(days=7)
            
            # 删除7天前的记录
            old_dates = [d for d in usage.keys() if d < cutoff.isoformat()]
            for old_date in old_dates:
                del usage[old_date]
                
        except Exception as e:
            logger.debug(f"清理绑卡旧记录失败: {e}")
    
    def can_register(self) -> tuple:
        """
        检查是否可以注册
        
        Returns:
            tuple: (是否可以注册, 剩余额度, 提示信息)
        """
        if self.is_activated():
            return (True, -1, "已激活，无限制")
        
        limit = self.get_daily_limit()
        used = self.get_today_registered_count()
        remaining = limit - used
        
        if remaining > 0:
            return (True, remaining, f"未激活，今日剩余 {remaining}/{limit} 个")
        else:
            return (False, 0, f"未激活，今日额度已用完 ({limit}/{limit})")
    
    def can_bind_payment(self) -> tuple:
        """
        检查是否可以绑卡
        
        Returns:
            tuple: (是否可以绑卡, 剩余额度, 提示信息)
        """
        if self.is_activated():
            return (True, -1, "已激活，无限制")
        
        limit = self.get_payment_daily_limit()
        used = self.get_today_payment_count()
        remaining = limit - used
        
        if remaining > 0:
            return (True, remaining, f"未激活，今日剩余 {remaining}/{limit} 个")
        else:
            return (False, 0, f"未激活，今日绑卡额度已用完 ({limit}/{limit})")
    
    def activate(self, activation_code: str, machine_id: str = None) -> tuple:
        """
        激活设备（本地统一激活码验证）
        
        Args:
            activation_code: 激活码
            machine_id: 机器码（可选，统一激活码不需要）
            
        Returns:
            tuple: (是否成功, 提示信息)
        """
        try:
            # 验证激活码格式
            if not activation_code or len(activation_code) < 10:
                return (False, "激活码格式错误")
            
            # 验证统一激活码
            if self._verify_universal_activation_code(activation_code):
                # 激活成功
                if 'license' not in self.config:
                    self.config['license'] = {}
                
                self.config['license']['activated'] = True
                self.config['license']['activation_code'] = activation_code
                self.config['license']['machine_id'] = machine_id or 'universal'
                self.config['license']['activated_at'] = datetime.now().isoformat()
                
                if self._save_config():
                    logger.info(f"✅ 设备激活成功（统一激活码）")
                    return (True, "激活成功！每日注册无限制")
                else:
                    return (False, "保存激活状态失败")
            else:
                logger.warning(f"激活码验证失败")
                return (False, "激活码无效")
                
        except Exception as e:
            logger.error(f"激活失败: {e}")
            return (False, f"激活异常: {str(e)}")
    
    def _verify_universal_activation_code(self, code: str) -> bool:
        """
        验证统一激活码（所有用户通用）
        
        Args:
            code: 用户输入的激活码
            
        Returns:
            bool: 是否有效
        """
        # 移除激活码中的分隔符和空格
        clean_code = code.replace('-', '').replace(' ', '').upper()
        
        # 生成统一激活码的哈希值
        # 使用多层加密确保安全性
        secret_key = "ZZX-CURSOR-AUTO-2025"  # 密钥
        salt = "UNIVERSAL-ACTIVATION"        # 盐值
        
        # 第一层：基础哈希
        base_hash = hashlib.sha256(f"{secret_key}-{salt}".encode()).hexdigest()
        
        # 第二层：MD5混合（增加复杂度）
        mixed_hash = hashlib.md5(base_hash.encode()).hexdigest()
        
        # 第三层：SHA256最终加密
        final_hash = hashlib.sha256(f"{mixed_hash}-{secret_key}".encode()).hexdigest()
        
        # 取前16位作为激活码
        valid_code = final_hash[:16].upper()
        
        # 验证
        return clean_code == valid_code
    
    def generate_universal_activation_code(self) -> str:
        """
        生成统一激活码（管理员使用）
        
        Returns:
            str: 格式化的激活码 (XXXX-XXXX-XXXX-XXXX)
        """
        # 使用与验证相同的加密逻辑
        secret_key = "ZZX-CURSOR-AUTO-2025"
        salt = "UNIVERSAL-ACTIVATION"
        
        # 多层加密
        base_hash = hashlib.sha256(f"{secret_key}-{salt}".encode()).hexdigest()
        mixed_hash = hashlib.md5(base_hash.encode()).hexdigest()
        final_hash = hashlib.sha256(f"{mixed_hash}-{secret_key}".encode()).hexdigest()
        
        # 取前16位
        code = final_hash[:16].upper()
        
        # 格式化为 XXXX-XXXX-XXXX-XXXX
        formatted = f"{code[:4]}-{code[4:8]}-{code[8:12]}-{code[12:16]}"
        
        logger.info(f"✨ 统一激活码: {formatted}")
        
        return formatted
    
    def _generate_local_activation_code(self, machine_id: str) -> str:
        """
        生成本地测试用的激活码（已弃用）
        （现在使用统一激活码）
        
        Args:
            machine_id: 机器码
            
        Returns:
            str: 激活码
        """
        # 使用机器码生成激活码（已弃用）
        hash_result = hashlib.sha256(f"ACTIVATION-{machine_id}".encode()).hexdigest()
        activation_code = hash_result[:12].upper()
        
        # 格式化为 XXXX-XXXX-XXXX
        formatted = f"{activation_code[:4]}-{activation_code[4:8]}-{activation_code[8:12]}"
        
        logger.debug(f"💡 本地测试激活码（已弃用）: {formatted}")
        
        return formatted
    
    def get_activation_info(self) -> dict:
        """
        获取激活信息
        
        Returns:
            dict: 激活信息
        """
        license_info = self.config.get('license', {})
        
        return {
            'activated': license_info.get('activated', False),
            'machine_id': license_info.get('machine_id'),
            'activation_code': license_info.get('activation_code'),
            'activated_at': license_info.get('activated_at'),
            'daily_limit': self.get_daily_limit(),
            'today_used': self.get_today_registered_count(),
            'today_remaining': self.get_daily_limit() - self.get_today_registered_count() if not self.is_activated() else -1
        }
    
    def deactivate(self) -> bool:
        """
        解除激活（用于测试）
        
        Returns:
            bool: 是否成功
        """
        try:
            if 'license' in self.config:
                self.config['license']['activated'] = False
                if self._save_config():
                    logger.info("✅ 已解除激活")
                    return True
            return False
        except Exception as e:
            logger.error(f"解除激活失败: {e}")
            return False


# 全局单例
_activation_manager = None

def get_activation_manager():
    """获取激活管理器单例"""
    global _activation_manager
    if _activation_manager is None:
        _activation_manager = ActivationManager()
    return _activation_manager

