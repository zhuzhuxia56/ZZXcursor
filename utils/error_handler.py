#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一错误处理模块
提供异常捕获、错误分类、用户友好的错误提示等功能
"""

import sys
import traceback
import functools
from typing import Optional, Callable, Type, Dict, Any, Union
from enum import Enum
from PyQt6.QtWidgets import QMessageBox, QWidget
from PyQt6.QtCore import QObject, pyqtSignal
from utils.logger import get_logger

logger = get_logger("error_handler")


class ErrorLevel(Enum):
    """错误级别枚举"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """错误分类枚举"""
    NETWORK = "network"          # 网络相关错误
    DATABASE = "database"        # 数据库相关错误
    FILE_IO = "file_io"         # 文件IO错误
    BROWSER = "browser"         # 浏览器相关错误
    API = "api"                 # API调用错误
    AUTHENTICATION = "auth"      # 认证相关错误
    VALIDATION = "validation"    # 数据验证错误
    PERMISSION = "permission"    # 权限相关错误
    RESOURCE = "resource"       # 资源相关错误（内存、磁盘等）
    UNKNOWN = "unknown"         # 未知错误


class AppError(Exception):
    """应用自定义异常基类"""
    
    def __init__(
        self, 
        message: str, 
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        level: ErrorLevel = ErrorLevel.ERROR,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.category = category
        self.level = level
        self.details = details or {}
        self.cause = cause
        self.timestamp = None
        
        # 记录时间戳
        import time
        self.timestamp = time.time()


class NetworkError(AppError):
    """网络相关错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.NETWORK, **kwargs)


class DatabaseError(AppError):
    """数据库相关错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.DATABASE, **kwargs)


class BrowserError(AppError):
    """浏览器相关错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.BROWSER, **kwargs)


class APIError(AppError):
    """API调用错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.API, **kwargs)


class AuthenticationError(AppError):
    """认证相关错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.AUTHENTICATION, **kwargs)


class ValidationError(AppError):
    """数据验证错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.VALIDATION, **kwargs)


class ErrorHandler(QObject):
    """错误处理器"""
    
    # 信号定义
    error_occurred = pyqtSignal(object)  # AppError对象
    critical_error = pyqtSignal(str)     # 严重错误消息
    
    def __init__(self):
        super().__init__()
        
        # 错误统计
        self._error_stats = {
            category.value: 0 for category in ErrorCategory
        }
        
        # 错误历史记录（最多保留100条）
        self._error_history = []
        self._max_history = 100
        
        # 用户友好错误消息映射
        self._error_messages = self._init_error_messages()
        
        logger.info("错误处理器初始化完成")
    
    def _init_error_messages(self) -> Dict[ErrorCategory, Dict[str, str]]:
        """初始化用户友好的错误消息"""
        return {
            ErrorCategory.NETWORK: {
                "title": "网络连接错误",
                "general": "网络连接出现问题，请检查网络设置后重试。",
                "timeout": "网络请求超时，请检查网络连接。",
                "connection_refused": "无法连接到服务器，请稍后重试。",
                "dns_error": "域名解析失败，请检查网络设置。"
            },
            ErrorCategory.DATABASE: {
                "title": "数据库错误", 
                "general": "数据库操作失败，请重启程序或联系技术支持。",
                "connection_error": "无法连接到数据库文件。",
                "corruption": "数据库文件可能已损坏。",
                "permission": "没有数据库文件的读写权限。"
            },
            ErrorCategory.BROWSER: {
                "title": "浏览器错误",
                "general": "浏览器操作失败，请检查浏览器配置。",
                "not_found": "未找到浏览器可执行文件。",
                "launch_failed": "浏览器启动失败。",
                "automation_error": "浏览器自动化操作失败。"
            },
            ErrorCategory.API: {
                "title": "API调用错误",
                "general": "服务器API调用失败，请稍后重试。",
                "rate_limit": "API调用频率超限，请稍后重试。",
                "authentication": "API认证失败，请检查Token。",
                "server_error": "服务器内部错误，请稍后重试。"
            },
            ErrorCategory.AUTHENTICATION: {
                "title": "认证错误",
                "general": "身份认证失败。",
                "invalid_token": "Token无效或已过期。",
                "permission_denied": "没有执行此操作的权限。",
                "login_required": "需要登录才能执行此操作。"
            },
            ErrorCategory.VALIDATION: {
                "title": "数据验证错误",
                "general": "输入的数据格式不正确。",
                "required_field": "必填字段不能为空。",
                "invalid_format": "数据格式不正确。",
                "out_of_range": "数据超出有效范围。"
            },
            ErrorCategory.PERMISSION: {
                "title": "权限错误",
                "general": "没有执行此操作的权限。",
                "file_access": "没有文件访问权限。",
                "admin_required": "需要管理员权限。"
            },
            ErrorCategory.RESOURCE: {
                "title": "资源错误",
                "general": "系统资源不足。",
                "memory_error": "内存不足，请关闭其他程序。",
                "disk_full": "磁盘空间不足。",
                "file_not_found": "找不到指定的文件。"
            },
            ErrorCategory.UNKNOWN: {
                "title": "未知错误",
                "general": "发生了未知错误，请查看日志了解详情。"
            }
        }
    
    def handle_exception(
        self, 
        exc: Exception, 
        context: Optional[str] = None,
        show_dialog: bool = True,
        parent: Optional[QWidget] = None
    ) -> AppError:
        """
        处理异常
        
        Args:
            exc: 异常对象
            context: 上下文信息
            show_dialog: 是否显示错误对话框
            parent: 父窗口
        
        Returns:
            AppError: 转换后的应用错误对象
        """
        # 如果已经是AppError，直接处理
        if isinstance(exc, AppError):
            app_error = exc
        else:
            # 转换为AppError
            app_error = self._convert_to_app_error(exc, context)
        
        # 记录错误
        self._log_error(app_error)
        
        # 更新统计
        self._error_stats[app_error.category.value] += 1
        
        # 添加到历史记录
        self._add_to_history(app_error)
        
        # 发射信号
        self.error_occurred.emit(app_error)
        
        if app_error.level == ErrorLevel.CRITICAL:
            self.critical_error.emit(str(app_error))
        
        # 显示用户对话框
        if show_dialog:
            self._show_error_dialog(app_error, parent)
        
        return app_error
    
    def _convert_to_app_error(self, exc: Exception, context: Optional[str] = None) -> AppError:
        """
        将普通异常转换为AppError
        
        Args:
            exc: 原始异常
            context: 上下文信息
        
        Returns:
            AppError: 转换后的应用错误
        """
        message = str(exc) or "未知错误"
        if context:
            message = f"{context}: {message}"
        
        # 根据异常类型确定错误分类
        category = self._classify_exception(exc)
        level = self._determine_error_level(exc)
        
        return AppError(
            message=message,
            category=category,
            level=level,
            details={
                'exception_type': type(exc).__name__,
                'context': context
            },
            cause=exc
        )
    
    def _classify_exception(self, exc: Exception) -> ErrorCategory:
        """
        根据异常类型分类
        
        Args:
            exc: 异常对象
        
        Returns:
            ErrorCategory: 错误分类
        """
        exc_type = type(exc).__name__
        exc_message = str(exc).lower()
        
        # 网络相关
        if any(keyword in exc_type.lower() or keyword in exc_message for keyword in 
               ['network', 'connection', 'timeout', 'dns', 'socket', 'http', 'url']):
            return ErrorCategory.NETWORK
        
        # 数据库相关
        if any(keyword in exc_type.lower() or keyword in exc_message for keyword in 
               ['database', 'sqlite', 'db', 'sql']):
            return ErrorCategory.DATABASE
        
        # 文件IO相关
        if any(keyword in exc_type.lower() for keyword in 
               ['filenotfound', 'permissionerror', 'ioerror', 'oserror']):
            return ErrorCategory.FILE_IO
        
        # 浏览器相关
        if any(keyword in exc_type.lower() or keyword in exc_message for keyword in 
               ['browser', 'selenium', 'playwright', 'chrome', 'webdriver']):
            return ErrorCategory.BROWSER
        
        # 认证相关
        if any(keyword in exc_message for keyword in 
               ['authentication', 'authorization', 'token', 'login', 'credential']):
            return ErrorCategory.AUTHENTICATION
        
        # 权限相关
        if 'permission' in exc_type.lower() or 'permission' in exc_message:
            return ErrorCategory.PERMISSION
        
        # 资源相关
        if any(keyword in exc_type.lower() for keyword in 
               ['memory', 'resource', 'disk']):
            return ErrorCategory.RESOURCE
        
        # 验证相关
        if any(keyword in exc_type.lower() or keyword in exc_message for keyword in 
               ['validation', 'invalid', 'format']):
            return ErrorCategory.VALIDATION
        
        return ErrorCategory.UNKNOWN
    
    def _determine_error_level(self, exc: Exception) -> ErrorLevel:
        """
        确定错误级别
        
        Args:
            exc: 异常对象
        
        Returns:
            ErrorLevel: 错误级别
        """
        exc_type = type(exc).__name__
        
        # 严重错误
        if any(keyword in exc_type.lower() for keyword in 
               ['critical', 'fatal', 'system', 'memory']):
            return ErrorLevel.CRITICAL
        
        # 一般错误
        if any(keyword in exc_type.lower() for keyword in 
               ['error', 'exception', 'failed']):
            return ErrorLevel.ERROR
        
        # 警告
        if any(keyword in exc_type.lower() for keyword in 
               ['warning', 'deprecated']):
            return ErrorLevel.WARNING
        
        return ErrorLevel.ERROR
    
    def _log_error(self, app_error: AppError):
        """记录错误到日志"""
        log_message = f"[{app_error.category.value.upper()}] {app_error}"
        
        if app_error.details:
            log_message += f" | 详情: {app_error.details}"
        
        if app_error.cause:
            log_message += f" | 原因: {type(app_error.cause).__name__}: {app_error.cause}"
        
        # 根据错误级别选择日志级别
        if app_error.level == ErrorLevel.CRITICAL:
            logger.critical(log_message)
        elif app_error.level == ErrorLevel.ERROR:
            logger.error(log_message)
        elif app_error.level == ErrorLevel.WARNING:
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    def _add_to_history(self, app_error: AppError):
        """添加错误到历史记录"""
        self._error_history.append({
            'timestamp': app_error.timestamp,
            'category': app_error.category.value,
            'level': app_error.level.value,
            'message': str(app_error),
            'details': app_error.details
        })
        
        # 保持历史记录数量限制
        if len(self._error_history) > self._max_history:
            self._error_history.pop(0)
    
    def _show_error_dialog(self, app_error: AppError, parent: Optional[QWidget] = None):
        """显示错误对话框"""
        category_messages = self._error_messages.get(app_error.category, 
                                                    self._error_messages[ErrorCategory.UNKNOWN])
        
        title = category_messages.get("title", "错误")
        
        # 尝试获取更具体的错误消息
        message = category_messages.get("general", str(app_error))
        
        # 检查是否有更具体的错误类型
        error_lower = str(app_error).lower()
        for key, value in category_messages.items():
            if key != "title" and key != "general" and key in error_lower:
                message = value
                break
        
        # 根据错误级别选择对话框类型
        if app_error.level == ErrorLevel.CRITICAL:
            icon = QMessageBox.Icon.Critical
        elif app_error.level == ErrorLevel.ERROR:
            icon = QMessageBox.Icon.Warning
        elif app_error.level == ErrorLevel.WARNING:
            icon = QMessageBox.Icon.Information
        else:
            icon = QMessageBox.Icon.Information
        
        # 创建对话框
        msg_box = QMessageBox(parent)
        msg_box.setIcon(icon)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        
        # 添加详细信息
        if app_error.details:
            detailed_text = "详细信息:\n"
            for key, value in app_error.details.items():
                detailed_text += f"• {key}: {value}\n"
            msg_box.setDetailedText(detailed_text)
        
        msg_box.exec()
    
    def get_error_stats(self) -> Dict[str, int]:
        """获取错误统计信息"""
        return self._error_stats.copy()
    
    def get_error_history(self, limit: Optional[int] = None) -> list:
        """
        获取错误历史记录
        
        Args:
            limit: 限制返回的记录数量
        
        Returns:
            list: 错误历史记录列表
        """
        if limit is None:
            return self._error_history.copy()
        return self._error_history[-limit:].copy()
    
    def clear_error_history(self):
        """清空错误历史记录"""
        self._error_history.clear()
        logger.info("错误历史记录已清空")


def safe_execute(
    func: Callable = None,
    *,
    context: Optional[str] = None,
    show_dialog: bool = False,
    default_return = None,
    reraise: bool = False
):
    """
    安全执行装饰器
    
    Args:
        func: 被装饰的函数
        context: 上下文信息
        show_dialog: 是否显示错误对话框
        default_return: 异常时的默认返回值
        reraise: 是否重新抛出异常
    
    Returns:
        装饰器函数
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                error_handler = get_error_handler()
                error_handler.handle_exception(
                    e, 
                    context=context or f"{f.__module__}.{f.__name__}",
                    show_dialog=show_dialog
                )
                
                if reraise:
                    raise
                
                return default_return
        return wrapper
    
    if func is None:
        return decorator
    else:
        return decorator(func)


# 全局错误处理器实例
_error_handler_instance = None


def get_error_handler() -> ErrorHandler:
    """
    获取全局错误处理器实例
    
    Returns:
        ErrorHandler: 错误处理器实例
    """
    global _error_handler_instance
    if _error_handler_instance is None:
        _error_handler_instance = ErrorHandler()
    return _error_handler_instance


def handle_exception(exc: Exception, context: Optional[str] = None, **kwargs) -> AppError:
    """
    便捷的异常处理函数
    
    Args:
        exc: 异常对象
        context: 上下文信息
        **kwargs: 其他参数
    
    Returns:
        AppError: 处理后的错误对象
    """
    return get_error_handler().handle_exception(exc, context, **kwargs)
