#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资源路径助手
解决 PyInstaller 打包后资源文件路径问题
"""

import sys
import os
from pathlib import Path


def get_resource_path(relative_path: str) -> Path:
    """
    获取资源文件的绝对路径
    
    在开发环境和打包后的环境中都能正确工作
    
    Args:
        relative_path: 相对于项目根目录的资源路径，例如 "gui/resources/images/xxx.gif"
    
    Returns:
        Path: 资源文件的绝对路径
    
    Examples:
        >>> get_resource_path("gui/resources/images/zhuzhuxia.gif")
        Path("C:/.../_internal/gui/resources/images/zhuzhuxia.gif")  # 打包后
        或
        Path("C:/.../Zzx-cursor-auto/gui/resources/images/zhuzhuxia.gif")  # 开发环境
    """
    try:
        # PyInstaller 创建临时文件夹，路径存储在 _MEIPASS 中
        base_path = Path(sys._MEIPASS)
    except AttributeError:
        # 如果不是打包环境，使用项目根目录
        # 假设此文件在 utils/ 目录下
        base_path = Path(__file__).parent.parent
    
    # 标准化路径分隔符（支持 / 和 \）
    relative_path = relative_path.replace('\\', '/').replace('/', os.sep)
    
    return base_path / relative_path


def get_gui_resource(resource_name: str) -> Path:
    """
    获取 GUI 资源文件路径的快捷方法
    
    Args:
        resource_name: 资源文件名，例如 "zhuzhuxia.gif" 或 "wechat_qr.jpg"
    
    Returns:
        Path: gui/resources/images/ 下的资源文件路径
    """
    return get_resource_path(f"gui/resources/images/{resource_name}")


def resource_exists(relative_path: str) -> bool:
    """
    检查资源文件是否存在
    
    Args:
        relative_path: 相对路径
    
    Returns:
        bool: 文件是否存在
    """
    return get_resource_path(relative_path).exists()

