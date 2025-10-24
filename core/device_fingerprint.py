#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设备指纹识别模块
生成唯一的设备ID，用于授权验证
"""

import hashlib
import platform
import socket
import uuid
from typing import Optional

from utils.logger import get_logger

logger = get_logger("device_fingerprint")


class DeviceFingerprint:
    """设备指纹识别器"""
    
    def __init__(self):
        self._device_id = None
        self._device_info = {}
    
    def get_device_id(self) -> str:
        """
        获取设备唯一ID（多重指纹组合）
        
        Returns:
            str: 设备唯一ID（SHA256哈希）
        """
        if self._device_id:
            return self._device_id
        
        try:
            # 收集设备信息
            fingerprint_data = []
            
            # 1. MAC地址（最稳定的硬件标识）
            mac = self._get_mac_address()
            if mac:
                fingerprint_data.append(f"mac:{mac}")
                self._device_info['mac'] = mac
            
            # 2. 机器码（Windows: MachineGuid, Linux: machine-id）
            machine_id = self._get_machine_id()
            if machine_id:
                fingerprint_data.append(f"machine:{machine_id}")
                self._device_info['machine_id'] = machine_id
            
            # 3. CPU信息
            cpu_info = self._get_cpu_info()
            if cpu_info:
                fingerprint_data.append(f"cpu:{cpu_info}")
                self._device_info['cpu'] = cpu_info
            
            # 4. 主机名
            hostname = socket.gethostname()
            fingerprint_data.append(f"host:{hostname}")
            self._device_info['hostname'] = hostname
            
            # 5. 系统信息
            system = platform.system()
            fingerprint_data.append(f"os:{system}")
            self._device_info['system'] = system
            
            # 组合所有信息并生成SHA256哈希
            combined = "|".join(fingerprint_data)
            self._device_id = hashlib.sha256(combined.encode()).hexdigest()
            
            logger.info(f"✅ 设备ID已生成: {self._device_id[:16]}...")
            logger.debug(f"设备信息: {self._device_info}")
            
            return self._device_id
            
        except Exception as e:
            logger.error(f"生成设备ID失败: {e}")
            # 降级方案：使用UUID
            fallback_id = str(uuid.uuid4())
            self._device_id = hashlib.sha256(fallback_id.encode()).hexdigest()
            return self._device_id
    
    def _get_mac_address(self) -> Optional[str]:
        """获取MAC地址"""
        try:
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff)
                           for elements in range(0, 2*6, 2)][::-1])
            return mac
        except:
            return None
    
    def _get_machine_id(self) -> Optional[str]:
        """获取机器码"""
        try:
            system = platform.system()
            
            if system == "Windows":
                # Windows: 读取MachineGuid
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Microsoft\Cryptography",
                    0,
                    winreg.KEY_READ | winreg.KEY_WOW64_64KEY
                )
                machine_guid = winreg.QueryValueEx(key, "MachineGuid")[0]
                winreg.CloseKey(key)
                return machine_guid
                
            elif system == "Linux":
                # Linux: 读取machine-id
                try:
                    with open('/etc/machine-id', 'r') as f:
                        return f.read().strip()
                except:
                    with open('/var/lib/dbus/machine-id', 'r') as f:
                        return f.read().strip()
                        
            elif system == "Darwin":  # macOS
                # macOS: 使用IOPlatformUUID
                import subprocess
                result = subprocess.run(
                    ['ioreg', '-rd1', '-c', 'IOPlatformExpertDevice'],
                    capture_output=True,
                    text=True
                )
                for line in result.stdout.split('\n'):
                    if 'IOPlatformUUID' in line:
                        return line.split('"')[3]
            
            return None
            
        except Exception as e:
            logger.debug(f"获取机器码失败: {e}")
            return None
    
    def _get_cpu_info(self) -> Optional[str]:
        """获取CPU信息"""
        try:
            # 使用platform获取处理器信息
            processor = platform.processor()
            if processor:
                return processor[:50]  # 限制长度
            return None
        except:
            return None
    
    def get_ip_address(self) -> str:
        """获取当前IP地址"""
        try:
            # 方法1：连接外部服务器获取公网IP
            import requests
            response = requests.get('https://api.ipify.org?format=json', timeout=3)
            if response.status_code == 200:
                ip = response.json().get('ip')
                self._device_info['ip'] = ip
                return ip
        except:
            pass
        
        try:
            # 方法2：获取本地IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            self._device_info['ip'] = ip
            return ip
        except:
            return "未知"
    
    def get_device_info(self) -> dict:
        """获取完整设备信息"""
        if not self._device_id:
            self.get_device_id()
        
        return {
            'device_id': self._device_id,
            'ip': self.get_ip_address(),
            'mac': self._device_info.get('mac', '未知'),
            'machine_id': self._device_info.get('machine_id', '未知'),
            'hostname': self._device_info.get('hostname', '未知'),
            'system': self._device_info.get('system', '未知'),
            'cpu': self._device_info.get('cpu', '未知')
        }


# 全局单例
_fingerprint = None

def get_device_fingerprint() -> DeviceFingerprint:
    """获取设备指纹识别器单例"""
    global _fingerprint
    if _fingerprint is None:
        _fingerprint = DeviceFingerprint()
    return _fingerprint

