#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Turnstile 处理器
Shadow DOM 访问逻辑
"""

import time
from utils.logger import get_logger

logger = get_logger("turnstile_handler")


def handle_turnstile(tab, max_wait_seconds=60):
    """
    处理Cloudflare Turnstile人机验证
    Turnstile 验证自动处理
    参考: https://blog.csdn.net/youmypig/article/details/147189205
    使用Shadow DOM访问iframe内的checkbox
    
    Args:
        tab: DrissionPage 的 tab 对象
        max_wait_seconds: 最大等待时间（秒）
        
    Returns:
        bool: 是否成功
    """
    logger.info("\n" + "="*60)
    logger.info("⚠️  开始处理Cloudflare Turnstile验证...")
    logger.info("="*60)
    
    start_url = tab.url
    start_time = time.time()
    last_click_time = 0  # 上次点击的时间
    click_count = 0  # 点击次数
    
    while time.time() - start_time < max_wait_seconds:
        try:
            # ⚡ 检查1: Turnstile元素是否已消失？（验证成功的主要标志）
            try:
                turnstile_check = tab.ele("#cf-turnstile", timeout=0.5)
                if not turnstile_check:
                    logger.info(f"✅ Turnstile元素已消失，验证成功！")
                    return True
            except:
                # 元素不存在也是成功
                logger.info(f"✅ Turnstile元素不存在，验证成功！")
                return True
            
            # 检查2: 页面是否已跳转？（验证成功）
            if tab.url != start_url:
                logger.info(f"✅ 验证成功！页面已跳转")
                logger.info(f"   从: {start_url}")
                logger.info(f"   到: {tab.url}")
                return True
            
            # ⚡ 每10秒尝试点击一次（持续重试直到成功）
            current_time = time.time()
            if current_time - last_click_time >= 10 or click_count == 0:
                click_count += 1
                last_click_time = current_time
                logger.info(f"🔄 第 {click_count} 次尝试点击Turnstile验证框...")
                
                try:
                    # 方法1: 标准Shadow DOM访问（参考CSDN文章）
                    # 路径: #cf-turnstile -> div -> shadow_root -> iframe -> body -> input
                    turnstile = tab.ele("#cf-turnstile", timeout=2)
                    if turnstile:
                        logger.info("  ✅ 找到 #cf-turnstile")
                        
                        # 获取第一个子div
                        child_div = turnstile.child()
                        if child_div:
                            logger.info("  ✅ 找到子div")
                            
                            # 进入shadow root
                            shadow = child_div.shadow_root
                            if shadow:
                                logger.info("  ✅ 进入Shadow DOM")
                                
                                # 在shadow root中查找iframe
                                iframe = shadow.ele("tag:iframe", timeout=2)
                                if iframe:
                                    logger.info("  ✅ 找到iframe")
                                    
                                    # ⚡ 尝试多种方式找到并点击验证框
                                    input_clicked = False
                                    
                                    # 方式1: 通过body查找input
                                    try:
                                        body = iframe.ele("tag:body", timeout=2)
                                        if body:
                                            # 使用sr()访问shadow root中的input
                                            input_elem = body.sr("tag:input@type=checkbox", timeout=2)
                                            if input_elem:
                                                logger.info("  ✅ 找到checkbox（方式1），点击...")
                                                input_elem.click()
                                                input_clicked = True
                                    except Exception as e:
                                        logger.debug(f"  方式1失败: {e}")
                                    
                                    # 方式2: 直接在iframe中查找input
                                    if not input_clicked:
                                        try:
                                            input_elem = iframe.ele("tag:input@type=checkbox", timeout=2)
                                            if input_elem:
                                                logger.info("  ✅ 找到checkbox（方式2），点击...")
                                                input_elem.click()
                                                input_clicked = True
                                        except Exception as e:
                                            logger.debug(f"  方式2失败: {e}")
                                    
                                    # 方式3: 点击iframe本身
                                    if not input_clicked:
                                        try:
                                            logger.info("  尝试直接点击iframe...")
                                            iframe.click()
                                            input_clicked = True
                                        except Exception as e:
                                            logger.debug(f"  方式3失败: {e}")
                                    
                                    if input_clicked:
                                        logger.info(f"  ✅ 已点击！等待10秒检查结果...")
                                        
                                        # 等待3秒后立即检查
                                        time.sleep(3)
                                        try:
                                            if not tab.ele("#cf-turnstile", timeout=1):
                                                logger.info("  ✅ 点击后Turnstile已消失！")
                                                return True
                                        except:
                                            logger.info("  ✅ 点击后Turnstile已消失！")
                                            return True
                                        
                                        # 检查URL跳转
                                        if tab.url != start_url:
                                            logger.info("  ✅ 点击后页面已跳转！")
                                            return True
                                    else:
                                        logger.warning("  ⚠️ 未能点击验证框")
                                else:
                                    logger.warning("  ⚠️ Shadow DOM中未找到iframe")
                            else:
                                logger.warning("  ⚠️ 未找到Shadow Root")
                        else:
                            logger.warning("  ⚠️ 未找到子div")
                    else:
                        logger.warning("  ⚠️ 未找到#cf-turnstile元素")
                    
                except Exception as e:
                    logger.debug(f"  点击失败: {e}")
            
            # 显示等待进度（每5秒）
            elapsed = int(time.time() - start_time)
            if elapsed % 5 == 0 and elapsed > 0:
                time_to_next_click = 10 - (current_time - last_click_time)
                if time_to_next_click > 0:
                    logger.info(f"⏳ 等待验证... ({elapsed}/{max_wait_seconds}秒) | {int(time_to_next_click)}秒后重试")
            
            time.sleep(1)  # 每秒检查一次
            
        except Exception as e:
            logger.debug(f"验证检查异常: {e}")
            time.sleep(1)
    
    # ⚡ 超时检查：同时检查URL和Turnstile元素
    try:
        turnstile_exists = tab.ele("#cf-turnstile", timeout=1)
        if not turnstile_exists or tab.url != start_url:
            logger.info(f"✅ 验证完成！最终URL: {tab.url}")
            return True
    except:
        # 元素不存在，验证成功
        logger.info(f"✅ 验证完成！Turnstile已消失")
        return True
    
    # 真正超时了，等待用户手动操作
    logger.warning(f"\n⚠️  自动验证超时（{max_wait_seconds}秒）")
    logger.warning(f"   当前URL: {tab.url}")
    logger.info("\n" + "=" * 60)
    logger.info("💡 等待手动点击验证框...")
    logger.info("=" * 60)
    
    # 继续等待用户手动点击（检查Turnstile消失）
    manual_wait = 30
    for i in range(manual_wait):
        try:
            # 检查Turnstile是否消失
            if not tab.ele("#cf-turnstile", timeout=0.5):
                logger.info(f"✅ 手动验证成功！Turnstile已消失")
                return True
        except:
            logger.info(f"✅ 手动验证成功！Turnstile已消失")
            return True
        
        # 检查URL跳转
        if tab.url != start_url:
            logger.info(f"✅ 手动验证成功！页面已跳转")
            return True
        
        if i % 5 == 0:
            logger.info(f"等待手动操作... ({i}/{manual_wait}秒)")
        time.sleep(1)
    
    logger.error("❌ 验证失败（自动+手动均超时）")
    return False

