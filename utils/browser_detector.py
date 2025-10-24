#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
浏览器检测工具
检测系统中是否安装了 Chrome 或 Edge 浏览器
"""

from pathlib import Path
from typing import Tuple


def detect_chrome() -> Tuple[bool, str]:
    """
    检测 Chrome 浏览器
    
    Returns:
        tuple: (是否安装, 浏览器路径)
    """
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe",
    ]
    
    for path in chrome_paths:
        p = Path(path)
        if p.exists():
            return True, str(p)
    
    return False, ""


def detect_edge() -> Tuple[bool, str]:
    """
    检测 Edge 浏览器
    
    Returns:
        tuple: (是否安装, 浏览器路径)
    """
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    
    for path in edge_paths:
        p = Path(path)
        if p.exists():
            return True, str(p)
    
    return False, ""


def detect_any_browser() -> Tuple[bool, str, str]:
    """
    检测任意可用的浏览器（Chrome 或 Edge）
    
    Returns:
        tuple: (是否有浏览器, 浏览器类型, 浏览器路径)
    """
    # 优先检测 Chrome
    has_chrome, chrome_path = detect_chrome()
    if has_chrome:
        return True, "Chrome", chrome_path
    
    # 其次检测 Edge
    has_edge, edge_path = detect_edge()
    if has_edge:
        return True, "Edge", edge_path
    
    return False, "", ""


def get_browser_status() -> dict:
    """
    获取浏览器状态详情
    
    Returns:
        dict: 浏览器状态信息
    """
    has_chrome, chrome_path = detect_chrome()
    has_edge, edge_path = detect_edge()
    has_any, browser_type, browser_path = detect_any_browser()
    
    return {
        'has_chrome': has_chrome,
        'chrome_path': chrome_path,
        'has_edge': has_edge,
        'edge_path': edge_path,
        'has_any_browser': has_any,
        'preferred_browser': browser_type,
        'preferred_path': browser_path,
    }

