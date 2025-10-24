#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用路径管理
获取应用数据目录（用户目录）
"""

import os
from pathlib import Path


def get_app_data_dir() -> Path:
    """
    获取应用数据目录
    
    Returns:
        Path: 应用数据目录路径
    """
    if os.name == 'nt':  # Windows
        appdata = os.getenv('APPDATA')
        if not appdata:
            appdata = Path.home() / 'AppData' / 'Roaming'
        else:
            appdata = Path(appdata)
    elif os.name == 'posix':  # Linux/Mac
        appdata = Path.home() / '.config'
    else:
        appdata = Path.home()
    
    # 应用数据目录
    app_dir = appdata / 'Zzx-Cursor-Auto'
    
    # 确保目录存在
    app_dir.mkdir(parents=True, exist_ok=True)
    
    return app_dir


def get_config_file() -> Path:
    """获取配置文件路径"""
    return get_app_data_dir() / 'config.json'


def get_data_dir() -> Path:
    """获取数据目录"""
    data_dir = get_app_data_dir() / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_database_file() -> Path:
    """获取数据库文件路径"""
    return get_data_dir() / 'accounts.db'


def get_key_file() -> Path:
    """获取加密密钥文件路径"""
    return get_data_dir() / '.key'


def get_logs_dir() -> Path:
    """获取日志目录"""
    logs_dir = get_data_dir() / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir

