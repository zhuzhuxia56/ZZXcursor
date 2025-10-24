#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
国家代码库
ISO 3166-1 alpha-2 标准（2字母国家代码）
"""

# 国家代码映射表（ISO代码 -> 中文名称）
COUNTRY_CODES = {
    # 常用国家
    "US": "美国",
    "CN": "中国",
    "GB": "英国",
    "CA": "加拿大",
    "JP": "日本",
    "DE": "德国",
    "FR": "法国",
    "AU": "澳大利亚",
    "SG": "新加坡",
    "KR": "韩国",
    
    # 亚洲
    "HK": "中国香港",
    "MO": "中国澳门",
    "TW": "台湾",
    "IN": "印度",
    "ID": "印度尼西亚",
    "TH": "泰国",
    "VN": "越南",
    "MY": "马来西亚",
    "PH": "菲律宾",
    "BD": "孟加拉国",
    "PK": "巴基斯坦",
    "MM": "缅甸",
    "KH": "柬埔寨",
    "LA": "老挝",
    "NP": "尼泊尔",
    "LK": "斯里兰卡",
    "BN": "文莱",
    "MN": "蒙古",
    "KZ": "哈萨克斯坦",
    
    # 欧洲
    "IT": "意大利",
    "ES": "西班牙",
    "NL": "荷兰",
    "CH": "瑞士",
    "SE": "瑞典",
    "NO": "挪威",
    "DK": "丹麦",
    "FI": "芬兰",
    "PL": "波兰",
    "BE": "比利时",
    "AT": "奥地利",
    "IE": "爱尔兰",
    "PT": "葡萄牙",
    "GR": "希腊",
    "CZ": "捷克",
    "HU": "匈牙利",
    "RO": "罗马尼亚",
    "BG": "保加利亚",
    "HR": "克罗地亚",
    "SK": "斯洛伐克",
    "SI": "斯洛文尼亚",
    "LT": "立陶宛",
    "LV": "拉脱维亚",
    "EE": "爱沙尼亚",
    "IS": "冰岛",
    "LU": "卢森堡",
    "MT": "马耳他",
    "CY": "塞浦路斯",
    "RU": "俄罗斯",
    "UA": "乌克兰",
    "BY": "白俄罗斯",
    "MD": "摩尔多瓦",
    "GE": "格鲁吉亚",
    "AM": "亚美尼亚",
    "AZ": "阿塞拜疆",
    
    # 美洲
    "MX": "墨西哥",
    "BR": "巴西",
    "AR": "阿根廷",
    "CL": "智利",
    "CO": "哥伦比亚",
    "PE": "秘鲁",
    "VE": "委内瑞拉",
    "EC": "厄瓜多尔",
    "CR": "哥斯达黎加",
    "PA": "巴拿马",
    "UY": "乌拉圭",
    "PY": "巴拉圭",
    "BO": "玻利维亚",
    "CU": "古巴",
    "DO": "多米尼加",
    "GT": "危地马拉",
    "HN": "洪都拉斯",
    "SV": "萨尔瓦多",
    "NI": "尼加拉瓜",
    "JM": "牙买加",
    "TT": "特立尼达和多巴哥",
    
    # 非洲
    "ZA": "南非",
    "EG": "埃及",
    "NG": "尼日利亚",
    "KE": "肯尼亚",
    "GH": "加纳",
    "ET": "埃塞俄比亚",
    "TZ": "坦桑尼亚",
    "UG": "乌干达",
    "DZ": "阿尔及利亚",
    "MA": "摩洛哥",
    "AO": "安哥拉",
    "SD": "苏丹",
    "CI": "科特迪瓦",
    "CM": "喀麦隆",
    "SN": "塞内加尔",
    "ZW": "津巴布韦",
    
    # 大洋洲
    "NZ": "新西兰",
    "FJ": "斐济",
    "PG": "巴布亚新几内亚",
    
    # 中东
    "AE": "阿联酋",
    "SA": "沙特阿拉伯",
    "IL": "以色列",
    "TR": "土耳其",
    "IQ": "伊拉克",
    "IR": "伊朗",
    "JO": "约旦",
    "LB": "黎巴嫩",
    "KW": "科威特",
    "QA": "卡塔尔",
    "BH": "巴林",
    "OM": "阿曼",
    "YE": "也门",
}


def get_country_name(country_code: str) -> str:
    """
    根据国家代码获取中文名称
    
    Args:
        country_code: ISO 3166-1 alpha-2 代码（如 US, CN, GB）
        
    Returns:
        str: 中文国家名称，如果未找到返回代码本身
    """
    return COUNTRY_CODES.get(country_code.upper(), country_code)


def is_valid_country_code(country_code: str) -> bool:
    """
    验证国家代码是否有效
    
    Args:
        country_code: 国家代码
        
    Returns:
        bool: 是否是有效的国家代码
    """
    return country_code.upper() in COUNTRY_CODES


def get_all_country_codes() -> dict:
    """
    获取所有国家代码
    
    Returns:
        dict: 完整的国家代码字典
    """
    return COUNTRY_CODES.copy()


def get_common_countries() -> list:
    """
    获取常用国家列表
    
    Returns:
        list: [(代码, 名称), ...] 的列表
    """
    common = ["US", "CN", "GB", "CA", "JP", "DE", "FR", "AU", "SG", "KR"]
    return [(code, COUNTRY_CODES[code]) for code in common]

