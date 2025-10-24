#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
美国地址生成器
随机生成真实的美国地址信息
"""

import random


# 美国常见姓名
US_FIRST_NAMES = [
    "James", "John", "Robert", "Michael", "William",
    "David", "Richard", "Joseph", "Thomas", "Charles",
    "Mary", "Patricia", "Jennifer", "Linda", "Barbara",
    "Elizabeth", "Susan", "Jessica", "Sarah", "Karen",
    "Nancy", "Lisa", "Betty", "Margaret", "Sandra",
    "Ashley", "Kimberly", "Emily", "Donna", "Michelle"
]

US_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones",
    "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
    "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris",
    "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson"
]


# 美国地址数据库（覆盖主要州）
US_ADDRESSES = [
    # New York
    {"street": "123 Broadway", "city": "New York", "state": "NY", "zip": "10001"},
    {"street": "456 5th Avenue", "city": "New York", "state": "NY", "zip": "10018"},
    {"street": "789 Madison Ave", "city": "New York", "state": "NY", "zip": "10065"},
    {"street": "321 Park Ave", "city": "New York", "state": "NY", "zip": "10022"},
    {"street": "654 Wall Street", "city": "New York", "state": "NY", "zip": "10005"},
    
    # California
    {"street": "100 Market St", "city": "San Francisco", "state": "CA", "zip": "94102"},
    {"street": "200 Sunset Blvd", "city": "Los Angeles", "state": "CA", "zip": "90028"},
    {"street": "300 Hollywood Blvd", "city": "Los Angeles", "state": "CA", "zip": "90028"},
    {"street": "400 Vine St", "city": "Los Angeles", "state": "CA", "zip": "90038"},
    {"street": "500 Wilshire Blvd", "city": "Los Angeles", "state": "CA", "zip": "90017"},
    {"street": "600 University Ave", "city": "Palo Alto", "state": "CA", "zip": "94301"},
    {"street": "700 El Camino Real", "city": "San Mateo", "state": "CA", "zip": "94402"},
    
    # Texas
    {"street": "111 Main St", "city": "Houston", "state": "TX", "zip": "77002"},
    {"street": "222 Commerce St", "city": "Dallas", "state": "TX", "zip": "75201"},
    {"street": "333 Congress Ave", "city": "Austin", "state": "TX", "zip": "78701"},
    {"street": "444 Houston St", "city": "San Antonio", "state": "TX", "zip": "78205"},
    
    # Florida
    {"street": "150 Ocean Drive", "city": "Miami Beach", "state": "FL", "zip": "33139"},
    {"street": "250 Brickell Ave", "city": "Miami", "state": "FL", "zip": "33131"},
    {"street": "350 Orange Ave", "city": "Orlando", "state": "FL", "zip": "32801"},
    {"street": "450 Bay St", "city": "Jacksonville", "state": "FL", "zip": "32202"},
    
    # Illinois
    {"street": "888 Michigan Ave", "city": "Chicago", "state": "IL", "zip": "60611"},
    {"street": "999 State St", "city": "Chicago", "state": "IL", "zip": "60605"},
    {"street": "777 Wacker Dr", "city": "Chicago", "state": "IL", "zip": "60606"},
    
    # Washington
    {"street": "1000 1st Ave", "city": "Seattle", "state": "WA", "zip": "98104"},
    {"street": "1100 Pike St", "city": "Seattle", "state": "WA", "zip": "98101"},
    
    # Massachusetts
    {"street": "200 Boylston St", "city": "Boston", "state": "MA", "zip": "02116"},
    {"street": "300 Newbury St", "city": "Boston", "state": "MA", "zip": "02115"},
    
    # Pennsylvania
    {"street": "400 Market St", "city": "Philadelphia", "state": "PA", "zip": "19106"},
    {"street": "500 Walnut St", "city": "Philadelphia", "state": "PA", "zip": "19106"},
    
    # Georgia
    {"street": "600 Peachtree St", "city": "Atlanta", "state": "GA", "zip": "30308"},
    {"street": "700 Spring St", "city": "Atlanta", "state": "GA", "zip": "30308"},
    
    # Arizona
    {"street": "800 Central Ave", "city": "Phoenix", "state": "AZ", "zip": "85004"},
    {"street": "900 Jefferson St", "city": "Phoenix", "state": "AZ", "zip": "85003"},
    
    # Colorado
    {"street": "1200 17th St", "city": "Denver", "state": "CO", "zip": "80202"},
    {"street": "1300 Broadway", "city": "Denver", "state": "CO", "zip": "80203"},
    
    # Oregon
    {"street": "1400 SW 5th Ave", "city": "Portland", "state": "OR", "zip": "97201"},
    
    # Nevada
    {"street": "1500 Las Vegas Blvd", "city": "Las Vegas", "state": "NV", "zip": "89109"},
    
    # Virginia
    {"street": "1600 Wilson Blvd", "city": "Arlington", "state": "VA", "zip": "22209"},
    
    # North Carolina
    {"street": "1700 Trade St", "city": "Charlotte", "state": "NC", "zip": "28202"},
    
    # Ohio
    {"street": "1800 Euclid Ave", "city": "Cleveland", "state": "OH", "zip": "44115"},
    
    # Michigan
    {"street": "1900 Woodward Ave", "city": "Detroit", "state": "MI", "zip": "48226"},
]


def generate_random_name() -> str:
    """
    生成随机美国姓名
    
    Returns:
        str: 完整姓名（First Last）
    """
    first_name = random.choice(US_FIRST_NAMES)
    last_name = random.choice(US_LAST_NAMES)
    return f"{first_name} {last_name}"


def generate_random_address() -> dict:
    """
    生成随机美国地址
    
    Returns:
        dict: 包含 street, city, state, zip 的字典
    """
    address = random.choice(US_ADDRESSES)
    return address.copy()


def generate_full_address_info() -> dict:
    """
    生成完整的美国地址信息（姓名+地址）
    
    Returns:
        dict: 包含 name, street, city, state, zip 的字典
    """
    name = generate_random_name()
    address = generate_random_address()
    
    return {
        "name": name,
        "street": address["street"],
        "city": address["city"],
        "state": address["state"],
        "zip": address["zip"],
        "country": "US"
    }


def get_address_count() -> int:
    """
    获取地址库中的地址数量
    
    Returns:
        int: 地址数量
    """
    return len(US_ADDRESSES)

