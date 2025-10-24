#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机器码管理器
获取并管理设备唯一标识
"""

import sys
import hashlib
import platform
import uuid
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import get_logger
from utils.app_paths import get_config_file

logger = get_logger("machine_id")


class MachineIDManager:
    """机器码管理器"""
    
    @staticmethod
    def get_machine_id() -> str:
        """
        获取设备唯一机器码
        
        Returns:
            str: 机器码（32位MD5哈希）
        """
        try:
            components = []
            
            # 1. 硬盘序列号
            try:
                if platform.system() == 'Windows':
                    import subprocess
                    result = subprocess.run(
                        ['wmic', 'diskdrive', 'get', 'serialnumber'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    disk_serial = result.stdout.strip().split('\n')[-1].strip()
                    if disk_serial and disk_serial != 'SerialNumber':
                        components.append(f"disk:{disk_serial}")
                else:
                    # Linux/Mac
                    disk_serial = str(uuid.getnode())
                    components.append(f"disk:{disk_serial}")
            except Exception as e:
                logger.debug(f"获取硬盘序列号失败: {e}")
            
            # 2. CPU信息
            try:
                cpu_brand = platform.processor()
                if cpu_brand:
                    components.append(f"cpu:{cpu_brand}")
            except:
                components.append(f"cpu:unknown")
            
            # 3. 主板UUID（如果可用）
            try:
                if platform.system() == 'Windows':
                    import subprocess
                    result = subprocess.run(
                        ['wmic', 'csproduct', 'get', 'uuid'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    board_uuid = result.stdout.strip().split('\n')[-1].strip()
                    if board_uuid and board_uuid != 'UUID':
                        components.append(f"board:{board_uuid}")
            except Exception as e:
                logger.debug(f"获取主板UUID失败: {e}")
            
            # 4. MAC地址
            try:
                mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff)
                                for elements in range(0, 8*6, 8)][::-1])
                components.append(f"mac:{mac}")
            except:
                pass
            
            # 5. 计算机名
            components.append(f"name:{platform.node()}")
            
            # 组合所有组件并计算哈希
            if not components:
                # 备用方案：使用UUID
                components.append(f"uuid:{uuid.uuid4()}")
            
            combined = "|".join(components)
            machine_id = hashlib.md5(combined.encode()).hexdigest()
            
            logger.info(f"✅ 机器码生成成功: {machine_id[:16]}...")
            logger.debug(f"机器码组件: {len(components)} 个")
            
            return machine_id
            
        except Exception as e:
            logger.error(f"生成机器码失败: {e}")
            # 备用方案
            fallback = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()
            logger.warning(f"使用备用机器码: {fallback[:16]}...")
            return fallback
    
    @staticmethod
    def save_machine_id(machine_id: str, config_file: str = None):
        """
        保存机器码到配置文件
        
        Args:
            machine_id: 机器码
            config_file: 配置文件路径（可选，默认使用用户目录）
        """
        try:
            import json
            from pathlib import Path
            
            # 使用用户目录的配置文件路径
            if config_file:
                config_path = Path(config_file)
            else:
                config_path = get_config_file()
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {}
            
            # 保存机器码
            if 'license' not in config:
                config['license'] = {}
            
            config['license']['machine_id'] = machine_id
            
            # 写回文件
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            logger.info("✅ 机器码已保存到配置文件")
            return True
            
        except Exception as e:
            logger.error(f"保存机器码失败: {e}")
            return False
    
    @staticmethod
    def load_machine_id(config_file: str = None) -> str:
        """
        从配置文件加载机器码
        
        Args:
            config_file: 配置文件路径（可选，默认使用用户目录）
            
        Returns:
            str: 机器码，如果不存在则返回None
        """
        try:
            import json
            
            # 使用用户目录的配置文件路径
            if config_file:
                config_path = Path(config_file)
            else:
                config_path = get_config_file()
            
            if not config_path.exists():
                return None
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            machine_id = config.get('license', {}).get('machine_id')
            if machine_id:
                logger.debug(f"从配置加载机器码: {machine_id[:16]}...")
            
            return machine_id
            
        except Exception as e:
            logger.error(f"加载机器码失败: {e}")
            return None


# 全局单例
_machine_id_manager = None

def get_machine_id_manager():
    """获取机器码管理器单例"""
    global _machine_id_manager
    if _machine_id_manager is None:
        _machine_id_manager = MachineIDManager()
    return _machine_id_manager

