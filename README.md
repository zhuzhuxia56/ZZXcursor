# Zzx Cursor Auto Manager

<div align="center">

![Logo](gui/resources/images/ZZX.png)

**Cursor AI 账号自动化管理工具**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-lightgrey.svg)]()

[功能特点](#功能特点) • [快速开始](#快速开始) • [使用指南](#使用指南) • [开发](#开发) • [许可证](#许可证)

</div>

---

## 🌟 功能特点

### 核心功能

- 🤖 **自动注册** - 全自动注册 Cursor 账号
  - 邮箱验证自动化
  - Turnstile 验证码处理
  - 深度登录获取 Token
  
- 💳 **自动绑卡** - 自动绑定支付方式开启 Pro 试用
  - 虚拟卡生成/导入
  - Stripe 表单自动填写
  - 支持批量绑卡

- 🔄 **账号切换** - 一键切换 Cursor 账号
  - 自动更新配置文件
  - 机器码智能管理
  - 自动重启 Cursor

- 📊 **账号管理** - 完善的账号管理功能
  - 查看使用量和剩余天数
  - 批量刷新账号信息
  - 导入/导出账号数据

### 界面特性

- 🎨 **现代化 UI** - 精美的用户界面
  - 深色/浅色主题切换
  - 流畅的动画效果
  - 响应式布局

- 🔒 **数据安全** - 加密存储
  - 本地 SQLite 数据库
  - Token 加密保存
  - 机器码绑定

---

## 🚀 快速开始

### 下载

访问 [Releases](https://github.com/zhuzhuxia56/ZZXcursor/releases) 下载最新版本：

- **Windows**: `Zzx-Cursor-Auto-Setup.exe` （安装包）或 `.zip`（便携版）
- **macOS**: `Zzx-Cursor-Auto-macOS.dmg` （安装镜像）

### Windows 安装

1. 下载 `Zzx-Cursor-Auto-Setup.exe`
2. 双击运行（可能需要点击"仍要运行"）
3. 按照安装向导完成安装

> ⚠️ **Windows Defender 警告**：本软件是开源项目，未购买代码签名证书（约 $400/年）。软件完全安全，点击"更多信息" → "仍要运行"即可。

### macOS 安装

1. 下载 `Zzx-Cursor-Auto-macOS.dmg`
2. 打开 DMG 文件
3. 拖拽应用到 Applications 文件夹
4. 首次运行可能需要：`xattr -cr "/Applications/Zzx Cursor Auto Manager.app"`

---

## 📖 使用指南

### 1. 配置邮箱

1. 打开软件，进入"设置"
2. 配置 tempmail.plus 邮箱信息
3. 测试邮箱连接

### 2. 自动注册账号

1. 点击"自动注册"
2. 软件会自动完成注册流程
3. 账号自动保存到数据库

### 3. 账号切换

1. 选择要切换的账号
2. 点击"当前登录"按钮
3. Cursor 会自动重启并切换账号

### 4. 批量绑卡

1. 导入虚拟卡号或配置自动生成
2. 选择多个账号
3. 点击"批量绑卡"
4. 软件自动为所有账号绑卡

---

## 🛠️ 开发

### 环境要求

- Python 3.11+
- PyQt6
- DrissionPage
- 其他依赖见 `requirements.txt`

### 本地运行

```bash
# 克隆仓库
git clone https://github.com/zhuzhuxia56/ZZXcursor.git
cd ZZXcursor

# 安装依赖
pip install -r requirements.txt

# 运行
python main.py
```

### 打包

**Windows**:
```bash
pip install -r requirements.txt
pyinstaller build.spec --clean
```

**macOS**:
```bash
pip install -r requirements_macos.txt
./build_macos.sh
```

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 如何贡献

1. Fork 本仓库
2. 创建功能分支：`git checkout -b feature/AmazingFeature`
3. 提交更改：`git commit -m 'Add some AmazingFeature'`
4. 推送分支：`git push origin feature/AmazingFeature`
5. 提交 Pull Request

---

## 📝 许可证

本项目采用 [MIT License](LICENSE) 开源许可证。

这意味着您可以：
- ✅ 免费使用、修改、分发
- ✅ 用于商业用途
- ✅ 私人使用

唯一要求：保留原作者的版权声明。

---

## ⚠️ 免责声明

本软件仅供学习和研究使用。

- 请遵守 Cursor 的服务条款
- 不要滥用自动化功能
- 作者不对使用本软件产生的任何后果负责

---

## 🙏 致谢

- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - GUI 框架
- [DrissionPage](https://github.com/g1879/DrissionPage) - 浏览器自动化
- [Cursor](https://cursor.com/) - AI 编程工具

---

## 📧 联系方式

- GitHub: [@zhuzhuxia56](https://github.com/zhuzhuxia56)
- Issues: [提交问题](https://github.com/zhuzhuxia56/ZZXcursor/issues)

---

<div align="center">

**如果这个项目对您有帮助，请给个 ⭐ Star！**

Made with ❤️ by zhuzhuxia56

</div>
