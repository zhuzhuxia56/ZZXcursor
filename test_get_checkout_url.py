#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：通过 SessionToken 获取 Stripe 绑卡页面 URL
"""

import requests
import urllib.parse


def get_checkout_url_from_session_token(session_token: str, tier: str = "pro") -> dict:
    """
    通过 SessionToken 获取 Stripe 绑卡页面 URL
    
    Args:
        session_token: SessionToken（格式：user_xxx::eyJhbGci...）
        tier: 订阅等级（pro/business/hobby）
    
    Returns:
        dict: {'success': bool, 'url': str, 'error': str}
    """
    print("="*80)
    print("📡 开始获取 Stripe 绑卡页面 URL")
    print("="*80)
    print(f"SessionToken: {session_token[:50]}...")
    print(f"Tier: {tier}")
    print()
    
    # URL 编码 SessionToken（如果包含 ::）
    encoded_token = session_token
    if '::' in session_token and '%3A%3A' not in session_token:
        encoded_token = urllib.parse.quote(session_token, safe='')
        print(f"✅ SessionToken 已进行 URL 编码")
    
    # API 地址
    api_url = "https://cursor.com/api/checkout"
    
    # 请求头
    headers = {
        "Accept": "application/json, */*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Content-Type": "application/json",
        "Origin": "https://cursor.com",
        "Referer": "https://cursor.com/settings",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "Cookie": f"WorkosCursorSessionToken={encoded_token}",  # 使用 Cookie 认证
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }
    
    # 请求数据
    data = {
        "allowAutomaticPayment": True,
        "allowTrial": True,
        "tier": tier
    }
    
    try:
        print(f"📤 发送请求到: {api_url}")
        print(f"📦 请求数据: {data}")
        print()
        
        # 发送 POST 请求
        response = requests.post(
            api_url,
            json=data,
            headers=headers,
            timeout=15
        )
        
        print(f"📥 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            checkout_url = response.text.strip()
            
            print()
            print("✅ 成功获取绑卡页面 URL!")
            print("="*80)
            print(f"🔗 URL: {checkout_url}")
            print("="*80)
            print()
            
            # 验证 URL 格式
            if "checkout.stripe.com" in checkout_url:
                print("✅ URL 验证通过（Stripe 支付页面）")
                return {
                    'success': True,
                    'url': checkout_url,
                    'tier': tier,
                    'error': None
                }
            else:
                print(f"⚠️ URL 格式异常: {checkout_url}")
                return {
                    'success': False,
                    'url': checkout_url,
                    'tier': tier,
                    'error': 'URL 格式不是 Stripe'
                }
        
        elif response.status_code == 401:
            print("❌ 认证失败（401）")
            print("💡 可能原因：SessionToken 无效或已过期")
            return {
                'success': False,
                'url': None,
                'error': '认证失败 - SessionToken 无效或已过期'
            }
        
        elif response.status_code == 400:
            print(f"❌ 请求错误（400）")
            print(f"💡 可能原因：tier 参数不正确或账号不支持该 tier")
            try:
                error_text = response.text
                print(f"📄 错误详情: {error_text[:200]}")
            except:
                pass
            return {
                'success': False,
                'url': None,
                'error': f'请求错误 - tier={tier} 不支持'
            }
        
        else:
            print(f"❌ 请求失败: HTTP {response.status_code}")
            try:
                error_text = response.text
                print(f"📄 响应内容: {error_text[:200]}")
            except:
                pass
            return {
                'success': False,
                'url': None,
                'error': f'HTTP {response.status_code}'
            }
    
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return {
            'success': False,
            'url': None,
            'error': str(e)
        }


def test_all_tiers(session_token: str):
    """测试所有可能的 tier 参数"""
    print("\n" + "="*80)
    print("🔍 测试所有可能的 tier 参数")
    print("="*80)
    print()
    
    tiers = ["pro", "business", "hobby"]
    
    for tier in tiers:
        print(f"\n{'='*80}")
        print(f"测试 tier: {tier}")
        print(f"{'='*80}")
        
        result = get_checkout_url_from_session_token(session_token, tier)
        
        if result['success']:
            print(f"\n🎉 找到可用的 tier: {tier}")
            print(f"🔗 绑卡页面 URL:")
            print(f"{result['url']}")
            return result
        
        print()
    
    print("\n❌ 所有 tier 参数均失败")
    return None


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║       🧪 Cursor 绑卡页面 URL 获取测试脚本                                  ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
    """)
    
    # 输入 SessionToken
    print("请输入 SessionToken（格式：user_xxx::eyJhbGci...）")
    print("提示：可以从软件的账号详情中复制")
    print()
    
    session_token = input("SessionToken: ").strip()
    
    if not session_token:
        print("❌ SessionToken 不能为空")
        exit(1)
    
    # 验证格式
    if '::' not in session_token:
        print("⚠️ SessionToken 格式可能不正确（应包含 '::'）")
        print("继续尝试...")
    
    print()
    print("="*80)
    print("开始测试...")
    print("="*80)
    print()
    
    # 测试单个 tier
    print("选择要测试的 tier:")
    print("1. pro（推荐）")
    print("2. business")
    print("3. hobby")
    print("4. 测试所有（依次尝试）")
    print()
    
    choice = input("请选择 (1-4): ").strip()
    
    if choice == "1":
        result = get_checkout_url_from_session_token(session_token, "pro")
    elif choice == "2":
        result = get_checkout_url_from_session_token(session_token, "business")
    elif choice == "3":
        result = get_checkout_url_from_session_token(session_token, "hobby")
    else:
        result = test_all_tiers(session_token)
    
    print()
    print("="*80)
    print("测试完成")
    print("="*80)
    
    if result and result.get('success'):
        print()
        print("✅ 成功！您可以复制以下 URL 在浏览器中打开：")
        print()
        print(result['url'])
        print()
        print("💡 提示：这个 URL 是临时的，通常几分钟后会过期")
    else:
        print()
        print("❌ 获取失败")
        if result and result.get('error'):
            print(f"错误信息: {result['error']}")
        print()
        print("💡 可能的原因：")
        print("  1. SessionToken 无效或已过期")
        print("  2. 账号已有付费订阅")
        print("  3. 网络连接问题")
    
    print()
    input("按 Enter 键退出...")

