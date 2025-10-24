# Zzx Cursor Auto Manager - 发布版本说明

## 📦 打包状态

### ✅ 已完成
- ✅ 图标文件：`ZZX.ico`
- ✅ PyInstaller配置：`build.spec`
- ✅ 程序打包：`dist/Zzx Cursor Auto Manager/`
- ✅ Inno Setup脚本：`installer.iss`
- ✅ 所有代码已使用用户目录路径

### ⏳ 待完成
- ⏳ 编译安装程序（需要安装 Inno Setup）
- ⏳ 测试安装和运行

---

## 🚀 如何完成打包

### 1. 安装 Inno Setup（如果尚未安装）

**下载地址**：https://jrsoftware.org/isdl.php

**安装步骤**：
1. 下载 `innosetup-6.x.x.exe`
2. 运行安装程序
3. 默认安装路径即可
4. 安装完成

### 2. 编译安装程序

**方法1：使用批处理文件（推荐）**
```cmd
双击运行：编译安装程序.bat
```

**方法2：手动编译**
```cmd
cd "C:\Users\34067\Desktop\azzcursor\Zzx-cursor-auto"
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

**方法3：使用图形界面**
1. 双击 `installer.iss` 文件
2. Inno Setup 会自动打开
3. 点击 "Build" → "Compile"

### 3. 获取安装程序

编译成功后，安装程序在：
```
Zzx-cursor-auto/output/Zzx-Cursor-Auto-Setup.exe
```

---

## 📋 分发给用户

### 需要分发的文件
- `Zzx-Cursor-Auto-Setup.exe` - 安装程序

### 需要告知用户的信息

**激活码**：`E9CC-8F28-1EFE-C375`
- 用途：解除每日注册5个的限制
- 位置：设置 → 激活码绑定

**解锁码**：`ZZX-CURSOR-2025`
- 用途：解锁虚拟卡自动生成功能
- 位置：绑卡配置 → 自动生成卡号

### 使用说明

1. **安装**
   - 双击 `Zzx-Cursor-Auto-Setup.exe`
   - 选择安装位置（默认 C:\Program Files\Zzx Cursor Auto\）
   - 完成安装

2. **首次运行**
   - 双击桌面快捷方式
   - 软件会自动在 %APPDATA% 创建数据目录
   - 首次运行会生成加密密钥和配置文件

3. **激活软件**
   - 打开设置页面
   - 输入激活码：`E9CC-8F28-1EFE-C375`
   - 点击"绑定激活码"

4. **配置邮箱**
   - 打开邮箱配置页面
   - 填写接收邮箱、PIN码、域名
   - 保存配置

5. **开始使用**
   - 点击"刷新账号"自动注册新账号
   - 所有账号数据保存在 %APPDATA%\Zzx-Cursor-Auto\data\

---

## 📊 项目文件结构

### 开发文件（不分发）
```
Zzx-cursor-auto/
  ├── build/                      (PyInstaller 构建缓存)
  ├── dist/                       (打包后的程序)
  ├── build.spec                  (PyInstaller 配置)
  ├── installer.iss               (Inno Setup 脚本)
  ├── 编译安装程序.bat             (编译工具)
  ├── ZZX.ico                     (图标文件)
  └── 打包完成指南.md              (本文档)
```

### 分发文件
```
output/
  └── Zzx-Cursor-Auto-Setup.exe  (唯一需要分发的文件)
```

---

## 🔧 开发者工具

### 重新打包

如果修改了代码，需要重新打包：

```cmd
cd "C:\Users\34067\Desktop\azzcursor\Zzx-cursor-auto"

# 1. 重新打包 exe
pyinstaller build.spec --clean

# 2. 重新编译安装程序
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

### 快速测试

测试打包后的 exe（不安装）：

```cmd
cd dist\Zzx Cursor Auto Manager
"Zzx Cursor Auto Manager.exe"
```

### 清理构建文件

```cmd
# 删除构建缓存
rmdir /s /q build
rmdir /s /q dist
rmdir /s /q output

# 重新打包
pyinstaller build.spec
```

---

## 🐛 常见问题

### Q1: 打包失败，提示缺少模块？
A: 检查 `build.spec` 的 `hiddenimports` 列表，添加缺失的模块

### Q2: exe无法运行，提示缺少dll？
A: 可能是 PyQt6 或 Python 的dll未正确打包，重新运行：
```cmd
pyinstaller build.spec --clean
```

### Q3: 安装程序编译失败？
A: 检查：
- Inno Setup 是否正确安装
- `installer.iss` 路径是否正确
- `dist/Zzx Cursor Auto Manager/` 是否存在

### Q4: 安装后软件无法启动？
A: 可能原因：
- Windows Defender 误报（添加到白名单）
- 缺少管理员权限（右键 → 以管理员身份运行）
- 缺少运行库（安装 VC++ Redistributable）

### Q5: 数据目录在哪里？
A: `C:\Users\你的用户名\AppData\Roaming\Zzx-Cursor-Auto\`

查看方法：
```cmd
echo %APPDATA%\Zzx-Cursor-Auto
explorer %APPDATA%\Zzx-Cursor-Auto
```

---

## 📞 技术支持

如有问题，请联系：
- 开发者：Zzx Dev
- 项目地址：[GitHub链接]

---

**最后更新**：2025-10-22
**版本**：1.0.0

