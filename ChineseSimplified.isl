; *** Inno Setup 简体中文语言文件 ***
; 
; 用于 Zzx Cursor Auto Manager 安装程序

[LangOptions]
LanguageName=简体中文
LanguageID=$0804
LanguageCodePage=936

[Messages]
; 安装向导
SetupAppTitle=安装
SetupWindowTitle=安装 - %1
UninstallAppTitle=卸载
UninstallAppFullTitle=%1 卸载

; 欢迎页面
WelcomeLabel1=欢迎使用 [name] 安装向导
WelcomeLabel2=安装向导将在您的电脑上安装 [name/ver]。%n%n建议您在继续之前关闭所有其它应用程序。

; 许可协议
LicenseLabel=在安装 [name] 之前，请阅读下列重要信息。
LicenseLabel3=请阅读下列许可协议。您在继续安装前必须同意这些协议条款。
LicenseAccepted=我接受协议(&A)
LicenseNotAccepted=我不接受协议(&D)

; 安装位置
SelectDirLabel3=安装程序将安装 [name] 到下列文件夹。
SelectDirBrowseLabel=单击"下一步"继续。如果您想选择不同的文件夹，单击"浏览"。
DiskSpaceMBLabel=至少需要有 [mb] MB 的可用磁盘空间。
SelectDirDesc=您想将 [name] 安装在何处？

; 开始菜单
SelectStartMenuFolderLabel3=安装程序将在下列开始菜单文件夹中创建程序的快捷方式。
SelectStartMenuFolderBrowseLabel=单击"下一步"继续。如果您想选择不同的文件夹，单击"浏览"。
SelectStartMenuFolderDesc=您想在哪个开始菜单文件夹中创建程序的快捷方式？

; 准备安装
ReadyLabel1=安装程序现在准备开始在您的电脑上安装 [name]。
ReadyLabel2a=单击"安装"继续此安装。如果您想要回顾或更改设置，请单击"上一步"。
ReadyLabel2b=单击"安装"继续此安装。

; 正在安装
InstallingLabel=安装程序正在您的电脑上安装 [name]，请稍候...
StatusInstalling=正在安装 %1...
StatusCreateDirs=正在创建目录...
StatusExtractFiles=正在解压文件...
StatusCreateIcons=正在创建快捷方式...
StatusCreateRegistry=正在写入注册表...
StatusRegisterFiles=正在注册文件...
StatusSavingUninstall=正在保存卸载信息...
StatusRunProgram=正在完成安装...

; 完成页面
FinishedHeadingLabel=[name] 安装完成
FinishedLabelNoIcons=安装程序已在您的电脑上安装了 [name]。
FinishedLabel=安装程序已在您的电脑上安装了 [name]。可以通过单击安装的图标运行此应用程序。
FinishedRestartLabel=要完成 [name] 的安装，安装程序必须重新启动您的电脑。您现在要重新启动吗？
FinishedRestartMessage=要完成 [name] 的安装，安装程序必须重新启动您的电脑。%n%n您现在要重新启动吗？
ShowReadmeCheck=是，我想查看自述文件
ClickFinish=单击"完成"退出安装程序。
FinishedLabelRun=启动 [name]

; 按钮
ButtonBack=< 上一步(&B)
ButtonNext=下一步(&N) >
ButtonInstall=安装(&I)
ButtonOK=确定
ButtonCancel=取消
ButtonYes=是(&Y)
ButtonYesToAll=全是(&A)
ButtonNo=否(&N)
ButtonNoToAll=全否(&O)
ButtonFinish=完成(&F)
ButtonBrowse=浏览(&B)...
ButtonWizardBrowse=浏览(&R)...

; 错误消息
ErrorCreatingDir=安装程序无法创建目录"%1"
ErrorTooManyFilesInDir=无法在目录"%1"中创建文件，因为里面的文件太多

; 准备卸载
ConfirmUninstall=您确定要完全移除 %1 及其所有组件吗？
UninstallOnlyOnWin64=此安装程序只能在 64 位 Windows 上卸载。
OnlyOnWin64=此程序只能在 64 位 Windows 上运行。
OnlyOnThisPlatform=此程序只能在 %1 上运行。

; 卸载
UninstallStatusLabel=正在从您的电脑上移除 %1，请稍候...
UninstalledAll=%1 已成功地从您的电脑上移除。
UninstalledMost=%1 卸载完成。%n%n有些内容无法被移除。您可以手工移除它们。
UninstalledAndNeedsRestart=要完成 %1 的卸载，必须重新启动您的电脑。%n%n您现在要重新启动吗？

; 退出设置
ExitSetupTitle=退出安装
ExitSetupMessage=安装程序未完成安装。如果您现在退出，程序将不能安装。%n%n您可以以后再运行安装程序完成安装。%n%n退出安装程序吗？

; 关闭应用程序
CloseApplications=关闭应用程序
CloseApplicationsMessage=安装程序将自动关闭下列应用程序。%n%n
CloseApplicationsFullMessage=安装程序检测到下列应用程序正在运行：%n%n%1%n单击"是"关闭这些应用程序并继续，或单击"否"退出安装。

; 准备安装
PreparingDesc=安装程序正在准备安装 [name] 到您的电脑上。
PreviousInstallNotCompleted=先前程序的安装/卸载未完成。您需要重新启动电脑才能完成那个安装。%n%n在重新启动电脑后，再次运行安装程序以完成 [name] 的安装。
CannotContinue=安装程序无法继续。请单击"取消"退出。

; 磁盘空间
DiskSpaceMBLabel=至少需要有 [mb] MB 的可用磁盘空间。
ToInstall=安装
Free=可用

; 进度和错误
SetupLdrStartupMessage=这将安装 %1。您想要继续吗？
SelectLanguageTitle=选择安装语言
SelectLanguageLabel=选择安装时要使用的语言：

; Admin 权限
AdditionalIcons=附加图标：
CreateDesktopIcon=创建桌面快捷方式(&D)
CreateQuickLaunchIcon=创建快速运行栏快捷方式(&Q)

; 目录存在
DirExists=文件夹：%n%n%1%n%n已经存在。您一定要安装到这个文件夹吗？
DirDoesntExist=文件夹：%n%n%1%n%n不存在。您想要创建此文件夹吗？

; 用户信息
UserInfoTitle=用户信息
UserInfoDesc=请输入您的信息。
UserInfoName=用户名(&U)：
UserInfoOrg=组织(&O)：
UserInfoSerial=序列号(&S)：
UserInfoNameRequired=您必须输入名字。

[CustomMessages]
; 自定义消息
AdditionalIcons=附加图标：

