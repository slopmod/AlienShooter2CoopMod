; Per-user installation. Only audited release files are removed on uninstall;
; saves, runtime copies and local configuration are deliberately not listed.
#ifndef ReleaseDir
  #error ReleaseDir must name the audited standalone launcher directory
#endif
#ifndef OutputDir
  #error OutputDir must name the release output directory
#endif
#ifndef AppVersion
  #error AppVersion is required
#endif

[Setup]
AppId={{D40B4A4B-1D41-4A23-A204-092E2B1ECA42}
AppName={cm:AppName}
AppVersion={#AppVersion}
AppVerName={cm:AppName} {#AppVersion}
DefaultDirName={localappdata}\Programs\AS2CoopCampaign
DefaultGroupName={cm:AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
WizardStyle=modern
InfoBeforeFile={#ReleaseDir}\INSTALL_EN.txt
LanguageDetectionMethod=none
ShowLanguageDialog=yes
UsePreviousLanguage=no
UninstallDisplayIcon={app}\AS2CoopCampaign.exe
UninstallDisplayName={cm:AppName}
OutputDir={#OutputDir}
OutputBaseFilename=AS2CoopCampaign-{#AppVersion}-setup
Compression=lzma2
SolidCompression=yes
CloseApplications=no
RestartApplications=no
SetupLogging=yes
VersionInfoVersion={#StringChange(AppVersion, "-preview", "")}.0
VersionInfoDescription=Alien Shooter 2 cooperative campaign installer

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"; InfoBeforeFile: "{#ReleaseDir}\INSTALL_EN.txt"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"; InfoBeforeFile: "{#ReleaseDir}\INSTALL_RU.txt"

[CustomMessages]
english.AppName=Alien Shooter 2 — Cooperative Campaign
russian.AppName=Alien Shooter 2 — Совместная кампания
english.CampaignShortcut=Cooperative Campaign
russian.CampaignShortcut=Совместная кампания
english.GuideShortcut=Installation guide
russian.GuideShortcut=Инструкция по установке
english.GuideFile=INSTALL_EN.txt
russian.GuideFile=INSTALL_RU.txt
english.DesktopIcon=Create a desktop shortcut
russian.DesktopIcon=Создать ярлык на рабочем столе
english.Launch=Open the cooperative campaign launcher
russian.Launch=Открыть лаунчер совместной кампании
english.SeparateFolder=Choose a separate folder for the mod. Select the installed game's folder in the launcher after installation.
russian.SeparateFolder=Выберите отдельную папку для мода. Папку установленной игры вы укажете в лаунчере после установки.
english.LanguageWriteFailed=Could not save the selected mod language. Check that the installation folder is writable.
russian.LanguageWriteFailed=Не удалось сохранить выбранный язык мода. Проверьте возможность записи в папку установки.

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopIcon}"; Flags: unchecked

[Files]
Source: "{#ReleaseDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{cm:CampaignShortcut}"; Filename: "{app}\AS2CoopCampaign.exe"; WorkingDir: "{app}"
Name: "{group}\{cm:GuideShortcut}"; Filename: "{app}\{cm:GuideFile}"
Name: "{autodesktop}\{cm:AppName}"; Filename: "{app}\AS2CoopCampaign.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\AS2CoopCampaign.exe"; Description: "{cm:Launch}"; Flags: nowait postinstall skipifsilent

[Code]
function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (CurPageID = wpSelectDir) and FileExists(ExpandConstant('{app}\AlienShooter.exe')) then
  begin
    SuppressibleMsgBox(CustomMessage('SeparateFolder'), mbError, MB_OK, IDOK);
    Result := False;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  LanguageCode: String;
begin
  if CurStep = ssPostInstall then
  begin
    LanguageCode := 'en';
    if ActiveLanguage = 'russian' then LanguageCode := 'ru';
    { Keep local source paths and other player settings intact. This file is
      created as configuration, so uninstall does not delete it or saves. }
    if not SaveStringToFile(ExpandConstant('{app}\campaign-language.txt'), LanguageCode + #13#10, False) then
      RaiseException(CustomMessage('LanguageWriteFailed'));
  end;
end;
