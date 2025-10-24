#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
绑卡配置面板
作为标签页显示在主界面中
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QGroupBox, QRadioButton, 
    QButtonGroup, QMessageBox, QScrollArea, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

import sys
import json
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.logger import get_logger
from core.country_codes import get_country_name, is_valid_country_code
from utils.app_paths import get_config_file
from utils.resource_path import get_gui_resource

logger = get_logger("payment_panel")


class PaymentPanel(QWidget):
    """绑卡配置面板"""
    
    config_changed = pyqtSignal()  # 配置变更信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PaymentPanel")  # 设置对象名用于CSS
        # 使用用户目录的配置文件路径
        self.config_file = get_config_file()
        self.config = self._load_config()
        self.is_auto_gen_unlocked = False  # 自动生成功能解锁状态
        self.has_unsaved_changes = False  # 是否有未保存的修改
        self.init_ui()
        self._load_current_config()
        self._connect_change_signals()  # 连接所有变更信号
        
        # ⭐ 启动定时器，定期刷新卡号数量（检测外部删除）
        from PyQt6.QtCore import QTimer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_card_count)
        self.refresh_timer.start(2000)  # 每2秒刷新一次
        
        # ⭐ 监听卡池更新信号（删除后立即刷新）
        try:
            from core.card_pool_manager import get_card_pool_manager
            card_manager = get_card_pool_manager()
            card_manager.cards_updated.connect(self._on_card_pool_updated)
            logger.info("✅ 已连接卡池更新信号")
        except Exception as e:
            logger.warning(f"连接卡池信号失败: {e}")
    
    def init_ui(self):
        """初始化界面"""
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setObjectName("PaymentScrollArea")  # 设置对象名
        
        # 主容器
        container = QWidget()
        container.setObjectName("PaymentContainer")  # 设置对象名用于CSS
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title = QLabel("💳 自动绑卡配置")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # 说明
        desc = QLabel("配置注册成功后是否自动绑定支付方式，开启 7 天 Cursor Pro 免费试用")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #7f8c8d; padding: 5px 0;")
        layout.addWidget(desc)
        
        # 基础配置
        basic_group = self._create_basic_config_group()
        layout.addWidget(basic_group)
        
        # 虚拟卡配置
        card_group = self._create_card_config_group()
        layout.addWidget(card_group)
        
        # 固定信息配置
        fixed_info_group = self._create_fixed_info_group()
        layout.addWidget(fixed_info_group)
        
        # 高级配置
        advanced_group = self._create_advanced_config_group()
        layout.addWidget(advanced_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("💾 保存配置")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 10px 30px;
                font-weight: bold;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        self.save_btn.clicked.connect(self._on_save)
        
        self.test_btn = QPushButton("🧪 测试绑卡")
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 10px 30px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.test_btn.clicked.connect(self._on_test)
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.test_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        scroll.setWidget(container)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
    
    def _create_basic_config_group(self):
        """创建基础配置组"""
        group = QGroupBox("基础配置")
        layout = QVBoxLayout()
        
        # 启用绑卡
        self.enable_checkbox = QCheckBox("启用自动绑卡")
        self.enable_checkbox.stateChanged.connect(self._on_enable_changed)
        layout.addWidget(self.enable_checkbox)
        
        hint1 = QLabel("✓ 启用后，注册成功会自动绑定支付方式，开启 7 天免费试用")
        hint1.setStyleSheet("color: #27ae60; font-size: 11px; padding-left: 25px;")
        layout.addWidget(hint1)
        
        hint2 = QLabel("✗ 禁用后，只注册账号，不绑定支付方式")
        hint2.setStyleSheet("color: #95a5a6; font-size: 11px; padding-left: 25px;")
        layout.addWidget(hint2)
        
        layout.addSpacing(10)
        
        # 自动填写
        self.auto_fill_checkbox = QCheckBox("自动填写支付信息")
        layout.addWidget(self.auto_fill_checkbox)
        
        hint3 = QLabel("自动生成虚拟银行账户信息并填写")
        hint3.setStyleSheet("color: #7f8c8d; font-size: 11px; padding-left: 25px;")
        layout.addWidget(hint3)
        
        group.setLayout(layout)
        return group
    
    def _create_card_config_group(self):
        """创建虚拟卡配置组（左右分栏）"""
        group = QGroupBox("虚拟卡配置")
        main_layout = QVBoxLayout()
        
        # 左右分栏
        columns_layout = QHBoxLayout()
        
        # ========== 左栏：自动生成 ==========
        left_panel = QWidget()
        left_panel.setObjectName("CardLeftPanel")  # 设置对象名用于CSS
        left_layout = QVBoxLayout(left_panel)
        
        # 创建单选按钮组（确保互斥）
        self.card_mode_group = QButtonGroup(self)
        self.card_mode_group.buttonClicked.connect(self._on_card_mode_changed)
        
        # 左栏标题
        title_layout = QHBoxLayout()
        self.auto_gen_radio = QRadioButton("🎲 自动生成卡号")
        self.auto_gen_radio.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.card_mode_group.addButton(self.auto_gen_radio, 1)
        title_layout.addWidget(self.auto_gen_radio)
        
        # 锁头图标
        self.lock_icon = QLabel("🔒")
        self.lock_icon.setStyleSheet("font-size: 16px; color: #e74c3c;")
        self.lock_icon.setToolTip("需要解锁码")
        title_layout.addWidget(self.lock_icon)
        title_layout.addStretch()
        
        left_layout.addLayout(title_layout)
        
        # 解锁区域
        self.unlock_widget = QWidget()
        unlock_layout = QVBoxLayout(self.unlock_widget)
        unlock_layout.setContentsMargins(10, 10, 0, 0)
        
        unlock_label = QLabel("🔐 请输入解锁码:")
        unlock_label.setStyleSheet("color: #e74c3c; font-weight: bold; font-size: 12px;")
        unlock_layout.addWidget(unlock_label)
        
        unlock_input_layout = QHBoxLayout()
        self.unlock_input = QLineEdit()
        self.unlock_input.setPlaceholderText("输入解锁码以使用自动生成功能")
        self.unlock_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.unlock_input.setStyleSheet("padding: 5px; border: 2px solid #e74c3c; border-radius: 3px;")
        unlock_input_layout.addWidget(self.unlock_input)
        
        self.unlock_btn = QPushButton("🔓 解锁")
        self.unlock_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 5px 15px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.unlock_btn.clicked.connect(self._on_unlock)
        unlock_input_layout.addWidget(self.unlock_btn)
        
        unlock_layout.addLayout(unlock_input_layout)
        
        unlock_hint = QLabel("💡 联系管理员获取解锁码")
        unlock_hint.setStyleSheet("color: #95a5a6; font-size: 10px;")
        unlock_layout.addWidget(unlock_hint)
        
        left_layout.addWidget(self.unlock_widget)
        
        # 卡头配置（默认锁定）
        self.auto_gen_widget = QWidget()
        auto_gen_layout = QVBoxLayout(self.auto_gen_widget)
        auto_gen_layout.setContentsMargins(10, 10, 0, 0)
        
        bin_layout = QHBoxLayout()
        bin_label = QLabel("BIN 卡头前缀:")
        bin_label.setMinimumWidth(120)
        self.bin_input = QLineEdit()
        self.bin_input.setPlaceholderText("例如: 5224900")
        self.bin_input.setMaxLength(10)
        bin_layout.addWidget(bin_label)
        bin_layout.addWidget(self.bin_input)
        auto_gen_layout.addLayout(bin_layout)
        
        hint = QLabel("💡 卡头决定了卡号的前几位")
        hint.setStyleSheet("color: #3498db; font-size: 11px;")
        auto_gen_layout.addWidget(hint)
        
        # 常用卡头示例
        examples_label = QLabel("常用卡头示例:")
        examples_label.setStyleSheet("font-weight: bold; margin-top: 5px; font-size: 11px;")
        auto_gen_layout.addWidget(examples_label)
        
        examples_text = "• 5224900 - MasterCard (默认)\n• 4242424 - Visa (Stripe 测试卡)\n• 5555555 - MasterCard\n• 3782822 - American Express"
        examples = QLabel(examples_text)
        examples.setStyleSheet("color: #7f8c8d; font-size: 10px; padding-left: 10px;")
        auto_gen_layout.addWidget(examples)
        
        left_layout.addWidget(self.auto_gen_widget)
        left_layout.addStretch()
        
        # ========== 右栏：导入卡号 ==========
        right_panel = QWidget()
        right_panel.setObjectName("CardRightPanel")  # 设置对象名用于CSS
        right_layout = QVBoxLayout(right_panel)
        
        # 右栏标题
        self.import_card_radio = QRadioButton("📥 导入卡号")
        self.import_card_radio.setChecked(True)  # 默认选择导入卡号
        self.import_card_radio.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.card_mode_group.addButton(self.import_card_radio, 2)  # 加入单选组
        right_layout.addWidget(self.import_card_radio)
        
        # 导入卡号配置
        self.import_card_widget = QWidget()
        import_layout = QVBoxLayout(self.import_card_widget)
        import_layout.setContentsMargins(10, 10, 0, 0)
        
        format_label = QLabel("格式: 卡号|月份|年份|CVV")
        format_label.setStyleSheet("font-size: 11px; color: #e74c3c; font-weight: bold;")
        import_layout.addWidget(format_label)
        
        format_example = QLabel("例如: 6228364744475537|07|2025|574")
        format_example.setStyleSheet("font-size: 10px; color: #7f8c8d; padding-left: 10px;")
        import_layout.addWidget(format_example)
        
        import_layout.addSpacing(5)
        
        # 卡号列表输入
        # 卡号列表标签和获取按钮
        list_header_layout = QHBoxLayout()
        list_label = QLabel("卡号列表（最多500组）:")
        list_label.setStyleSheet("font-size: 11px; margin-top: 5px;")
        list_header_layout.addWidget(list_label)
        
        # ⭐ 获取虚拟卡按钮
        get_card_btn = QPushButton("💳 获取虚拟卡")
        get_card_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        get_card_btn.clicked.connect(self._on_get_virtual_card)
        list_header_layout.addWidget(get_card_btn)
        list_header_layout.addStretch()
        import_layout.addLayout(list_header_layout)
        
        from PyQt6.QtWidgets import QTextEdit
        self.card_list_input = QTextEdit()
        self.card_list_input.setPlaceholderText(
            "每行一组卡号，格式:\n"
            "6228364744475537|07|2025|574\n"
            "6228362423623013|06|2026|668\n"
            "...\n\n"
            "最多可导入500组"
        )
        self.card_list_input.setMaximumHeight(200)
        self.card_list_input.setStyleSheet("font-family: Consolas; font-size: 11px;")
        import_layout.addWidget(self.card_list_input)
        
        # 统计信息
        self.card_count_label = QLabel("已导入: 0 组")
        self.card_count_label.setStyleSheet("color: #27ae60; font-weight: bold; font-size: 11px;")
        import_layout.addWidget(self.card_count_label)
        
        # 验证按钮
        validate_btn = QPushButton("✓ 验证格式")
        validate_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 5px 15px;
                border-radius: 3px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        validate_btn.clicked.connect(self._on_validate_cards)
        import_layout.addWidget(validate_btn)
        
        right_layout.addWidget(self.import_card_widget)
        right_layout.addStretch()
        
        # 添加到主布局
        columns_layout.addWidget(left_panel)
        columns_layout.addWidget(right_panel)
        
        main_layout.addLayout(columns_layout)
        
        group.setLayout(main_layout)
        return group
    
    def _create_fixed_info_group(self):
        """创建固定信息配置组"""
        group = QGroupBox("固定信息配置")
        layout = QVBoxLayout()
        
        # 启用固定信息
        self.fixed_info_checkbox = QCheckBox("启用固定信息（每次都用相同的地址信息）")
        self.fixed_info_checkbox.stateChanged.connect(self._on_fixed_info_changed)
        layout.addWidget(self.fixed_info_checkbox)
        
        hint1 = QLabel("✓ 启用后，每次绑卡都使用下方设置的固定信息")
        hint1.setStyleSheet("color: #27ae60; font-size: 11px; padding-left: 25px;")
        layout.addWidget(hint1)
        
        hint2 = QLabel("✓ 姓名和地址留空时，会随机生成美国地址进行自动填写")
        hint2.setStyleSheet("color: #3498db; font-size: 11px; padding-left: 25px; margin-bottom: 10px;")
        layout.addWidget(hint2)
        
        # 固定信息输入
        self.fixed_info_widget = QWidget()
        fixed_layout = QVBoxLayout(self.fixed_info_widget)
        fixed_layout.setContentsMargins(20, 10, 0, 0)
        
        # 国家代码（左右分栏）
        country_layout = QHBoxLayout()
        country_label = QLabel("国家代码:")
        country_label.setMinimumWidth(100)
        
        # 左边：输入框
        self.country_input = QLineEdit()
        self.country_input.setPlaceholderText("输入2位ISO代码")
        self.country_input.setMaxLength(2)
        self.country_input.setText("US")
        self.country_input.setFixedWidth(120)
        self.country_input.textChanged.connect(self._on_country_code_changed)
        
        # 右边：国家名称显示
        self.country_name_label = QLabel("美国")
        self.country_name_label.setStyleSheet("color: #27ae60; font-weight: bold; font-size: 13px; padding-left: 10px;")
        
        country_layout.addWidget(country_label)
        country_layout.addWidget(self.country_input)
        country_layout.addWidget(self.country_name_label)
        country_layout.addStretch()
        fixed_layout.addLayout(country_layout)
        
        # 错误提示（红字）
        self.country_error_label = QLabel("")
        self.country_error_label.setStyleSheet("color: #e74c3c; font-size: 11px; padding-left: 120px;")
        self.country_error_label.setVisible(False)
        fixed_layout.addWidget(self.country_error_label)
        
        # 提示信息
        country_hint = QLabel("💡 可以直接输入任意国家代码（2位大写字母），如: US, UK, DE, FR 等")
        country_hint.setStyleSheet("color: #3498db; font-size: 11px; padding-left: 120px;")
        fixed_layout.addWidget(country_hint)
        
        # 姓名（必填）
        name_layout = QHBoxLayout()
        name_label = QLabel("姓名:*")
        name_label.setMinimumWidth(100)
        name_label.setStyleSheet("color: #e74c3c; font-weight: bold;")  # 红色星号表示必填
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("必填！例如: John Smith")
        self.name_input.textChanged.connect(self._on_required_field_changed)
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        fixed_layout.addLayout(name_layout)
        
        # 姓名错误提示
        self.name_error_label = QLabel("")
        self.name_error_label.setStyleSheet("color: #e74c3c; font-size: 11px; padding-left: 120px;")
        self.name_error_label.setVisible(False)
        fixed_layout.addWidget(self.name_error_label)
        
        # 地址（必填）
        address_layout = QHBoxLayout()
        address_label = QLabel("地址:*")
        address_label.setMinimumWidth(100)
        address_label.setStyleSheet("color: #e74c3c; font-weight: bold;")  # 红色星号表示必填
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("必填！例如: 123 Main St")
        self.address_input.textChanged.connect(self._on_required_field_changed)
        address_layout.addWidget(address_label)
        address_layout.addWidget(self.address_input)
        fixed_layout.addLayout(address_layout)
        
        # 地址错误提示
        self.address_error_label = QLabel("")
        self.address_error_label.setStyleSheet("color: #e74c3c; font-size: 11px; padding-left: 120px;")
        self.address_error_label.setVisible(False)
        fixed_layout.addWidget(self.address_error_label)
        
        # 城市（带启用开关）
        city_layout = QHBoxLayout()
        self.city_enable_checkbox = QCheckBox()
        self.city_enable_checkbox.setChecked(True)
        self.city_enable_checkbox.stateChanged.connect(self._on_optional_field_toggle)
        self.city_enable_checkbox.setToolTip("勾选则填写城市，不勾选则跳过")
        city_label = QLabel("城市:")
        city_label.setMinimumWidth(80)
        self.city_input = QLineEdit()
        self.city_input.setPlaceholderText("例如: New York（留空会随机生成美国城市）")
        city_layout.addWidget(self.city_enable_checkbox)
        city_layout.addWidget(city_label)
        city_layout.addWidget(self.city_input)
        fixed_layout.addLayout(city_layout)
        
        # 州/省（带启用开关）
        state_layout = QHBoxLayout()
        self.state_enable_checkbox = QCheckBox()
        self.state_enable_checkbox.setChecked(True)
        self.state_enable_checkbox.stateChanged.connect(self._on_optional_field_toggle)
        self.state_enable_checkbox.setToolTip("勾选则填写州/省，不勾选则跳过")
        state_label = QLabel("州/省:")
        state_label.setMinimumWidth(80)
        self.state_input = QLineEdit()
        self.state_input.setPlaceholderText("例如: NY（留空会随机生成美国州）")
        state_layout.addWidget(self.state_enable_checkbox)
        state_layout.addWidget(state_label)
        state_layout.addWidget(self.state_input)
        fixed_layout.addLayout(state_layout)
        
        # 邮编（带启用开关）
        zip_layout = QHBoxLayout()
        self.zip_enable_checkbox = QCheckBox()
        self.zip_enable_checkbox.setChecked(True)
        self.zip_enable_checkbox.stateChanged.connect(self._on_optional_field_toggle)
        self.zip_enable_checkbox.setToolTip("勾选则填写邮编，不勾选则跳过")
        zip_label = QLabel("邮编:")
        zip_label.setMinimumWidth(80)
        self.zip_input = QLineEdit()
        self.zip_input.setPlaceholderText("例如: 10001（留空会随机生成美国邮编）")
        zip_layout.addWidget(self.zip_enable_checkbox)
        zip_layout.addWidget(zip_label)
        zip_layout.addWidget(self.zip_input)
        fixed_layout.addLayout(zip_layout)
        
        # 可选字段说明
        optional_hint = QLabel("💡 不勾选的字段将在填写时自动跳过")
        optional_hint.setStyleSheet("color: #95a5a6; font-size: 11px; padding-left: 30px;")
        fixed_layout.addWidget(optional_hint)
        
        layout.addWidget(self.fixed_info_widget)
        
        group.setLayout(layout)
        return group
    
    def _create_advanced_config_group(self):
        """创建高级配置组"""
        group = QGroupBox("高级配置")
        layout = QVBoxLayout()
        
        # 失败处理
        failure_label = QLabel("绑卡失败时的处理方式:")
        layout.addWidget(failure_label)
        
        self.failure_group = QButtonGroup(self)
        
        self.skip_radio = QRadioButton("跳过继续（推荐）")
        self.skip_radio.setStyleSheet("padding-left: 10px;")
        self.failure_group.addButton(self.skip_radio, 1)
        layout.addWidget(self.skip_radio)
        
        skip_hint = QLabel("绑卡失败后跳过，账号仍会保存，可手动绑卡")
        skip_hint.setStyleSheet("color: #7f8c8d; font-size: 11px; padding-left: 35px;")
        layout.addWidget(skip_hint)
        
        self.abort_radio = QRadioButton("中止注册")
        self.abort_radio.setStyleSheet("padding-left: 10px;")
        self.failure_group.addButton(self.abort_radio, 2)
        layout.addWidget(self.abort_radio)
        
        abort_hint = QLabel("绑卡失败则中止注册，不保存账号")
        abort_hint.setStyleSheet("color: #7f8c8d; font-size: 11px; padding-left: 35px;")
        layout.addWidget(abort_hint)
        
        group.setLayout(layout)
        return group
    
    def _load_config(self):
        """加载配置文件"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {}
        except Exception as e:
            print(f"加载配置失败: {e}")
            return {}
    
    def _reload_config(self):
        """重新加载配置，恢复到修改前的状态"""
        try:
            # ⚡ 临时标记为正在恢复（避免触发变更信号）
            self._is_reloading = True
            
            # 重新加载配置文件
            self.config = self._load_config()
            
            # 重新加载当前配置到界面
            self._load_current_config()
            
            # ⚡ 恢复完成，清除标记
            self._is_reloading = False
            self.has_unsaved_changes = False
            
            logger.info("✅ 绑卡配置已恢复到修改前的状态")
        except Exception as e:
            self._is_reloading = False
            logger.error(f"恢复配置失败: {e}")
    
    def _load_current_config(self):
        """加载当前配置到界面"""
        payment_config = self.config.get('payment_binding', {})
        
        # 基础配置
        self.enable_checkbox.setChecked(payment_config.get('enabled', False))
        self.auto_fill_checkbox.setChecked(payment_config.get('auto_fill', True))
        
        # 卡号模式（默认导入模式）
        card_mode = payment_config.get('card_mode', 'import')
        if card_mode == 'auto_generate':
            self.auto_gen_radio.setChecked(True)
        else:
            self.import_card_radio.setChecked(True)
        
        # 卡头配置
        self.bin_input.setText(payment_config.get('card_bin_prefix', '5224900'))
        
        # 导入的卡号（持久化读取）
        imported_cards = payment_config.get('imported_cards', [])
        if imported_cards:
            card_lines = []
            for card in imported_cards:
                line = f"{card['number']}|{card['month']}|{card['year']}|{card['cvv']}"
                card_lines.append(line)
            self.card_list_input.setPlainText('\n'.join(card_lines))
            self.card_count_label.setText(f"已导入: {len(imported_cards)} 组")
            logger.info(f"✅ 从配置加载了 {len(imported_cards)} 组卡号")
        else:
            logger.debug("配置中没有导入的卡号")
        
        # 固定信息配置
        fixed_info = payment_config.get('fixed_info', {})
        self.fixed_info_checkbox.setChecked(fixed_info.get('enabled', False))
        
        # 设置国家代码（可编辑下拉框直接设置文本）
        country_code = fixed_info.get('country', 'US')
        self.country_input.setText(country_code)
        
        self.name_input.setText(fixed_info.get('name', ''))
        self.address_input.setText(fixed_info.get('address', ''))
        self.city_input.setText(fixed_info.get('city', ''))
        self.state_input.setText(fixed_info.get('state', ''))
        self.zip_input.setText(fixed_info.get('zip', ''))
        
        # 加载可选字段的启用状态（默认都启用）
        self.city_enable_checkbox.setChecked(fixed_info.get('enable_city', True))
        self.state_enable_checkbox.setChecked(fixed_info.get('enable_state', True))
        self.zip_enable_checkbox.setChecked(fixed_info.get('enable_zip', True))
        
        # 触发开关状态更新
        self._on_optional_field_toggle()
        
        # 高级配置
        skip_on_error = payment_config.get('skip_on_error', True)
        if skip_on_error:
            self.skip_radio.setChecked(True)
        else:
            self.abort_radio.setChecked(True)
        
        # 初始状态
        self._check_unlock_status()  # 检查解锁状态
        self._on_enable_changed()
        self._on_card_mode_changed()
        self._on_fixed_info_changed()
    
    def _check_unlock_status(self):
        """检查自动生成功能的解锁状态（从配置文件读取）"""
        # ⭐ 从配置文件读取解锁状态（持久化）
        payment_config = self.config.get('payment_binding', {})
        self.is_auto_gen_unlocked = payment_config.get('auto_gen_unlocked', False)
        
        if self.is_auto_gen_unlocked:
            logger.info("✅ 自动生成功能已解锁（从配置加载）")
        else:
            logger.debug("🔒 自动生成功能已锁定")
        
        self._update_auto_gen_lock_state()
    
    def _update_auto_gen_lock_state(self):
        """更新自动生成区域的锁定状态"""
        if self.is_auto_gen_unlocked:
            # 已解锁
            self.lock_icon.setText("🔓")
            self.lock_icon.setStyleSheet("font-size: 16px; color: #27ae60;")
            self.lock_icon.setToolTip("已解锁")
            self.unlock_widget.setVisible(False)
            self.auto_gen_widget.setEnabled(True)
        else:
            # 锁定
            self.lock_icon.setText("🔒")
            self.lock_icon.setStyleSheet("font-size: 16px; color: #e74c3c;")
            self.lock_icon.setToolTip("需要解锁码")
            self.unlock_widget.setVisible(True)
            self.auto_gen_widget.setEnabled(False)
    
    def _verify_unlock_code(self, code: str) -> bool:
        """
        验证解锁码（加密验证）
        
        Args:
            code: 用户输入的解锁码
            
        Returns:
            bool: 是否有效
        """
        import hashlib
        
        # 移除解锁码中的分隔符和空格，转大写
        clean_code = code.replace('-', '').replace(' ', '').upper()
        
        # 生成解锁码的哈希值（多层加密）
        secret_key = "ZZX-PAYMENT-UNLOCK-2025"  # 密钥
        salt = "CARD-BIN-GENERATOR"              # 盐值
        
        # 第一层：基础哈希
        base_hash = hashlib.sha256(f"{secret_key}-{salt}".encode()).hexdigest()
        
        # 第二层：MD5混合
        mixed_hash = hashlib.md5(base_hash.encode()).hexdigest()
        
        # 第三层：SHA256最终加密
        final_hash = hashlib.sha256(f"{mixed_hash}-{secret_key}".encode()).hexdigest()
        
        # 取前15位作为解锁码（ZZX-CURSOR-2025 转换后的值）
        valid_code = final_hash[:15].upper()
        
        # 验证（也支持原始格式）
        return clean_code == valid_code or clean_code == "ZZXCURSOR2025"
    
    def _on_unlock(self):
        """验证解锁码"""
        try:
            # 获取输入的解锁码
            input_code = self.unlock_input.text().strip()
            
            if not input_code:
                QMessageBox.warning(self, "提示", "请输入解锁码")
                return
            
            # 验证解锁码
            if self._verify_unlock_code(input_code):
                # 解锁成功
                self.is_auto_gen_unlocked = True
                self._update_auto_gen_lock_state()
                
                # ⭐ 保存解锁状态到配置文件（持久化）
                try:
                    # ⭐ 重新加载最新配置（避免覆盖其他面板的修改）
                    latest_config = self._load_config()
                    
                    if 'payment_binding' not in latest_config:
                        latest_config['payment_binding'] = {}
                    
                    latest_config['payment_binding']['auto_gen_unlocked'] = True
                    
                    with open(self.config_file, 'w', encoding='utf-8') as f:
                        json.dump(latest_config, f, indent=2, ensure_ascii=False)
                    
                    # ⭐ 更新本地配置
                    self.config = latest_config
                    
                    logger.info("✅ 解锁状态已保存到配置文件（永久有效）")
                except Exception as e:
                    logger.error(f"保存解锁状态失败: {e}")
                
                # ⭐ 使用 Toast 通知
                from gui.widgets.toast_notification import show_toast
                main_window = self.window()
                show_toast(main_window, "🔓 解锁成功！", duration=2000)
                
                # 清空输入框
                self.unlock_input.clear()
            else:
                # 解锁失败
                QMessageBox.warning(
                    self,
                    "解锁失败",
                    "❌ 解锁码不正确！\n\n"
                    "请检查输入的解锁码是否正确。"
                )
                
                # 清空输入框
                self.unlock_input.clear()
                self.unlock_input.setFocus()
        
        except Exception as e:
            QMessageBox.critical(self, "错误", f"验证解锁码时出错：\n{e}")
    
    def _on_enable_changed(self):
        """启用状态改变"""
        enabled = self.enable_checkbox.isChecked()
        
        self.auto_fill_checkbox.setEnabled(enabled)
        self.auto_gen_radio.setEnabled(enabled)
        self.import_card_radio.setEnabled(enabled)
        self.fixed_info_checkbox.setEnabled(enabled)
        self.skip_radio.setEnabled(enabled)
        self.abort_radio.setEnabled(enabled)
        self.test_btn.setEnabled(enabled)
        
        if enabled:
            self._on_card_mode_changed()
            self._on_fixed_info_changed()
        else:
            self.auto_gen_widget.setEnabled(False)
            self.import_card_widget.setEnabled(False)
            self.fixed_info_widget.setEnabled(False)
    
    def _connect_change_signals(self):
        """连接所有变更信号，用于检测未保存的修改"""
        # 注意：此方法在 _load_current_config 之后调用，避免初始加载触发变更
        
        # 基础配置
        self.enable_checkbox.stateChanged.connect(self._mark_as_changed)
        self.auto_fill_checkbox.stateChanged.connect(self._mark_as_changed)
        
        # 卡号模式
        self.card_mode_group.buttonClicked.connect(self._mark_as_changed)
        
        # 卡头配置
        self.bin_input.textChanged.connect(self._mark_as_changed)
        
        # 导入卡号
        self.card_list_input.textChanged.connect(self._mark_as_changed)
        
        # 固定信息
        self.fixed_info_checkbox.stateChanged.connect(self._mark_as_changed)
        self.country_input.textChanged.connect(self._mark_as_changed)
        self.name_input.textChanged.connect(self._mark_as_changed)
        self.address_input.textChanged.connect(self._mark_as_changed)
        self.city_input.textChanged.connect(self._mark_as_changed)
        self.state_input.textChanged.connect(self._mark_as_changed)
        self.zip_input.textChanged.connect(self._mark_as_changed)
        # 可选字段开关
        self.city_enable_checkbox.stateChanged.connect(self._mark_as_changed)
        self.state_enable_checkbox.stateChanged.connect(self._mark_as_changed)
        self.zip_enable_checkbox.stateChanged.connect(self._mark_as_changed)
        
        # 高级配置
        self.failure_group.buttonClicked.connect(self._mark_as_changed)
        
        # 初始化后重置标记（避免初始加载被标记为已修改）
        self.has_unsaved_changes = False
    
    def _mark_as_changed(self):
        """标记为有未保存的修改"""
        # ⚡ 如果正在恢复配置，不标记为已修改
        if hasattr(self, '_is_reloading') and self._is_reloading:
            return
        self.has_unsaved_changes = True
    
    def check_unsaved_changes(self) -> bool:
        """
        检查是否有未保存的修改
        
        Returns:
            bool: True 表示可以继续，False 表示用户取消
        """
        if self.has_unsaved_changes:
            # ⭐ 使用新的动图警告对话框
            from gui.dialogs.unsaved_warning_dialog import UnsavedWarningDialog
            
            reply = UnsavedWarningDialog.ask_save(self)
            
            if reply == 1:  # 是
                # 保存配置
                save_success = self._on_save()
                return save_success  # 返回保存结果
            elif reply == 2:  # 否
                # 放弃修改
                self.has_unsaved_changes = False
                return True
            else:  # 0 或其他（取消）
                # 取消，留在当前页面
                return False
        
        return True
    
    def _on_card_mode_changed(self):
        """卡号模式改变"""
        auto_gen_mode = self.auto_gen_radio.isChecked()
        
        # 如果选择自动生成，根据解锁状态显示相应界面
        if auto_gen_mode:
            # ⭐ 解锁状态会持久保持，不会因为切换模式而重置
            if self.is_auto_gen_unlocked:
                # 已解锁：隐藏解锁区域，显示配置区域
                self.unlock_widget.setVisible(False)
                self.auto_gen_widget.setEnabled(True)
            else:
                # 未解锁：显示解锁区域，禁用配置区域
                self.unlock_widget.setVisible(True)
                self.auto_gen_widget.setEnabled(False)
        else:
            # 导入模式：隐藏解锁区域
            # ⭐ 注意：不重置解锁状态，只是隐藏界面
            self.unlock_widget.setVisible(False)
        
        # 控制导入区域的启用/禁用
        self.import_card_widget.setEnabled(not auto_gen_mode)
    
    def _on_fixed_info_changed(self):
        """固定信息状态改变"""
        enabled = self.fixed_info_checkbox.isChecked()
        self.fixed_info_widget.setEnabled(enabled)
        
        # 勾选时触发必填字段验证
        if enabled:
            self._on_required_field_changed()
    
    def _on_country_code_changed(self):
        """国家代码输入改变时的实时验证"""
        country_code = self.country_input.text().upper().strip()
        
        # 自动转大写
        if self.country_input.text() != country_code:
            self.country_input.setText(country_code)
            return
        
        if not country_code:
            # 空值：显示默认
            self.country_name_label.setText("美国")
            self.country_name_label.setStyleSheet("color: #27ae60; font-weight: bold; font-size: 13px; padding-left: 10px;")
            self.country_error_label.setVisible(False)
            return
        
        # 验证国家代码
        if is_valid_country_code(country_code):
            # 有效：显示绿色国家名称
            country_name = get_country_name(country_code)
            self.country_name_label.setText(country_name)
            self.country_name_label.setStyleSheet("color: #27ae60; font-weight: bold; font-size: 13px; padding-left: 10px;")
            self.country_error_label.setVisible(False)
        else:
            # 无效：显示红色错误
            self.country_name_label.setText("❌")
            self.country_name_label.setStyleSheet("color: #e74c3c; font-weight: bold; font-size: 13px; padding-left: 10px;")
            self.country_error_label.setText(f"⚠️ 未收录此国家代码或代码有误，请上网查找国家ISO代码")
            self.country_error_label.setVisible(True)
        
        # 标记为已修改
        self._mark_as_changed()
    
    def _on_required_field_changed(self):
        """必填字段改变时的实时验证"""
        # 只在启用固定信息时才验证
        if not self.fixed_info_checkbox.isChecked():
            self.name_error_label.setVisible(False)
            self.address_error_label.setVisible(False)
            return
        
        # 验证姓名
        name = self.name_input.text().strip()
        if not name:
            self.name_error_label.setText("❌ 姓名不能为空！")
            self.name_error_label.setVisible(True)
            self.name_input.setStyleSheet("border: 2px solid #e74c3c;")
        else:
            self.name_error_label.setVisible(False)
            self.name_input.setStyleSheet("")
        
        # 验证地址
        address = self.address_input.text().strip()
        if not address:
            self.address_error_label.setText("❌ 地址不能为空！")
            self.address_error_label.setVisible(True)
            self.address_input.setStyleSheet("border: 2px solid #e74c3c;")
        else:
            self.address_error_label.setVisible(False)
            self.address_input.setStyleSheet("")
        
        # 标记为已修改
        self._mark_as_changed()
    
    def _on_optional_field_toggle(self):
        """可选字段开关状态改变"""
        # 控制输入框的启用/禁用
        self.city_input.setEnabled(self.city_enable_checkbox.isChecked())
        self.state_input.setEnabled(self.state_enable_checkbox.isChecked())
        self.zip_input.setEnabled(self.zip_enable_checkbox.isChecked())
        
        # 标记为已修改
        self._mark_as_changed()
    
    def _on_get_virtual_card(self):
        """获取虚拟卡按钮点击"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
        from PyQt6.QtGui import QPixmap, QMovie
        from PyQt6.QtCore import Qt
        from pathlib import Path
        
        # 创建弹窗
        dialog = QDialog(self)
        dialog.setWindowTitle("获取虚拟卡")
        dialog.setMinimumSize(700, 600)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(20)
        
        # 标题
        title = QLabel("💳 获取虚拟卡（小程序）")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #9C27B0;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # 说明文字
        hint = QLabel("如果需要虚拟卡，请扫描下方二维码进入小程序获取")
        hint.setStyleSheet("font-size: 13px; color: #666;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
        
        # 重要提示
        warning = QLabel("⚠️ 重要：一卡只能绑定一个账号，绑定成功后自动删除该卡号")
        warning.setStyleSheet("font-size: 12px; color: #e74c3c; font-weight: bold;")
        warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(warning)
        
        # 二维码和GIF横向布局
        content_layout = QHBoxLayout()
        
        # 左侧：二维码
        qr_container = QVBoxLayout()
        qr_label_title = QLabel("扫码进入小程序")
        qr_label_title.setStyleSheet("font-size: 12px; font-weight: bold;")
        qr_label_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_container.addWidget(qr_label_title)
        
        qr_label = QLabel()
        qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_path = get_gui_resource("wechat_qr.jpg")
        if qr_path.exists():
            pixmap = QPixmap(str(qr_path))
            scaled_pixmap = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            qr_label.setPixmap(scaled_pixmap)
        else:
            qr_label.setText("二维码未找到")
        qr_label.setStyleSheet("border: 2px solid #ddd; border-radius: 8px; padding: 10px; background: white;")
        qr_container.addWidget(qr_label)
        content_layout.addLayout(qr_container)
        
        # 右侧：使用教程GIF
        gif_container = QVBoxLayout()
        gif_label_title = QLabel("使用教程")
        gif_label_title.setStyleSheet("font-size: 12px; font-weight: bold;")
        gif_label_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        gif_container.addWidget(gif_label_title)
        
        gif_label = QLabel()
        gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        gif_path = get_gui_resource("virtual_card_guide.gif")
        if gif_path.exists():
            movie = QMovie(str(gif_path))
            movie.setScaledSize(movie.scaledSize().scaled(350, 350, Qt.AspectRatioMode.KeepAspectRatio))
            gif_label.setMovie(movie)
            movie.start()
        else:
            gif_label.setText("教程GIF未找到")
        gif_label.setStyleSheet("border: 2px solid #ddd; border-radius: 8px; padding: 10px; background: white;")
        gif_container.addWidget(gif_label)
        content_layout.addLayout(gif_container)
        
        layout.addLayout(content_layout)
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                padding: 8px 30px;
                border-radius: 5px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        dialog.exec()
    
    def _on_card_pool_updated(self, remaining_count: int):
        """卡池更新时的回调（立即刷新）"""
        try:
            self.card_count_label.setText(f"已导入: {remaining_count} 组")
            logger.info(f"✅ 卡池已更新，剩余: {remaining_count} 组")
        except Exception as e:
            logger.error(f"更新卡号显示失败: {e}")
    
    def _refresh_card_count(self):
        """刷新卡号数量显示（定期调用）"""
        try:
            # 重新加载配置
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    fresh_config = json.load(f)
                
                # 获取最新的卡号列表
                imported_cards = fresh_config.get('payment_binding', {}).get('imported_cards', [])
                
                # 更新显示（只更新数量，不改变输入框内容）
                current_count_text = self.card_count_label.text()
                new_count_text = f"已导入: {len(imported_cards)} 组"
                
                if current_count_text != new_count_text:
                    self.card_count_label.setText(new_count_text)
                    logger.debug(f"🔄 卡号数量已更新: {len(imported_cards)} 组")
        except Exception as e:
            logger.debug(f"刷新卡号数量失败: {e}")
    
    def _on_validate_cards(self):
        """验证导入的卡号格式"""
        try:
            text = self.card_list_input.toPlainText().strip()
            if not text:
                QMessageBox.warning(self, "提示", "请先输入卡号列表")
                return
            
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            if len(lines) > 500:
                QMessageBox.warning(
                    self,
                    "超出限制",
                    f"导入的卡号数量超过限制！\n\n"
                    f"当前: {len(lines)} 组\n"
                    f"限制: 500 组\n\n"
                    f"请删除多余的 {len(lines) - 500} 组"
                )
                return
            
            valid_cards = []
            invalid_lines = []
            
            for i, line in enumerate(lines, 1):
                parts = line.split('|')
                
                # 检查格式
                if len(parts) != 4:
                    invalid_lines.append(f"第{i}行: 格式错误（应为4个部分）")
                    continue
                
                card_num, month, year, cvv = parts
                
                # 验证卡号（16位数字）
                if not card_num.isdigit() or len(card_num) != 16:
                    invalid_lines.append(f"第{i}行: 卡号必须是16位数字")
                    continue
                
                # 验证月份（01-12）
                if not month.isdigit() or not (1 <= int(month) <= 12):
                    invalid_lines.append(f"第{i}行: 月份必须是01-12")
                    continue
                
                # 验证年份（4位数字）
                if not year.isdigit() or len(year) != 4:
                    invalid_lines.append(f"第{i}行: 年份必须是4位数字（如2025）")
                    continue
                
                # 验证CVV（3位数字）
                if not cvv.isdigit() or len(cvv) != 3:
                    invalid_lines.append(f"第{i}行: CVV必须是3位数字")
                    continue
                
                valid_cards.append({
                    'number': card_num,
                    'month': month,
                    'year': year,
                    'cvv': cvv
                })
            
            # 显示结果
            if invalid_lines:
                error_msg = "\n".join(invalid_lines[:10])  # 只显示前10个错误
                if len(invalid_lines) > 10:
                    error_msg += f"\n... 还有 {len(invalid_lines) - 10} 个错误"
                
                QMessageBox.warning(
                    self,
                    "格式验证失败",
                    f"发现 {len(invalid_lines)} 个格式错误：\n\n{error_msg}\n\n"
                    f"有效卡号: {len(valid_cards)} 组"
                )
            else:
                QMessageBox.information(
                    self,
                    "验证成功",
                    f"✅ 所有卡号格式正确！\n\n"
                    f"有效卡号: {len(valid_cards)} 组"
                )
            
            # 更新统计
            self.card_count_label.setText(f"已导入: {len(valid_cards)} 组")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"验证失败：\n{e}")
    
    def _on_save(self) -> bool:
        """
        保存配置
        
        Returns:
            bool: 保存是否成功
        """
        try:
            # ⭐ 验证必填字段（启用固定信息时）
            if self.fixed_info_checkbox.isChecked():
                name = self.name_input.text().strip()
                address = self.address_input.text().strip()
                
                errors = []
                if not name:
                    errors.append("• 姓名不能为空")
                    self.name_error_label.setText("❌ 姓名不能为空！")
                    self.name_error_label.setVisible(True)
                    self.name_input.setStyleSheet("border: 2px solid #e74c3c;")
                
                if not address:
                    errors.append("• 地址不能为空")
                    self.address_error_label.setText("❌ 地址不能为空！")
                    self.address_error_label.setVisible(True)
                    self.address_input.setStyleSheet("border: 2px solid #e74c3c;")
                
                if errors:
                    QMessageBox.warning(
                        self,
                        "保存失败",
                        "❌ 启用固定信息时，姓名和地址为必填项！\n\n"
                        + "\n".join(errors) +
                        "\n\n请填写完整后再保存。"
                    )
                    return False
            
            # 读取国家代码
            country_code = self.country_input.text().strip().upper()
            
            # 读取卡号模式和数据
            card_mode = 'auto_generate' if self.auto_gen_radio.isChecked() else 'import'
            
            # 如果是自动生成模式，检查是否已解锁
            if card_mode == 'auto_generate' and not self.is_auto_gen_unlocked:
                QMessageBox.warning(
                    self,
                    "提示",
                    "⚠️ 自动生成卡号功能已锁定！\n\n"
                    "请先输入解锁码解锁，或切换到'导入卡号'模式。"
                )
                return False
            
            # 如果是导入模式，验证并解析卡号列表
            imported_cards = []
            if card_mode == 'import':
                text = self.card_list_input.toPlainText().strip()
                if text:
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    
                    # 验证格式
                    validation_errors = []
                    for i, line in enumerate(lines[:500], 1):
                        parts = line.split('|')
                        
                        # 检查格式
                        if len(parts) != 4:
                            validation_errors.append(f"第{i}行: 格式错误（应为：卡号|月份|年份|CVV）")
                            continue
                        
                        card_num, month, year, cvv = parts
                        
                        # 验证卡号（16位数字）
                        if not card_num.isdigit() or len(card_num) != 16:
                            validation_errors.append(f"第{i}行: 卡号必须是16位数字")
                            continue
                        
                        # 验证月份（01-12）
                        if not month.isdigit() or not (1 <= int(month) <= 12):
                            validation_errors.append(f"第{i}行: 月份必须是01-12")
                            continue
                        
                        # 验证年份（4位数字）
                        if not year.isdigit() or len(year) != 4:
                            validation_errors.append(f"第{i}行: 年份必须是4位数字（如2025）")
                            continue
                        
                        # 验证CVV（3位数字）
                        if not cvv.isdigit() or len(cvv) != 3:
                            validation_errors.append(f"第{i}行: CVV必须是3位数字")
                            continue
                        
                        # 格式正确，添加到列表
                        imported_cards.append({
                            'number': card_num,
                            'month': month,
                            'year': year,
                            'cvv': cvv
                        })
                    
                    # 如果有格式错误，显示并终止保存
                    if validation_errors:
                        error_msg = "\n".join(validation_errors[:10])
                        if len(validation_errors) > 10:
                            error_msg += f"\n... 还有 {len(validation_errors) - 10} 个错误"
                        
                        QMessageBox.critical(
                            self,
                            "格式错误",
                            f"❌ 保存失败！发现 {len(validation_errors)} 个格式错误：\n\n"
                            f"{error_msg}\n\n"
                            f"请修正错误后再保存。\n"
                            f"有效卡号: {len(imported_cards)} 组"
                        )
                        return False  # 终止保存
            
            # 如果启用了自动绑卡，检查是否可以生成卡
            if self.enable_checkbox.isChecked():
                if card_mode == 'auto_generate':
                    # 左边：必须解锁 + BIN卡头至少6位
                    if not self.is_auto_gen_unlocked:
                        QMessageBox.critical(
                            self,
                            "保存失败",
                            "❌ 自动生成卡号功能未解锁！\n\n"
                            "请先输入解锁码解锁，或切换到'导入卡号'模式。"
                        )
                        return False
                    
                    bin_prefix = self.bin_input.text().strip()
                    if not bin_prefix:
                        QMessageBox.critical(
                            self,
                            "保存失败",
                            "❌ BIN 卡头前缀不能为空！\n\n"
                            "请输入有效的卡头前缀（如：5224900）"
                        )
                        return False
                    
                    if not bin_prefix.isdigit():
                        QMessageBox.critical(
                            self,
                            "保存失败",
                            "❌ BIN 卡头前缀必须是数字！\n\n"
                            f"当前输入: {bin_prefix}\n"
                            f"正确示例: 5224900"
                        )
                        return False
                    
                    if len(bin_prefix) < 6:
                        QMessageBox.critical(
                            self,
                            "保存失败",
                            "❌ BIN 卡头前缀至少需要6位数字！\n\n"
                            f"当前输入: {bin_prefix} ({len(bin_prefix)}位)\n"
                            f"正确示例: 5224900 (7位)"
                        )
                        return False
                
                elif card_mode == 'import':
                    # 右边：必须有导入的卡号
                    if len(imported_cards) == 0:
                        QMessageBox.critical(
                            self,
                            "保存失败",
                            "❌ 未导入任何卡号！\n\n"
                            "启用自动绑卡时，必须导入至少一组卡号。\n\n"
                            "请导入卡号，或禁用自动绑卡功能。"
                        )
                        return False
            
            # 读取配置
            payment_config = {
                'enabled': self.enable_checkbox.isChecked(),
                'auto_fill': self.auto_fill_checkbox.isChecked(),
                'skip_on_error': self.skip_radio.isChecked(),
                'card_mode': card_mode,
                'card_bin_prefix': self.bin_input.text().strip() or '5224900',
                'imported_cards': imported_cards,
                'fixed_info': {
                    'enabled': self.fixed_info_checkbox.isChecked(),
                    'country': country_code or 'US',
                    'name': self.name_input.text().strip(),
                    'address': self.address_input.text().strip(),
                    'city': self.city_input.text().strip(),
                    'state': self.state_input.text().strip(),
                    'zip': self.zip_input.text().strip(),
                    # 可选字段的启用状态
                    'enable_city': self.city_enable_checkbox.isChecked(),
                    'enable_state': self.state_enable_checkbox.isChecked(),
                    'enable_zip': self.zip_enable_checkbox.isChecked()
                }
            }
            
            # ⭐ 重新加载最新配置（避免覆盖其他面板的修改）
            latest_config = self._load_config()
            
            # 更新绑卡配置部分
            if 'payment_binding' not in latest_config:
                latest_config['payment_binding'] = {}
            
            latest_config['payment_binding'].update(payment_config)
            
            # 保存到文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(latest_config, f, indent=2, ensure_ascii=False)
            
            # ⭐ 更新本地配置为最新版本
            self.config = latest_config
            
            # ⭐ 使用 Toast 通知显示保存成功
            from gui.widgets.toast_notification import show_toast
            
            # 获取主窗口
            main_window = self.window()
            show_toast(main_window, "✅ 绑卡配置已保存！", duration=2000)
            
            # 发送配置变更信号
            self.config_changed.emit()
            
            # 重置未保存标记
            self.has_unsaved_changes = False
            
            return True  # 保存成功
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "保存失败",
                f"保存配置时出错：\n{e}"
            )
            return False  # 保存失败
    
    def _on_test(self):
        """测试绑卡"""
        if not self.enable_checkbox.isChecked():
            QMessageBox.warning(
                self,
                "提示",
                "请先启用自动绑卡功能"
            )
            return
        
        reply = QMessageBox.question(
            self,
            "测试绑卡",
            "即将启动浏览器进行绑卡测试。\n\n"
            "测试前请确保：\n"
            "  1. 已注册 Cursor 账号\n"
            "  2. 浏览器中有有效的登录 Cookie\n"
            "  3. 账号未绑定过支付方式\n\n"
            "是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            import subprocess
            import sys
            
            subprocess.Popen([sys.executable, "test_payment_binding.py"])
            
            QMessageBox.information(
                self,
                "测试启动",
                "测试程序已启动！\n\n"
                "请在新窗口中查看测试过程。"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "启动失败",
                f"无法启动测试程序：\n{e}\n\n"
                f"请手动运行：python test_payment_binding.py"
            )

