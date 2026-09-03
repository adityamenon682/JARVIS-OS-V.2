; JARVIS Windows Installer
; ------------------------
; Wraps the PyInstaller output (dist\JARVIS\) into a proper installable
; Windows application: Start Menu shortcut, optional desktop shortcut,
; Program Files install location, and a Windows uninstaller entry.
;
; Requirements:
;   1. Inno Setup 6+ (free): https://jrsoftware.org/isinfo.php
;   2. Run scripts\build_windows.bat first so dist\JARVIS\JARVIS.exe exists.
;
; Usage:
;   Open this file in the Inno Setup Compiler and click Compile, or from a
;   command prompt with Inno Setup on PATH:
;     iscc scripts\windows_installer.iss
;
; Output: dist\installer\JARVIS-Setup.exe
;
; This script only packages already-built files. It does not compile Python
; code and does not bundle secrets (.env, api_keys.json, long_term.json) —
; those are created by the app itself on first run, same as the source
; checkout and the plain PyInstaller build.

#define AppName "JARVIS"
#define AppVersion "0.1.0"
#define AppPublisher "MAL19 Industries"
#define AppExeName "JARVIS.exe"
#define SourceDir "..\dist\JARVIS"

[Setup]
AppId={{7E9C7F0B-6E5A-4C7E-9E4E-JARVIS0001}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=JARVIS-Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
; Pulls in everything build_windows.py produced (exe + bundled assets/config
; templates + all PyInstaller runtime dependencies).
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName} now"; Flags: nowait postinstall skipifsilent
