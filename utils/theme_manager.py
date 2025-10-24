#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主题管理器
处理亮色和深色主题的切换，支持自动定时切换
"""

import json
import sys
from datetime import datetime, time
from pathlib import Path
from typing import Optional, Callable

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.logger import get_logger
from utils.app_paths import get_config_file

logger = get_logger("theme_manager")


class ThemeManager(QObject):
    """主题管理器"""
    
    # 信号：主题改变时发出
    theme_changed = pyqtSignal(str)  # theme_name: "light" 或 "dark"
    
    def __init__(self, config_path: str = None):
        super().__init__()
        
        # 使用用户目录的配置文件路径
        if config_path:
            self.config_path = Path(config_path)
        else:
            self.config_path = get_config_file()
        
        self.config = self._load_config()
        self.current_theme = self.config.get('theme', {}).get('current_theme', 'light')
        
        # 定时器用于自动切换
        self.auto_switch_timer = QTimer()
        self.auto_switch_timer.timeout.connect(self._check_auto_switch)
        
        # 主题文件路径
        self.light_theme_path = Path(__file__).parent.parent / "gui" / "resources" / "styles.qss"
        self.dark_theme_path = Path(__file__).parent.parent / "gui" / "resources" / "styles_dark.qss"
        
        # ⭐ QSS样式表缓存（预加载，避免切换时I/O）
        self._cached_stylesheets = {}
        self._preload_stylesheets()
        
        # 启动自动检查
        self._start_auto_check()
        
        logger.info(f"主题管理器初始化完成，当前主题: {self.current_theme}")
    
    def _load_config(self) -> dict:
        """加载配置文件"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
        
        # 返回默认配置
        return {
            "theme": {
                "current_theme": "light",
                "auto_switch": False,
                "dark_start_time": "19:00",
                "light_start_time": "07:00"
            }
        }
    
    def _save_config(self):
        """保存配置文件（只更新主题相关配置）"""
        try:
            # ⭐ 重新加载最新配置，避免覆盖其他模块的修改
            latest_config = {}
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    latest_config = json.load(f)
            
            # ⭐ 只更新主题相关的配置
            if 'theme' not in latest_config:
                latest_config['theme'] = {}
            
            # 从当前配置中复制主题设置
            if 'theme' in self.config:
                latest_config['theme'].update(self.config['theme'])
            
            # 保存更新后的配置
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(latest_config, f, ensure_ascii=False, indent=2)
            
            # ⭐ 更新本地配置为最新版本
            self.config = latest_config
            
            logger.debug("配置文件已保存（仅更新主题部分）")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
    
    def _preload_stylesheets(self):
        """预加载所有主题样式表到内存（启动时执行一次）"""
        try:
            logger.debug("开始预加载QSS样式表...")
            
            # 加载浅色主题
            if self.light_theme_path.exists():
                with open(self.light_theme_path, 'r', encoding='utf-8') as f:
                    self._cached_stylesheets['light'] = f.read()
                logger.debug(f"浅色主题已缓存 ({len(self._cached_stylesheets['light'])} 字符)")
            else:
                logger.warning(f"浅色主题文件不存在: {self.light_theme_path}")
            
            # 加载深色主题
            if self.dark_theme_path.exists():
                with open(self.dark_theme_path, 'r', encoding='utf-8') as f:
                    self._cached_stylesheets['dark'] = f.read()
                logger.debug(f"深色主题已缓存 ({len(self._cached_stylesheets['dark'])} 字符)")
            else:
                logger.warning(f"深色主题文件不存在: {self.dark_theme_path}")
            
            logger.info("✅ QSS样式表预加载完成")
            
        except Exception as e:
            logger.error(f"预加载样式表失败: {e}")
    
    def get_current_theme(self) -> str:
        """获取当前主题"""
        return self.current_theme
    
    def is_dark_theme(self) -> bool:
        """判断是否为深色主题"""
        return self.current_theme == "dark"
    
    def switch_theme(self, theme_name: str = None, save_config: bool = True, manual: bool = False):
        """
        切换主题
        
        Args:
            theme_name: 主题名称 ("light" 或 "dark")，如果为 None 则自动切换
            save_config: 是否保存配置到文件
            manual: 是否为用户手动切换（True 会禁用自动切换）
        """
        if theme_name is None:
            # 自动切换到相反主题
            theme_name = "dark" if self.current_theme == "light" else "light"
        
        if theme_name not in ["light", "dark"]:
            logger.warning(f"无效的主题名称: {theme_name}")
            return
        
        if theme_name == self.current_theme:
            logger.debug(f"主题已经是 {theme_name}，无需切换")
            return
        
        # 更新当前主题
        old_theme = self.current_theme
        self.current_theme = theme_name
        
        # 加载并应用样式
        success = self._apply_theme(theme_name)
        
        if success:
            # 更新配置
            if 'theme' not in self.config:
                self.config['theme'] = {}
            self.config['theme']['current_theme'] = theme_name
            
            # ⭐ 如果是用户手动切换，禁用自动切换
            if manual:
                self.config['theme']['auto_switch'] = False
                self.auto_switch_timer.stop()
                logger.info("⚠️ 用户手动切换主题，自动切换已禁用")
            
            # 保存配置
            if save_config:
                self._save_config()
            
            # 发出信号
            self.theme_changed.emit(theme_name)
            
            logger.info(f"主题切换成功: {old_theme} → {theme_name} (手动={manual})")
        else:
            # 切换失败，恢复原主题
            self.current_theme = old_theme
            logger.error(f"主题切换失败: {old_theme} → {theme_name}")
    
    def _apply_theme(self, theme_name: str) -> bool:
        """
        应用主题样式（优化版：使用缓存，无I/O）
        
        Args:
            theme_name: 主题名称
            
        Returns:
            bool: 是否成功应用
        """
        try:
            # ⭐ 优先从缓存读取（无I/O，快速）
            style_sheet = self._cached_stylesheets.get(theme_name)
            
            if not style_sheet:
                # 缓存中没有，降级到文件读取
                logger.warning(f"缓存中没有主题 {theme_name}，尝试从文件读取")
                
                theme_file = self.dark_theme_path if theme_name == "dark" else self.light_theme_path
                
                if not theme_file.exists():
                    logger.error(f"主题文件不存在: {theme_file}")
                    return False
                
                # 读取并缓存
                with open(theme_file, 'r', encoding='utf-8') as f:
                    style_sheet = f.read()
                    self._cached_stylesheets[theme_name] = style_sheet
            
            # 获取应用程序实例并应用样式
            app = QApplication.instance()
            if app:
                app.setStyleSheet(style_sheet)
                logger.debug(f"已应用主题样式: {theme_name} (从缓存)")
                return True
            else:
                logger.error("无法获取QApplication实例")
                return False
                
        except Exception as e:
            logger.error(f"应用主题失败: {e}")
            return False
    
    def set_auto_switch(self, enabled: bool, dark_start_time: str = "19:00", light_start_time: str = "07:00"):
        """
        设置自动切换
        
        Args:
            enabled: 是否启用自动切换
            dark_start_time: 深色模式开始时间 (格式: "HH:MM")
            light_start_time: 浅色模式开始时间 (格式: "HH:MM")
        """
        # 更新配置
        if 'theme' not in self.config:
            self.config['theme'] = {}
        
        self.config['theme']['auto_switch'] = enabled
        self.config['theme']['dark_start_time'] = dark_start_time
        self.config['theme']['light_start_time'] = light_start_time
        
        # 保存配置
        self._save_config()
        
        if enabled:
            # 启动自动检查
            self._start_auto_check()
            # 立即检查一次
            self._check_auto_switch()
            logger.info(f"自动切换已启用: 深色 {dark_start_time}, 浅色 {light_start_time}")
        else:
            # 停止自动检查
            self.auto_switch_timer.stop()
            logger.info("自动切换已禁用")
    
    def is_auto_switch_enabled(self) -> bool:
        """判断是否启用了自动切换"""
        return self.config.get('theme', {}).get('auto_switch', False)
    
    def get_auto_switch_times(self) -> tuple[str, str]:
        """获取自动切换时间"""
        theme_config = self.config.get('theme', {})
        dark_start = theme_config.get('dark_start_time', '19:00')
        light_start = theme_config.get('light_start_time', '07:00')
        return dark_start, light_start
    
    def _start_auto_check(self):
        """启动自动检查定时器"""
        if self.is_auto_switch_enabled():
            # 每分钟检查一次
            self.auto_switch_timer.start(60000)
            logger.debug("自动切换检查定时器已启动")
    
    def _check_auto_switch(self):
        """检查是否需要自动切换主题"""
        if not self.is_auto_switch_enabled():
            return
        
        try:
            # 获取当前时间
            current_time = datetime.now().time()
            
            # 获取配置的切换时间
            dark_start, light_start = self.get_auto_switch_times()
            
            # 解析时间字符串
            dark_start_time = datetime.strptime(dark_start, "%H:%M").time()
            light_start_time = datetime.strptime(light_start, "%H:%M").time()
            
            # 判断应该使用什么主题
            should_be_dark = self._should_be_dark_theme(current_time, dark_start_time, light_start_time)
            
            # 如果需要切换
            if should_be_dark and self.current_theme == "light":
                logger.info(f"自动切换到深色模式 (当前时间: {current_time.strftime('%H:%M')})")
                self.switch_theme("dark", save_config=True)
            elif not should_be_dark and self.current_theme == "dark":
                logger.info(f"自动切换到浅色模式 (当前时间: {current_time.strftime('%H:%M')})")
                self.switch_theme("light", save_config=True)
                
        except Exception as e:
            logger.error(f"自动切换检查失败: {e}")
    
    def _should_be_dark_theme(self, current_time: time, dark_start: time, light_start: time) -> bool:
        """
        判断在给定时间是否应该使用深色主题
        
        Args:
            current_time: 当前时间
            dark_start: 深色模式开始时间
            light_start: 浅色模式开始时间
            
        Returns:
            bool: 是否应该使用深色主题
        """
        # 处理跨天的情况
        if dark_start <= light_start:
            # 同一天内：dark_start <= current < light_start
            return dark_start <= current_time < light_start
        else:
            # 跨天：current >= dark_start OR current < light_start
            return current_time >= dark_start or current_time < light_start
    
    def force_reload_current_theme(self):
        """强制重新加载当前主题（用于初始化）"""
        self._apply_theme(self.current_theme)
        logger.debug(f"强制重新加载主题: {self.current_theme}")


# 全局主题管理器实例
_theme_manager = None

def get_theme_manager(config_path: str = "./config.json") -> ThemeManager:
    """获取主题管理器单例"""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager(config_path)
    return _theme_manager
