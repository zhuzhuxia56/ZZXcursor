#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机器码生成器模块
生成和管理 Cursor 的设备指纹信息
"""

import uuid
import hashlib
import json
from typing import Dict, Optional


class MachineIdGenerator:
    """机器码生成器"""
    
    @staticmethod
    def generate_machine_info(platform: str = 'win32', user_id: Optional[str] = None) -> Dict[str, str]:
        """
        生成随机机器码信息
        
        Args:
            platform: 平台类型 (win32/darwin/linux)
            user_id: 用户ID，用于生成 telemetry.machineId
            
        Returns:
            Dict[str, str]: 包含所有机器码字段的字典
        """
        # 生成基础 UUIDs
        mac_machine_id = str(uuid.uuid4())
        dev_device_id = str(uuid.uuid4())
        sqm_id = str(uuid.uuid4()).upper()
        machine_guid = str(uuid.uuid4())
        
        # 生成 telemetry.machineId (特殊格式: auth0|user_xxx...)
        if user_id:
            # 如果提供了 user_id，使用它来生成 machineId
            # 格式: auth0|user_xxx -> hash
            machine_id_base = f"auth0|{user_id}"
        else:
            # 否则生成随机的
            machine_id_base = f"auth0|user_{uuid.uuid4().hex[:16]}"
        
        # 使用 SHA256 生成固定长度的哈希
        machine_id_hash = hashlib.sha256(machine_id_base.encode()).hexdigest()
        machine_id = f"{machine_id_base}{machine_id_hash}"
        
        return {
            "telemetry.machineId": machine_id,
            "telemetry.macMachineId": mac_machine_id,
            "telemetry.devDeviceId": dev_device_id,
            "telemetry.sqmId": f"{{{sqm_id}}}",  # Windows GUID 格式
            "system.machineGuid": machine_guid
        }
    
    @staticmethod
    def parse_machine_info(machine_info_data: any) -> Optional[Dict[str, str]]:
        """
        解析机器码信息
        
        Args:
            machine_info_data: JSON 字符串或字典
            
        Returns:
            Optional[Dict[str, str]]: 机器码字典，如果解析失败返回 None
        """
        try:
            if isinstance(machine_info_data, str):
                data = json.loads(machine_info_data)
            elif isinstance(machine_info_data, dict):
                data = machine_info_data
            else:
                return None
            
            # 验证必需的字段
            required_fields = [
                "telemetry.machineId",
                "telemetry.macMachineId",
                "telemetry.devDeviceId",
                "telemetry.sqmId",
                "system.machineGuid"
            ]
            
            result = {}
            for field in required_fields:
                if field in data:
                    result[field] = data[field]
            
            return result if len(result) == len(required_fields) else None
            
        except (json.JSONDecodeError, TypeError):
            return None
    
    @staticmethod
    def to_json(machine_info: Dict[str, str]) -> str:
        """
        将机器码字典转换为 JSON 字符串
        
        Args:
            machine_info: 机器码字典
            
        Returns:
            str: JSON 字符串
        """
        return json.dumps(machine_info, ensure_ascii=False)
    
    @staticmethod
    def validate_machine_info(machine_info: Dict[str, str]) -> bool:
        """
        验证机器码信息是否完整
        
        Args:
            machine_info: 机器码字典
            
        Returns:
            bool: 是否有效
        """
        required_fields = [
            "telemetry.machineId",
            "telemetry.macMachineId",
            "telemetry.devDeviceId",
            "telemetry.sqmId",
            "system.machineGuid"
        ]
        
        return all(field in machine_info for field in required_fields)
    
    @staticmethod
    def get_machine_id_preview(machine_info: Dict[str, str], max_length: int = 30) -> str:
        """
        获取机器码的预览文本（用于UI显示）
        
        Args:
            machine_info: 机器码字典
            max_length: 最大显示长度
            
        Returns:
            str: 预览文本
        """
        if not machine_info:
            return "无绑定机器码"
        
        mac_id = machine_info.get("telemetry.macMachineId", "")
        if len(mac_id) > max_length:
            return f"{mac_id[:max_length]}..."
        return mac_id


def generate_machine_info(platform: str = 'win32', user_id: Optional[str] = None) -> Dict[str, str]:
    """
    便捷函数：生成机器码
    
    Args:
        platform: 平台类型
        user_id: 用户ID
        
    Returns:
        Dict[str, str]: 机器码字典
    """
    return MachineIdGenerator.generate_machine_info(platform, user_id)


def parse_machine_info(machine_info_data: any) -> Optional[Dict[str, str]]:
    """
    便捷函数：解析机器码
    
    Args:
        machine_info_data: JSON 字符串或字典
        
    Returns:
        Optional[Dict[str, str]]: 机器码字典
    """
    return MachineIdGenerator.parse_machine_info(machine_info_data)

