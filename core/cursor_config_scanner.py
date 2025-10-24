#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursor 配置文件扫描器
从 state.vscdb 数据库读取当前登录账号信息
"""

import sqlite3
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import urllib.parse

from utils.logger import get_logger

logger = get_logger("cursor_config_scanner")


class CursorConfigScanner:
    """Cursor 配置文件扫描器 - 基于 state.vscdb 数据库"""
    
    def __init__(self):
        """初始化扫描器"""
        self.platform = sys.platform
        self.db_paths = []
    
    def detect_state_db_paths(self) -> List[Path]:
        """
        检测所有 state.vscdb 数据库路径
        
        Returns:
            List[Path]: 数据库文件路径列表
        """
        home = Path.home()
        possible_paths = []
        
        if self.platform == 'win32':
            # Windows 平台
            roaming = os.getenv('APPDATA', home / 'AppData' / 'Roaming')
            local = os.getenv('LOCALAPPDATA', home / 'AppData' / 'Local')
            
            possible_paths = [
                Path(roaming) / 'Cursor' / 'User' / 'globalStorage' / 'state.vscdb',
                Path(local) / 'Cursor' / 'User' / 'globalStorage' / 'state.vscdb',
                home / '.cursor' / 'User' / 'globalStorage' / 'state.vscdb',
            ]
            
            # 扫描所有盘符
            import string
            drives = [f"{d}:/" for d in string.ascii_uppercase if Path(f"{d}:/").exists()]
            
            for drive in drives:
                possible_paths.extend([
                    Path(drive) / 'Cursor' / 'User' / 'globalStorage' / 'state.vscdb',
                    Path(drive) / 'Program Files' / 'Cursor' / 'User' / 'globalStorage' / 'state.vscdb',
                ])
        
        elif self.platform == 'darwin':
            # macOS 平台
            possible_paths = [
                home / 'Library' / 'Application Support' / 'Cursor' / 'User' / 'globalStorage' / 'state.vscdb',
                home / '.cursor' / 'User' / 'globalStorage' / 'state.vscdb',
            ]
        
        else:
            # Linux 平台
            possible_paths = [
                home / '.config' / 'Cursor' / 'User' / 'globalStorage' / 'state.vscdb',
                home / '.cursor' / 'User' / 'globalStorage' / 'state.vscdb',
            ]
        
        # 返回所有存在的路径
        existing_paths = [p for p in possible_paths if p.exists()]
        
        # 按最后修改时间排序（最近修改的优先 - 这是当前使用的）
        if existing_paths:
            existing_paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            logger.info(f"找到 {len(existing_paths)} 个 state.vscdb 数据库")
            for i, p in enumerate(existing_paths, 1):
                logger.debug(f"  {i}. {p} (修改时间: {time.ctime(p.stat().st_mtime)})")
        else:
            logger.warning("未找到任何 state.vscdb 数据库")
        
        self.db_paths = existing_paths
        return existing_paths
    
    def read_state_vscdb(self, db_path: Path, max_retries: int = 3) -> Optional[Dict[str, str]]:
        """
        读取 state.vscdb 数据库
        
        Args:
            db_path: 数据库文件路径
            max_retries: 最大重试次数
            
        Returns:
            Optional[Dict]: 数据库数据
        """
        for attempt in range(max_retries):
            try:
                # 使用只读模式打开（防止数据库锁定）
                uri = f"file:{db_path}?mode=ro"
                conn = sqlite3.connect(uri, uri=True, timeout=2.0, check_same_thread=False)
                cursor = conn.cursor()
                
                # 读取所有认证相关的字段和机器码字段
                cursor.execute("""
                    SELECT key, value FROM ItemTable 
                    WHERE key LIKE '%email%' 
                       OR key LIKE '%Token%' 
                       OR key LIKE '%token%'
                       OR key LIKE 'cursorAuth/%'
                       OR key LIKE 'WorkosCursorSessionToken%'
                       OR key LIKE 'telemetry.%'
                       OR key LIKE 'system.machine%'
                """)
                rows = cursor.fetchall()
                
                data = {}
                for key, value in rows:
                    data[key] = value
                
                conn.close()
                
                if data:
                    logger.debug(f"成功读取数据库: {db_path}")
                    # 调试：打印所有邮箱字段
                    email_keys = [k for k in data.keys() if 'email' in k.lower()]
                    logger.debug(f"数据库中的邮箱字段: {email_keys}")
                    for key in email_keys:
                        logger.debug(f"  {key} = {data.get(key)}")
                    return data
                
                return None
                
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower():
                    logger.debug(f"数据库被锁定，重试 {attempt + 1}/{max_retries}")
                    time.sleep(0.2 * (attempt + 1))
                    continue
                else:
                    logger.error(f"数据库操作错误: {e}")
                    break
            
            except Exception as e:
                logger.error(f"读取数据库失败: {e}")
                break
        
        return None
    
    def extract_machine_info_from_db(self, db_data: Dict[str, str]) -> Optional[Dict[str, str]]:
        """
        从数据库数据中提取机器码信息
        
        Args:
            db_data: 数据库数据
            
        Returns:
            Optional[Dict]: 机器码信息字典，如果缺少字段则返回None
        """
        machine_info = {}
        
        # 提取5个必需的机器码字段
        machine_id_fields = [
            'telemetry.machineId',
            'telemetry.macMachineId',
            'telemetry.devDeviceId',
            'telemetry.sqmId',
            'system.machineGuid'
        ]
        
        for field in machine_id_fields:
            value = db_data.get(field)
            if value:
                machine_info[field] = value
        
        # 如果所有字段都存在，返回完整的机器码信息
        if len(machine_info) == len(machine_id_fields):
            logger.debug(f"成功提取机器码信息: {list(machine_info.keys())}")
            return machine_info
        elif machine_info:
            # 部分字段存在，记录警告
            logger.warning(f"机器码信息不完整: 找到 {len(machine_info)}/{len(machine_id_fields)} 个字段")
            return machine_info  # 返回部分信息
        else:
            logger.debug("未找到机器码信息")
            return None
    
    def extract_tokens_from_db(self, db_data: Dict[str, str]) -> Dict[str, Any]:
        """
        从数据库数据中提取 Token 信息
        
        Args:
            db_data: 数据库数据
            
        Returns:
            Dict: Token 信息字典
        """
        tokens = {
            'session_token': None,  # 用于 Cookie 认证的 Token
            'access_token': None,   # 原始 AccessToken (type=session)
            'refresh_token': None,
            'email': None,
            'user_id': None,
            'token_format': None,
            'cached_email': None
        }
        
        # ⭐⭐⭐ 关键：优先使用 cursorAuth/cachedEmail（当前真正登录的账号）
        cached_email = db_data.get('cursorAuth/cachedEmail')
        if cached_email:
            tokens['email'] = cached_email
            tokens['cached_email'] = cached_email
            logger.info(f"✓ 找到当前登录邮箱: {cached_email}")
        else:
            # 降级：尝试其他邮箱字段
            email = db_data.get('cursor.email') or db_data.get('user.email')
            if email:
                tokens['email'] = email
                logger.debug(f"使用备用邮箱字段: {email}")
        
        # 提取 AccessToken（type=session）
        access_token = db_data.get('cursorAuth/accessToken')
        if access_token and access_token.startswith('eyJ'):
            tokens['access_token'] = access_token
            logger.info(f"✓ 找到 AccessToken (type=session)")
            logger.debug(f"  AccessToken: {access_token[:50]}...")
            
            # ⭐⭐⭐ 关键：从 AccessToken 构造 SessionToken 格式
            try:
                import base64
                import json
                
                # 解析 JWT 获取用户ID
                parts = access_token.split('.')
                if len(parts) >= 2:
                    payload = parts[1]
                    padding = len(payload) % 4
                    if padding:
                        payload += '=' * (4 - padding)
                    decoded = base64.urlsafe_b64decode(payload)
                    token_data = json.loads(decoded)
                    user_id_from_token = token_data.get('sub', '').replace('auth0|', '')
                    
                    # 构造 SessionToken 格式：user_xxx::jwt_token
                    if user_id_from_token.startswith('user_'):
                        constructed_token = f"{user_id_from_token}::{access_token}"
                        tokens['session_token'] = constructed_token
                        tokens['user_id'] = user_id_from_token
                        tokens['token_format'] = 'constructed_from_access'
                        logger.info(f"✓ 从 AccessToken 构造 SessionToken: {user_id_from_token}::...")
                    else:
                        logger.warning(f"用户ID格式异常: {user_id_from_token}")
            except Exception as e:
                logger.error(f"构造 SessionToken 失败: {e}")
        
        # 提取 RefreshToken
        refresh_token = db_data.get('cursorAuth/refreshToken')
        if refresh_token:
            tokens['refresh_token'] = refresh_token
            logger.debug(f"✓ 找到 RefreshToken")
        
        # 提取原始的 WorkosCursorSessionToken（如果有）
        if not tokens['session_token']:
            session_token_keys = [
                'WorkosCursorSessionToken',
                'workos.sessionToken',
                'cursorAuth.sessionToken'
            ]
            
            for key in session_token_keys:
                if key in db_data and db_data[key]:
                    tokens['session_token'] = db_data[key]
                    tokens['token_format'] = 'workos_session'
                    logger.info(f"✓ 找到原始 SessionToken (来自 {key})")
                    logger.debug(f"  SessionToken: {db_data[key][:50]}...")
                    
                    # 提取用户ID
                    decoded = urllib.parse.unquote(db_data[key]) if '%3A%3A' in db_data[key] else db_data[key]
                    if '::' in decoded:
                        user_part = decoded.split('::')[0]
                        if user_part.startswith('user_'):
                            tokens['user_id'] = user_part
                    break
        
        return tokens
    
    def scan_all_databases(self) -> List[Dict[str, Any]]:
        """
        扫描所有数据库并提取信息
        
        Returns:
            List[Dict]: 账号信息列表
        """
        if not self.db_paths:
            self.detect_state_db_paths()
        
        accounts = []
        
        for db_path in self.db_paths:
            logger.info(f"扫描数据库: {db_path}")
            
            db_data = self.read_state_vscdb(db_path)
            if not db_data:
                logger.warning(f"  无法读取数据库")
                continue
            
            tokens = self.extract_tokens_from_db(db_data)
            
            # 提取机器码信息
            machine_info = self.extract_machine_info_from_db(db_data)
            
            # 检查是否有有效的 Token 和邮箱
            if (tokens['access_token'] or tokens['session_token']) and tokens['email']:
                account_info = {
                    'db_path': str(db_path),
                    **tokens
                }
                
                # 添加机器码信息
                if machine_info:
                    account_info['machine_info'] = machine_info
                    logger.debug(f"✓ 提取到机器码信息")
                else:
                    # 如果数据库中没有机器码，生成一个新的
                    logger.info(f"数据库中没有机器码，生成新机器码...")
                    from core.machine_id_generator import generate_machine_info
                    user_id = tokens.get('user_id')
                    new_machine_info = generate_machine_info(platform='win32', user_id=user_id)
                    account_info['machine_info'] = new_machine_info
                    logger.info(f"✓ 已生成新机器码")
                
                accounts.append(account_info)
                logger.info(f"✓ 提取到账号: {tokens.get('email', '未知')}")
            else:
                logger.warning(f"✗ 数据库中未找到有效的 Token 或邮箱")
        
        return accounts
    
    def get_current_account(self) -> Optional[Dict[str, Any]]:
        """
        获取当前登录的账号（最近修改的数据库）
        
        Returns:
            Optional[Dict]: 当前账号信息或 None
        """
        accounts = self.scan_all_databases()
        
        if accounts:
            # 返回第一个（最近修改的数据库）
            current = accounts[0]
            logger.info(f"当前登录账号: {current.get('email', '未知')}")
            return current
        
        logger.warning("未找到当前登录的账号")
        return None


# 全局扫描器实例
_scanner = None


def get_scanner() -> CursorConfigScanner:
    """
    获取全局扫描器实例（单例）
    
    Returns:
        CursorConfigScanner: 扫描器实例
    """
    global _scanner
    if _scanner is None:
        _scanner = CursorConfigScanner()
    return _scanner


if __name__ == '__main__':
    # 测试代码
    print("=" * 60)
    print("Cursor 配置扫描器测试 - state.vscdb 数据库读取")
    print("=" * 60)
    
    scanner = CursorConfigScanner()
    
    # 检测数据库路径
    paths = scanner.detect_state_db_paths()
    print(f"\n找到 {len(paths)} 个 state.vscdb 数据库:")
    for p in paths:
        print(f"  - {p}")
    
    # 获取当前账号
    print("\n" + "=" * 60)
    account = scanner.get_current_account()
    
    if account:
        print(f"\n✅ 当前登录账号:")
        print(f"  邮箱: {account.get('email', '未知')}")
        print(f"  缓存邮箱: {account.get('cached_email', '未知')}")
        print(f"  Token 格式: {account.get('token_format', '未知')}")
        print(f"  数据库: {account.get('db_path', '未知')}")
        
        if account.get('access_token'):
            print(f"  AccessToken: {account['access_token'][:50]}...")
        
        if account.get('session_token'):
            print(f"  SessionToken: {account['session_token'][:50]}...")
    else:
        print("\n❌ 未找到当前登录的账号")
