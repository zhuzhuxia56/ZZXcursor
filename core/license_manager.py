#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
授权管理器（本地版）
管理每日注册次数限制和激活码验证
"""

import json
from pathlib import Path
from datetime import datetime, time
from typing import Optional, Tuple

from utils.logger import get_logger
from utils.crypto import encrypt_data, decrypt_data

logger = get_logger("license_manager")


class LicenseManager:
    """授权管理器（本地加密存储）"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.license_file = self.data_dir / "license.dat"
        self.license_data = self._load_license()
    
    def _load_license(self) -> dict:
        """加载授权数据"""
        try:
            if self.license_file.exists():
                with open(self.license_file, 'r', encoding='utf-8') as f:
                    encrypted = f.read()
                    # 解密
                    decrypted = decrypt_data(encrypted)
                    if decrypted:
                        return json.loads(decrypted)
        except Exception as e:
            logger.error(f"加载授权数据失败: {e}")
        
        # 默认数据
        return {
            'activated': False,  # 是否已激活
            'activation_code': None,  # 激活码
            'device_id': None,  # 绑定的设备ID
            'daily_usage': {},  # {date: count}
            'activated_at': None  # 激活时间
        }
    
    def _save_license(self):
        """保存授权数据（加密）"""
        try:
            data_json = json.dumps(self.license_data, ensure_ascii=False, indent=2)
            # 加密
            encrypted = encrypt_data(data_json)
            
            with open(self.license_file, 'w', encoding='utf-8') as f:
                f.write(encrypted)
            
            logger.debug("授权数据已保存")
            return True
        except Exception as e:
            logger.error(f"保存授权数据失败: {e}")
            return False
    
    def check_daily_limit(self, device_id: str) -> Tuple[bool, int]:
        """
        检查今日是否还有注册次数
        
        Args:
            device_id: 设备ID
            
        Returns:
            (是否允许, 剩余次数)
        """
        try:
            # ⭐ 检查激活状态（24小时限制）
            if self.license_data.get('activated'):
                # 检查是否在24小时内
                if self._check_activation_valid():
                    return True, 999  # 激活期内，无限制
                else:
                    # 激活已过期，自动失效
                    logger.info("激活已过期（超过24小时），自动失效")
                    self._auto_deactivate()
                    # 继续检查每日限制
            
            # 获取今天日期
            today = datetime.now().strftime("%Y-%m-%d")
            
            # 检查是否需要重置（每天早上6点重置）
            self._check_and_reset_daily()
            
            # 获取今日使用次数
            daily_usage = self.license_data.get('daily_usage', {})
            used_count = daily_usage.get(today, 0)
            
            # 每天限制5次
            MAX_DAILY = 5
            remaining = MAX_DAILY - used_count
            
            if remaining > 0:
                return True, remaining
            else:
                return False, 0
                
        except Exception as e:
            logger.error(f"检查每日限制失败: {e}")
            # 出错时允许（降级）
            return True, 5
    
    def _check_and_reset_daily(self):
        """检查并重置每日计数（早上6点重置）"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            current_time = datetime.now().time()
            reset_time = time(6, 0)  # 早上6:00
            
            daily_usage = self.license_data.get('daily_usage', {})
            
            # 清理旧日期的记录（只保留今天的）
            keys_to_remove = []
            for date_str in daily_usage.keys():
                if date_str != today:
                    keys_to_remove.append(date_str)
            
            for key in keys_to_remove:
                del daily_usage[key]
                logger.debug(f"清理旧记录: {key}")
            
            self.license_data['daily_usage'] = daily_usage
            
        except Exception as e:
            logger.error(f"重置每日计数失败: {e}")
    
    def increment_usage(self, device_id: str) -> bool:
        """
        增加今日使用次数（注册成功后调用）
        
        Args:
            device_id: 设备ID
            
        Returns:
            bool: 是否成功
        """
        try:
            # 如果已激活，不计数
            if self.license_data.get('activated'):
                logger.debug("已激活设备，不计数")
                return True
            
            today = datetime.now().strftime("%Y-%m-%d")
            
            if 'daily_usage' not in self.license_data:
                self.license_data['daily_usage'] = {}
            
            # 增加计数
            self.license_data['daily_usage'][today] = \
                self.license_data['daily_usage'].get(today, 0) + 1
            
            used = self.license_data['daily_usage'][today]
            logger.info(f"今日使用次数：{used}/5")
            
            # 保存
            return self._save_license()
            
        except Exception as e:
            logger.error(f"增加使用次数失败: {e}")
            return False
    
    def activate(self, device_id: str, activation_code: str) -> Tuple[bool, str]:
        """
        激活设备（本地版，简单验证格式）
        
        Args:
            device_id: 设备ID
            activation_code: 激活码
            
        Returns:
            (是否成功, 消息)
        """
        try:
            # ⭐ 本地版：简单验证激活码格式
            # 格式：XXXX-XXXX-XXXX（12位，包含横杠）
            if not activation_code or len(activation_code.replace('-', '')) != 12:
                return False, "激活码格式错误（应为XXXX-XXXX-XXXX）"
            
            # 检查是否已激活
            if self.license_data.get('activated'):
                old_code = self.license_data.get('activation_code', '')
                return False, f"设备已激活（激活码：{old_code[:4]}****）"
            
            # 激活设备
            self.license_data['activated'] = True
            self.license_data['activation_code'] = activation_code
            self.license_data['device_id'] = device_id
            self.license_data['activated_at'] = datetime.now().isoformat()
            
            # 保存
            if self._save_license():
                logger.info(f"✅ 设备已激活：{activation_code}")
                return True, "激活成功！现在可以无限制使用自动注册功能"
            else:
                return False, "保存激活信息失败"
                
        except Exception as e:
            logger.error(f"激活设备失败: {e}")
            return False, f"激活失败：{str(e)}"
    
    def deactivate(self) -> bool:
        """取消激活（解绑）"""
        try:
            self.license_data['activated'] = False
            self.license_data['activation_code'] = None
            self.license_data['activated_at'] = None
            
            logger.info("设备已解绑")
            return self._save_license()
            
        except Exception as e:
            logger.error(f"解绑失败: {e}")
            return False
    
    def _check_activation_valid(self) -> bool:
        """检查激活是否在24小时内有效"""
        try:
            if not self.license_data.get('activated'):
                return False
            
            activated_at = self.license_data.get('activated_at')
            if not activated_at:
                return False
            
            # 解析激活时间
            activated_time = datetime.fromisoformat(activated_at)
            current_time = datetime.now()
            
            # 计算时间差
            elapsed = (current_time - activated_time).total_seconds()
            
            # 24小时 = 86400秒
            if elapsed < 86400:
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"检查激活有效期失败: {e}")
            return False
    
    def _auto_deactivate(self):
        """自动失效（24小时过期）"""
        try:
            self.license_data['activated'] = False
            # ⭐ 保留激活码记录，但标记为已过期
            self.license_data['expired'] = True
            self._save_license()
            logger.info("激活已自动失效")
        except Exception as e:
            logger.error(f"自动失效失败: {e}")
    
    def get_activation_time_remaining(self) -> Tuple[bool, int]:
        """
        获取激活剩余时间
        
        Returns:
            (是否激活, 剩余秒数)
        """
        try:
            if not self.license_data.get('activated'):
                return False, 0
            
            activated_at = self.license_data.get('activated_at')
            if not activated_at:
                return False, 0
            
            activated_time = datetime.fromisoformat(activated_at)
            current_time = datetime.now()
            
            elapsed = (current_time - activated_time).total_seconds()
            remaining = max(0, 86400 - elapsed)  # 24小时
            
            if remaining > 0:
                return True, int(remaining)
            else:
                return False, 0
                
        except Exception as e:
            logger.error(f"获取剩余时间失败: {e}")
            return False, 0
    
    def is_activated(self) -> bool:
        """判断是否已激活（且在24小时内）"""
        if not self.license_data.get('activated'):
            return False
        return self._check_activation_valid()
    
    def get_activation_info(self) -> dict:
        """获取激活信息"""
        return {
            'activated': self.license_data.get('activated', False),
            'activation_code': self.license_data.get('activation_code'),
            'activated_at': self.license_data.get('activated_at'),
            'device_id': self.license_data.get('device_id')
        }
    
    def get_daily_usage_info(self) -> dict:
        """获取今日使用信息"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            used = self.license_data.get('daily_usage', {}).get(today, 0)
            
            if self.is_activated():
                return {
                    'used': used,
                    'limit': 999,
                    'remaining': 999,
                    'unlimited': True
                }
            else:
                MAX_DAILY = 5
                return {
                    'used': used,
                    'limit': MAX_DAILY,
                    'remaining': max(0, MAX_DAILY - used),
                    'unlimited': False
                }
        except Exception as e:
            logger.error(f"获取使用信息失败: {e}")
            return {
                'used': 0,
                'limit': 5,
                'remaining': 5,
                'unlimited': False
            }


# 全局单例
_license_manager = None

def get_license_manager() -> LicenseManager:
    """获取授权管理器单例"""
    global _license_manager
    if _license_manager is None:
        _license_manager = LicenseManager()
    return _license_manager

