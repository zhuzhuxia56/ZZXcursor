; Inno Setup 安装脚本
; Zzx Cursor Auto Manager 安装程序配置

#define MyAppName "Zzx Cursor Auto Manager"
#define MyAppVersion "1.2.0"
#define MyAppPublisher "Zzx Dev"
#define MyAppExeName "Zzx Cursor Auto Manager.exe"
#define MyAppURL "https://github.com/zzx"

[Setup]
; 基本信息
AppId={{8F3C9D1E-6A4B-4F2C-9E8D-7C5B3A2F1D9E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; 安装目录
DefaultDirName={autopf}\Zzx Cursor Auto
DefaultGroupName={#MyAppName}
AllowNoIcons=yes

; 输出设置
OutputDir=output
OutputBaseFilename=Zzx-Cursor-Auto-Setup-v1.2.0
SetupIconFile=ZZX.ico

; 压缩设置
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
LZMANumBlockThreads=4

; 安装界面
WizardStyle=modern

; 权限设置
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; 语言
ShowLanguageDialog=no
LanguageDetectionMethod=uilanguage

; Windows版本要求
MinVersion=10.0
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; 卸载设置
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
; 使用项目中的中文语言文件（GitHub Actions 兼容）
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标:"; Flags: checkedonce

[Files]
; 打包所有文件
Source: "dist\Zzx Cursor Auto Manager\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\Zzx Cursor Auto Manager\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; 开始菜单快捷方式
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Comment: "Cursor 账号自动化管理工具"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"

; 桌面快捷方式
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; WorkingDir: "{app}"; Comment: "Cursor 账号自动化管理工具"

[Run]
; 安装完成后询问是否运行（以管理员身份）
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent runascurrentuser shellexec

[Code]
// Pascal 脚本 - 用于自定义安装行为

// 检查是否已安装，提示用户
function InitializeSetup(): Boolean;
var
  InstalledVersion: String;
  UninstallPath: String;
  ResultCode: Integer;
begin
  Result := True;
  
  // 检查注册表中是否存在安装信息
  if RegQueryStringValue(HKLM, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{8F3C9D1E-6A4B-4F2C-9E8D-7C5B3A2F1D9E}_is1', 
     'DisplayVersion', InstalledVersion) then
  begin
    // 已安装，询问用户
    if MsgBox('检测到 Zzx Cursor Auto Manager ' + InstalledVersion + ' 已安装。' + #13#10 + #13#10 +
              '是否要覆盖安装（更新）？' + #13#10 + #13#10 +
              '选择"是"：覆盖更新（保留用户数据）' + #13#10 +
              '选择"否"：取消安装', 
              mbConfirmation, MB_YESNO) = IDNO then
    begin
      Result := False;
      Exit;
    end;
    
    // 用户选择覆盖，先卸载旧版本
    if RegQueryStringValue(HKLM, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{8F3C9D1E-6A4B-4F2C-9E8D-7C5B3A2F1D9E}_is1',
       'UninstallString', UninstallPath) then
    begin
      // 静默卸载并保留用户数据（通过参数控制）
      Exec(RemoveQuotes(UninstallPath), '/VERYSILENT /NORESTART /SUPPRESSMSGBOXES /KEEPUSERDATA=1', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    end;
  end;
end;

// 设置快捷方式为管理员权限
procedure SetShortcutRunAsAdmin(ShortcutPath: String);
var
  ShellObj: Variant;
  ShortcutObj: Variant;
  ResultCode: Integer;
begin
  try
    ShellObj := CreateOleObject('WScript.Shell');
    ShortcutObj := ShellObj.CreateShortcut(ShortcutPath);
    // 读取并修改快捷方式
    ShortcutObj.Save;
    
    // 使用 PowerShell 设置管理员权限
    Exec('powershell.exe', '-NoProfile -Command "' + 
         '$bytes = [System.IO.File]::ReadAllBytes(''' + ShortcutPath + '''); ' +
         '$bytes[0x15] = $bytes[0x15] -bor 0x20; ' +
         '[System.IO.File]::WriteAllBytes(''' + ShortcutPath + ''', $bytes)"',
         '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  except
  end;
end;

// 安装前的准备工作
procedure CurStepChanged(CurStep: TSetupStep);
var
  AppDataPath: String;
  DesktopShortcut: String;
  StartMenuShortcut: String;
begin
  if CurStep = ssPostInstall then
  begin
    // 安装完成后，创建用户数据目录
    AppDataPath := ExpandConstant('{userappdata}\Zzx-Cursor-Auto');
    if not DirExists(AppDataPath) then
      CreateDir(AppDataPath);
    
    // 创建data子目录
    if not DirExists(AppDataPath + '\data') then
      CreateDir(AppDataPath + '\data');
      
    // 创建logs子目录
    if not DirExists(AppDataPath + '\data\logs') then
      CreateDir(AppDataPath + '\data\logs');
    
    // 设置桌面快捷方式为管理员权限
    DesktopShortcut := ExpandConstant('{autodesktop}\{#MyAppName}.lnk');
    if FileExists(DesktopShortcut) then
      SetShortcutRunAsAdmin(DesktopShortcut);
    
    // 设置开始菜单快捷方式为管理员权限
    StartMenuShortcut := ExpandConstant('{group}\{#MyAppName}.lnk');
    if FileExists(StartMenuShortcut) then
      SetShortcutRunAsAdmin(StartMenuShortcut);
  end;
end;

// 卸载时的清理工作
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppDataPath: String;
  ResultCode: Integer;
  KeepUserData: Boolean;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    // 检查是否有保留数据的参数（更新安装时传递）
    KeepUserData := False;
    if ExpandConstant('{param:KEEPUSERDATA|0}') = '1' then
      KeepUserData := True;
    
    // 如果是更新安装，直接保留数据，不询问
    if KeepUserData then
    begin
      Exit;  // 保留数据，不删除
    end;
    
    // 手动卸载时，询问是否删除用户数据
    if MsgBox('是否同时删除用户数据（配置文件、账号数据库等）？' + #13#10 +  
              '选择"是"：删除所有数据（包括配置和账号）' + #13#10 +  
              '选择"否"：保留数据供下次安装使用', 
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      // 用户选择"是"，删除所有数据
      // 1. 删除 AppData 中的用户数据
      AppDataPath := ExpandConstant('{userappdata}\Zzx-Cursor-Auto');
      if DirExists(AppDataPath) then
      begin
        Exec('powershell.exe', 
             '-NoProfile -ExecutionPolicy Bypass -Command "' +
             'Start-Sleep -Milliseconds 500; ' +
             'if (Test-Path ''' + AppDataPath + ''') { ' +
             '  Remove-Item ''' + AppDataPath + ''' -Recurse -Force -ErrorAction SilentlyContinue ' +
             '}"',
             '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      end;
      
      // 2. 删除安装目录下的 data 文件夹（兼容旧版本）
      AppDataPath := ExpandConstant('{app}\data');
      if DirExists(AppDataPath) then
      begin
        Exec('powershell.exe', 
             '-NoProfile -ExecutionPolicy Bypass -Command "' +
             'Start-Sleep -Milliseconds 500; ' +
             'if (Test-Path ''' + AppDataPath + ''') { ' +
             '  Remove-Item ''' + AppDataPath + ''' -Recurse -Force -ErrorAction SilentlyContinue ' +
             '}"',
             '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      end;
    end;
    // 如果选择"否"（IDNO），什么都不做，保留数据
  end;
end;

