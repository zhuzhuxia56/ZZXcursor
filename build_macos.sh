#!/bin/bash
# macOS 打包脚本

echo "========================================"
echo "  Zzx Cursor Auto - macOS 打包工具"
echo "========================================"
echo ""

cd "$(dirname "$0")"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python3"
    echo ""
    echo "请先安装 Python:"
    echo "  brew install python@3.13"
    echo ""
    exit 1
fi

echo "✅ 找到 Python: $(python3 --version)"
echo ""

# 检查 PyInstaller
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo "❌ 未找到 PyInstaller"
    echo ""
    echo "正在安装..."
    pip3 install pyinstaller
    echo ""
fi

echo "✅ PyInstaller 已就绪"
echo ""

# 安装依赖
echo "正在检查依赖..."
pip3 install -r requirements_macos.txt --quiet
echo "✅ 依赖已安装"
echo ""

# 打包
echo "开始打包..."
echo ""
pyinstaller build_macos.spec --clean

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "  打包成功!"
    echo "========================================"
    echo ""
    echo "应用程序位置:"
    echo "  $(pwd)/dist/Zzx Cursor Auto Manager.app"
    echo ""
    echo "您现在可以:"
    echo "  1. 测试: open \"dist/Zzx Cursor Auto Manager.app\""
    echo "  2. 移动到 /Applications 文件夹"
    echo "  3. 制作 DMG 安装包（可选）"
    echo ""
else
    echo ""
    echo "❌ 打包失败!"
    echo "请检查错误信息"
    echo ""
    exit 1
fi

