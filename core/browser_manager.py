#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
浏览器管理器
浏览器自动化控制
"""

from DrissionPage import ChromiumOptions, Chromium
import sys
import os
import json
from pathlib import Path
from utils.logger import get_logger
from utils.app_paths import get_config_file

logger = get_logger("browser_manager")


class BrowserManager:
    """浏览器管理器"""
    
    def __init__(self):
        self.browser = None

    def init_browser(self, user_agent=None, headless=False, incognito=None, user_data_dir=None):
        """
        初始化浏览器
        
        Args:
            user_agent: 用户代理
            headless: 是否使用无头模式
            incognito: 是否使用无痕模式（None=从配置读取）
            user_data_dir: 自定义用户数据目录（用于批量绑卡的指纹隔离）
        """
        co = self._get_browser_options(user_agent, headless, incognito, user_data_dir)
        
        # ⭐ 打印Chrome启动命令（调试用）
        try:
            # 尝试获取实际的启动命令
            logger.info("=" * 60)
            logger.info("🔍 Chrome 启动参数检查:")
            if hasattr(co, '_arguments'):
                args = co._arguments if co._arguments else []
                has_incognito = '--incognito' in args
                logger.info(f"  --incognito 参数: {'✅ 已添加（无痕模式）' if has_incognito else '❌ 未添加（普通模式）'}")
                logger.info(f"  所有参数: {args}")
            logger.info("=" * 60)
        except:
            pass
        
        self.browser = Chromium(co)
        
        return self.browser

    def _get_browser_options(self, user_agent=None, headless=False, incognito=None, user_data_dir=None):
        """
        获取浏览器配置
        
        Args:
            user_agent: 用户代理
            headless: 是否使用无头模式
            incognito: 是否使用无痕模式（None=从配置读取，默认True）
            user_data_dir: 自定义用户数据目录
        """
        co = ChromiumOptions()
        
        # ⭐ 使用独立的用户数据目录（避免影响 Cursor）
        import tempfile
        from pathlib import Path
        
        if user_data_dir:
            # 使用自定义的用户数据目录（批量绑卡时的指纹隔离）
            co.set_user_data_path(user_data_dir)
            logger.info(f"✅ 使用自定义用户数据目录: {user_data_dir}")
        else:
            # 创建临时用户数据目录
            temp_dir = Path(tempfile.gettempdir()) / "zzx_cursor_auto_browser"
            temp_dir.mkdir(parents=True, exist_ok=True)
            co.set_user_data_path(str(temp_dir))
            logger.info(f"✅ 使用默认用户数据目录: {temp_dir}")
        
        # ⚡ 非无头模式时加载扩展（扩展在无头模式和无痕模式下可能有问题）
        # ⭐ 但是如果明确指定了incognito=False，说明用户需要扩展，应该加载
        should_load_extension = not headless and (incognito is False or incognito is None)
        
        if should_load_extension:
            # 加载 turnstilePatch 扩展
            try:
                extension_path = self._get_extension_path("turnstilePatch")
                co.add_extension(extension_path)
                logger.info(f"✅ 加载扩展: {extension_path}")
            except FileNotFoundError as e:
                logger.warning(f"警告: {e}")
        else:
            if headless:
                logger.info("⏭️ 无头模式，跳过扩展加载")
            elif incognito:
                logger.info("⏭️ 无痕模式可能不支持扩展，跳过加载")

        # 浏览器配置
        co.set_pref("credentials_enable_service", False)
        co.set_argument("--hide-crash-restore-bubble")
        
        # ⭐ 根据配置决定是否使用无痕模式
        logger.info("=" * 60)
        logger.info("📋 浏览器模式配置:")
        
        if incognito is None:
            # 从配置文件读取
            incognito = self._load_incognito_setting()
            logger.info(f"  ✅ 从配置文件读取: incognito_mode = {incognito}")
        else:
            logger.info(f"  ✅ 外部传入参数: incognito = {incognito}")
        
        if incognito:
            co.set_argument("--incognito")
            logger.info("  🕶️  无痕模式已启用")
            logger.info("  └→ 效果: Cookie和扩展配置不会保留，每次都是全新环境")
        else:
            logger.info("  🌐 普通模式（未启用无痕）")
            logger.info("  └→ 效果: Cookie和扩展配置会保留")
        
        logger.info("=" * 60)
        
        co.auto_port()
        
        if user_agent:
            co.set_user_agent(user_agent)

        # ⚡ 设置无头模式
        if headless:
            co.headless(True)
            co.set_argument("--disable-gpu")
            co.set_argument("--no-sandbox")
            co.set_argument("--disable-dev-shm-usage")
            logger.info("✅ 使用无头模式")
        else:
            co.headless(False)  # 显示浏览器窗口

        # Mac 系统特殊处理
        if sys.platform == "darwin":
            co.set_argument("--no-sandbox")
            co.set_argument("--disable-gpu")

        # ⭐ 记录所有浏览器启动参数（用于调试）
        try:
            # 获取所有参数
            all_args = []
            if hasattr(co, '_arguments') and co._arguments:
                all_args = co._arguments
            elif hasattr(co, 'arguments'):
                all_args = co.arguments
            
            logger.debug(f"浏览器启动参数列表: {all_args}")
            
            # 检查是否包含 --incognito
            has_incognito = '--incognito' in all_args
            logger.info(f"🔍 参数检查: --incognito = {has_incognito}")
            
        except Exception as e:
            logger.debug(f"无法获取参数列表: {e}")

        return co

    def _load_incognito_setting(self) -> bool:
        """
        从配置文件读取无痕模式设置
        
        Returns:
            bool: 是否启用无痕模式（默认True，更安全）
        """
        try:
            config_file = get_config_file()
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # 从 browser.incognito_mode 读取，默认 True
                return config.get('browser', {}).get('incognito_mode', True)
        except Exception as e:
            logger.debug(f"读取无痕模式配置失败，使用默认值: {e}")
        
        return True  # 默认启用无痕模式（更安全）
    
    def _get_extension_path(self, exname='turnstilePatch'):
        """获取插件路径"""
        root_dir = os.getcwd()
        extension_path = os.path.join(root_dir, 'core', exname)
        
        # 尝试相对路径
        if not os.path.exists(extension_path):
            from pathlib import Path
            extension_path = Path(__file__).parent / exname

        if hasattr(sys, "_MEIPASS"):
            extension_path = os.path.join(sys._MEIPASS, exname)

        if not os.path.exists(extension_path):
            raise FileNotFoundError(f"插件不存在: {extension_path}")

        return str(extension_path)

    def quit(self):
        """
        安全地关闭浏览器
        只关闭我们启动的浏览器实例，不影响其他 Chrome/Cursor 进程
        """
        if self.browser:
            try:
                logger.info("正在关闭浏览器...")
                
                # 方法1: 先尝试关闭所有标签页
                try:
                    tabs = self.browser.get_tabs()
                    for tab in tabs:
                        try:
                            tab.close()
                            logger.debug(f"已关闭标签页: {tab.url[:50] if hasattr(tab, 'url') else 'unknown'}")
                        except:
                            pass
                except Exception as e:
                    logger.debug(f"关闭标签页时出错: {e}")
                
                # 方法2: 然后关闭浏览器实例
                try:
                    self.browser.quit()
                    logger.info("✅ 浏览器已关闭")
                except Exception as e:
                    logger.warning(f"关闭浏览器时出错: {e}")
                    
            except Exception as e:
                logger.error(f"关闭浏览器异常: {e}")
                pass
    
    def close_tabs_only(self):
        """
        只关闭标签页，不关闭浏览器进程
        适用于需要保留浏览器的场景
        """
        if self.browser:
            try:
                logger.info("关闭所有标签页（保留浏览器）...")
                tabs = self.browser.get_tabs()
                for i, tab in enumerate(tabs):
                    try:
                        tab.close()
                        logger.debug(f"已关闭标签页 {i+1}/{len(tabs)}")
                    except:
                        pass
                logger.info("✅ 标签页已关闭，浏览器保持运行")
            except Exception as e:
                logger.error(f"关闭标签页失败: {e}")

