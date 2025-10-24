#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志工具模块
使用 loguru 实现日志记录
"""

import sys
import re
from pathlib import Path
from loguru import logger

# 导入路径管理
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.app_paths import get_logs_dir


def remove_emojis(text):
    """
    移除文本中的 emoji 符号（保留中文）
    用于控制台输出，避免 Windows GBK 编码问题
    只移除无法用 GBK 编码的 emoji，保留中文、英文、数字等
    """
    # 只移除 emoji 符号，不移除中文（中文范围: \u4e00-\u9fff）
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # 😀-😏 表情符号
        "\U0001F300-\U0001F5FF"  # 🌀-🗿 符号和图标
        "\U0001F680-\U0001F6FF"  # 🚀-🛿 交通和地图符号
        "\U0001F1E0-\U0001F1FF"  # 🇠-🇿 旗帜
        "\U0001F900-\U0001F9FF"  # 🤀-🧿 补充符号
        "\U0001FA00-\U0001FA6F"  # 🨀-🩯 扩展符号
        "\u2600-\u26FF"          # ☀-⛿ 杂项符号（包括 ✓✅⚠等）
        "\u2700-\u27BF"          # ✀-➿ 装饰符号
        "\u2300-\u23FF"          # ⌀-⏿ 技术符号（包括 ⏰）
        "\uFE00-\uFE0F"          # 变体选择器
        "\u200d"                 # 零宽连字符
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub('', text)


def setup_logger(log_dir: str = None):
    """
    设置日志记录器（优化版：增强异常捕获和崩溃日志）
    
    Args:
        log_dir: 日志文件目录（可选，默认使用用户目录）
    """
    # 使用用户目录的日志路径
    if log_dir:
        log_path = Path(log_dir)
    else:
        log_path = get_logs_dir()
    
    log_path.mkdir(parents=True, exist_ok=True)
    
    # 移除默认的处理器
    logger.remove()
    
    # 添加控制台输出（彩色）
    # 只在有控制台时添加（打包后 console=False 时 sys.stdout 为 None）
    # ⭐ 注意：Windows 控制台默认使用 GBK 编码，无法显示 emoji
    # 解决方案：使用过滤器移除 emoji，避免编码错误
    if sys.stdout is not None:
        try:
            # 创建一个过滤器函数，移除消息中的 emoji
            def console_filter(record):
                """过滤控制台输出，移除 emoji"""
                record["message"] = remove_emojis(record["message"])
                return True
            
            logger.add(
                sys.stdout,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
                level="INFO",  # 控制台只显示 INFO 及以上级别
                colorize=False,  # ⭐ 禁用颜色避免编码问题
                catch=True,  # 捕获异常
                backtrace=False,
                diagnose=False,
                enqueue=False,  # ⭐ 同步输出
                filter=console_filter  # ⭐ 使用过滤器移除 emoji
            )
        except:
            pass  # 忽略控制台输出失败
    
    # 添加文件输出（普通日志）
    logger.add(
        log_path / "app_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="00:00",  # 每天轮转
        retention="7 days",  # 保留7天
        encoding="utf-8",
        enqueue=True,  # 异步写入
        catch=True,  # 捕获异常
        backtrace=True,  # ⭐ 记录堆栈跟踪
        diagnose=True   # ⭐ 记录诊断信息
    )
    
    # 添加错误日志文件
    logger.add(
        log_path / "error_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="00:00",
        retention="30 days",  # 错误日志保留30天
        encoding="utf-8",
        enqueue=True,
        catch=True,  # 捕获异常
        backtrace=True,  # ⭐ 完整堆栈跟踪
        diagnose=True   # ⭐ 详细诊断信息
    )
    
    # ⭐ 添加崩溃日志文件（记录所有未捕获的异常）
    # 注意：enqueue=False 时不能使用 exc_info（会导致序列化错误）
    logger.add(
        log_path / "crash_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="CRITICAL",
        rotation="10 MB",
        retention="90 days",  # 崩溃日志保留90天
        encoding="utf-8",
        enqueue=False,  # ⭐ 同步写入，确保崩溃时记录
        catch=True,
        backtrace=False,  # 禁用以避免序列化问题
        diagnose=False   # 禁用以避免序列化问题
    )
    
    # ⭐ 配置全局异常捕获器
    def handle_exception(exc_type, exc_value, exc_traceback):
        """捕获所有未处理的异常"""
        if issubclass(exc_type, KeyboardInterrupt):
            # 不记录 Ctrl+C
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger.critical("❌ 未捕获的异常导致程序崩溃", exc_info=(exc_type, exc_value, exc_traceback))
    
    sys.excepthook = handle_exception
    
    logger.info("日志系统初始化完成（已启用全局异常捕获）")
    return logger


def get_logger(name: str = None):
    """
    获取日志记录器
    
    Args:
        name: 模块名称
        
    Returns:
        logger: 日志记录器实例
    """
    return logger.bind(name=name) if name else logger


