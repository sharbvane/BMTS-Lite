[Setup]
AppId=BMTSLite
AppName=BMTS Lite
AppVersion=0.1.1
AppPublisher=BMTS Lite
AppPublisherURL=https://github.com/sharbvane/bgm-montage
DefaultDirName={localappdata}\Programs\BMTS Lite
DefaultGroupName=BMTS Lite
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=release
OutputBaseFilename=BMTS-Lite-Setup-0.1.1-Windows-x64
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\BMTS-Lite.exe
CloseApplications=yes
[Files]
Source: "build\dist\BMTS-Lite\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{autoprograms}\BMTS Lite"; Filename: "{app}\BMTS-Lite.exe"
Name: "{autodesktop}\BMTS Lite"; Filename: "{app}\BMTS-Lite.exe"; Tasks: desktopicon
[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; Flags: unchecked
[Run]
Filename: "{app}\BMTS-Lite.exe"; Description: "Open BMTS Lite"; Flags: nowait postinstall skipifsilent
