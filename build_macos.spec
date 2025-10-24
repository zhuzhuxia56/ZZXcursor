# -*- mode: python ; coding: utf-8 -*-

"""
PyInstaller 打包配置文件 - macOS 版本
用于将 Zzx Cursor Auto Manager 打包成 macOS 应用程序
"""

import sys
from pathlib import Path

block_cipher = None

# 项目根目录
ROOT_DIR = Path('.').resolve()

# 收集所有需要打包的数据文件
from PyInstaller.utils.hooks import collect_all, collect_submodules

# 收集所有第三方库的完整内容
requests_datas, requests_binaries, requests_hiddenimports = collect_all('requests')
urllib3_datas, urllib3_binaries, urllib3_hiddenimports = collect_all('urllib3')
drissionpage_datas, drissionpage_binaries, drissionpage_hiddenimports = collect_all('DrissionPage')
jwt_datas, jwt_binaries, jwt_hiddenimports = collect_all('jwt')
loguru_datas, loguru_binaries, loguru_hiddenimports = collect_all('loguru')

datas = [
    # GUI资源文件（图标、样式表等）
    ('gui/resources', 'gui/resources'),
    # Turnstile补丁扩展
    ('core/turnstilePatch', 'core/turnstilePatch'),
]

# 添加所有第三方库的数据文件
datas += requests_datas
datas += urllib3_datas
datas += drissionpage_datas
datas += jwt_datas
datas += loguru_datas

# 添加所有二进制文件
binaries = []
binaries += requests_binaries
binaries += urllib3_binaries
binaries += drissionpage_binaries
binaries += jwt_binaries
binaries += loguru_binaries

# 收集所有隐藏导入（移除 Windows 特定的）
hiddenimports = [
    # PyQt6 模块
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.QtSvg',      # SVG 图标支持
    'PyQt6.sip',        # PyQt6 核心绑定
    
    # DrissionPage 及其依赖
    'DrissionPage',
    'colorama',
    
    # 加密和网络
    'cryptography',
    'cryptography.fernet',
    'cryptography.hazmat',
    'cryptography.hazmat.primitives',
    'cryptography.hazmat.backends',
    
    # JWT
    'jwt',
    'pyjwt',
    
    # HTTP请求
    'requests',
    'requests.adapters',
    'requests.auth',
    'requests.cookies',
    'requests.exceptions',
    'requests.models',
    'requests.sessions',
    'requests.structures',
    'requests.utils',
    'urllib3',
    'urllib3.util',
    'urllib3.util.retry',
    'urllib3.connection',
    'urllib3.exceptions',
    
    # 日期时间处理
    'dateutil',
    'dateutil.parser',
    
    # 日志
    'loguru',
    
    # macOS 特定
    'fcntl',            # 文件锁
    
    # Python 标准库
    'sqlite3',
    'json',
    'base64',
    'hashlib',
    'subprocess',
    'traceback',
    'contextlib',
]

a = Analysis(
    ['main.py'],
    pathex=[str(ROOT_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=(hiddenimports + requests_hiddenimports + urllib3_hiddenimports + 
                   drissionpage_hiddenimports + jwt_hiddenimports + loguru_hiddenimports),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的模块
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL.ImageTk',
        'tkinter',
        '_tkinter',
        'unittest',
        'test',
        'tests',
        'pydoc',
        'doctest',
        # macOS 不需要 Windows 特定模块
        'win32api',
        'win32con',
        'win32file',
        'win32event',
        'pywintypes',
        'msvcrt',
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Zzx Cursor Auto Manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Zzx Cursor Auto Manager',
)

app = BUNDLE(
    coll,
    name='Zzx Cursor Auto Manager.app',
    icon='ZZX.icns',  # macOS 应用图标（需要先创建此文件）
    bundle_identifier='com.zzx.cursor-auto',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False,
        'CFBundleDocumentTypes': [],
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.13.0',  # macOS 10.13+
        'NSRequiresAquaSystemAppearance': False,
    },
)

