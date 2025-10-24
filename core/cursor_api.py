#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursor 官方 API 模块
官方 API 调用和数据处理
"""

import json
import time
import urllib.request
import urllib.error
from typing import Optional, Dict, Any
import jwt
from datetime import datetime

from utils.logger import get_logger

logger = get_logger("cursor_api")


class CursorServerError(Exception):
    """Cursor服务器错误（500等）"""
    pass


class CursorOfficialAPI:
    """Cursor 官方 API 客户端"""
    
    # API 端点
    BASE_URL = "https://api2.cursor.sh"
    AUTH_URL = "https://cursor.com"
    POLL_ENDPOINT = f"{BASE_URL}/auth/poll"
    
    def __init__(self, timeout: int = 60):
        """
        初始化 API 客户端
        
        Args:
            timeout: 请求超时时间（秒），默认60秒
        """
        self.timeout = timeout
    
    def poll_auth_status(self, uuid: str) -> Optional[Dict[str, Any]]:
        """
        轮询授权状态
        
        Args:
            uuid: 登录 UUID
            
        Returns:
            Optional[Dict]: 如果授权完成，返回 Token 信息；否则返回 None
        """
        try:
            url = f"{self.POLL_ENDPOINT}?uuid={uuid}"
            
            req = urllib.request.Request(url, method='POST')
            req.add_header('Content-Type', 'application/json')
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
            req.add_header('Accept', 'application/json')
            
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    data = response.read().decode('utf-8')
                    result = json.loads(data)
                    
                    if 'accessToken' in result:
                        logger.info("成功获取 AccessToken")
                        return result
                    
            return None
            
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            logger.debug(f"HTTP 错误: {e.code}")
            return None
        except Exception as e:
            logger.debug(f"轮询请求失败: {e}")
            return None
    
    def get_user_info_by_bearer(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        使用 Bearer 认证获取用户信息（标准方式，学习自 YCursor）
        
        Args:
            access_token: AccessToken (type='session')，纯 JWT 格式
            
        Returns:
            Optional[Dict]: 用户信息
        """
        try:
            url = f"{self.AUTH_URL}/api/auth/me"
            
            req = urllib.request.Request(url)
            # ✅ Bearer 认证（YCursor 的标准方式）
            req.add_header('Authorization', f'Bearer {access_token}')
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            req.add_header('Accept', 'application/json')
            
            logger.debug(f"GET {url} (Bearer 认证)")
            logger.debug(f"Authorization: Bearer {access_token[:50]}...")
            
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    data = response.read().decode('utf-8')
                    result = json.loads(data)
                    logger.debug(f"✓ Bearer 认证成功，获取用户信息: {result.get('email', 'unknown')}")
                    return result
                elif response.status == 204:
                    logger.warning(f"API 返回 204 - Token 可能无效")
                    return None
                else:
                    logger.error(f"API 返回状态码: {response.status}")
                    return None
            
        except urllib.error.HTTPError as e:
            logger.error(f"Bearer 认证失败 - HTTP {e.code}: {e.reason}")
            return None
        except Exception as e:
            logger.error(f"Bearer 认证异常: {e}")
            return None
    
    def get_user_info_by_cookie(self, session_token: str) -> Optional[Dict[str, Any]]:
        """
        使用 Cookie 认证获取用户信息（用于构造的 user_xxx::jwt 格式）
        
        Args:
            session_token: 构造的 SessionToken 格式 (user_xxx::jwt)
                          ⚠️ 注意：这不是真正的 type='web' Token
                          只是用于 API 调用的格式
            
        Returns:
            Optional[Dict]: 用户信息
        """
        try:
            import urllib.parse
            
            # URL 编码
            encoded_token = session_token
            if '::' in session_token and '%3A%3A' not in session_token:
                encoded_token = urllib.parse.quote(session_token, safe='')
                logger.debug(f"SessionToken 格式已 URL 编码")
            
            url = f"{self.AUTH_URL}/api/auth/me"
            
            req = urllib.request.Request(url)
            # ✅ Cookie 认证（用于 user_xxx::jwt 格式）
            req.add_header('Cookie', f'WorkosCursorSessionToken={encoded_token}')
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            req.add_header('Accept', 'application/json')
            req.add_header('Accept-Language', 'zh-CN,zh;q=0.9,en;q=0.8')
            req.add_header('Referer', 'https://www.cursor.com/')
            
            logger.debug(f"GET {url} (Cookie 认证)")
            logger.debug(f"Cookie: WorkosCursorSessionToken={encoded_token[:50]}...")
            logger.debug(f"完整URL: {url}")
            logger.debug(f"请求头: User-Agent, Accept, Accept-Language, Referer")
            
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    data = response.read().decode('utf-8')
                    result = json.loads(data)
                    logger.debug(f"✓ Cookie 认证成功，获取用户信息: {result.get('email', 'unknown')}")
                    return result
                elif response.status == 204:
                    logger.warning(f"API 返回 204 - Token 可能无效")
                    return None
                else:
                    logger.error(f"API 返回状态码: {response.status}")
                    return None
            
        except urllib.error.HTTPError as e:
            logger.error(f"Cookie 认证失败 - HTTP {e.code}: {e.reason}")
            # ⭐ 如果是500错误，抛出特殊异常
            if e.code == 500:
                raise CursorServerError("Cursor服务器返回500错误，可能正在维护")
            return None
        except Exception as e:
            logger.error(f"Cookie 认证异常: {e}")
            return None
    
    def get_user_info(self, token: str) -> Optional[Dict[str, Any]]:
        """
        智能获取用户信息（自动选择认证方式）
        
        Args:
            token: Token（自动识别类型）
                  - AccessToken: eyj... → Bearer 认证
                  - SessionToken: user_xxx::jwt → Cookie 认证
            
        Returns:
            Optional[Dict]: 用户信息
        """
        # 检测 Token 类型
        if '::' in token or '%3A%3A' in token:
            # SessionToken 格式 → Cookie 认证
            logger.info("检测到 SessionToken 格式，使用 Cookie 认证")
            return self.get_user_info_by_cookie(token)
        elif token.startswith('eyJ'):
            # AccessToken 格式 → Bearer 认证
            logger.info("检测到 AccessToken 格式，使用 Bearer 认证")
            return self.get_user_info_by_bearer(token)
        else:
            logger.error(f"未知的 Token 格式: {token[:50]}...")
            return None
    
    def get_usage_summary_by_bearer(self, access_token: str) -> Optional[Dict[str, Any]]:
        """使用 Bearer 认证获取使用情况"""
        try:
            url = f"{self.AUTH_URL}/api/usage-summary"
            req = urllib.request.Request(url)
            req.add_header('Authorization', f'Bearer {access_token}')
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            req.add_header('Accept', 'application/json')
            
            logger.debug(f"GET {url} (Bearer)")
            
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    return json.loads(response.read().decode('utf-8'))
                return None
        except Exception as e:
            logger.debug(f"Bearer 获取使用情况失败: {e}")
            return None
    
    def get_usage_summary_by_cookie(self, session_token: str) -> Optional[Dict[str, Any]]:
        """使用 Cookie 认证获取使用情况"""
        try:
            import urllib.parse
            encoded_token = session_token
            if '::' in session_token and '%3A%3A' not in session_token:
                encoded_token = urllib.parse.quote(session_token, safe='')
            
            url = f"{self.AUTH_URL}/api/usage-summary"
            req = urllib.request.Request(url)
            req.add_header('Cookie', f'WorkosCursorSessionToken={encoded_token}')
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            req.add_header('Accept', 'application/json')
            req.add_header('Referer', 'https://www.cursor.com/')
            
            logger.debug(f"GET {url} (Cookie)")
            
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    return json.loads(response.read().decode('utf-8'))
                return None
        except Exception as e:
            logger.debug(f"Cookie 获取使用情况失败: {e}")
            return None
    
    def get_usage_summary(self, token: str) -> Optional[Dict[str, Any]]:
        """智能获取使用情况（自动选择认证方式）"""
        if '::' in token or '%3A%3A' in token:
            return self.get_usage_summary_by_cookie(token)
        elif token.startswith('eyJ'):
            return self.get_usage_summary_by_bearer(token)
        return None
    
    def validate_token(self, access_token: str) -> bool:
        """
        验证 Token 是否有效
        
        Args:
            access_token: 访问令牌
            
        Returns:
            bool: Token 是否有效
        """
        try:
            # 1. 尝试解析 JWT
            payload = jwt.decode(access_token, options={"verify_signature": False})
            
            # 2. 检查类型
            if payload.get('type') != 'session':
                logger.warning(f"Token 类型错误: {payload.get('type')}")
                return False
            
            # 3. 检查过期时间
            exp = payload.get('exp')
            if exp:
                if datetime.now().timestamp() >= exp:
                    logger.warning("Token 已过期")
                    return False
            
            # 4. 调用 API 验证
            user_info = self.get_user_info(access_token)
            return user_info is not None
            
        except Exception as e:
            logger.error(f"验证 Token 失败: {e}")
            return False
    
    def extract_token_from_browser(self, page) -> Optional[Dict[str, Any]]:
        """
        从浏览器页面提取 Token
        
        Args:
            page: DrissionPage 的页面对象
            
        Returns:
            Optional[Dict]: Token 信息
        """
        try:
            # 从 localStorage 读取
            access_token = page.run_js("return localStorage.getItem('cursorAuth/accessToken');")
            refresh_token = page.run_js("return localStorage.getItem('cursorAuth/refreshToken');")
            email = page.run_js("return localStorage.getItem('cursorAuth/cachedEmail');")
            
            if access_token:
                logger.info("成功从浏览器提取 Token")
                return {
                    'accessToken': access_token,
                    'refreshToken': refresh_token or access_token,
                    'email': email or 'unknown@cursor.com'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"从浏览器提取 Token 失败: {e}")
            return None
    
    def get_account_details_by_bearer(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        通过 Bearer 认证获取完整账号详情（学习自 YCursor）
        ⭐ 用于直接使用 AccessToken 添加账号
        
        Args:
            access_token: 纯 AccessToken (type='session')，格式：eyJhbGci...
            
        Returns:
            Optional[Dict]: 完整的账号详情
        """
        try:
            logger.info("使用 Bearer 认证获取账号详情...")
            
            # 并行调用 3 个 API
            user_info = self.get_user_info_by_bearer(access_token)
            if not user_info:
                logger.error("无法获取用户信息（Bearer 认证）")
                return None
            
            usage_info = self.get_usage_summary_by_bearer(access_token)
            stripe_info = self.get_stripe_info_by_bearer(access_token)
            
            # 合并信息
            result = {
                'email': user_info.get('email', 'unknown@cursor.com'),
                'user_id': user_info.get('sub', ''),
                'email_verified': user_info.get('email_verified', False),
                'name': user_info.get('name', ''),
            }
            
            if usage_info:
                result['membership_type'] = usage_info.get('membershipType', 'free')
                individual_usage = usage_info.get('individualUsage', {})
                plan = individual_usage.get('plan', {})
                used = plan.get('used', 0)
                limit = plan.get('limit', 1000)
                result['usage_percent'] = round((used / limit) * 100, 1) if limit > 0 else 0
                result['used'] = used
                result['limit'] = limit
            
            if stripe_info:
                result['days_remaining'] = stripe_info.get('daysRemainingOnTrial', 0)
                result['subscription_status'] = stripe_info.get('subscriptionStatus', '')  # ⭐ 订阅状态
                if 'membershipType' in stripe_info:
                    result['membership_type'] = stripe_info.get('membershipType', result.get('membership_type', 'free'))
            
            # ⭐ 获取真实费用数据和最后使用时间（Bearer认证无法获取，需要构造Cookie格式）
            # 尝试构造临时Cookie格式来获取费用
            try:
                user_id = user_info.get('sub', '').replace('auth0|', '')
                if user_id:
                    temp_cookie_format = f"{user_id}::{access_token}"
                    usage_events = self.get_usage_events(temp_cookie_format)
                    if usage_events:
                        # 传递 membership_type 用于计算欠费
                        membership = result.get('membership_type', 'free')
                        cost_info = self.calculate_total_cost(usage_events, membership)
                        result['total_cost'] = cost_info['total_cost']
                        result['total_tokens'] = cost_info['total_tokens']
                        result['usage_event_count'] = cost_info['event_count']
                        result['unpaid_amount'] = cost_info['unpaid_amount']  # ⭐ 欠费金额
                        result['model_usage'] = cost_info['by_model']  # ⭐ 模型费用详情
                        
                        # ⭐ 提取最后使用时间
                        events = usage_events.get('usageEventsDisplay', [])
                        if events and len(events) > 0:
                            latest_event = events[0]
                            timestamp = latest_event.get('timestamp')  # ⭐ 字段名是 timestamp
                            if timestamp:
                                # 转换时间戳（毫秒）为ISO格式
                                from datetime import datetime
                                timestamp_sec = int(timestamp) / 1000
                                dt = datetime.fromtimestamp(timestamp_sec)
                                result['last_used'] = dt.isoformat()
                                logger.debug(f"✓ 最后使用时间: {result['last_used']}")
                        
                        logger.info(f"✓ 获取费用数据: ${result['total_cost']}, {result['total_tokens']} tokens")
            except Exception as e:
                logger.debug(f"Bearer认证获取费用数据失败: {e}")
            
            logger.info(f"✓ Bearer 认证获取账号详情成功: {result['email']}")
            return result
            
        except Exception as e:
            logger.error(f"Bearer 获取账号详情失败: {e}")
            return None
    
    def get_account_details_by_cookie(self, session_token: str, detailed: bool = True, 
                                     last_refresh_time: str = None, accumulated_cost: float = 0) -> Optional[Dict[str, Any]]:
        """
        通过 Cookie 认证获取账号详情（支持增量刷新）
        ⭐ 用于从数据库读取的账号（已构造成 user_xxx::jwt 格式）
        
        Args:
            session_token: 构造的 SessionToken 格式 (user_xxx::jwt)
            detailed: 是否获取详细使用记录（默认True）
            last_refresh_time: 上次刷新时间（ISO格式），用于增量刷新
            accumulated_cost: 累计历史金额，增量刷新时累加
            
        Returns:
            Optional[Dict]: 完整的账号详情
        """
        try:
            if last_refresh_time:
                logger.info(f"使用增量刷新模式（从 {last_refresh_time} 到现在）...")
            else:
                logger.info("使用完整刷新模式（获取所有记录）...")
            
            # 调用 API 获取用户信息
            user_info = self.get_user_info_by_cookie(session_token)
            if not user_info:
                logger.error("无法获取用户信息（Cookie 认证）")
                return None
            
            usage_info = self.get_usage_summary_by_cookie(session_token)
            stripe_info = self.get_stripe_info_by_cookie(session_token)
            
            # 合并信息
            result = {
                'email': user_info.get('email', 'unknown@cursor.com'),
                'user_id': user_info.get('sub', ''),
                'email_verified': user_info.get('email_verified', False),
                'name': user_info.get('name', ''),
            }
            
            if usage_info:
                result['membership_type'] = usage_info.get('membershipType', 'free')
                individual_usage = usage_info.get('individualUsage', {})
                plan = individual_usage.get('plan', {})
                used = plan.get('used', 0)
                limit = plan.get('limit', 1000)
                result['usage_percent'] = round((used / limit) * 100, 1) if limit > 0 else 0
                result['used'] = used
                result['limit'] = limit
            
            if stripe_info:
                result['days_remaining'] = stripe_info.get('daysRemainingOnTrial', 0)
                result['subscription_status'] = stripe_info.get('subscriptionStatus', '')  # ⭐ 订阅状态
                if 'membershipType' in stripe_info:
                    result['membership_type'] = stripe_info.get('membershipType', result.get('membership_type', 'free'))
            
            # ⭐ 增量刷新：只获取从 last_refresh_time 到现在的记录
            try:
                # 计算查询起始时间
                start_timestamp = None
                if last_refresh_time:
                    from datetime import datetime
                    try:
                        # 解析 ISO 格式时间
                        dt = datetime.fromisoformat(last_refresh_time.replace('Z', '+00:00'))
                        start_timestamp = str(int(dt.timestamp() * 1000))  # 转为毫秒时间戳
                        logger.info(f"从 {last_refresh_time} 开始获取增量记录")
                    except Exception as e:
                        logger.warning(f"解析 last_refresh_time 失败: {e}，将获取全部记录")
                        start_timestamp = None
                
                # 获取使用记录（增量或全量）
                usage_events = self.get_usage_events(
                    session_token, 
                    start_date=start_timestamp  # 从指定时间开始
                )
                
                if usage_events:
                    # 提取记录列表
                    events = usage_events.get('usageEventsDisplay', [])
                    event_count = len(events)
                    
                    # 计算费用
                    membership = result.get('membership_type', 'free')
                    cost_info = self.calculate_total_cost(usage_events, membership)
                    
                    # 计算新增金额
                    new_cost = cost_info['total_cost']
                    
                    # ⭐ 增量模式：累加历史金额
                    if last_refresh_time and accumulated_cost > 0:
                        result['accumulated_cost'] = accumulated_cost + new_cost
                        result['total_cost'] = result['accumulated_cost']  # 显示累计总金额
                        logger.info(f"✓ 增量刷新: 新增 ${new_cost:.2f}, 累计 ${result['accumulated_cost']:.2f} ({event_count} 条新记录)")
                    else:
                        # 完整模式：直接使用计算的金额
                        result['accumulated_cost'] = new_cost
                        result['total_cost'] = new_cost
                        logger.info(f"✓ 完整刷新: 总计 ${new_cost:.2f} ({event_count} 条记录)")
                    
                    result['total_tokens'] = cost_info['total_tokens']
                    result['usage_event_count'] = cost_info['event_count']
                    result['unpaid_amount'] = cost_info['unpaid_amount']
                    result['model_usage'] = cost_info['by_model']
                    
                    # ⭐ 更新最后刷新时间（取最新记录的时间）
                    if events and len(events) > 0:
                        latest_event = events[0]
                        timestamp = latest_event.get('timestamp')
                        if timestamp:
                            from datetime import datetime
                            timestamp_sec = int(timestamp) / 1000
                            dt = datetime.fromtimestamp(timestamp_sec)
                            result['last_used'] = dt.isoformat()
                            result['last_refresh_time'] = dt.isoformat()  # ⭐ 保存用于下次增量刷新
                            logger.debug(f"✓ 最新记录时间: {result['last_refresh_time']}")
                else:
                    # 没有新记录
                    if last_refresh_time and accumulated_cost > 0:
                        # 增量模式且有历史金额：保持原值
                        result['accumulated_cost'] = accumulated_cost
                        result['total_cost'] = accumulated_cost
                        result['last_refresh_time'] = last_refresh_time
                        logger.info(f"✓ 无新增记录，保持累计金额 ${accumulated_cost:.2f}")
                    else:
                        # 完整模式或无历史：设为0
                        result['accumulated_cost'] = 0
                        result['total_cost'] = 0
                        result['total_tokens'] = 0
                        result['usage_event_count'] = 0
                        result['unpaid_amount'] = 0
                        result['model_usage'] = {}
                        logger.info("✓ 暂无使用记录")
            except Exception as e:
                logger.error(f"获取费用数据失败: {e}")
                # 出错时保持原值或设为0
                if last_refresh_time and accumulated_cost > 0:
                    result['accumulated_cost'] = accumulated_cost
                    result['total_cost'] = accumulated_cost
                else:
                    result['accumulated_cost'] = 0
                    result['total_cost'] = 0
                result['total_tokens'] = 0
                result['usage_event_count'] = 0
                result['unpaid_amount'] = 0
                result['model_usage'] = {}
            
            logger.info(f"✓ Cookie 认证获取账号详情成功: {result['email']}")
            return result
            
        except Exception as e:
            logger.error(f"Cookie 获取账号详情失败: {e}")
            return None
    
    def get_account_details(self, token: str, detailed: bool = True, 
                           last_refresh_time: str = None, accumulated_cost: float = 0) -> Optional[Dict[str, Any]]:
        """
        智能获取完整账号详情（自动选择认证方式，支持增量刷新）
        
        Args:
            token: Token（自动识别类型）
                  - AccessToken: eyj... → Bearer 认证
                  - SessionToken: user_xxx::jwt → Cookie 认证
            detailed: 是否获取详细使用记录（默认True）
            last_refresh_time: 上次刷新时间（用于增量刷新）
            accumulated_cost: 累计历史金额（用于增量刷新）
            
        Returns:
            Optional[Dict]: 账号详情
        """
        if '::' in token or '%3A%3A' in token:
            # 构造的 SessionToken 格式 → Cookie 认证
            return self.get_account_details_by_cookie(
                token, 
                detailed=detailed,
                last_refresh_time=last_refresh_time,
                accumulated_cost=accumulated_cost
            )
        elif token.startswith('eyJ'):
            # 纯 AccessToken → Bearer 认证（不支持增量刷新）
            return self.get_account_details_by_bearer(token)
        else:
            logger.error(f"未知的 Token 格式")
            return None
    
    def verify_token_with_api(self, access_token: str) -> bool:
        """
        通过 API 验证 Token 是否有效
        
        Args:
            access_token: 访问令牌
            
        Returns:
            bool: Token 是否有效
        """
        user_info = self.get_user_info(access_token)
        return user_info is not None
    
    def get_stripe_info_by_bearer(self, access_token: str) -> Optional[Dict[str, Any]]:
        """使用 Bearer 认证获取 Stripe 信息"""
        try:
            url = f"{self.AUTH_URL}/api/auth/stripe"
            req = urllib.request.Request(url)
            req.add_header('Authorization', f'Bearer {access_token}')
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            req.add_header('Accept', 'application/json')
            
            logger.debug(f"GET {url} (Bearer)")
            
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    return json.loads(response.read().decode('utf-8'))
                return None
        except Exception as e:
            logger.debug(f"Bearer 获取 Stripe 信息失败: {e}")
            return None
    
    def get_stripe_info_by_cookie(self, session_token: str) -> Optional[Dict[str, Any]]:
        """使用 Cookie 认证获取 Stripe 信息"""
        try:
            import urllib.parse
            encoded_token = session_token
            if '::' in session_token and '%3A%3A' not in session_token:
                encoded_token = urllib.parse.quote(session_token, safe='')
            
            url = f"{self.AUTH_URL}/api/auth/stripe"
            req = urllib.request.Request(url)
            req.add_header('Cookie', f'WorkosCursorSessionToken={encoded_token}')
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            req.add_header('Accept', 'application/json')
            req.add_header('Referer', 'https://www.cursor.com/')
            
            logger.debug(f"GET {url} (Cookie)")
            
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    return json.loads(response.read().decode('utf-8'))
                return None
        except Exception as e:
            logger.debug(f"Cookie 获取 Stripe 信息失败: {e}")
            return None
    
    def get_stripe_info(self, token: str) -> Optional[Dict[str, Any]]:
        """智能获取 Stripe 信息（自动选择认证方式）"""
        if '::' in token or '%3A%3A' in token:
            return self.get_stripe_info_by_cookie(token)
        elif token.startswith('eyJ'):
            return self.get_stripe_info_by_bearer(token)
        return None
    
    def get_usage_events(self, token: str, start_date: str = None, end_date: str = None, get_all_pages: bool = True) -> Optional[Dict[str, Any]]:
        """
        获取详细的使用记录和费用信息（支持多页获取）
        
        API: POST https://cursor.com/api/dashboard/get-filtered-usage-events
        
        Args:
            token: SessionToken (user_xxx::eyJ...)
            start_date: 开始日期（时间戳毫秒）
            end_date: 结束日期（时间戳毫秒）
            get_all_pages: 是否获取所有页（默认True）
            
        Returns:
            Optional[Dict]: 使用记录，包含每次调用的实际费用
        """
        try:
            from datetime import datetime, timedelta
            import urllib.parse
            
            # ⭐ 默认查询当月数据（从每月1号到现在）
            if not end_date:
                end_timestamp = int(datetime.now().timestamp() * 1000)
            else:
                end_timestamp = int(end_date)
            
            if not start_date:
                # 获取本月1号0点的时间戳
                now = datetime.now()
                start_dt = datetime(now.year, now.month, 1, 0, 0, 0)
                start_timestamp = int(start_dt.timestamp() * 1000)
            else:
                start_timestamp = int(start_date)
            
            # URL编码SessionToken
            if '::' in token and '%3A%3A' not in token:
                encoded_token = urllib.parse.quote(token, safe='')
            else:
                encoded_token = token
            
            url = f"{self.AUTH_URL}/api/dashboard/get-filtered-usage-events"
            
            # ⭐ 获取所有页的数据
            all_events = []
            page = 1
            page_size = 100
            total_count = 0
            
            while True:
                # 构造POST数据
                post_data = {
                    "teamId": 0,
                    "startDate": str(start_timestamp),
                    "endDate": str(end_timestamp),
                    "page": page,
                    "pageSize": page_size
                }
                
                # 构造请求
                req = urllib.request.Request(url, method='POST')
                req.add_header('Cookie', f'WorkosCursorSessionToken={encoded_token}')
                req.add_header('Content-Type', 'application/json')
                req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                req.add_header('Accept', '*/*')
                req.add_header('Referer', 'https://cursor.com/cn/dashboard?tab=usage')
                req.add_header('Origin', 'https://cursor.com')
                
                # 发送请求
                post_bytes = json.dumps(post_data).encode('utf-8')
                
                logger.debug(f"POST {url} (Page {page})")
                
                with urllib.request.urlopen(req, data=post_bytes, timeout=self.timeout) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode('utf-8'))
                        total_count = data.get('totalUsageEventsCount', 0)
                        current_events = data.get('usageEventsDisplay', [])
                        
                        all_events.extend(current_events)
                        
                        logger.debug(f"✓ 第{page}页: {len(current_events)}条记录")
                        
                        # 如果不获取所有页，或者已经获取完所有数据
                        if not get_all_pages or len(current_events) < page_size or len(all_events) >= total_count:
                            break
                        
                        page += 1
                    else:
                        break
            
            logger.info(f"✓ 获取使用记录成功，共 {total_count} 条（已获取{len(all_events)}条）")
            
            return {
                'totalUsageEventsCount': total_count,
                'usageEventsDisplay': all_events
            }
                
        except Exception as e:
            logger.debug(f"获取使用记录失败: {e}")
            return None
    
    def calculate_total_cost(self, usage_events: Dict[str, Any], membership_type: str = 'free') -> Dict[str, Any]:
        """
        计算总费用和欠费金额
        
        Args:
            usage_events: get_usage_events返回的数据
            membership_type: 套餐类型（用于计算抵扣）
            
        Returns:
            Dict: 费用统计
                - total_cost: 总费用（美元）
                - total_tokens: 总tokens
                - event_count: 事件数量
                - by_model: 按模型分组的费用
                - unpaid_amount: 实际欠费金额 ⭐
        """
        if not usage_events or 'usageEventsDisplay' not in usage_events:
            return {'total_cost': 0, 'total_tokens': 0, 'event_count': 0, 'by_model': {}, 'unpaid_amount': 0}
        
        events = usage_events['usageEventsDisplay']
        total_cost = 0
        total_tokens = 0
        by_model = {}
        charged_count = 0
        
        for event in events:
            # ⭐ 跳过错误和不计费的事件
            kind = event.get('kind', '')
            if 'NOT_CHARGED' in kind or 'ERRORED' in kind:
                continue
            
            # ⭐ 使用 totalCents（美分转美元）- 这是最准确的
            token_usage = event.get('tokenUsage', {})
            event_cost = token_usage.get('totalCents', 0) / 100
            
            total_cost += event_cost
            charged_count += 1
            
            # 计算tokens
            token_usage = event.get('tokenUsage', {})
            event_tokens = (
                token_usage.get('inputTokens', 0) +
                token_usage.get('outputTokens', 0) +
                token_usage.get('cacheWriteTokens', 0) +
                token_usage.get('cacheReadTokens', 0)
            )
            total_tokens += event_tokens
            
            # 按模型分组
            model = event.get('model', 'unknown')
            if model not in by_model:
                by_model[model] = {'cost': 0, 'tokens': 0, 'count': 0}
            
            by_model[model]['cost'] += event_cost
            by_model[model]['tokens'] += event_tokens
            by_model[model]['count'] += 1
        
        # ⭐ 计算实际欠费金额（总费用 - 套餐抵扣）
        PLAN_CREDIT = {
            'pro': 20,
            'pro_trial': 20,
            'business': 40,
            'team': 40,
            'enterprise': 100,
            'free': 10,          # ⭐ FREE套餐有$10抵扣
            'free_trial': 10     # ⭐ FREE试用也是$10
        }
        
        plan_credit = PLAN_CREDIT.get(membership_type.lower(), 0)
        unpaid_amount = max(0, total_cost - plan_credit)
        
        return {
            'total_cost': round(total_cost, 2),
            'total_tokens': total_tokens,
            'event_count': len(events),
            'charged_count': charged_count,  # 实际计费的事件数
            'by_model': by_model,
            'unpaid_amount': round(unpaid_amount, 2)  # ⭐ 实际欠费
        }


# 全局 API 客户端实例
_api_client = None


def get_api_client() -> CursorOfficialAPI:
    """
    获取全局 API 客户端实例（单例）
    
    Returns:
        CursorOfficialAPI: API 客户端实例
    """
    global _api_client
    if _api_client is None:
        _api_client = CursorOfficialAPI()
    return _api_client


