; SMOXI Service — Inno Setup 6 installer script
; Compile via scripts/build_installer.ps1 or ISCC.exe

#define MyAppName "SMOXI Service"
#ifndef MyAppVersion
  #define MyAppVersion "1.5.0"
#endif
#define MyAppPublisher "SMOXI"
#define MyAppURL "https://smoxi.uz"
#define MyAppExeName "smoxi-service.exe"

[Setup]
AppId={{A7C3E9F1-8B2D-4F6A-9C1E-5D8B0A2F4E6C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\SMOXI Service
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=SMOXIServiceSetup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
; Nuitka onedir output — adjust Source if using onefile
Source: "..\dist\smoxi-service\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch SMOXI Service"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\uploads"
Type: filesandordirs; Name: "{app}\backups"
