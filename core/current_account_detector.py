#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
当前账号检测器
从 state.vscdb 数据库读取并调用官方 API 获取账号详情
"""

from typing import Optional, Dict, Any
import jwt
from datetime import datetime

from core.cursor_config_scanner import get_scanner
from core.cursor_api import get_api_client
from utils.logger import get_logger

logger = get_logger("current_account_detector")


class CurrentAccountDetector:
    """当前账号检测器"""
    
    def __init__(self, storage=None):
        """初始化检测器"""
        self.scanner = get_scanner()
        self.api_client = get_api_client()
        self.storage = storage  # ⭐ 传入storage实例，避免重复创建
    
    def validate_access_token(self, access_token: str) -> Dict[str, Any]:
        """
        验证 AccessToken 格式和有效性
        
        Args:
            access_token: JWT AccessToken
            
        Returns:
            Dict: 验证结果 {valid: bool, payload: dict, error: str, token_type: str}
        """
        try:
            # 解析 JWT（不验证签名）
            payload = jwt.decode(access_token, options={"verify_signature": False})
            
            # 检查类型
            token_type = payload.get('type', 'unknown')
            logger.debug(f"Token 类型: {token_type}")
            
            # type 可以是 "session" 或 "web"，都是有效的
            if token_type not in ['session', 'web']:
                return {
                    'valid': False,
                    'payload': payload,
                    'token_type': token_type,
                    'error': f"Token 类型未知: {token_type}"
                }
            
            # 检查过期时间
            exp = payload.get('exp')
            if exp:
                exp_time = datetime.fromtimestamp(exp)
                now = datetime.now()
                
                if now >= exp_time:
                    return {
                        'valid': False,
                        'payload': payload,
                        'token_type': token_type,
                        'error': f"Token 已过期: {exp_time}"
                    }
                
                # 计算剩余时间
                remaining = (exp_time - now).days
                logger.debug(f"Token 剩余有效期: {remaining} 天")
            
            return {
                'valid': True,
                'payload': payload,
                'token_type': token_type,
                'error': None
            }
            
        except jwt.DecodeError as e:
            return {
                'valid': False,
                'payload': {},
                'token_type': 'unknown',
                'error': f"JWT 解析失败: {e}"
            }
        except Exception as e:
            return {
                'valid': False,
                'payload': {},
                'token_type': 'unknown',
                'error': f"Token 验证异常: {e}"
            }
    
    def detect_current_account(self) -> Optional[Dict[str, Any]]:
        """
        检测当前登录的账号
        
        Returns:
            Optional[Dict]: 账号信息或 None
        """
        logger.info("开始检测当前 Cursor 账号...")
        
        # 1. 从数据库读取账号信息
        account_info = self.scanner.get_current_account()
        
        if not account_info:
            logger.warning("未找到数据库或账号信息")
            return None
        
        logger.info(f"找到数据库: {account_info.get('db_path')}")
        logger.info(f"当前登录邮箱: {account_info.get('email', '未知')}")
        
        # 2. 获取 Token
        # ⭐⭐⭐ 关键：必须使用 SessionToken 格式（user_xxx::jwt）进行 Cookie 认证
        session_token = account_info.get('session_token')
        access_token = account_info.get('access_token')
        token_format = account_info.get('token_format')
        
        if not session_token:
            logger.error("未找到可用的 SessionToken（Cookie 认证需要 user_xxx::jwt 格式）")
            return {
                'status': 'no_token',
                'error': '未找到 SessionToken',
                **account_info
            }
        
        logger.info(f"✓ 使用 SessionToken (格式: {token_format})")
        logger.debug(f"SessionToken: {session_token[:80]}...")
        
        # 验证 AccessToken（如果有）
        token_type = None
        if access_token:
            validation = self.validate_access_token(access_token)
            if validation['valid']:
                token_type = validation['token_type']
                logger.info(f"✓ AccessToken 验证通过 (type={token_type})")
            else:
                logger.warning(f"AccessToken 验证失败: {validation['error']}")
        
        # 3. 调用 API 获取详细信息（支持增量刷新）
        try:
            # ⭐ 尝试从现有数据库读取增量刷新信息
            last_refresh_time = None
            accumulated_cost = 0
            
            try:
                # 使用已经初始化的storage实例（避免重复创建）
                if hasattr(self, 'storage') and self.storage:
                    # 直接通过邮箱查询
                    email = account_info.get('email')
                    all_accounts = self.storage.get_all_accounts()
                    for acc in all_accounts:
                        if acc.get('email') == email:
                            last_refresh_time = acc.get('last_refresh_time')
                            accumulated_cost = acc.get('accumulated_cost', 0) or 0
                            logger.debug(f"从数据库读取: last_refresh_time={last_refresh_time}, accumulated_cost={accumulated_cost}")
                            break
            except Exception as e:
                logger.warning(f"读取增量刷新信息失败: {e}，将使用完整刷新")
                last_refresh_time = None
                accumulated_cost = 0
            
            # 根据是否有历史数据决定刷新模式
            if last_refresh_time:
                logger.info(f"启动增量刷新（上次: {last_refresh_time}，累计: ${accumulated_cost:.2f}）")
            else:
                logger.info("启动完整刷新（首次获取所有记录）")
            
            # SessionToken 格式（user_xxx::jwt）进行 Cookie 认证
            details = self.api_client.get_account_details(
                session_token, 
                detailed=True,
                last_refresh_time=last_refresh_time,
                accumulated_cost=accumulated_cost
            )
            
            if not details:
                logger.error("API 调用失败，无法获取账号详情")
                return {
                    'status': 'api_error',
                    'error': 'API 调用失败',
                    'email': account_info.get('email'),
                    'db_path': account_info.get('db_path'),
                    'token_type': token_type
                }
            
            logger.info("✓ 启动检测成功，账号信息已获取")
            
            # 4. 合并信息
            result = {
                'status': 'active',
                'email': details.get('email') or account_info.get('email'),
                'user_id': details.get('user_id'),
                'membership_type': details.get('membership_type', 'free'),
                'usage_percent': details.get('usage_percent', 0),
                'used': details.get('used', 0),
                'limit': details.get('limit', 1000),
                'days_remaining': details.get('days_remaining', 0),  # ⭐ 从 API 获取剩余天数
                'subscription_status': details.get('subscription_status'),  # ⭐ 订阅状态
                'total_cost': details.get('total_cost'),  # ⭐ 真实费用
                'total_tokens': details.get('total_tokens'),  # ⭐ 总tokens
                'unpaid_amount': details.get('unpaid_amount'),  # ⭐ 欠费金额
                'model_usage': details.get('model_usage'),  # ⭐ 模型费用详情
                'last_used': details.get('last_used'),  # ⭐ 最后使用时间
                'access_token': account_info.get('access_token'),
                'refresh_token': account_info.get('refresh_token'),
                'session_token': account_info.get('session_token'),
                'db_path': account_info.get('db_path'),
                'token_format': token_format,
                'detected_at': datetime.now().isoformat()
            }
            
            # 添加机器码信息（如果存在）
            if account_info.get('machine_info'):
                result['machine_info'] = account_info.get('machine_info')
                logger.debug(f"✓ 包含机器码信息")
            
            logger.info(f"✅ 检测成功: {result['email']} ({result['membership_type'].upper()})")
            return result
            
        except Exception as e:
            logger.exception(f"检测账号时发生异常: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'email': account_info.get('email'),
                'db_path': account_info.get('db_path')
            }
    
    def detect_all_accounts(self, detailed: bool = False) -> list:
        """
        检测所有可用的账号配置
        
        Args:
            detailed: 是否获取详细信息（默认False，快速模式）
        
        Returns:
            list: 账号信息列表
        """
        logger.info("开始扫描所有账号...")
        
        accounts = self.scanner.scan_all_databases()
        results = []
        
        for acc_info in accounts:
            access_token = acc_info.get('access_token')
            session_token = acc_info.get('session_token')
            
            api_token = access_token if access_token else session_token
            
            if not api_token:
                continue
            
            # 获取完整详情
            try:
                details = self.api_client.get_account_details(api_token, detailed=True)
                
                if details:
                    if api_token:
                        result = {
                            'status': 'active',
                            'email': details.get('email') or acc_info.get('email'),
                            'membership_type': details.get('membership_type', 'free'),
                            'usage_percent': details.get('usage_percent', 0),
                            'db_path': acc_info.get('db_path'),
                            **acc_info
                        }
                        results.append(result)
                        logger.info(f"✓ 检测到账号: {result['email']}")
            except Exception as e:
                logger.error(f"获取账号详情失败: {e}")
        
        logger.info(f"共检测到 {len(results)} 个有效账号")
        return results


# 全局检测器实例
_detector = None


def get_detector(storage=None) -> CurrentAccountDetector:
    """
    获取全局检测器实例（单例）
    
    Args:
        storage: 可选的storage实例，用于读取增量刷新信息
    
    Returns:
        CurrentAccountDetector: 检测器实例
    """
    global _detector
    if _detector is None:
        _detector = CurrentAccountDetector(storage=storage)
    else:
        # 更新storage实例（如果传入了新的）
        if storage:
            _detector.storage = storage
    return _detector


def detect_current_account() -> Optional[Dict[str, Any]]:
    """
    检测当前账号（便捷函数）
    
    Returns:
        Optional[Dict]: 账号信息或 None
    """
    return get_detector().detect_current_account()


if __name__ == '__main__':
    # 测试代码
    print("=" * 60)
    print("当前账号检测器测试")
    print("=" * 60)
    
    detector = CurrentAccountDetector()
    
    # 检测当前账号
    account = detector.detect_current_account()
    
    if account:
        print("\n✅ 检测到当前账号:")
        print(f"  状态: {account.get('status')}")
        print(f"  邮箱: {account.get('email')}")
        print(f"  套餐: {account.get('membership_type', 'unknown').upper()}")
        print(f"  使用率: {account.get('usage_percent', 0)}%")
        print(f"  数据库: {account.get('db_path')}")
        print(f"  Token类型: {account.get('token_type')}")
    else:
        print("\n❌ 未检测到账号或检测失败")
