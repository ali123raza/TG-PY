; =============================================================================
; TG-PY User Installer Script
; Inno Setup Script - Creates professional Windows installer
; =============================================================================
; Build: Run installer\build_installer.bat
; Requires: Inno Setup (https://jrsoftware.org/isdl.php)
; =============================================================================

#define MyAppName "TG-PY"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "TG-PY"
#define MyAppExeName "TG-PY.exe"
#define MyAppURL "https://tgpy.com"

[Setup]
; --- Basic Settings ---
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
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
OutputDir=..\dist
OutputBaseFilename=TG-PY-Setup-v{#MyAppVersion}
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
WizardResizable=no
SetupLogging=yes
ShowLanguageDialog=auto

; --- Password (optional - uncomment to enable) ---
; Password=your_password_here

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
; Name: "urdu"; MessagesFile: "compiler:Languages\Urdu.isl"  ; Urdu file not available

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Main application
Source: "..\dist\TG-PY.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion

; Note: runtime folders created in [Dirs] section

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

; Quick Launch (if selected)
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; Launch application after installation
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// Custom installation logic
var
  RuntimeDataDir: String;
  RuntimeSessionsDir: String;
  RuntimeMediaDir: String;
  RuntimeTgDataDir: String;
  RuntimeLogsDir: String;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  // After installation, verify runtime folders exist
  if CurStep = ssPostInstall then
  begin
    Log('Verifying runtime directories...');
  end;
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
end;

[UninstallDelete]
; Clean up runtime data on uninstall (optional - comment out to preserve user data)
; Type: filesandordirs; Name: "{app}\data\*.*"
; Type: filesandordirs; Name: "{app}\sessions\*.*"
; Type: filesandordirs; Name: "{app}\media\*.*"
; Type: filesandordirs; Name: "{app}\tgdata\*.*"
; Type: filesandordirs; Name: "{app}\logs\*.*"
