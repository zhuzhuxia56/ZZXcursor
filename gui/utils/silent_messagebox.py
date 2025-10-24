#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
静音消息框
禁用系统提示音的 QMessageBox 包装器
"""

from PyQt6.QtWidgets import QMessageBox, QApplication
from PyQt6.QtCore import Qt


class SilentMessageBox(QMessageBox):
    """静音的消息框（无系统提示音）"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 禁用系统声音
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
    
    @staticmethod
    def information(parent, title, text, buttons=QMessageBox.StandardButton.Ok):
        """静音的信息提示框"""
        msg = SilentMessageBox(parent)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setStandardButtons(buttons)
        # 完全禁用系统声音
        QApplication.instance().beep = lambda: None
        return msg.exec()
    
    @staticmethod
    def warning(parent, title, text, buttons=QMessageBox.StandardButton.Ok):
        """静音的警告框"""
        msg = SilentMessageBox(parent)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setStandardButtons(buttons)
        QApplication.instance().beep = lambda: None
        return msg.exec()
    
    @staticmethod
    def critical(parent, title, text, buttons=QMessageBox.StandardButton.Ok):
        """静音的错误框"""
        msg = SilentMessageBox(parent)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setStandardButtons(buttons)
        QApplication.instance().beep = lambda: None
        return msg.exec()
    
    @staticmethod
    def question(parent, title, text, buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No):
        """静音的询问框"""
        msg = SilentMessageBox(parent)
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setStandardButtons(buttons)
        QApplication.instance().beep = lambda: None
        return msg.exec()


def disable_message_box_sound():
    """全局禁用 QMessageBox 的系统声音"""
    # 重写 QApplication 的 beep 方法
    QApplication.beep = lambda: None

