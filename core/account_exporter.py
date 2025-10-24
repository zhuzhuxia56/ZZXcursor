#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账号导入导出模块
支持多种格式的账号数据导入导出
"""

import json
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from utils.logger import get_logger
from utils.crypto import get_crypto_manager

logger = get_logger("account_exporter")


class AccountExporter:
    """账号导入导出器"""
    
    def __init__(self):
        """初始化导出器"""
        self.crypto = get_crypto_manager()
    
    def export_to_json(self, accounts: List[Dict[str, Any]], file_path: str, encrypt: bool = True) -> bool:
        """
        导出账号到 JSON 文件
        
        Args:
            accounts: 账号列表
            file_path: 导出文件路径
            encrypt: 是否加密 Token
            
        Returns:
            bool: 是否成功
        """
        try:
            export_data = {
                'version': '1.0',
                'app': 'Zzx-Cursor-Auto',
                'export_date': datetime.now().isoformat(),
                'encrypted': encrypt,
                'count': len(accounts),
                'accounts': []
            }
            
            for account in accounts:
                access_token = account.get('access_token', '')
                refresh_token = account.get('refresh_token', '')
                
                # ⭐ 如果 refresh_token 为空，用 access_token 填充（它们通常是同一个值）
                if not refresh_token and access_token:
                    refresh_token = access_token
                
                account_data = {
                    'email': account.get('email'),
                    'password': account.get('password') if account.get('password') else None,
                    'access_token': access_token,
                    'refresh_token': refresh_token,  # ⭐ 如果为空则用 access_token
                    'session_token': account.get('session_token') if account.get('session_token') else None,  # ⭐ null
                    'user_id': account.get('user_id', ''),
                    'membership_type': account.get('membership_type', 'free'),
                    'days_remaining': account.get('days_remaining', 0),
                    'usage_percent': account.get('usage_percent', 0),
                    'used': account.get('used', 0),
                    'limit_value': account.get('limit_value', 1000),
                    'notes': account.get('notes') if account.get('notes') else None,
                    'created_at': account.get('created_at', ''),
                    'last_used': account.get('last_used') if account.get('last_used') else None,
                    'last_refresh_time': account.get('last_refresh_time') if account.get('last_refresh_time') else None,  # ⭐ 增量刷新时间
                    'accumulated_cost': account.get('accumulated_cost', 0),  # ⭐ 累计金额
                    'system_type': 'win32',
                }
                
                # ⭐ 机器码信息（必须保留）
                machine_info = account.get('machine_info')
                if machine_info:
                    account_data['machine_info'] = machine_info
                
                # 如果需要加密
                if encrypt:
                    if account_data.get('access_token'):
                        account_data['access_token'] = self.crypto.encrypt(account_data['access_token'])
                    if account_data.get('refresh_token'):
                        account_data['refresh_token'] = self.crypto.encrypt(account_data['refresh_token'])
                    # ⭐ session_token 只有非空时才加密
                    if account_data.get('session_token'):
                        account_data['session_token'] = self.crypto.encrypt(account_data['session_token'])
                    if account_data.get('password'):
                        account_data['password'] = self.crypto.encrypt(account_data['password'])
                    # ⭐ 加密机器码信息 - 每个字段单独加密
                    if account_data.get('machine_info') and isinstance(account_data['machine_info'], dict):
                        encrypted_machine_info = {}
                        for key, value in account_data['machine_info'].items():
                            if value:
                                encrypted_machine_info[key] = self.crypto.encrypt(str(value))
                            else:
                                encrypted_machine_info[key] = ''
                        account_data['machine_info'] = encrypted_machine_info
                
                export_data['accounts'].append(account_data)
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功导出 {len(accounts)} 个账号到: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出账号失败: {e}")
            return False
    
    def import_from_json(self, file_path: str) -> Optional[List[Dict[str, Any]]]:
        """
        从 JSON 文件导入账号（智能识别各种格式）
        
        支持的格式：
        1. Zzx 标准格式：{'accounts': [...]}
        2. FlyCursor 格式：[{...}] 或 {'accounts': [...]}
        3. 任意包含 access_token 的 JSON 格式
        4. 无外层括号的多对象格式（自动修复）
        
        Args:
            file_path: 文件路径
            
        Returns:
            Optional[List]: 账号列表或 None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # ⭐ 尝试解析JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                # ⭐ 如果解析失败，尝试自动修复格式
                logger.debug(f"JSON解析失败: {e}，尝试自动修复")
                
                # 修复方法1：包装为数组（可能缺少外层[]）
                if not content.startswith('['):
                    content_fixed = '[' + content + ']'
                else:
                    content_fixed = content
                
                # 修复方法2：移除结尾的多余逗号
                import re
                content_fixed = re.sub(r',\s*]', ']', content_fixed)
                
                # 尝试解析修复后的内容
                try:
                    data = json.loads(content_fixed)
                    logger.info("✓ 自动修复JSON格式成功（添加数组括号 + 移除多余逗号）")
                except Exception as e2:
                    logger.error(f"无法自动修复JSON格式: {e2}")
                    return None
            
            # ⭐ 智能识别各种格式
            accounts_data = None
            encrypted = False
            
            # 格式1: 标准格式 {'accounts': [...], 'encrypted': true/false}
            if isinstance(data, dict) and 'accounts' in data:
                accounts_data = data['accounts']
                encrypted = data.get('encrypted', False)
                logger.info(f"识别为标准格式，包含 {len(accounts_data)} 个账号")
            
            # 格式2: 直接是账号数组 [{...}, {...}]
            elif isinstance(data, list):
                accounts_data = data
                logger.info(f"识别为数组格式，包含 {len(accounts_data)} 个账号")
            
            # 格式3: 单个账号对象 {...}
            elif isinstance(data, dict):
                # 尝试提取 access_token
                if self._has_access_token(data):
                    accounts_data = [data]
                    logger.info("识别为单个账号对象")
                else:
                    logger.error("JSON 中未找到 access_token 字段")
                    return None
            
            if not accounts_data:
                logger.error("无法识别 JSON 格式")
                return None
            
            # ⭐ 智能解析每个账号
            accounts = []
            for item in accounts_data:
                account = self._extract_account_from_json(item, encrypted)
                if account:
                    accounts.append(account)
            
            logger.info(f"成功解析 {len(accounts)} 个账号")
            return accounts if accounts else None
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}")
            return None
        except Exception as e:
            logger.error(f"导入账号失败: {e}")
            return None
    
    def _has_access_token(self, data: dict) -> bool:
        """
        检查字典中是否包含 access_token
        
        支持的字段名：
        - access_token
        - accessToken
        - token
        - Access_Token
        """
        token_fields = ['access_token', 'accessToken', 'token', 'Access_Token', 'ACCESS_TOKEN']
        for field in token_fields:
            if data.get(field):
                return True
        return False
    
    def _extract_account_from_json(self, item: dict, encrypted: bool = False) -> Optional[Dict[str, Any]]:
        """
        从 JSON 对象中智能提取账号信息
        
        支持多层嵌套结构，如：
        - 顶层字段：{"access_token": "..."}
        - auth_info嵌套：{"auth_info": {"cursorAuth/accessToken": "..."}}
        
        Args:
            item: JSON 账号对象
            encrypted: 是否已加密
            
        Returns:
            Optional[Dict]: 标准账号数据或 None
        """
        try:
            # ⭐ 智能提取 access_token（支持多种字段名和嵌套结构）
            access_token = (
                item.get('access_token') or 
                item.get('accessToken') or 
                item.get('token') or 
                item.get('Access_Token') or
                item.get('ACCESS_TOKEN')
            )
            
            # ⭐ 如果顶层没找到，尝试从 auth_info 中提取
            if not access_token and item.get('auth_info'):
                auth_info = item['auth_info']
                access_token = (
                    auth_info.get('cursorAuth/accessToken') or
                    auth_info.get('accessToken') or
                    auth_info.get('access_token') or
                    auth_info.get('token')
                )
            
            if not access_token:
                logger.warning(f"账号对象中未找到 access_token: {item.get('email', 'unknown')}")
                return None
            
            # ⭐ 智能提取 refresh_token
            refresh_token = (
                item.get('refresh_token') or 
                item.get('refreshToken') or 
                item.get('Refresh_Token')
            )
            
            # ⭐ 如果顶层没找到，尝试从 auth_info 中提取
            if not refresh_token and item.get('auth_info'):
                auth_info = item['auth_info']
                refresh_token = (
                    auth_info.get('cursorAuth/refreshToken') or
                    auth_info.get('refreshToken') or
                    auth_info.get('refresh_token')
                )
            
            # 如果还是没有，使用 access_token
            if not refresh_token:
                refresh_token = access_token
            
            # ⭐ 智能提取邮箱（支持多种字段名）
            email = (
                item.get('email') or 
                item.get('Email') or 
                item.get('mail') or 
                item.get('user') or
                item.get('username')
            )
            
            # ⭐ 如果顶层没找到，尝试从 auth_info 中提取
            if not email and item.get('auth_info'):
                auth_info = item['auth_info']
                email = (
                    auth_info.get('cursorAuth/cachedEmail') or
                    auth_info.get('email') or
                    auth_info.get('Email')
                )
            
            # 默认邮箱
            if not email:
                email = 'unknown@cursor.com'
            
            # ⭐ 提取使用量信息（支持modelUsage嵌套）
            used = item.get('used') or 0
            limit_value = item.get('limit_value') or item.get('limit') or 1000
            
            if item.get('modelUsage'):
                model_usage = item['modelUsage']
                used = model_usage.get('used') or used
                limit_value = model_usage.get('total') or limit_value
            
            # ⭐ 计算使用率
            usage_percent = item.get('usage_percent') or item.get('usagePercent') or 0
            if not usage_percent and limit_value > 0:
                usage_percent = round((used / limit_value) * 100, 1)
            
            # 构建标准账号数据
            account = {
                'email': email,
                'access_token': access_token,
                'refresh_token': refresh_token,
                'session_token': item.get('session_token') or item.get('sessionToken') or '',
                'user_id': item.get('user_id') or item.get('userId') or '',
                'membership_type': item.get('membership_type') or item.get('membershipType') or 'free',
                'days_remaining': item.get('days_remaining') or item.get('daysRemaining') or item.get('daysRemainingOnTrial') or 0,
                'usage_percent': usage_percent,
                'used': used,
                'limit_value': limit_value,
                'notes': item.get('notes') or f"导入于 {datetime.now().strftime('%Y-%m-%d')}",
                'last_refresh_time': item.get('last_refresh_time') or item.get('lastRefreshTime') or None,  # ⭐ 增量刷新时间
                'accumulated_cost': item.get('accumulated_cost') or item.get('accumulatedCost') or 0,  # ⭐ 累计金额
            }
            
            # 提取机器码信息
            machine_info = item.get('machine_info') or item.get('machineInfo')
            if machine_info:
                account['machine_info'] = machine_info
            
            # ⭐ 解密（如果需要）
            if encrypted:
                if account['access_token']:
                    try:
                        account['access_token'] = self.crypto.decrypt(account['access_token'])
                    except:
                        logger.warning(f"解密 access_token 失败: {email}")
                
                if account['refresh_token']:
                    try:
                        account['refresh_token'] = self.crypto.decrypt(account['refresh_token'])
                    except:
                        logger.warning(f"解密 refresh_token 失败: {email}")
                
                if account.get('session_token'):
                    try:
                        account['session_token'] = self.crypto.decrypt(account['session_token'])
                    except:
                        pass
                
                # 解密机器码
                if account.get('machine_info'):
                    try:
                        if isinstance(account['machine_info'], str):
                            machine_info_json = self.crypto.decrypt(account['machine_info'])
                            account['machine_info'] = json.loads(machine_info_json)
                        elif isinstance(account['machine_info'], dict):
                            decrypted_machine_info = {}
                            for key, value in account['machine_info'].items():
                                if value:
                                    try:
                                        decrypted_machine_info[key] = self.crypto.decrypt(value)
                                    except:
                                        decrypted_machine_info[key] = value
                                else:
                                    decrypted_machine_info[key] = ''
                            account['machine_info'] = decrypted_machine_info
                    except:
                        logger.warning(f"解密 machine_info 失败: {email}")
            
            logger.debug(f"成功提取账号: {email}")
            return account
            
        except Exception as e:
            logger.error(f"提取账号信息失败: {e}")
            return None
    
    def import_from_flycursor(self, file_path: str) -> Optional[List[Dict[str, Any]]]:
        """
        从 FlyCursor 格式导入账号
        
        Args:
            file_path: FlyCursor 导出的 JSON 文件
            
        Returns:
            Optional[List]: 账号列表
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # FlyCursor 格式转换
            accounts = []
            
            # 处理不同的 FlyCursor 格式
            if isinstance(data, list):
                # 格式1：直接是账号数组
                for item in data:
                    account = {
                        'email': item.get('email'),
                        'access_token': item.get('accessToken') or item.get('access_token'),
                        'refresh_token': item.get('refreshToken') or item.get('refresh_token'),
                        'membership_type': 'free',
                        'notes': 'From FlyCursor'
                    }
                    # 提取机器码信息
                    if item.get('machine_info'):
                        account['machine_info'] = item.get('machine_info')
                    accounts.append(account)
            
            elif isinstance(data, dict) and 'accounts' in data:
                # 格式2：有 accounts 字段
                for item in data['accounts']:
                    account = {
                        'email': item.get('email'),
                        'access_token': item.get('accessToken') or item.get('access_token'),
                        'refresh_token': item.get('refreshToken') or item.get('refresh_token'),
                        'membership_type': 'free',
                        'notes': 'From FlyCursor'
                    }
                    # 提取机器码信息
                    if item.get('machine_info'):
                        account['machine_info'] = item.get('machine_info')
                    accounts.append(account)
            
            logger.info(f"成功导入 {len(accounts)} 个 FlyCursor 账号")
            return accounts
            
        except Exception as e:
            logger.error(f"导入 FlyCursor 账号失败: {e}")
            return None
    
    def export_to_csv(self, accounts: List[Dict[str, Any]], file_path: str) -> bool:
        """
        导出账号到 CSV 文件
        
        Args:
            accounts: 账号列表
            file_path: 导出文件路径
            
        Returns:
            bool: 是否成功
        """
        try:
            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                
                # 写入表头
                writer.writerow([
                    '邮箱', '套餐类型', '使用率%', '剩余天数',
                    '已用/总量', '创建时间', '最后使用', '备注'
                ])
                
                # 写入数据
                for account in accounts:
                    writer.writerow([
                        account.get('email', ''),
                        account.get('membership_type', 'free').upper(),
                        account.get('usage_percent', 0),
                        account.get('days_remaining', 0),
                        f"{account.get('used', 0)}/{account.get('limit_value', 1000)}",
                        account.get('created_at', '')[:10],
                        account.get('last_used', '')[:10],
                        account.get('notes', '')
                    ])
            
            logger.info(f"成功导出 {len(accounts)} 个账号到 CSV: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出到 CSV 失败: {e}")
            return False
    
    def export_to_txt(self, accounts: List[Dict[str, Any]], file_path: str, encrypt: bool = True) -> bool:
        """
        导出账号到纯文本 TXT 文件（AccessToken 格式）
        
        格式（一行一个账号，中间用-----分隔）：
        邮箱：xxx@example.com；-----access_token：eyJhbGc...；（明文）
        邮箱：xxx@example.com；-----access_token：gAAAAABnGx...；（加密）
        
        Args:
            accounts: 账号列表
            file_path: 导出文件路径
            encrypt: 是否加密 access_token（默认True）
            
        Returns:
            bool: 是否成功
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # 写入每个账号（一行一个）
                for account in accounts:
                    email = account.get('email', 'unknown@cursor.com')
                    access_token = account.get('access_token', '')
                    
                    # ⭐ 如果需要加密
                    if encrypt and access_token:
                        try:
                            access_token = self.crypto.encrypt(access_token)
                        except Exception as e:
                            logger.warning(f"加密 access_token 失败: {email}, {e}")
                            # 加密失败，使用明文
                    
                    # 一行包含邮箱和 access_token，中间用-----分隔
                    f.write(f"邮箱：{email}；-----access_token：{access_token}；\n")
            
            encrypt_status = "加密" if encrypt else "明文"
            logger.info(f"成功导出 {len(accounts)} 个账号到 TXT ({encrypt_status}): {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出到 TXT 失败: {e}")
            return False
    
    def decrypt_and_view(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        解密并查看加密的导出文件
        
        Args:
            file_path: 加密文件路径
            
        Returns:
            Optional[Dict]: 解密后的数据，包含所有账号信息
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, dict):
                logger.error("文件格式错误")
                return None
            
            # 检查是否加密
            encrypted = data.get('encrypted', False)
            
            if not encrypted:
                logger.info("文件未加密，直接返回")
                return data
            
            # 解密所有账号数据
            decrypted_data = data.copy()
            decrypted_accounts = []
            
            for account in data.get('accounts', []):
                decrypted_account = account.copy()
                
                # 解密 access_token
                if decrypted_account.get('access_token'):
                    try:
                        decrypted_account['access_token'] = self.crypto.decrypt(
                            decrypted_account['access_token']
                        )
                    except Exception as e:
                        logger.error(f"解密 access_token 失败: {e}")
                        decrypted_account['access_token'] = '[解密失败]'
                
                # 解密 refresh_token
                if decrypted_account.get('refresh_token'):
                    try:
                        decrypted_account['refresh_token'] = self.crypto.decrypt(
                            decrypted_account['refresh_token']
                        )
                    except Exception as e:
                        logger.error(f"解密 refresh_token 失败: {e}")
                        decrypted_account['refresh_token'] = '[解密失败]'
                
                # 解密 session_token
                if decrypted_account.get('session_token'):
                    try:
                        decrypted_account['session_token'] = self.crypto.decrypt(
                            decrypted_account['session_token']
                        )
                    except Exception as e:
                        logger.error(f"解密 session_token 失败: {e}")
                        decrypted_account['session_token'] = '[解密失败]'
                
                # 解密 password
                if decrypted_account.get('password'):
                    try:
                        decrypted_account['password'] = self.crypto.decrypt(
                            decrypted_account['password']
                        )
                    except Exception as e:
                        logger.error(f"解密 password 失败: {e}")
                        decrypted_account['password'] = '[解密失败]'
                
                # ⭐ 解密 machine_info - 支持新旧两种格式
                if decrypted_account.get('machine_info'):
                    try:
                        if isinstance(decrypted_account['machine_info'], str):
                            # 旧格式：整个JSON字符串加密
                            machine_info_json = self.crypto.decrypt(
                                decrypted_account['machine_info']
                            )
                            decrypted_account['machine_info'] = json.loads(machine_info_json)
                        elif isinstance(decrypted_account['machine_info'], dict):
                            # 新格式：每个字段单独加密
                            decrypted_machine_info = {}
                            for key, value in decrypted_account['machine_info'].items():
                                if value:
                                    try:
                                        decrypted_machine_info[key] = self.crypto.decrypt(value)
                                    except Exception as e:
                                        logger.error(f"解密 machine_info.{key} 失败: {e}")
                                        decrypted_machine_info[key] = '[解密失败]'
                                else:
                                    decrypted_machine_info[key] = ''
                            decrypted_account['machine_info'] = decrypted_machine_info
                    except Exception as e:
                        logger.error(f"解密 machine_info 失败: {e}")
                        decrypted_account['machine_info'] = '[解密失败]'
                
                decrypted_accounts.append(decrypted_account)
            
            decrypted_data['accounts'] = decrypted_accounts
            decrypted_data['encrypted'] = False  # 标记为已解密
            
            logger.info(f"成功解密 {len(decrypted_accounts)} 个账号")
            return decrypted_data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}")
            return None
        except Exception as e:
            logger.error(f"解密查看失败: {e}")
            return None


# 全局导出器实例
_exporter = None


def get_exporter() -> AccountExporter:
    """
    获取全局导出器实例（单例）
    
    Returns:
        AccountExporter: 导出器实例
    """
    global _exporter
    if _exporter is None:
        _exporter = AccountExporter()
    return _exporter

