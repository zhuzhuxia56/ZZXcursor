#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
卡池管理器
管理导入的卡号，实现轮询使用
"""

import sys
import json
from pathlib import Path
from typing import Optional, Dict
from PyQt6.QtCore import QObject, pyqtSignal

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import get_logger
from utils.app_paths import get_config_file

logger = get_logger("card_pool_manager")


class CardPoolManager(QObject):
    """卡池管理器"""
    
    # 信号：卡池更新时触发
    cards_updated = pyqtSignal(int)  # 参数：剩余卡号数量
    
    def __init__(self):
        super().__init__()
        # 使用用户目录的配置文件路径
        self.config_file = get_config_file()
        self.current_index = 0
        self.cards = []
        self._load_cards()
    
    def _load_cards(self):
        """从配置文件加载卡号"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                payment_config = config.get('payment_binding', {})
                self.cards = payment_config.get('imported_cards', [])
                
                if self.cards:
                    logger.info(f"✅ 加载了 {len(self.cards)} 组卡号")
                else:
                    logger.warning("卡池为空")
            
        except Exception as e:
            logger.error(f"加载卡号失败: {e}")
            self.cards = []
    
    def get_next_card(self) -> Optional[Dict]:
        """
        获取下一张卡号（轮询方式）
        
        Returns:
            dict: {'number': ..., 'month': ..., 'year': ..., 'cvv': ..., 'index': ...} 或 None
        """
        if not self.cards:
            logger.warning("卡池为空，无法获取卡号")
            return None
        
        # 获取当前卡号
        card = self.cards[self.current_index].copy()
        card['index'] = self.current_index  # 添加索引信息
        
        logger.info(f"从卡池获取卡号 [{self.current_index + 1}/{len(self.cards)}]")
        logger.info(f"  卡号: {card['number']}")
        logger.info(f"  有效期: {card['month']}/{card['year']}")
        
        # 移动到下一张卡
        self.current_index = (self.current_index + 1) % len(self.cards)
        
        return card
    
    def remove_card_by_number(self, card_number: str) -> bool:
        """
        删除指定卡号（绑卡成功后调用）
        
        Args:
            card_number: 卡号
            
        Returns:
            bool: 是否成功删除
        """
        try:
            # 查找并删除卡号
            for i, card in enumerate(self.cards):
                if card['number'] == card_number:
                    deleted_card = self.cards.pop(i)
                    logger.info(f"✅ 已删除使用过的卡号: {card_number}")
                    logger.info(f"   剩余卡号: {len(self.cards)} 组")
                    
                    # 调整当前索引
                    if i < self.current_index:
                        self.current_index -= 1
                    elif self.current_index >= len(self.cards) and len(self.cards) > 0:
                        self.current_index = 0
                    
                    # 保存到配置文件
                    self._save_cards_to_config()
                    
                    # 发送信号通知 UI 更新
                    self.cards_updated.emit(len(self.cards))
                    
                    return True
            
            logger.warning(f"未找到要删除的卡号: {card_number}")
            return False
            
        except Exception as e:
            logger.error(f"删除卡号失败: {e}")
            return False
    
    def _save_cards_to_config(self):
        """保存卡号列表到配置文件"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 更新卡号列表
                if 'payment_binding' not in config:
                    config['payment_binding'] = {}
                
                config['payment_binding']['imported_cards'] = self.cards
                
                # 保存
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                
                logger.info(f"✅ 卡号列表已更新到配置文件")
                
        except Exception as e:
            logger.error(f"保存卡号列表失败: {e}")
    
    def has_cards(self) -> bool:
        """检查卡池是否有卡"""
        return len(self.cards) > 0
    
    def get_card_count(self) -> int:
        """获取卡池中的卡数量"""
        return len(self.cards)
    
    def reset_index(self):
        """重置索引到开始"""
        self.current_index = 0
        logger.info("卡池索引已重置")


# 全局卡池管理器实例
_card_pool_manager = None


def get_card_pool_manager() -> CardPoolManager:
    """获取全局卡池管理器实例"""
    global _card_pool_manager
    if _card_pool_manager is None:
        _card_pool_manager = CardPoolManager()
    return _card_pool_manager


def reload_card_pool():
    """重新加载卡池"""
    global _card_pool_manager
    _card_pool_manager = CardPoolManager()
    return _card_pool_manager

