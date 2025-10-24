#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮箱验证处理器
邮箱验证码获取和处理
"""

import time
import re
import requests
from datetime import datetime, timedelta
from utils.logger import get_logger

logger = get_logger("email_verification")


class EmailVerificationHandler:
    """邮箱验证处理器"""
    
    def __init__(self, account, receiving_email, receiving_pin):
        """
        初始化
        
        Args:
            account: 注册的邮箱账号
            receiving_email: tempmail.plus 接收邮箱（完整邮箱地址）
            receiving_pin: tempmail.plus PIN码
        """
        self.account = account
        self.receiving_email = receiving_email  # ⭐ 保存完整邮箱地址
        self.epin = receiving_pin
        self.session = requests.Session()
    
    def test_connection(self):
        """
        测试邮箱连接是否正常（真实测试：获取并识别邮件内容）
        
        Returns:
            tuple: (是否成功, 提示消息)
        """
        try:
            logger.info("🔄 测试临时邮箱连接...")
            logger.info(f"接收邮箱: {self.receiving_email}")
            logger.info(f"PIN码: {self.epin}")
            
            # 步骤1：尝试获取邮件列表（包含邮件内容）
            url = f"https://tempmail.plus/api/mails?email={self.receiving_email}&limit=5&epin={self.epin}"
            response = self.session.get(url, timeout=10)
            
            logger.info(f"HTTP状态码: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"❌ HTTP 错误: {response.status_code}")
                return False, f"HTTP 错误: {response.status_code}"
            
            data = response.json()
            result = data.get("result")
            error = data.get("error")
            mail_list = data.get("mail_list", [])
            
            logger.info(f"API响应: result={result}, error={error}")
            logger.info(f"邮件数量: {len(mail_list)}")
            
            # ⭐ 检查是否有错误
            if error:
                logger.error(f"❌ API返回错误: {error}")
                return False, f"邮箱或PIN码错误: {error}"
            
            # ⭐ 检查result
            if result is not True:
                logger.error(f"❌ API返回失败: result={result}")
                return False, "邮箱或PIN码错误"
            
            # ⭐ 检查mail_list是否为列表
            if not isinstance(mail_list, list):
                logger.error(f"❌ mail_list格式错误: {type(mail_list)}")
                return False, "API返回格式错误"
            
            # 步骤2：如果有邮件，尝试读取第一封邮件的详细内容（真实测试）
            if len(mail_list) > 0:
                first_mail = mail_list[0]
                mail_id = first_mail.get("mail_id") or first_mail.get("_id")
                
                logger.info(f"✅ 发现 {len(mail_list)} 封邮件，测试读取第一封...")
                
                # 尝试获取邮件详情
                detail_url = f"https://tempmail.plus/api/mails/{mail_id}?email={self.receiving_email}&epin={self.epin}"
                detail_response = self.session.get(detail_url, timeout=10)
                
                if detail_response.status_code == 200:
                    detail_data = detail_response.json()
                    if detail_data.get("result") is True:
                        logger.info("✅ 成功读取邮件内容，邮箱和PIN码验证通过")
                        logger.info(f"   邮件主题: {detail_data.get('subject', 'N/A')}")
                        return True, "邮箱连接正常，PIN码正确"
                    else:
                        logger.error("❌ 无法读取邮件内容，PIN码可能错误")
                        return False, "PIN码错误：无法读取邮件内容"
                else:
                    logger.error(f"❌ 读取邮件失败: HTTP {detail_response.status_code}")
                    return False, "PIN码错误或网络问题"
            else:
                # 没有邮件，但API响应正常（说明邮箱和PIN码基本正确）
                logger.info("✅ API响应正常，暂无邮件")
                logger.info("⚠️ 无法完全验证PIN码（邮箱中无邮件）")
                logger.info("💡 建议：发送一封测试邮件到该邮箱以完全验证")
                return True, "邮箱连接正常（暂无邮件，无法完全验证PIN码）"
                
        except Exception as e:
            logger.error(f"❌ 连接测试失败: {e}")
            return False, f"连接失败: {str(e)}"

    def get_verification_code(self, max_retries=30, retry_interval=1):
        """
        获取验证码，带有重试机制（每秒检查一次）

        Args:
            max_retries: 最大重试次数（默认30次 = 30秒）
            retry_interval: 重试间隔时间（秒，默认1秒）

        Returns:
            验证码 (字符串或 None)
        """
        for attempt in range(max_retries):
            try:
                if attempt == 0:
                    logger.info(f"开始获取验证码（每秒检查，最多30秒）...")
                elif attempt % 10 == 0:
                    logger.info(f"尝试获取验证码 (第 {attempt + 1}/{max_retries} 次)...")

                verify_code, first_id = self._get_latest_mail_code()
                if verify_code is not None and first_id is not None:
                    self._cleanup_mail(first_id)
                    return verify_code

                if attempt < max_retries - 1:
                    time.sleep(retry_interval)

            except Exception as e:
                logger.error(f"获取验证码失败: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_interval)
                else:
                    raise Exception(f"获取验证码失败: {e}") from e

        raise Exception(f"经过 {max_retries} 秒后仍未获取到验证码")

    def _get_latest_mail_code(self):
        """
        获取最新邮件中的验证码（智能过滤发给注册邮箱的邮件）
        
        Returns:
            tuple: (验证码, 邮件ID) 或 (None, None)
        """
        try:
            # 获取邮件列表
            url = f"https://tempmail.plus/api/mails?email={self.receiving_email}&limit=20&epin={self.epin}"
            response = self.session.get(url, timeout=15)
            
            logger.debug(f"📧 请求邮件列表 API: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                logger.debug(f"📧 API 响应: result={data.get('result')}, has_data={bool(data.get('first_id'))}")
                
                if not data.get("result"):
                    logger.debug("❌ API 返回 result=False，没有新邮件")
                    return None, None
                
                # ⭐ 改进：遍历最近的多封邮件，而不只是检查最新的一封
                # 这样可以应对"碰巧收到其他邮件"的情况
                mail_ids = []
                
                # 从API响应中提取邮件ID列表
                # tempmail.plus API 返回的数据结构中包含邮件ID
                first_id = data.get("first_id")
                if first_id:
                    mail_ids.append(first_id)
                
                # 如果API返回了邮件列表，也加入
                mails_data = data.get("mail_list", []) or data.get("mails", [])
                for mail in mails_data[:5]:  # 最多检查5封邮件
                    if isinstance(mail, dict) and (mail.get("id") or mail.get("mail_id")):
                        current_id = mail.get("id") or mail.get("mail_id")
                        if current_id not in mail_ids:
                            mail_ids.append(current_id)
                
                if not mail_ids:
                    logger.debug("📭 邮件列表为空")
                    return None, None
                
                logger.info(f"📬 发现 {len(mail_ids)} 封邮件，开始遍历查找 Cursor 验证码...")
                logger.info(f"🎯 目标收件人: {self.account}")
                logger.info("-" * 60)
                
                # ⭐ 遍历邮件列表，找到第一封 Cursor 发来的邮件
                for idx, mail_id in enumerate(mail_ids):
                    logger.info(f"🔍 检查邮件 {idx + 1}/{len(mail_ids)} (ID: {mail_id})")
                    
                    # 获取邮件详情
                    mail_url = f"https://tempmail.plus/api/mails/{mail_id}?email={self.receiving_email}&epin={self.epin}"
                    mail_response = self.session.get(mail_url, timeout=15)
                    
                    if mail_response.status_code == 200:
                        mail_data = mail_response.json()
                        
                        if mail_data.get("result"):
                            mail_text = mail_data.get("text", "")
                            mail_subject = mail_data.get("subject", "")
                            mail_to = mail_data.get("to", "")
                            mail_from = mail_data.get("from", "")
                            mail_date = mail_data.get("date", "")  # 邮件时间戳
                            
                            logger.info(f"📧 邮件详情:")
                            logger.info(f"  ├─ ID: {mail_id}")
                            logger.info(f"  ├─ 主题: {mail_subject}")
                            logger.info(f"  ├─ 发件人: {mail_from}")
                            logger.info(f"  ├─ 收件人: {mail_to}")
                            logger.info(f"  ├─ 注册邮箱: {self.account}")
                            logger.info(f"  └─ 时间: {mail_date}")
                            
                            # ⭐ 检查邮件时间（如果相差超过2分钟，说明是旧邮件）
                            if mail_date:
                                try:
                                    # 处理不同格式的时间戳
                                    if isinstance(mail_date, str) and mail_date.isdigit():
                                        # 纯数字时间戳（秒）
                                        mail_timestamp = int(mail_date)
                                    elif isinstance(mail_date, (int, float)):
                                        # 数字时间戳
                                        mail_timestamp = int(mail_date)
                                    else:
                                        # 尝试解析时间字符串
                                        from dateutil import parser
                                        parsed_date = parser.parse(mail_date)
                                        mail_timestamp = int(parsed_date.timestamp())
                                    
                                    current_timestamp = int(time.time())
                                    time_diff_seconds = current_timestamp - mail_timestamp
                                    time_diff_minutes = time_diff_seconds / 60
                                    
                                    logger.info(f"⏰ 邮件时间差: {time_diff_minutes:.1f} 分钟前")
                                    
                                    if time_diff_minutes > 2:
                                        logger.warning(f"❌ 邮件时间超过2分钟（{time_diff_minutes:.1f}分钟前），跳过旧邮件")
                                        continue  # 跳过这封邮件，检查下一封
                                    elif time_diff_minutes < 0:
                                        logger.warning(f"❌ 邮件时间异常（来自未来？），跳过")
                                        continue
                                except Exception as e:
                                    logger.warning(f"⚠️ 解析邮件时间失败: {e}")
                                    logger.warning(f"   原始时间: {mail_date}")
                                    logger.warning(f"   继续处理此邮件...")
                            
                            # ⭐ 首先验证收件人是否匹配
                            # 注意：tempmail.plus 可能会显示转发邮箱，我们需要检查邮件内容
                            recipient_match = False
                            
                            # 方法1：直接比较收件人
                            if mail_to.lower() == self.account.lower():
                                recipient_match = True
                                logger.info(f"✅ 收件人直接匹配: {mail_to}")
                            # 方法2：检查邮件内容中是否包含注册邮箱
                            elif self.account.lower() in mail_text.lower():
                                recipient_match = True
                                logger.info(f"✅ 邮件内容中包含注册邮箱: {self.account}")
                            # 方法3：检查主题中是否包含邮箱
                            elif self.account.lower() in mail_subject.lower():
                                recipient_match = True
                                logger.info(f"✅ 邮件主题中包含注册邮箱: {self.account}")
                            
                            if not recipient_match:
                                logger.warning(f"❌ 收件人不匹配！")
                                logger.warning(f"   期望: {self.account}")
                                logger.warning(f"   实际收件人: {mail_to}")
                                logger.warning(f"   跳过此邮件，继续查找...")
                                continue  # 直接跳过，查找下一封
                            
                            # 检查是否是 Cursor 官方邮件
                            is_cursor_email = (
                                'cursor' in mail_from.lower() or
                                'no-reply@cursor' in mail_from.lower() or
                                'noreply@cursor' in mail_from.lower()
                            )
                            
                            if is_cursor_email:
                                logger.info(f"✅ 发现匹配的 Cursor 官方邮件（第 {idx + 1} 封）")
                                logger.info(f"   主题: {mail_subject}")
                                logger.info(f"   发件人: {mail_from}")
                                logger.info(f"   收件人: {mail_to}")
                                logger.info(f"   ✓ 收件人验证通过！")
                                
                                # 提取验证码
                                code = self._extract_code(mail_text)
                                if code:
                                    logger.info(f"✅ 提取到验证码: {code}")
                                    return code, mail_id
                                else:
                                    logger.warning(f"⚠️ 是 Cursor 邮件但未找到验证码，继续检查下一封...")
                                    logger.info(f"📄 邮件内容前200字符: {mail_text[:200]}")
                            else:
                                logger.debug(f"⏭️ 不是 Cursor 邮件（发件人: {mail_from}），检查下一封...")
                        else:
                            logger.debug(f"⏭️ 邮件详情 API 返回 result=False，跳过")
                    else:
                        logger.debug(f"⏭️ 获取邮件详情失败: HTTP {mail_response.status_code}，跳过")
                
                logger.info(f"📭 遍历完 {len(mail_ids)} 封邮件，未找到 Cursor 验证码")
            else:
                logger.error(f"❌ 获取邮件列表失败: HTTP {response.status_code}")
            
            return None, None
            
        except Exception as e:
            logger.error(f"获取邮件失败: {e}")
            return None, None

    def _extract_code(self, text):
        """
        从文本中提取6位验证码
        
        Args:
            text: 邮件文本内容
            
        Returns:
            str: 验证码或 None
        """
        try:
            if not text:
                return None
            
            # 移除邮箱地址（避免域名被误识别）
            if self.account:
                text = text.replace(self.account, '')
            
            # 使用正则表达式提取 6 位数字验证码
            code_match = re.search(r"(?<![a-zA-Z@.])\b\d{6}\b", text)
            
            if code_match:
                return code_match.group()
            
            logger.warning("未找到6位数字验证码")
            return None
            
        except Exception as e:
            logger.error(f"提取验证码失败: {e}")
            return None

    def _cleanup_mail(self, mail_id):
        """
        删除已读邮件
        
        Args:
            mail_id: 邮件ID
        """
        try:
            delete_url = "https://tempmail.plus/api/mails/"
            payload = {
                "email": self.receiving_email,  # 使用完整邮箱地址
                "first_id": mail_id,
                "epin": self.epin,
            }
            
            # 尝试删除
            for attempt in range(3):
                response = self.session.delete(delete_url, data=payload, timeout=10)
                try:
                    result = response.json().get("result")
                    if result is True:
                        logger.info(f"邮件已删除: {mail_id}")
                        return True
                except:
                    pass
                time.sleep(0.5)
            
            logger.warning(f"删除邮件失败: {mail_id}")
            return False
            
        except Exception as e:
            logger.error(f"删除邮件异常: {e}")
            return False

