#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
费用计算模块
基于套餐类型和使用量估算费用
"""

from typing import Dict, Any


# Cursor 套餐价格表（2025年）
SUBSCRIPTION_PRICES = {
    'free': 0,
    'pro': 20,          # $20/月
    'business': 40,     # $40/月
    'team': 40,         # $40/月
    'enterprise': 100,  # 估算
    'pro_trial': 20,    # 试用期按Pro计算
    'free_trial': 0
}


def calculate_cost_info(account: Dict[str, Any]) -> Dict[str, Any]:
    """
    计算账号费用信息
    
    Args:
        account: 账号数据字典
        
    Returns:
        Dict: 费用信息
            - monthly_cost: 月订阅费用
            - used_value: 已消耗价值
            - remaining_value: 剩余价值
            - usage_percent: 使用率
            - price_per_request: 单次请求价值
    """
    # 获取基础数据
    membership = account.get('membership_type', 'free').lower()
    monthly_cost = SUBSCRIPTION_PRICES.get(membership, 0)
    
    usage_percent = account.get('usage_percent', 0)
    used = account.get('used', 0)
    limit = account.get('limit_value', 1000)
    
    # 计算单次请求价值
    price_per_request = monthly_cost / limit if limit > 0 else 0
    
    # 基于使用次数计算（更精确）
    used_value = used * price_per_request
    remaining_value = (limit - used) * price_per_request
    
    return {
        'monthly_cost': monthly_cost,
        'used_value': round(used_value, 2),
        'remaining_value': round(remaining_value, 2),
        'usage_percent': usage_percent,
        'price_per_request': round(price_per_request, 4),
        'used_requests': used,
        'total_requests': limit
    }


def format_cost(cost: float) -> str:
    """
    格式化费用显示
    
    Args:
        cost: 费用金额
        
    Returns:
        str: 格式化的费用字符串
    """
    if cost == 0:
        return "$0"
    elif cost < 0.01:
        return "$0.01"
    else:
        return f"${cost:.2f}"


def get_cost_color(used_value: float, monthly_cost: float) -> str:
    """
    根据消耗比例返回颜色代码
    
    Args:
        used_value: 已消耗价值
        monthly_cost: 月费
        
    Returns:
        str: 颜色代码
    """
    if monthly_cost == 0:
        return "#808080"  # 灰色（Free）
    
    ratio = used_value / monthly_cost if monthly_cost > 0 else 0
    
    if ratio >= 0.9:
        return "#e81123"  # 红色（>=90%）
    elif ratio >= 0.7:
        return "#ffa500"  # 橙色（>=70%）
    else:
        return "#107c10"  # 绿色（<70%）





