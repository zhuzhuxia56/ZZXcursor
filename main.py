#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zzx-Cursor-Auto 主程序入口
自动化 Cursor 账号管理系统
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

# 强制导入关键模块（确保 PyInstaller 打包）
import requests  # HTTP 请求
import urllib3   # HTTP 底层库
import jwt       # JWT Token 解析

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from gui.main_window import MainWindow
from gui.dialogs.splash_screen import show_splash_screen
from utils.logger import setup_logger
from utils.browser_detector import detect_any_browser


def exception_hook(exc_type, exc_value, exc_traceback):
    """全局异常处理钩子"""
    import traceback
    logger = setup_logger()
    
    # 记录异常到日志
    logger.error("=" * 80)
    logger.error("!!! 未捕获的异常 !!!")
    logger.error("=" * 80)
    logger.error(f"异常类型: {exc_type.__name__}")
    logger.error(f"异常信息: {exc_value}")
    logger.error("异常堆栈:")
    for line in traceback.format_tb(exc_traceback):
        logger.error(line.rstrip())
    logger.error("=" * 80)
    
    # 调用默认处理器
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


def init_config_file():
    """初始化配置文件（首次运行时）"""
    import json
    from utils.app_paths import get_config_file, get_app_data_dir
    
    config_file = get_config_file()
    
    # 如果配置文件不存在，创建默认配置
    if not config_file.exists():
        default_config = {
            "email": {
                "domain": "",
                "receiving_email": "",
                "receiving_email_pin": ""
            },
            "phone_verification": {
                "enabled": False,
                "custom_code": ""
            },
            "payment_binding": {
                "enabled": False,
                "auto_fill": False,
                "card_mode": "import",
                "auto_gen_unlocked": False
            },
            "browser": {
                "incognito_mode": True,
                "headless": False
            },
            "theme": {
                "current_theme": "light",
                "auto_switch": False,
                "dark_start_time": "19:00",
                "light_start_time": "07:00"
            },
            "ui": {
                "enable_animations": True,
                "animation_speed": "normal",
                "reduce_motion": False
            },
            "performance": {
                "batch_concurrent": 2,
                "card_animation_threshold": 50
            },
            "auto_detect": {
                "enabled": True,
                "interval": 30
            },
            "license": {
                "activated": False,
                "machine_id": ""
            }
        }
        
        # 创建配置文件
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        
        return True  # 首次运行
    
    return False  # 已有配置


def main():
    """主函数"""
    # 初始化配置文件
    is_first_run = init_config_file()
    
    # 初始化日志
    logger = setup_logger()
    logger.info("="*60)
    logger.info("Zzx-Cursor-Auto 启动")
    if is_first_run:
        logger.info("首次运行，已创建默认配置文件")
    logger.info("="*60)
    
    # 设置全局异常钩子
    sys.excepthook = exception_hook
    
    # ⭐ 扫描并保存设备机器码
    try:
        from core.machine_id_manager import get_machine_id_manager
        machine_mgr = get_machine_id_manager()
        
        # 尝试从配置加载
        machine_id = machine_mgr.load_machine_id()
        if not machine_id:
            # 首次运行，生成机器码
            logger.info("首次运行，正在生成设备机器码...")
            machine_id = machine_mgr.get_machine_id()
            machine_mgr.save_machine_id(machine_id)
        else:
            logger.info(f"设备机器码: {machine_id[:16]}...")
    except Exception as e:
        logger.error(f"机器码初始化失败: {e}")
    
    try:
        # 创建应用
        app = QApplication(sys.argv)
        app.setApplicationName("Zzx Cursor Auto Manager")
        app.setOrganizationName("Zzx Dev")
        
        # 设置应用图标和样式
        app.setQuitOnLastWindowClosed(True)
        
        # ⭐ 全局禁用系统提示音（避免弹窗太吵）
        try:
            QApplication.beep = lambda: None
            logger.info("已禁用系统提示音")
        except Exception as e:
            logger.warning(f"禁用系统提示音失败: {e}")
        
        # ⭐ 检测浏览器（Chrome 或 Edge）
        logger.info("检测浏览器...")
        has_browser, browser_type, browser_path = detect_any_browser()
        
        if not has_browser:
            logger.warning("未检测到 Chrome 或 Edge 浏览器")
            # 显示友好提示
            msg = QMessageBox()
            msg.setWindowTitle("浏览器检测")
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setText(
                "未检测到 Chrome 或 Edge 浏览器！\n\n"
                "自动注册功能需要 Chrome 浏览器支持。"
            )
            msg.setInformativeText(
                "Windows 10/11 用户可以使用系统自带的 Edge 浏览器\n\n"
                "或点击下载 Chrome：https://www.google.com/chrome/\n\n"
                "您仍然可以使用账号管理、配置等功能"
            )
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.setDefaultButton(QMessageBox.StandardButton.Ok)
            msg.exec()
        else:
            logger.info(f"✓ 检测到浏览器: {browser_type} ({browser_path})")
        
        logger.info("显示启动画面...")
        
        # 显示启动画面并获取检测到的账号信息
        initialization_success, detected_account = show_splash_screen()
        
        if not initialization_success:
            logger.warning("启动画面显示失败，但继续启动程序")
        
        if detected_account:
            email = detected_account.get('email', '未知')
            plan = detected_account.get('membership_type', 'free').upper()
            logger.info(f"启动画面完成，已检测账号: {email} ({plan})")
        else:
            logger.info("启动画面完成，未检测到账号")
        
        logger.info("创建主窗口...")
        
        # 创建主窗口，传递检测到的账号信息
        try:
            window = MainWindow(pre_detected_account=detected_account)
            window.show()
            
            logger.info("主窗口已显示")
            
        except Exception as e:
            logger.error(f"创建主窗口失败: {e}")
            QMessageBox.critical(
                None,
                "启动失败", 
                f"无法创建主窗口：\n{str(e)}\n\n请查看日志文件了解详情。"
            )
            return 1
        
        # 运行应用
        exit_code = app.exec()
        
        logger.info(f"应用退出，退出码: {exit_code}")
        return exit_code
        
    except Exception as e:
        logger.exception(f"程序运行异常: {e}")
        # 显示错误对话框
        try:
            if 'app' in locals():
                QMessageBox.critical(
                    None,
                    "程序错误", 
                    f"程序启动时发生严重错误：\n{str(e)}\n\n请查看日志文件了解详情。"
                )
        except:
            pass
        return 1


if __name__ == '__main__':
    sys.exit(main())

