#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zzx-Cursor-Auto 核心功能模块
"""

__version__ = "1.0.0"

# 导出核心类和便捷函数
from .cursor_config_scanner import CursorConfigScanner, get_scanner
from .current_account_detector import CurrentAccountDetector, get_detector, detect_current_account
from .cursor_api import CursorOfficialAPI, get_api_client
from .account_storage import AccountStorage, get_storage
from .cursor_switcher import CursorSwitcher, get_switcher

__all__ = [
    'CursorConfigScanner',
    'get_scanner',
    'CurrentAccountDetector',
    'get_detector',
    'detect_current_account',
    'CursorOfficialAPI',
    'get_api_client',
    'AccountStorage',
    'get_storage',
    'CursorSwitcher',
    'get_switcher',
]
