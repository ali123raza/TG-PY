; =============================================================================
; TG-PY Fresh Installer Script
; Inno Setup Script - Entry Point: main.py
; =============================================================================
; Build: Run build_fresh.bat
; Requires: Inno Setup (https://jrsoftware.org/isdl.php)
; =============================================================================

#define MyAppName "TG-PY"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "TG-PY"
#define MyAppExeName "TG-PY.exe"
#define MyAppURL "https://tgpy.com"

[Setup]
; --- Basic Settings ---
AppId={{F1R2S3T4-U5V6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; --- Installation Paths ---
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=no
UsePreviousAppDir=yes

; --- Output ---
OutputDir=.\fresh_build
OutputBaseFilename=TG-PY-Fresh-Setup-v{#MyAppVersion}
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

; --- Compression ---
Compression=lzma2/max
SolidCompression=yes
LZMAUseSeparateProcess=yes

; --- User Permissions ---
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; --- UI Settings ---
WizardStyle=modern
SetupLogging=yes
ShowLanguageDialog=auto

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main application
Source: "fresh_build\TG-PY.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "fresh_build\README_LICENSE.md"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
; Create runtime directories (empty folders for app data)
Name: "{app}\data"; Permissions: users-full
Name: "{app}\sessions"; Permissions: users-full
Name: "{app}\media"; Permissions: users-full
Name: "{app}\tgdata"; Permissions: users-full
Name: "{app}\logs"; Permissions: users-full

[Icons]
; Start Menu
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Desktop icon (if selected)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Launch application after installation
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    Log('Fresh installation - license check enabled');
  end;
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
end;
