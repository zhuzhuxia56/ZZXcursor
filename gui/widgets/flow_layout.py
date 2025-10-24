#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FlowLayout - 流式布局管理器
自动换行的网格布局，根据容器宽度自动调整列数
"""

from PyQt6.QtCore import Qt, QRect, QSize, QPoint
from PyQt6.QtWidgets import QLayout, QWidgetItem


class FlowLayout(QLayout):
    """流式布局 - 自动换行的网格布局（支持居中对齐）"""
    
    def __init__(self, parent=None, margin=0, spacing=-1, center_align=True):
        """
        初始化流式布局
        
        Args:
            parent: 父组件
            margin: 边距
            spacing: 间距
            center_align: 是否居中对齐（默认True）
        """
        super().__init__(parent)
        
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        
        self.setSpacing(spacing)
        self._item_list = []
        self._center_align = center_align
        
        # ⭐ 新增：布局缓存
        self._cached_rect = None          # 上次布局的矩形
        self._cached_width = 0            # 上次容器宽度
        self._cached_positions = {}       # {item_id: QRect}
        self._cached_item_count = 0       # 上次item数量
        self._layout_dirty = True         # 布局是否需要重新计算
        self._frozen = False              # 是否冻结布局（完全禁用重排）
        self._threshold = 10              # 缓存阈值（默认10px）
        self._last_config_check = 0       # 上次检查配置的时间
    
    def __del__(self):
        """析构函数 - 清理所有项目"""
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)
    
    def addItem(self, item):
        """
        添加项目到布局
        
        Args:
            item: 布局项目
        """
        self._item_list.append(item)
    
    def count(self):
        """
        返回布局中的项目数量
        
        Returns:
            int: 项目数量
        """
        return len(self._item_list)
    
    def itemAt(self, index):
        """
        获取指定索引的项目
        
        Args:
            index: 索引
            
        Returns:
            QLayoutItem: 布局项目，如果索引无效则返回 None
        """
        if 0 <= index < len(self._item_list):
            return self._item_list[index]
        return None
    
    def takeAt(self, index):
        """
        移除并返回指定索引的项目
        
        Args:
            index: 索引
            
        Returns:
            QLayoutItem: 移除的布局项目，如果索引无效则返回 None
        """
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)
        return None
    
    def expandingDirections(self):
        """
        返回布局的扩展方向
        
        Returns:
            Qt.Orientations: 不扩展
        """
        return Qt.Orientation(0)
    
    def hasHeightForWidth(self):
        """
        布局是否根据宽度计算高度
        
        Returns:
            bool: True（流式布局需要根据宽度计算高度）
        """
        return True
    
    def heightForWidth(self, width):
        """
        根据宽度计算所需高度
        
        Args:
            width: 可用宽度
            
        Returns:
            int: 所需高度
        """
        height = self._do_layout(QRect(0, 0, width, 0), True)
        return height
    
    def _should_relayout(self, rect: QRect) -> bool:
        """
        判断是否需要重新布局
        
        Returns:
            bool: True表示需要重新计算，False表示使用缓存
        """
        # 首次布局
        if self._cached_rect is None:
            return True
        
        # 被标记为脏
        if self._layout_dirty:
            return True
        
        # item数量变化
        if len(self._item_list) != self._cached_item_count:
            return True
        
        # ⭐ 定期更新缓存阈值（每10秒检查一次配置，避免频繁读取文件）
        import time
        current_time = time.time()
        if current_time - self._last_config_check > 10:
            try:
                import json
                from pathlib import Path
                import sys
                # 导入 get_config_file
                sys.path.insert(0, str(Path(__file__).parent.parent.parent))
                from utils.app_paths import get_config_file
                
                config_path = get_config_file()
                if config_path.exists():
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        self._threshold = config.get('performance', {}).get('cache_threshold', 10)
                self._last_config_check = current_time
            except:
                pass
        
        # 宽度显著变化（超过阈值）
        if abs(rect.width() - self._cached_width) > self._threshold:
            return True
        
        # 其他情况使用缓存
        return False
    
    def invalidate(self):
        """标记布局为脏（需要重新计算）"""
        self._layout_dirty = True
        super().invalidate()
    
    def freeze(self):
        """冻结布局（完全禁用重排，用于批量操作）"""
        self._frozen = True
    
    def unfreeze(self):
        """解冻布局（恢复重排，并标记为脏）"""
        self._frozen = False
        self._layout_dirty = True
    
    def _apply_cached_layout(self):
        """应用缓存的布局位置（极快，无需计算）"""
        for item in self._item_list:
            item_id = id(item)
            if item_id in self._cached_positions:
                cached_rect = self._cached_positions[item_id]
                item.setGeometry(cached_rect)
    
    def _update_cache(self, rect: QRect):
        """更新缓存数据"""
        self._cached_rect = rect
        self._cached_width = rect.width()
        self._cached_item_count = len(self._item_list)
        self._layout_dirty = False
        
        # 缓存每个item的位置
        self._cached_positions.clear()
        for item in self._item_list:
            item_id = id(item)
            self._cached_positions[item_id] = item.geometry()
    
    def setGeometry(self, rect):
        """
        设置布局几何形状（优化版：使用缓存+冻结）
        
        Args:
            rect: 几何矩形
        """
        super().setGeometry(rect)
        
        # ⭐ 如果被冻结，完全不执行布局（性能最优）
        if self._frozen:
            return
        
        # ⭐ 智能判断：是否需要重新计算
        if self._should_relayout(rect):
            # 需要重新计算布局
            self._do_layout(rect, False)
            # 更新缓存
            self._update_cache(rect)
        else:
            # 使用缓存位置（极快）
            self._apply_cached_layout()
    
    def sizeHint(self):
        """
        返回布局的建议大小
        
        Returns:
            QSize: 建议大小
        """
        return self.minimumSize()
    
    def minimumSize(self):
        """
        返回布局的最小大小
        
        Returns:
            QSize: 最小大小
        """
        size = QSize()
        
        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())
        
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size
    
    def _do_layout(self, rect, test_only):
        """
        执行布局计算（支持居中对齐）
        
        Args:
            rect: 可用区域
            test_only: 是否仅测试（True 时只计算不实际布局）
            
        Returns:
            int: 布局所需的总高度
        """
        left, top, right, bottom = self.getContentsMargins()
        effective_rect = rect.adjusted(left, top, -right, -bottom)
        spacing = self.spacing()
        
        # 如果启用居中对齐，需要先计算每行的项目
        if self._center_align and not test_only:
            return self._do_layout_centered(rect, effective_rect, spacing, left, top, right, bottom)
        else:
            # 原始左对齐布局
            return self._do_layout_left_aligned(rect, effective_rect, spacing, left, top, right, bottom)
    
    def _do_layout_left_aligned(self, rect, effective_rect, spacing, left, top, right, bottom):
        """左对齐布局（原始逻辑）"""
        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0
        
        for item in self._item_list:
            widget = item.widget()
            if widget is None:
                continue
            
            # ⭐ 跳过隐藏的widget（筛选后的）
            if not widget.isVisible():
                continue
            
            size_hint = item.sizeHint()
            next_x = x + size_hint.width() + spacing
            
            if next_x - spacing > effective_rect.right() and line_height > 0:
                x = effective_rect.x()
                y = y + line_height + spacing
                next_x = x + size_hint.width() + spacing
                line_height = 0
            
            item.setGeometry(QRect(QPoint(x, y), size_hint))
            
            x = next_x
            line_height = max(line_height, size_hint.height())
        
        return y + line_height - rect.y() + bottom
    
    def _do_layout_centered(self, rect, effective_rect, spacing, left, top, right, bottom):
        """居中对齐布局（带缓存）"""
        # 第一步：将项目分组到各行
        lines = []
        current_line = []
        current_line_width = 0
        max_line_height = 0
        
        for item in self._item_list:
            widget = item.widget()
            if widget is None:
                continue
            
            # ⭐ 跳过隐藏的widget（筛选后的）
            if not widget.isVisible():
                continue
            
            size_hint = item.sizeHint()
            item_width = size_hint.width()
            
            # 计算如果添加这个项目，行宽是多少
            if current_line:
                needed_width = current_line_width + spacing + item_width
            else:
                needed_width = item_width
            
            # 如果超出宽度且当前行不为空，换行
            if needed_width > effective_rect.width() and current_line:
                lines.append((current_line, current_line_width, max_line_height))
                current_line = [item]
                current_line_width = item_width
                max_line_height = size_hint.height()
            else:
                current_line.append(item)
                current_line_width = needed_width
                max_line_height = max(max_line_height, size_hint.height())
        
        # 添加最后一行
        if current_line:
            lines.append((current_line, current_line_width, max_line_height))
        
        # 第二步：居中布局每一行
        y = effective_rect.y()
        
        for line_items, line_width, line_height in lines:
            # 计算居中偏移量
            x_offset = (effective_rect.width() - line_width) // 2
            x = effective_rect.x() + x_offset
            
            # 布局这一行的所有项目
            for item in line_items:
                size_hint = item.sizeHint()
                item.setGeometry(QRect(QPoint(x, y), size_hint))
                x += size_hint.width() + spacing
            
            # 移动到下一行
            y += line_height + spacing
        
        # ⭐ 在返回之前，缓存item位置
        for item in self._item_list:
            item_id = id(item)
            self._cached_positions[item_id] = item.geometry()
        
        # 返回总高度
        if lines:
            return y - spacing - rect.y() + bottom
        else:
            return top + bottom

