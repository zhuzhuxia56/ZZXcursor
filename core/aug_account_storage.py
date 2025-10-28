#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aug账号存储模块
"""

import json
from pathlib import Path
from datetime import datetime
from utils.app_paths import get_config_file
from utils.logger import get_logger

logger = get_logger("aug_account_storage")


class AugAccountStorage:
    """Aug账号存储管理器"""
    
    def __init__(self):
        self.config_file = get_config_file()
    
    def _load_config(self):
        """加载配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return {}
    
    def _save_config(self, config):
        """保存配置"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def get_all_accounts(self):
        """获取所有Aug账号"""
        config = self._load_config()
        return config.get('aug_accounts', [])
    
    def add_account(self, account_data):
        """添加Aug账号"""
        try:
            config = self._load_config()
            
            if 'aug_accounts' not in config:
                config['aug_accounts'] = []
            
            # 添加时间戳
            if 'time' not in account_data:
                account_data['time'] = datetime.now().strftime('%Y/%m/%d %H:%M')
            
            # 添加状态
            if 'status' not in account_data:
                account_data['status'] = '正常'
            
            config['aug_accounts'].append(account_data)
            
            if self._save_config(config):
                logger.info(f"✅ 添加Aug账号: {account_data.get('email', 'N/A')}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"添加账号失败: {e}")
            return False
    
    def update_account(self, index, account_data):
        """更新Aug账号"""
        try:
            config = self._load_config()
            
            if 'aug_accounts' not in config or index >= len(config['aug_accounts']):
                logger.error(f"账号索引无效: {index}")
                return False
            
            config['aug_accounts'][index] = account_data
            
            if self._save_config(config):
                logger.info(f"✅ 更新Aug账号: {account_data.get('email', 'N/A')}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"更新账号失败: {e}")
            return False
    
    def delete_account(self, index):
        """删除Aug账号"""
        try:
            config = self._load_config()
            
            if 'aug_accounts' not in config or index >= len(config['aug_accounts']):
                logger.error(f"账号索引无效: {index}")
                return False
            
            deleted = config['aug_accounts'].pop(index)
            
            if self._save_config(config):
                logger.info(f"✅ 删除Aug账号: {deleted.get('email', 'N/A')}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"删除账号失败: {e}")
            return False


# 全局单例
_aug_storage = None

def get_aug_storage():
    """获取Aug账号存储单例"""
    global _aug_storage
    if _aug_storage is None:
        _aug_storage = AugAccountStorage()
    return _aug_storage

