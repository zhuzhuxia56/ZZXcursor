#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账号管理工具栏
包含筛选、排序和批量操作功能
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QCheckBox, QLineEdit
)
from PyQt6.QtCore import pyqtSignal


class AccountToolbar(QWidget):
    """账号管理工具栏"""
    
    # 信号
    filter_changed = pyqtSignal(dict)  # 筛选条件改变
    sort_changed = pyqtSignal(str, bool)  # 排序改变（字段, 升序）
    add_clicked = pyqtSignal()  # 添加账号
    import_clicked = pyqtSignal()  # 导入账号
    export_clicked = pyqtSignal()  # 导出选中
    # ⭐ 已移除 view_encrypted_clicked 信号
    select_all_changed = pyqtSignal(bool)  # 全选状态改变
    batch_delete_clicked = pyqtSignal()  # 批量删除
    batch_refresh_clicked = pyqtSignal()  # 批量刷新
    batch_payment_clicked = pyqtSignal()  # 批量绑卡
    search_text_changed = pyqtSignal(str)  # 搜索文本改变
    
    def __init__(self, parent=None):
        """初始化工具栏"""
        super().__init__(parent)
        
        self.selected_count = 0
        self.total_count = 0
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 10)
        main_layout.setSpacing(10)
        
        # 第一行：标题和主要操作按钮
        title_row = QHBoxLayout()
        
        self.title_label = QLabel("📋 账号列表 (0个)")
        title_font = self.title_label.font()
        title_font.setPointSize(14)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        title_row.addWidget(self.title_label)
        
        title_row.addStretch()
        
        # 添加按钮
        add_btn = QPushButton("➕ 添加")
        add_btn.setProperty("primary", True)
        add_btn.clicked.connect(self.add_clicked.emit)
        title_row.addWidget(add_btn)
        
        # 导入按钮
        import_btn = QPushButton("📥 导入")
        import_btn.setProperty("secondary", True)
        import_btn.clicked.connect(self.import_clicked.emit)
        title_row.addWidget(import_btn)
        
        # 导出按钮
        self.export_btn = QPushButton("📤 导出选中")
        self.export_btn.setProperty("secondary", True)
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.export_clicked.emit)
        title_row.addWidget(self.export_btn)
        
        # ⭐ 已移除"查看加密文件"按钮 - 不让用户知道导出的是加密文件
        
        main_layout.addLayout(title_row)
        
        # 第二行：筛选器
        filter_row = QHBoxLayout()
        
        filter_label = QLabel("筛选:")
        filter_row.addWidget(filter_label)
        
        # 状态筛选
        self.status_combo = QComboBox()
        self.status_combo.addItems(["全部账号", "仅有效", "已失效", "即将过期(<7天)", "未绑卡"])
        self.status_combo.currentTextChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self.status_combo)
        
        # 类型筛选
        self.type_combo = QComboBox()
        self.type_combo.addItems(["全部类型", "FREE", "PRO", "TEAM", "ENTERPRISE"])
        self.type_combo.currentTextChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self.type_combo)
        
        # 月份筛选
        self.month_combo = QComboBox()
        self.month_combo.addItem("全部月份")
        # 动态添加最近12个月
        from datetime import datetime, timedelta
        now = datetime.now()
        for i in range(12):
            month = now - timedelta(days=i*30)
            self.month_combo.addItem(month.strftime("%Y-%m"))
        self.month_combo.currentTextChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self.month_combo)
        
        # 搜索框
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 搜索邮箱...")
        self.search_box.setMaximumWidth(200)
        self.search_box.textChanged.connect(self.search_text_changed.emit)
        filter_row.addWidget(self.search_box)
        
        filter_row.addStretch()
        
        main_layout.addLayout(filter_row)
        
        # 第三行：排序和批量操作
        action_row = QHBoxLayout()
        
        # 排序
        sort_label = QLabel("排序:")
        action_row.addWidget(sort_label)
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "创建时间 ↓",
            "创建时间 ↑",
            "剩余天数 ↓",
            "剩余天数 ↑",
            "已花费 ↓",
            "已花费 ↑",
            "最后使用 ↓",
            "最后使用 ↑"
        ])
        self.sort_combo.currentTextChanged.connect(self._on_sort_changed)
        action_row.addWidget(self.sort_combo)
        
        action_row.addSpacing(20)
        
        # 批量操作
        batch_label = QLabel("批量:")
        action_row.addWidget(batch_label)
        
        # 全选复选框
        self.select_all_checkbox = QCheckBox("全选")
        self.select_all_checkbox.stateChanged.connect(self._on_select_all_checkbox_changed)
        action_row.addWidget(self.select_all_checkbox)
        
        # 选择计数
        self.selection_label = QLabel("已选择 0 个")
        self.selection_label.setStyleSheet("color: #808080;")
        action_row.addWidget(self.selection_label)
        
        # 批量刷新按钮
        self.batch_refresh_btn = QPushButton("🔄 刷新")
        self.batch_refresh_btn.setProperty("secondary", True)
        self.batch_refresh_btn.setEnabled(False)
        self.batch_refresh_btn.clicked.connect(self.batch_refresh_clicked.emit)
        action_row.addWidget(self.batch_refresh_btn)
        
        # 批量绑卡按钮
        self.batch_payment_btn = QPushButton("💳 绑卡")
        self.batch_payment_btn.setProperty("secondary", True)
        self.batch_payment_btn.setEnabled(False)
        self.batch_payment_btn.clicked.connect(self.batch_payment_clicked.emit)
        action_row.addWidget(self.batch_payment_btn)
        
        # 批量删除按钮
        self.batch_delete_btn = QPushButton("🗑️ 删除")
        self.batch_delete_btn.setProperty("danger", True)
        self.batch_delete_btn.setEnabled(False)
        self.batch_delete_btn.clicked.connect(self.batch_delete_clicked.emit)
        action_row.addWidget(self.batch_delete_btn)
        
        action_row.addStretch()
        
        main_layout.addLayout(action_row)
    
    def _on_filter_changed(self):
        """筛选条件改变"""
        filter_dict = {
            'status': None,
            'type': None,
            'month': None
        }
        
        # 状态筛选
        status_text = self.status_combo.currentText()
        if status_text == "仅有效":
            filter_dict['status'] = 'active'
        elif status_text == "已失效":
            filter_dict['status'] = 'expired'
        elif status_text == "即将过期(<7天)":
            filter_dict['status'] = 'expiring_soon'
        elif status_text == "未绑卡":
            filter_dict['status'] = 'no_payment'
        
        # 类型筛选
        type_text = self.type_combo.currentText()
        if type_text != "全部类型":
            filter_dict['type'] = type_text.lower()
        
        # 月份筛选
        month_text = self.month_combo.currentText()
        if month_text != "全部月份":
            filter_dict['month'] = month_text
        
        self.filter_changed.emit(filter_dict)
    
    def _on_select_all_checkbox_changed(self, state):
        """全选复选框状态改变"""
        from PyQt6.QtCore import Qt
        # ⭐ 修复：半选中状态点击时也要响应
        if state == Qt.CheckState.Checked.value:
            self.select_all_changed.emit(True)
        elif state == Qt.CheckState.Unchecked.value:
            self.select_all_changed.emit(False)
        elif state == Qt.CheckState.PartiallyChecked.value:
            # 半选中状态点击时，视为要全选
            self.select_all_changed.emit(True)
    
    def _on_sort_changed(self):
        """排序改变"""
        sort_text = self.sort_combo.currentText()
        
        # 解析排序字段和方向
        sort_map = {
            "创建时间 ↓": ('created_at', False),
            "创建时间 ↑": ('created_at', True),
            "剩余天数 ↓": ('days_remaining', False),
            "剩余天数 ↑": ('days_remaining', True),
            "已花费 ↓": ('total_cost', False),
            "已花费 ↑": ('total_cost', True),
            "最后使用 ↓": ('last_used', False),
            "最后使用 ↑": ('last_used', True)
        }
        
        sort_by, ascending = sort_map.get(sort_text, ('created_at', False))
        self.sort_changed.emit(sort_by, ascending)
    
    def update_counts(self, selected: int, total: int, visible: int = None):
        """
        更新计数显示
        
        Args:
            selected: 选中数量
            total: 总账号数（包括隐藏的）
            visible: 可见账号数（筛选后的），用于判断全选状态
        """
        self.selected_count = selected
        self.total_count = total
        
        # ⭐ 如果没有提供visible，则等于total
        if visible is None:
            visible = total
        
        self.title_label.setText(f"📋 账号列表 ({total}个)")
        self.selection_label.setText(f"已选择 {selected} 个")
        
        # 更新按钮状态
        has_selection = selected > 0
        self.export_btn.setEnabled(has_selection)
        self.batch_delete_btn.setEnabled(has_selection)
        self.batch_refresh_btn.setEnabled(has_selection)
        self.batch_payment_btn.setEnabled(has_selection)
        
        # 更新全选复选框状态 - 阻塞信号避免循环触发
        from PyQt6.QtCore import Qt as QtCore
        # ⭐ 更新全选复选框状态（使用visible而不是total）
        self.select_all_checkbox.blockSignals(True)
        if selected == 0:
            self.select_all_checkbox.setCheckState(QtCore.CheckState.Unchecked)
        elif selected == visible and visible > 0:
            self.select_all_checkbox.setCheckState(QtCore.CheckState.Checked)
        else:
            self.select_all_checkbox.setCheckState(QtCore.CheckState.PartiallyChecked)
        self.select_all_checkbox.blockSignals(False)

