#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
绑卡支付处理模块
Stripe 支付流程自动化
"""

import time
import random
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import get_logger
from utils.app_paths import get_config_file
from .country_codes import get_country_name, is_valid_country_code
from .us_address_generator import generate_random_name, generate_random_address

logger = get_logger("payment_handler")


class VirtualCardGenerator:
    """虚拟卡信息生成器"""
    
    def __init__(self, bin_prefix=None):
        """
        初始化生成器
        
        Args:
            bin_prefix: BIN前缀，None 则从配置读取，默认5224900
        """
        if bin_prefix is None:
            # 从配置文件读取
            try:
                import json
                config_file = get_config_file()  # ⭐ 使用用户目录配置文件
                if config_file.exists():
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    bin_prefix = config.get('payment_binding', {}).get('card_bin_prefix', '5224900')
                else:
                    bin_prefix = '5224900'
            except:
                bin_prefix = '5224900'
        
        self.bin_prefix = bin_prefix
        self.current_year = 2025
    
    def luhn_checksum(self, card_number):
        """计算Luhn算法校验位"""
        def digits_of(n):
            return [int(d) for d in str(n)]
        
        digits = digits_of(card_number)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d * 2))
        
        return (10 - (checksum % 10)) % 10
    
    def generate_card_number(self):
        """生成16位符合Luhn算法的信用卡号"""
        prefix_len = len(self.bin_prefix)
        random_digits = ''.join([str(random.randint(0, 9)) for _ in range(15 - prefix_len)])
        card_without_checksum = self.bin_prefix + random_digits
        
        checksum = self.luhn_checksum(card_without_checksum)
        return card_without_checksum + str(checksum)
    
    @staticmethod
    def get_card_from_pool():
        """
        从卡池获取卡号
        
        Returns:
            dict: 卡号信息或 None
        """
        try:
            from .card_pool_manager import get_card_pool_manager
            
            manager = get_card_pool_manager()
            
            if not manager.has_cards():
                logger.warning("卡池为空，无法获取卡号")
                return None
            
            card = manager.get_next_card()
            return card
            
        except Exception as e:
            logger.error(f"从卡池获取卡号失败: {e}")
            return None
    
    @staticmethod
    def generate_us_bank_info():
        """
        生成美国银行账户信息（支持固定信息配置）
        
        Returns:
            dict: 包含银行账户信息
        """
        # 读取配置
        try:
            import json
            config_file = get_config_file()  # ⭐ 使用用户目录配置文件
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                fixed_info = config.get('payment_binding', {}).get('fixed_info', {})
            else:
                fixed_info = {}
        except:
            fixed_info = {}
        
        # 读取卡号模式配置
        try:
            import json
            config_file = get_config_file()  # ⭐ 使用用户目录配置文件
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                card_mode = config.get('payment_binding', {}).get('card_mode', 'auto_generate')
            else:
                card_mode = 'auto_generate'
        except:
            card_mode = 'auto_generate'
        
        # 根据模式获取卡号
        used_card_number = None  # 记录使用的卡号（用于绑卡成功后删除）
        full_card_data = None  # 记录完整的卡片数据（包括month、year、cvv）
        
        if card_mode == 'import':
            # 从卡池获取
            logger.info("使用导入的卡号")
            card_data = VirtualCardGenerator.get_card_from_pool()
            if card_data:
                card_number = card_data['number']
                used_card_number = card_number  # 记录卡号
                full_card_data = card_data  # 记录完整数据
                logger.info(f"  从卡池获取: {card_number}")
                logger.info(f"  有效期: {card_data['month']}/{card_data['year']}")
                logger.info(f"  CVV: {card_data['cvv']}")
            else:
                logger.warning("卡池为空，改用自动生成")
                card_gen = VirtualCardGenerator()
                card_number = card_gen.generate_card_number()
        else:
            # 自动生成
            logger.info("使用自动生成卡号")
            card_gen = VirtualCardGenerator()
            card_number = card_gen.generate_card_number()
            logger.info(f"  生成卡号: {card_number}")
        
        # 检查是否启用固定信息
        use_fixed = fixed_info.get('enabled', False)
        
        if use_fixed:
            # 使用GUI中配置的固定信息
            logger.info("使用固定信息配置")
            
            # 国家代码（默认US）
            country = fixed_info.get('country') or 'US'
            
            # 验证国家代码
            if not is_valid_country_code(country):
                logger.warning(f"⚠️ 无效的国家代码: {country}，改用默认: US")
                country = "US"
            
            # 姓名和地址（必填，留空则随机生成美国信息）
            name = fixed_info.get('name')
            address_line = fixed_info.get('address')
            
            if not name or not address_line:
                # 姓名或地址留空：随机生成美国地址
                logger.info("  姓名或地址留空，随机生成美国地址信息...")
                random_name = generate_random_name()
                random_addr = generate_random_address()
                
                name = name or random_name
                address_line = address_line or random_addr["street"]
                city = fixed_info.get('city') or random_addr["city"]
                state = fixed_info.get('state') or random_addr["state"]
                zip_code = fixed_info.get('zip') or random_addr["zip"]
            else:
                # 姓名和地址都填写了：使用固定值
                city = fixed_info.get('city') or "New York"
                state = fixed_info.get('state') or "NY"
                zip_code = fixed_info.get('zip') or "10001"
            
            phone = f"+1{random.randint(200,999)}{random.randint(200,999)}{random.randint(1000,9999)}"
            
            # 使用国家代码库显示中文名称
            country_name = get_country_name(country)
            logger.info(f"  国家: {country} ({country_name}) {'(固定)' if fixed_info.get('country') else '(默认)'}")
            logger.info(f"  姓名: {name} {'(固定)' if fixed_info.get('name') else '(随机生成)'}")
            logger.info(f"  地址: {address_line} {'(固定)' if fixed_info.get('address') else '(随机生成)'}")
            logger.info(f"  城市: {city} {'(固定)' if fixed_info.get('city') else '(随机生成)'}")
            logger.info(f"  州: {state} {'(固定)' if fixed_info.get('state') else '(随机生成)'}")
            logger.info(f"  邮编: {zip_code} {'(固定)' if fixed_info.get('zip') else '(随机生成)'}")
            
        else:
            # 完全随机生成美国地址
            logger.info("完全随机生成美国地址信息")
            country = "US"
            name = generate_random_name()
            random_addr = generate_random_address()
            address_line = random_addr["street"]
            city = random_addr["city"]
            state = random_addr["state"]
            zip_code = random_addr["zip"]
            phone = f"+1{random.randint(200,999)}{random.randint(200,999)}{random.randint(1000,9999)}"
        
        # 读取可选字段的启用状态（默认都启用）
        enable_city = fixed_info.get('enable_city', True)
        enable_state = fixed_info.get('enable_state', True)
        enable_zip = fixed_info.get('enable_zip', True)
        
        return {
            "routing_number": "121000358",  # 固定路径号码
            "account_number": card_number,
            "confirm_account": card_number,
            "country": country,  # 国家代码（US, CN, GB等）
            "name": name,
            "address": address_line,
            "city": city,
            "state": state,
            "zip": zip_code,
            "phone": phone,
            "_used_card_number": used_card_number,  # 内部使用，记录使用的卡号
            "_card_data": full_card_data,  # 内部使用，记录完整卡片数据
            "_enable_city": enable_city,  # 是否填写城市
            "_enable_state": enable_state,  # 是否填写州
            "_enable_zip": enable_zip  # 是否填写邮编
        }


class PaymentHandler:
    """绑卡支付处理器"""
    
    @staticmethod
    def get_checkout_url_by_api(tab, tier: str = "pro") -> tuple:
        """
        通过 API 获取 Stripe 绑卡页面 URL
        
        Args:
            tab: DrissionPage 的 tab 对象
            tier: 订阅等级（pro/business/hobby）
        
        Returns:
            tuple: (成功与否, URL或错误信息)
        """
        logger.info(f"\n通过 API 获取绑卡页面 URL（tier={tier}）...")
        
        try:
            import urllib.parse
            from .deep_token_getter import DeepTokenGetter
            
            # 1. 从 Cookie 获取 SessionToken
            session_token = DeepTokenGetter.get_session_token_from_cookies(tab)
            if not session_token:
                logger.warning("❌ 未找到 SessionToken，无法使用 API 方式")
                return False, "未找到 SessionToken"
            
            logger.info(f"✅ 获取到 SessionToken: {session_token[:50]}...")
            
            # 2. URL 编码 SessionToken
            encoded_token = session_token
            if '::' in session_token and '%3A%3A' not in session_token:
                encoded_token = urllib.parse.quote(session_token, safe='')
            
            # 3. 调用 API
            api_url = "https://cursor.com/api/checkout"
            
            headers = {
                "Accept": "application/json, */*",
                "Content-Type": "application/json",
                "Origin": "https://cursor.com",
                "Referer": "https://cursor.com/settings",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Cookie": f"WorkosCursorSessionToken={encoded_token}",
            }
            
            data = {
                "allowAutomaticPayment": True,
                "allowTrial": True,
                "tier": tier
            }
            
            logger.info(f"📤 调用 API: {api_url}")
            logger.info(f"📦 请求参数: tier={tier}")
            
            import requests
            response = requests.post(api_url, json=data, headers=headers, timeout=15)
            
            logger.info(f"📥 响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                checkout_url = response.text.strip()
                
                # 去除可能的引号
                checkout_url = checkout_url.strip('"').strip("'")
                
                if "checkout.stripe.com" in checkout_url:
                    logger.info("✅ 成功获取 Stripe 绑卡页面 URL!")
                    logger.info(f"🔗 URL: {checkout_url[:80]}...")
                    return True, checkout_url
                else:
                    logger.warning(f"⚠️ API 返回的 URL 格式异常: {checkout_url}")
                    return False, "URL 格式不正确"
            
            elif response.status_code == 401:
                logger.warning("❌ API 认证失败（401）")
                return False, "SessionToken 无效或已过期"
            
            else:
                logger.warning(f"❌ API 请求失败: HTTP {response.status_code}")
                try:
                    error_text = response.text[:200]
                    logger.warning(f"错误详情: {error_text}")
                except:
                    pass
                return False, f"HTTP {response.status_code}"
        
        except Exception as e:
            logger.error(f"❌ API 调用异常: {e}")
            return False, str(e)
    
    @staticmethod
    def navigate_to_billing(tab) -> bool:
        """
        导航到绑卡页面（Dashboard）
        
        Args:
            tab: DrissionPage 的 tab 对象
            
        Returns:
            bool: 是否成功
        """
        logger.info("\n" + "="*60)
        logger.info("步骤11: 导航到 Dashboard 进行绑卡")
        logger.info("="*60)
        
        try:
            # 导航到 Dashboard 的 Overview 页面（这里有 Free 7-day trial 按钮）
            dashboard_url = "https://cursor.com/cn/dashboard?tab=overview"
            logger.info(f"访问: {dashboard_url}")
            
            tab.get(dashboard_url, timeout=30)
            time.sleep(5)
            
            logger.info(f"当前页面: {tab.url}")
            
            if "dashboard" in tab.url:
                logger.info("✅ 已进入 Dashboard 页面")
                return True
            else:
                logger.warning(f"未进入 Dashboard，当前: {tab.url}")
                return False
                
        except Exception as e:
            logger.error(f"导航到 Dashboard 失败: {e}")
            return False
    
    @staticmethod
    def click_start_trial_button(tab) -> bool:
        """
        获取并访问 Stripe 绑卡页面
        
        优先使用 API 方式获取 URL，失败则尝试点击按钮
        
        Args:
            tab: DrissionPage 的 tab 对象
            
        Returns:
            bool: 是否成功
        """
        logger.info("\n" + "="*60)
        logger.info("获取 Stripe 绑卡页面")
        logger.info("="*60)
        
        # ⭐ 方法1: 通过 API 获取（推荐）
        logger.info("\n🚀 方法1: 尝试通过 API 获取绑卡页面...")
        success, result = PaymentHandler.get_checkout_url_by_api(tab, tier="pro")
        
        if success:
            checkout_url = result
            logger.info(f"✅ API 方式成功！直接访问绑卡页面")
            logger.info(f"🔗 URL: {checkout_url[:80]}...")
            
            # 直接访问 Stripe 绑卡页面
            try:
                tab.get(checkout_url, timeout=30)
                time.sleep(3)
                
                # 验证是否成功到达
                if "stripe.com" in tab.url or "checkout" in tab.url:
                    logger.info("✅ 已成功进入 Stripe 绑卡页面！")
                    return True
                else:
                    logger.warning(f"⚠️ 访问后页面不对，当前: {tab.url}")
                    return False
            except Exception as e:
                logger.error(f"访问绑卡页面失败: {e}")
                return False
        
        # ⭐ 方法2: API 失败，尝试点击按钮（备用方案）
        logger.warning(f"⚠️ API 方式失败: {result}")
        logger.info("\n🔄 方法2: 尝试通过点击按钮...")
        
        trial_button = None
        
        # 查找按钮（timeout=6秒）
        try:
            trial_button = tab.ele("text:Free 7-day trial", timeout=6)
            if trial_button:
                logger.info("✅ 通过文本找到 Trial 按钮")
        except:
            pass
        
        if not trial_button:
            try:
                trial_button = tab.ele("text:Start 7-day Free Trial", timeout=6)
                if trial_button:
                    logger.info("✅ 通过备用文本找到 Trial 按钮")
            except:
                pass
        
        if not trial_button:
            try:
                buttons = tab.eles("tag:button", timeout=6)
                for btn in buttons:
                    btn_text = btn.text.lower()
                    if "trial" in btn_text or "试用" in btn_text:
                        trial_button = btn
                        logger.info(f"✅ 通过模糊匹配找到按钮: {btn.text}")
                        break
            except:
                pass
        
        # 点击按钮
        if trial_button:
            logger.info(f"点击 Trial 按钮: '{trial_button.text}'")
            trial_button.click()
            
            logger.info("等待跳转到 Stripe 支付页面...")
            time.sleep(5)
            
            # 等待跳转到 Stripe（最多15秒）
            for i in range(15):
                if "stripe.com" in tab.url or "checkout" in tab.url:
                    logger.info(f"✅ 已跳转到 Stripe 支付页面！(等待{i+1}秒)")
                    return True
                time.sleep(1)
            
            if "stripe.com" in tab.url or "checkout" in tab.url:
                logger.info("✅ 检测到 Stripe 支付页面")
                return True
            else:
                logger.warning(f"⚠️ 未跳转到支付页面，当前URL: {tab.url}")
                return False
        else:
            logger.warning("❌ 未找到 'Free 7-day trial' 按钮")
            logger.info("💡 可能原因：")
            logger.info("  - 已有付费订阅")
            logger.info("  - 已使用过免费试用")
            logger.info("  - 页面加载未完成")
            return False
    
    @staticmethod
    def fill_stripe_payment(tab, browser) -> bool:
        """
        自动填写银行卡支付信息
        
        流程：
        1. 等待 Stripe 支付页面加载
        2. 选择"银行卡"支付方式
        3. 填写卡号、有效期、CVC
        4. 填写持卡人姓名
        5. 填写账单地址
        6. 点击"开始试用"按钮
        
        Args:
            tab: DrissionPage 的 tab 对象
            browser: 浏览器实例
            
        Returns:
            bool: 是否成功
        """
        try:
            logger.info("\n" + "="*60)
            logger.info("开始银行卡自动填写流程")
            logger.info("="*60)
            
            # 等待 Stripe 页面完全加载
            logger.info("等待 Stripe 支付页面加载...")
            time.sleep(8)
            
            # 生成卡信息
            card_info = VirtualCardGenerator.generate_us_bank_info()
            logger.info(f"\n生成卡信息:")
            logger.info(f"  卡号: {card_info['account_number']}")
            logger.info(f"  持卡人: {card_info['name']}")
            logger.info(f"  地址: {card_info['address']}, {card_info['city']}, {card_info['state']} {card_info['zip']}")
            logger.info(f"  ⭐ 待删除标记: {card_info.get('_used_card_number', 'None')}")
            
            # 步骤1: 选择"银行卡"支付方式
            if not PaymentHandler._select_card_payment(tab):
                return False
            
            # 步骤2: 填写银行卡信息（卡号、有效期、CVC）
            if not PaymentHandler._fill_card_details(tab, card_info):
                return False
            
            # 步骤3: 填写持卡人姓名
            if not PaymentHandler._fill_cardholder_name(tab, card_info['name']):
                return False
            
            # 步骤4: 填写账单地址
            if not PaymentHandler._fill_billing_address(tab, card_info):
                return False
            
            # 步骤5: 点击"开始试用"按钮
            if not PaymentHandler._click_start_trial_submit(tab):
                return False
            
            logger.info("\n" + "="*60)
            logger.info("✅ 银行卡自动填写流程完成")
            logger.info("="*60)
            
            # ⭐ 检查Dashboard是否有支付方式警告
            time.sleep(3)  # 等待页面完全加载
            has_payment_warning = PaymentHandler._check_payment_warning(tab)
            
            # ⭐ 绑卡成功后，立即删除已使用的卡号（无论如何都要删除）
            used_card_number = card_info.get('_used_card_number')
            logger.info(f"\n⭐ 检查删除逻辑: used_card_number = {used_card_number}")
            
            if used_card_number:
                logger.info("\n💾 绑卡流程完成，删除已使用的卡号...")
                try:
                    from .card_pool_manager import get_card_pool_manager
                    manager = get_card_pool_manager()
                    
                    logger.info(f"🔍 尝试删除卡号: {used_card_number}")
                    logger.info(f"🔍 卡池当前卡号数: {manager.get_card_count()} 组")
                    
                    if manager.remove_card_by_number(used_card_number):
                        logger.info(f"✅ 成功删除使用的卡号: {used_card_number}")
                        logger.info(f"✅ 删除后剩余卡号: {manager.get_card_count()} 组")
                    else:
                        logger.warning(f"⚠️ 未能删除卡号: {used_card_number}")
                        logger.warning(f"   可能原因：卡号不在卡池中")
                except Exception as e:
                    logger.error(f"❌ 删除卡号异常: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                logger.warning("⚠️ 未标记待删除卡号（可能使用了自动生成卡号）")
            
            # ⭐ 返回元组：(是否成功, 是否有支付警告)
            return (True, has_payment_warning)
            
        except Exception as e:
            logger.error(f"银行卡填写流程失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def _check_payment_warning(tab) -> bool:
        """
        检查Dashboard是否有支付方式警告
        
        Args:
            tab: DrissionPage 的 tab 对象
            
        Returns:
            bool: True表示有警告（需要保留浏览器），False表示无警告（可关闭）
        """
        try:
            logger.info("\n检查Dashboard支付警告...")
            
            # 等待页面加载
            time.sleep(2)
            
            # 检查页面文本
            page_text = tab.html.lower()
            
            # 关键警告文本
            warning_keywords = [
                "payment method is not eligible for a free trial",
                "not eligible for a free trial",
                "payment method is not eligible"
            ]
            
            for keyword in warning_keywords:
                if keyword in page_text:
                    logger.warning(f"⚠️ 发现支付警告：{keyword}")
                    logger.warning("⚠️ 支付方式可能有问题，保留浏览器供用户查看")
                    return True
            
            logger.info("✅ 未发现支付警告，绑卡应该成功")
            return False
            
        except Exception as e:
            logger.error(f"检查支付警告失败: {e}")
            return False  # 出错时当作无警告
    
    @staticmethod
    def _select_card_payment(tab) -> bool:
        """选择'银行卡'支付方式"""
        logger.info("\n步骤1: 选择'银行卡'支付方式...")
        
        card_radio = None
        
        # 等待最多15秒
        for i in range(15):
            try:
                # 方法1: 通过文本查找"银行卡"
                card_radio = tab.ele("text:银行卡", timeout=1)
                if card_radio:
                    logger.info(f"✅ 通过文本找到银行卡选项（等待{i+1}秒）")
                    break
            except:
                pass
            
            try:
                # 方法2: 查找包含"card"的radio按钮
                radios = tab.eles("tag:input@@type=radio", timeout=1)
                for radio in radios:
                    value = radio.attr("value") or ""
                    if "card" in value.lower():
                        card_radio = radio
                        logger.info(f"✅ 通过value找到银行卡选项（等待{i+1}秒）")
                        break
            except:
                pass
            
            if card_radio:
                break
            
            if (i+1) % 5 == 0:
                logger.info(f"等待银行卡选项加载... ({i+1}/15秒)")
            time.sleep(1)
        
        if not card_radio:
            logger.error("❌ 未找到银行卡选项")
            return False
        
        # 点击银行卡选项
        logger.info("点击银行卡...")
        card_radio.click()
        time.sleep(3)
        logger.info("✅ 已选择银行卡支付方式")
        
        return True
    
    @staticmethod
    def _fill_card_details(tab, card_info) -> bool:
        """填写银行卡详情（卡号、有效期、CVC）- 使用精确ID定位"""
        logger.info("\n步骤2: 填写银行卡信息...")
        
        try:
            # 卡号
            card_number = card_info['account_number']
            # 生成有效期（从卡池获取或随机生成）
            import random
            if '_card_data' in card_info and card_info['_card_data']:
                month = card_info['_card_data'].get('month', str(random.randint(1, 12)).zfill(2))
                year = card_info['_card_data'].get('year', '2028')
                cvv = card_info['_card_data'].get('cvv', str(random.randint(100, 999)))
            else:
                month = str(random.randint(1, 12)).zfill(2)
                year = str(random.randint(2025, 2030))
                cvv = str(random.randint(100, 999))
            
            logger.info(f"  卡号: {card_number}")
            logger.info(f"  有效期: {month}/{year}")
            logger.info(f"  CVV: {cvv}")
            
            # 等待表单加载
            time.sleep(3)
            
            # 查找卡号输入框（优先使用ID）
            card_number_input = None
            for i in range(10):
                try:
                    # 方法1: 通过精确ID
                    card_number_input = tab.ele("#cardNumber", timeout=1)
                    if card_number_input:
                        logger.info("✅ 找到卡号输入框（ID）")
                        break
                    
                    # 方法2: 通过name
                    card_number_input = tab.ele("@name=cardNumber", timeout=1)
                    if card_number_input:
                        logger.info("✅ 找到卡号输入框（name）")
                        break
                    
                    # 方法3: 通过placeholder
                    card_number_input = tab.ele("@placeholder=1234 1234 1234 1234", timeout=1)
                    if card_number_input:
                        logger.info("✅ 找到卡号输入框（placeholder）")
                        break
                        
                except:
                    if i % 3 == 0:
                        logger.info(f"等待卡号输入框... ({i+1}/10秒)")
                    time.sleep(1)
            
            if not card_number_input:
                logger.error("❌ 未找到卡号输入框")
                return False
            
            # 填写卡号
            logger.info("填写卡号...")
            card_number_input.input(card_number)
            time.sleep(1)
            
            # 填写有效期（优先使用ID）
            logger.info("填写有效期...")
            expiry_input = tab.ele("#cardExpiry", timeout=3)
            if not expiry_input:
                expiry_input = tab.ele("@name=cardExpiry", timeout=3)
            if not expiry_input:
                expiry_input = tab.ele("@placeholder=月份/年份", timeout=3)
            
            if expiry_input:
                expiry_input.input(f"{month}/{year[-2:]}")
                time.sleep(1)
                logger.info("✅ 有效期已填写")
            else:
                logger.warning("❌ 未找到有效期输入框")
                return False
            
            # 填写CVC（优先使用ID）
            logger.info("填写CVC...")
            cvc_input = tab.ele("#cardCvc", timeout=3)
            if not cvc_input:
                cvc_input = tab.ele("@name=cardCvc", timeout=3)
            if not cvc_input:
                cvc_input = tab.ele("@placeholder=CVC", timeout=3)
            
            if cvc_input:
                cvc_input.input(cvv)
                time.sleep(1)
                logger.info("✅ CVC已填写")
            else:
                logger.warning("❌ 未找到CVC输入框")
                return False
            
            logger.info("✅ 银行卡信息已填写")
            return True
            
        except Exception as e:
            logger.error(f"填写银行卡信息失败: {e}")
            return False
    
    @staticmethod
    def _fill_cardholder_name(tab, name: str) -> bool:
        """填写持卡人姓名 - 使用精确ID定位"""
        logger.info("\n步骤3: 填写持卡人姓名...")
        
        try:
            # 查找姓名输入框（优先使用ID）
            name_input = None
            
            # 方法1: 通过精确ID
            name_input = tab.ele("#billingName", timeout=3)
            if name_input:
                logger.info("✅ 找到姓名输入框（ID）")
            else:
                # 方法2: 通过name属性
                name_input = tab.ele("@name=billingName", timeout=3)
                if name_input:
                    logger.info("✅ 找到姓名输入框（name）")
                else:
                    # 方法3: 通过placeholder
                    name_input = tab.ele("@placeholder=全名", timeout=3)
                    if name_input:
                        logger.info("✅ 找到姓名输入框（placeholder）")
            
            if not name_input:
                logger.warning("未找到持卡人姓名输入框")
                return True  # 非必填，继续
            
            logger.info(f"填写持卡人姓名: {name}")
            name_input.input(name)
            time.sleep(1)
            
            logger.info("✅ 持卡人姓名已填写")
            return True
            
        except Exception as e:
            logger.error(f"填写持卡人姓名失败: {e}")
            return True  # 非必填，继续
    
    @staticmethod
    def _fill_billing_address(tab, card_info) -> bool:
        """填写账单地址 - 使用精确ID定位，支持任意国家"""
        logger.info("\n步骤4: 填写账单地址...")
        
        try:
            # 国家选择（支持任意国家，使用ISO 2字母代码）
            country_code = card_info.get('country', 'US')
            country_name = get_country_name(country_code)
            logger.info(f"选择国家: {country_code} ({country_name})")
            
            # 验证国家代码
            if not is_valid_country_code(country_code):
                logger.warning(f"⚠️ 无效的国家代码: {country_code}，改用默认: US")
                country_code = 'US'
                country_name = '美国'
            
            # 只有在非美国时才需要切换国家（美国是默认值）
            if country_code != 'US':
                try:
                    country_select = tab.ele("#billingCountry", timeout=3)
                    if not country_select:
                        country_select = tab.ele("@name=billingCountry", timeout=3)
                    
                    if country_select:
                        logger.info(f"找到国家选择器，切换到: {country_code} ({country_name})")
                        country_select.select.by_value(country_code)
                        time.sleep(1)
                        logger.info(f"✅ 国家已切换到: {country_name}")
                    else:
                        logger.warning("未找到国家选择器")
                except Exception as e:
                    logger.warning(f"选择国家失败: {e}")
            else:
                logger.info("国家: 美国（默认，无需操作）")
            
            # 地址第1行（必填）- 使用精确ID
            logger.info(f"填写地址第1行: {card_info['address']}")
            address1_input = tab.ele("#billingAddressLine1", timeout=3)
            if not address1_input:
                address1_input = tab.ele("@name=billingAddressLine1", timeout=3)
            if not address1_input:
                address1_input = tab.ele("@placeholder=地址", timeout=3)
            
            if address1_input:
                address1_input.input(card_info['address'])
                time.sleep(0.5)
                logger.info("✅ 地址第1行已填写")
            else:
                logger.error("❌ 未找到地址第1行输入框")
                return False  # 地址第1行是必填项
            
            # 地址第2行 - 完全跳过不填写
            logger.info("地址第2行: 跳过（不填写）")
            
            # 城市 - 根据开关决定是否填写（使用精确ID）
            enable_city = card_info.get('_enable_city', True)
            if enable_city:
                try:
                    city_input = tab.ele("#billingLocality", timeout=2)
                    if not city_input:
                        city_input = tab.ele("@name=billingLocality", timeout=2)
                    if not city_input:
                        city_input = tab.ele("@placeholder=城市", timeout=2)
                    
                    if city_input:
                        logger.info(f"填写城市: {card_info['city']}")
                        city_input.input(card_info['city'])
                        time.sleep(0.5)
                        logger.info("✅ 城市已填写")
                    else:
                        logger.info("城市输入框: 未找到，跳过")
                except Exception as e:
                    logger.debug(f"城市字段跳过: {e}")
            else:
                logger.info("城市: 已禁用，跳过填写")
            
            # 邮编 - 根据开关决定是否填写（使用精确ID）
            enable_zip = card_info.get('_enable_zip', True)
            if enable_zip:
                try:
                    zip_input = tab.ele("#billingPostalCode", timeout=2)
                    if not zip_input:
                        zip_input = tab.ele("@name=billingPostalCode", timeout=2)
                    if not zip_input:
                        zip_input = tab.ele("@placeholder=邮编", timeout=2)
                    
                    if zip_input:
                        logger.info(f"填写邮编: {card_info['zip']}")
                        zip_input.input(card_info['zip'])
                        time.sleep(0.5)
                        logger.info("✅ 邮编已填写")
                    else:
                        logger.info("邮编输入框: 未找到，跳过")
                except Exception as e:
                    logger.debug(f"邮编字段跳过: {e}")
            else:
                logger.info("邮编: 已禁用，跳过填写")
            
            # 州/省 - 根据开关决定是否填写（使用精确ID）
            enable_state = card_info.get('_enable_state', True)
            if enable_state:
                try:
                    state_select = tab.ele("#billingAdministrativeArea", timeout=2)
                    if not state_select:
                        state_select = tab.ele("@name=billingAdministrativeArea", timeout=2)
                    
                    if state_select:
                        logger.info(f"选择州: {card_info['state']}")
                        # 使用value选择（NY, CA, TX等）
                        state_select.select.by_value(card_info['state'])
                        time.sleep(0.5)
                        logger.info("✅ 州已选择")
                    else:
                        logger.info("州选择器: 未找到，跳过")
                except Exception as e:
                    logger.debug(f"州字段跳过: {e}")
            else:
                logger.info("州: 已禁用，跳过填写")
            
            logger.info("✅ 账单地址填写完成")
            return True
            
        except Exception as e:
            logger.error(f"填写账单地址失败: {e}")
            return True  # 非必填字段失败也继续
    
    @staticmethod
    def _click_start_trial_submit(tab) -> bool:
        """点击最终的"开始试用"提交按钮"""
        logger.info("\n" + "="*60)
        logger.info("步骤5: 查找'开始试用'按钮...")
        logger.info("="*60)
        
        start_trial_btn = None
        max_wait_btn = 20
        
        for i in range(max_wait_btn):
            try:
                # 方法1: 通过testid查找
                start_trial_btn = tab.ele("@data-testid=hosted-payment-submit-button", timeout=0.5)
                
                # 方法2: 通过文本查找
                if not start_trial_btn:
                    start_trial_btn = tab.ele("text:开始试用", timeout=0.5)
                if not start_trial_btn:
                    start_trial_btn = tab.ele("text:Start trial", timeout=0.5)
                
                # 方法3: 查找class包含SubmitButton的按钮
                if not start_trial_btn:
                    submit_btns = tab.eles("tag:button", timeout=0.5)
                    for btn in submit_btns:
                        btn_class = btn.attr("class") or ""
                        btn_text = btn.text or ""
                        if "SubmitButton" in btn_class or ("试用" in btn_text and "开始" in btn_text):
                            start_trial_btn = btn
                            break
                
                # 检查按钮是否可点击（不是disabled状态）
                if start_trial_btn:
                    disabled = start_trial_btn.attr("disabled")
                    btn_class = start_trial_btn.attr("class") or ""
                    
                    # 如果按钮是disabled或包含incomplete，继续等待
                    if disabled or "incomplete" in btn_class.lower():
                        if i % 5 == 0:
                            logger.info(f"按钮还在loading状态，等待变为可点击... ({i+1}/{max_wait_btn}秒)")
                        start_trial_btn = None
                    else:
                        logger.info(f"✅ 找到可点击的'开始试用'按钮！（等待{i+1}秒）")
                        break
            except:
                pass
            
            if (i+1) % 5 == 0 and not start_trial_btn:
                logger.info(f"等待'开始试用'按钮变为可点击... ({i+1}/{max_wait_btn}秒)")
            
            time.sleep(1)
        
        if start_trial_btn:
            logger.info("点击'开始试用'按钮...")
            start_trial_btn.click()
            logger.info("✅ 已点击，等待页面自动跳转到 Dashboard...")
            
            # 等待跳转到 Dashboard（最多60秒）
            logger.info("\n等待自动跳转到 Dashboard...")
            for wait_i in range(60):
                try:
                    current_url = tab.url
                    
                    if "dashboard" in current_url and "checkout" not in current_url:
                        logger.info(f"✅ 检测到已跳转到 Dashboard！(等待{wait_i+1}秒)")
                        logger.info(f"   当前页面: {current_url}")
                        return True
                except:
                    pass
                
                if (wait_i+1) % 10 == 0:
                    logger.info(f"⏳ 等待自动跳转... ({wait_i+1}/60秒)")
                
                time.sleep(1)
            
            logger.warning("⚠️ 60秒后未检测到跳转，但已提交")
            return True
        else:
            logger.error("❌ 未找到'开始试用'按钮")
            return False
