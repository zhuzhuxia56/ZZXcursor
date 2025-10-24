#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursor 账号切换模块
配置文件更新和账号切换逻辑
"""

import os
import sys
import json
import sqlite3
import shutil
from pathlib import Path
from contextlib import contextmanager
from typing import Dict, Any, List, Optional

from utils.logger import get_logger

# 文件锁支持（跨平台）
if sys.platform == 'win32':
    import msvcrt
else:
    import fcntl  # macOS/Linux 使用 fcntl

logger = get_logger("cursor_switcher")


class CursorSwitcher:
    """Cursor 账号切换器"""
    
    def __init__(self):
        """初始化切换器"""
        self.platform = sys.platform
        self.config_paths = self._detect_config_paths()
        self.db_paths = self._detect_db_paths()
    
    def _detect_config_paths(self) -> List[Path]:
        """
        检测 storage.json 配置文件路径
        
        Returns:
            List[Path]: 存在的配置文件路径列表
        """
        home = Path.home()
        possible_paths = []
        
        if self.platform == 'win32':
            roaming = os.getenv('APPDATA', home / 'AppData' / 'Roaming')
            local = os.getenv('LOCALAPPDATA', home / 'AppData' / 'Local')
            
            possible_paths = [
                Path(roaming) / 'Cursor' / 'User' / 'globalStorage' / 'storage.json',
                Path(local) / 'Cursor' / 'User' / 'globalStorage' / 'storage.json',
            ]
        elif self.platform == 'darwin':
            possible_paths = [
                home / 'Library' / 'Application Support' / 'Cursor' / 'User' / 'globalStorage' / 'storage.json',
            ]
        else:  # Linux
            possible_paths = [
                home / '.config' / 'Cursor' / 'User' / 'globalStorage' / 'storage.json',
            ]
        
        existing_paths = [p for p in possible_paths if p.exists()]
        
        if existing_paths:
            existing_paths.sort(key=lambda p: p.stat().st_atime, reverse=True)
            logger.info(f"找到 {len(existing_paths)} 个 storage.json 配置文件")
        else:
            logger.warning("未找到 Cursor 配置文件")
        
        return existing_paths
    
    def _detect_db_paths(self) -> List[Path]:
        """
        检测 state.vscdb 数据库文件路径
        
        Returns:
            List[Path]: 存在的数据库文件路径列表
        """
        home = Path.home()
        possible_paths = []
        
        if self.platform == 'win32':
            roaming = os.getenv('APPDATA', home / 'AppData' / 'Roaming')
            local = os.getenv('LOCALAPPDATA', home / 'AppData' / 'Local')
            
            possible_paths = [
                Path(roaming) / 'Cursor' / 'User' / 'globalStorage' / 'state.vscdb',
                Path(local) / 'Cursor' / 'User' / 'globalStorage' / 'state.vscdb',
            ]
        elif self.platform == 'darwin':
            possible_paths = [
                home / 'Library' / 'Application Support' / 'Cursor' / 'User' / 'globalStorage' / 'state.vscdb',
            ]
        else:  # Linux
            possible_paths = [
                home / '.config' / 'Cursor' / 'User' / 'globalStorage' / 'state.vscdb',
            ]
        
        existing_paths = [p for p in possible_paths if p.exists()]
        
        if existing_paths:
            logger.info(f"找到 {len(existing_paths)} 个 state.vscdb 数据库文件")
        
        return existing_paths
    
    @contextmanager
    def _file_lock(self, file_handle):
        """文件锁（跨平台）"""
        if self.platform == 'win32':
            # Windows: 使用 msvcrt
            try:
                msvcrt.locking(file_handle.fileno(), msvcrt.LK_LOCK, 1)
                yield file_handle
            finally:
                try:
                    msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, 1)
                except:
                    pass
        else:
            # macOS/Linux: 使用 fcntl
            try:
                fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX)
                yield file_handle
            finally:
                try:
                    fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
                except:
                    pass
    
    def switch_account(self, account: Dict[str, Any], 
                      machine_id_mode: str = 'generate_new',
                      reset_machine_id: bool = False,
                      reset_cursor_config: bool = False) -> bool:
        """
        切换到指定账号
        
        Args:
            account: 账号数据字典，必须包含:
                - email: 邮箱
                - access_token: 访问令牌
                - refresh_token: 刷新令牌（可选）
                - machine_info: 机器码信息（可选）
            machine_id_mode: 机器码处理模式:
                - 'use_bound': 使用账号绑定的机器码
                - 'generate_new': 生成新的机器码（默认）
                - 'reset_all': 清空所有机器码
            reset_machine_id: 是否重置机器码（向后兼容，优先级低于 machine_id_mode）
            reset_cursor_config: 是否完全重置 Cursor 配置
                
        Returns:
            bool: 是否成功
        """
        try:
            email = account.get('email')
            access_token = account.get('access_token')
            refresh_token = account.get('refresh_token', access_token)
            machine_info = account.get('machine_info')
            
            if not email or not access_token:
                logger.error("账号数据不完整：缺少 email 或 access_token")
                return False
            
            # ⭐ 解密 Token（如果是加密的）
            if access_token and access_token.startswith('gAAAAA'):
                try:
                    from utils.crypto import get_crypto_manager
                    crypto = get_crypto_manager()
                    decrypted_access = crypto.decrypt(access_token)
                    if decrypted_access:
                        access_token = decrypted_access
                        logger.debug("access_token 已解密")
                except Exception as e:
                    logger.warning(f"解密 access_token 失败: {e}")
            
            if refresh_token and refresh_token.startswith('gAAAAA'):
                try:
                    from utils.crypto import get_crypto_manager
                    crypto = get_crypto_manager()
                    decrypted_refresh = crypto.decrypt(refresh_token)
                    if decrypted_refresh:
                        refresh_token = decrypted_refresh
                        logger.debug("refresh_token 已解密")
                except Exception as e:
                    logger.warning(f"解密 refresh_token 失败: {e}")
            
            # 向后兼容：如果 reset_machine_id=True，则使用 reset_all 模式
            if reset_machine_id and machine_id_mode == 'generate_new':
                machine_id_mode = 'reset_all'
                logger.debug("检测到 reset_machine_id=True，切换到 reset_all 模式")
            
            # 可选：完全重置配置
            if reset_cursor_config:
                logger.info("  ↳ 执行完全重置配置...")
                self.reset_all_config()
            
            # 更新 storage.json
            logger.info("  ↳ 写入 storage.json...")
            storage_success = self._update_storage_files(email, access_token, refresh_token)
            
            # 更新 state.vscdb（传递机器码信息）
            logger.info("  ↳ 写入 state.vscdb...")
            db_success = self._update_db_files(
                email, access_token, refresh_token, 
                machine_id_mode=machine_id_mode,
                machine_info=machine_info
            )
            
            # 处理机器码
            logger.info("【3/5】处理机器码...")
            if machine_id_mode == 'generate_new':
                logger.info("  ↳ 生成新机器码")
            elif machine_id_mode == 'use_bound':
                logger.info("  ↳ 使用绑定的机器码")
            elif machine_id_mode == 'reset_all':
                logger.info("  ↳ 重置所有机器码")
            
            success = storage_success or db_success
            
            if success:
                logger.info("  ✅ 账号配置写入完成")
            else:
                logger.error("  ❌ 写入失败：未找到配置文件")
            
            return success
            
        except Exception as e:
            logger.error(f"切换账号失败: {e}", exc_info=True)
            return False
    
    def _update_storage_files(self, email: str, access_token: str, refresh_token: str) -> bool:
        """更新所有 storage.json 文件"""
        if not self.config_paths:
            logger.warning("未找到 storage.json 配置文件")
            return False
        
        updated_count = 0
        
        for config_file in self.config_paths:
            try:
                logger.debug(f"    更新: {config_file}")
                
                # 备份
                backup_file = config_file.with_suffix('.json.backup')
                shutil.copy2(config_file, backup_file)
                
                # 读取配置
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 更新 Token 字段
                config['cursorAuth/accessToken'] = access_token
                config['cursorAuth/refreshToken'] = refresh_token
                config['cursorAuth/cachedEmail'] = email
                config['cursorAuth/cachedSignUpType'] = 'Auth_0'
                
                # ⭐ 清空 WorkosCursorSessionToken（避免干扰）
                config['WorkosCursorSessionToken'] = ''
                config['workos.sessionToken'] = ''
                
                logger.debug(f"    ✓ 已清空 WorkosCursorSessionToken")
                
                # 写入配置（使用文件锁）
                with open(config_file, 'r+', encoding='utf-8') as f:
                    with self._file_lock(f):
                        f.seek(0)
                        f.truncate()
                        json.dump(config, f, ensure_ascii=False, indent=2)
                        f.flush()
                        os.fsync(f.fileno())
                
                logger.debug(f"    ✓ storage.json 已更新")
                updated_count += 1
                
            except Exception as e:
                logger.error(f"更新配置文件失败 {config_file}: {e}")
                continue
        
        return updated_count > 0
    
    def _update_db_files(self, email: str, access_token: str, refresh_token: str, 
                        machine_id_mode: str = 'generate_new',
                        machine_info: Optional[Dict[str, str]] = None,
                        reset_machine_id: bool = False) -> bool:
        """
        更新所有 state.vscdb 数据库文件
        
        Args:
            email: 邮箱
            access_token: 访问令牌
            refresh_token: 刷新令牌
            machine_id_mode: 机器码模式 ('use_bound', 'generate_new', 'reset_all')
            machine_info: 机器码信息（当 mode='use_bound' 时使用）
            reset_machine_id: 向后兼容参数
        """
        if not self.db_paths:
            logger.warning("未找到 state.vscdb 数据库文件")
            return False
        
        updated_count = 0
        
        for db_file in self.db_paths:
            try:
                logger.debug(f"    更新: {db_file}")
                
                # 备份
                backup_file = db_file.with_suffix('.vscdb.backup')
                shutil.copy2(db_file, backup_file)
                
                # 连接数据库
                conn = sqlite3.connect(str(db_file))
                cursor = conn.cursor()
                
                # 更新字段
                updates = [
                    ('cursorAuth/accessToken', access_token),
                    ('cursorAuth/refreshToken', refresh_token),
                    ('cursorAuth/cachedEmail', email),
                    ('cursorAuth/cachedSignUpType', 'Auth_0'),
                    # ⭐ 清空 WorkosCursorSessionToken（避免干扰）
                    ('WorkosCursorSessionToken', ''),
                    ('workos.sessionToken', ''),
                ]
                
                logger.debug(f"    ✓ 准备更新 {len(updates)} 个字段")
                
                # 处理机器码
                machine_id_fields = [
                    'telemetry.machineId',
                    'telemetry.macMachineId',
                    'telemetry.devDeviceId',
                    'telemetry.sqmId',
                    'system.machineGuid'
                ]
                
                if machine_id_mode == 'use_bound' and machine_info:
                    for field in machine_id_fields:
                        if field in machine_info:
                            updates.append((field, machine_info[field]))
                            
                elif machine_id_mode == 'generate_new':
                    from core.machine_id_generator import generate_machine_info
                    new_machine_info = generate_machine_info(self.platform)
                    for field in machine_id_fields:
                        if field in new_machine_info:
                            updates.append((field, new_machine_info[field]))
                            
                elif machine_id_mode == 'reset_all' or reset_machine_id:
                    for field in machine_id_fields:
                        updates.append((field, ''))
                
                for key, value in updates:
                    # 检查是否存在
                    cursor.execute("SELECT COUNT(*) FROM itemTable WHERE key = ?", (key,))
                    if cursor.fetchone()[0] == 0:
                        cursor.execute("INSERT INTO itemTable (key, value) VALUES (?, ?)", (key, value))
                    else:
                        cursor.execute("UPDATE itemTable SET value = ? WHERE key = ?", (value, key))
                
                conn.commit()
                conn.close()
                
                logger.debug(f"    ✓ state.vscdb 已更新")
                updated_count += 1
                
            except Exception as e:
                logger.error(f"更新数据库文件失败 {db_file}: {e}")
                continue
        
        return updated_count > 0
    
    def validate_cursor_installation(self) -> bool:
        """
        验证 Cursor 是否已安装
        
        Returns:
            bool: Cursor 是否已安装
        """
        has_config = len(self.config_paths) > 0
        has_db = len(self.db_paths) > 0
        
        return has_config or has_db
    
    def get_current_account(self) -> Optional[Dict[str, str]]:
        """
        获取当前登录的账号信息
        
        Returns:
            Optional[Dict]: 当前账号信息 {'email', 'access_token'}
        """
        if not self.config_paths:
            return None
        
        try:
            config_file = self.config_paths[0]
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            email = config.get('cursorAuth/cachedEmail')
            access_token = config.get('cursorAuth/accessToken')
            
            if email and access_token:
                return {
                    'email': email,
                    'access_token': access_token
                }
            
            return None
            
        except Exception as e:
            logger.error(f"获取当前账号失败: {e}")
            return None
    
    def reset_all_config(self) -> bool:
        """
        完全重置 Cursor 配置（危险操作）
        清除所有配置项，仅保留基础结构
        
        Returns:
            bool: 是否成功
        """
        try:
            logger.warning("⚠️ 执行完全重置配置...")
            
            # 重置 storage.json
            for config_file in self.config_paths:
                try:
                    # 创建最小配置
                    minimal_config = {}
                    
                    # 备份
                    backup_file = config_file.with_suffix('.json.full_reset_backup')
                    shutil.copy2(config_file, backup_file)
                    
                    # 写入最小配置
                    with open(config_file, 'w', encoding='utf-8') as f:
                        json.dump(minimal_config, f, ensure_ascii=False, indent=2)
                    
                    logger.info(f"✅ 已重置配置文件: {config_file}")
                except Exception as e:
                    logger.error(f"重置配置文件失败: {e}")
            
            # 重置数据库（清空特定表）
            for db_file in self.db_paths:
                try:
                    # 备份
                    backup_file = db_file.with_suffix('.vscdb.full_reset_backup')
                    shutil.copy2(db_file, backup_file)
                    
                    # 清空认证相关字段
                    conn = sqlite3.connect(str(db_file))
                    cursor = conn.cursor()
                    
                    # 删除所有 cursorAuth 相关字段
                    cursor.execute("DELETE FROM itemTable WHERE key LIKE 'cursorAuth/%'")
                    cursor.execute("DELETE FROM itemTable WHERE key LIKE 'telemetry.%'")
                    cursor.execute("DELETE FROM itemTable WHERE key LIKE 'Workos%'")
                    
                    conn.commit()
                    conn.close()
                    
                    logger.info(f"✅ 已重置数据库: {db_file}")
                except Exception as e:
                    logger.error(f"重置数据库失败: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"完全重置配置失败: {e}")
            return False
    
    def check_cursor_running(self) -> bool:
        """
        检查 Cursor 是否正在运行
        
        Returns:
            bool: True 表示 Cursor 正在运行
        """
        try:
            if self.platform == 'win32':
                # Windows: 使用 tasklist
                import subprocess
                result = subprocess.run(
                    ['tasklist', '/FI', 'IMAGENAME eq Cursor.exe'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return 'Cursor.exe' in result.stdout
            
            elif self.platform == 'darwin':
                # macOS: 使用 ps
                import subprocess
                result = subprocess.run(
                    ['ps', 'aux'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return 'Cursor' in result.stdout and 'Cursor.app' in result.stdout
            
            else:
                # Linux: 使用 ps
                import subprocess
                result = subprocess.run(
                    ['ps', 'aux'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return 'cursor' in result.stdout.lower()
        
        except Exception as e:
            logger.error(f"检查 Cursor 进程失败: {e}")
            return False
    
    def close_cursor_gracefully(self) -> bool:
        """
        优雅关闭 Cursor 进程（快速版，3秒内完成）
        先尝试温和关闭，1秒后检查，未关闭则强制终止
        
        Returns:
            bool: 是否成功
        """
        try:
            import time
            logger.info("【1/5】正在关闭 Cursor...")
            
            if self.platform == 'win32':
                # 方式1：psutil 温和终止（优先）
                try:
                    import psutil
                    terminated = False
                    
                    for proc in psutil.process_iter(['name']):
                        if proc.info['name'] == 'Cursor.exe':
                            logger.info("  ↳ 发送终止信号（SIGTERM）")
                            proc.terminate()  # 温和终止
                            terminated = True
                    
                    if terminated:
                        # 等待1秒检查
                        time.sleep(1)
                except:
                    logger.debug("  psutil 方式失败，使用备用方式")
                
                # 检查是否已关闭
                if not self.check_cursor_running():
                    logger.info("  ✅ Cursor 已正常退出")
                    return True
                
                # 方式2：强制终止（如果还在运行）
                logger.info("  ↳ 进程未退出，执行强制终止")
                import subprocess
                result = subprocess.run(
                    ['taskkill', '/F', '/IM', 'Cursor.exe'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                # 再等0.5秒
                time.sleep(0.5)
                
                if not self.check_cursor_running():
                    logger.info("  ✅ Cursor 进程已关闭")
                    return True
                else:
                    logger.error("  ❌ 无法关闭 Cursor 进程")
                    return False
            
            elif self.platform == 'darwin':
                # macOS: 先尝试温和关闭
                import subprocess
                subprocess.run(['pkill', 'Cursor'], timeout=5)
                time.sleep(1)
                
                if not self.check_cursor_running():
                    logger.info("  ✅ Cursor 已正常退出")
                    return True
                
                # 强制终止
                subprocess.run(['pkill', '-9', 'Cursor'], timeout=5)
                time.sleep(0.5)
                logger.info("  ✅ Cursor 进程已关闭")
                return True
            
            else:
                # Linux: 先尝试温和关闭
                import subprocess
                subprocess.run(['pkill', 'cursor'], timeout=5)
                time.sleep(1)
                
                if not self.check_cursor_running():
                    logger.info("  ✅ Cursor 已正常退出")
                    return True
                
                # 强制终止
                subprocess.run(['pkill', '-9', 'cursor'], timeout=5)
                time.sleep(0.5)
                logger.info("  ✅ Cursor 进程已关闭")
                return True
        
        except Exception as e:
            logger.error(f"关闭 Cursor 进程失败: {e}")
            return False
    
    def start_cursor(self) -> bool:
        """
        启动 Cursor
        
        Returns:
            bool: 是否成功
        """
        try:
            logger.info("正在启动 Cursor...")
            
            if self.platform == 'win32':
                # Windows: 查找 Cursor.exe
                import subprocess
                
                possible_paths = [
                    Path(os.getenv('LOCALAPPDATA', '')) / 'Programs' / 'cursor' / 'Cursor.exe',
                    Path(os.getenv('APPDATA', '')) / 'Programs' / 'cursor' / 'Cursor.exe',
                    Path('C:/Program Files/Cursor/Cursor.exe'),
                    Path('C:/Program Files (x86)/Cursor/Cursor.exe'),
                ]
                
                for cursor_exe in possible_paths:
                    if cursor_exe.exists():
                        logger.info(f"找到 Cursor: {cursor_exe}")
                        # ⭐ 使用多重标志确保完全独立的进程
                        DETACHED_PROCESS = 0x00000008
                        CREATE_NEW_PROCESS_GROUP = 0x00000200
                        CREATE_NO_WINDOW = 0x08000000
                        
                        subprocess.Popen(
                            [str(cursor_exe)], 
                            shell=False,
                            creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                            close_fds=True,
                            stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                        logger.info("✅ Cursor 已启动（完全独立进程）")
                        return True
                
                logger.error("未找到 Cursor.exe")
                return False
            
            elif self.platform == 'darwin':
                # macOS: 使用 open 命令（自动进程分离）
                import subprocess
                subprocess.Popen(
                    ['open', '-a', 'Cursor'],
                    start_new_session=True  # Unix 系统使用 start_new_session 实现进程分离
                )
                logger.info("✅ Cursor 已启动（独立进程）")
                return True
            
            else:
                # Linux: 使用 cursor 命令
                import subprocess
                subprocess.Popen(
                    ['cursor'],
                    start_new_session=True  # Unix 系统使用 start_new_session 实现进程分离
                )
                logger.info("✅ Cursor 已启动（独立进程）")
                return True
        
        except Exception as e:
            logger.error(f"启动 Cursor 失败: {e}")
            return False


# 全局切换器实例
_switcher = None


def get_switcher() -> CursorSwitcher:
    """
    获取全局切换器实例（单例）
    
    Returns:
        CursorSwitcher: 切换器实例
    """
    global _switcher
    if _switcher is None:
        _switcher = CursorSwitcher()
    return _switcher


def switch_cursor_account(account: Dict[str, Any]) -> bool:
    """
    切换 Cursor 账号（便捷函数）
    
    Args:
        account: 账号数据
        
    Returns:
        bool: 是否成功
    """
    switcher = get_switcher()
    return switcher.switch_account(account)


