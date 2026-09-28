; Inno Setup script for the youtube-dl Downloader native host + extension.
;
; Build order (see browser-extension/installer/README.md for full steps):
;   1. browser-extension/native-host/vendor/ffmpeg/ has ffmpeg.exe + ffprobe.exe
;   2. pyinstaller host.spec (from browser-extension/native-host/) -> dist/host/
;   3. package browser-extension/extension/ into youtube-dl-extension.xpi (this
;      directory) -- see build.ps1
;   4. iscc setup.iss (from this directory)
;
; What this installer does, since none of it can be done by the extension
; itself (a WebExtension can't touch the filesystem or registry directly):
;   - Installs the bundled host.exe (+ffmpeg) to Program Files
;   - Registers it as a native messaging host for Firefox (HKLM, so it's
;     available machine-wide since we're already running elevated)
;   - Installs the extension (signed by Mozilla, unlisted distribution) via
;     Firefox's enterprise policy mechanism (distribution/policies.json next
;     to firefox.exe), so it doesn't need a public Add-ons store listing.
;     It never touches an existing policies.json if one is already there
;     (see the Code section).
;
; Requires admin rights for both of those (Program Files, HKLM, and writing
; next to firefox.exe).
;
; Also requires Firefox to be closed before installing (see
; CheckFirefoxClosed below): Firefox only reads distribution/policies.json
; at startup, so installing or upgrading while it's running left the policy
; silently not taking effect until some later, easy-to-miss restart.

#define MyAppName "youtube-dl Downloader"
#define MyAppVersion "0.3.3"
#define MyAppPublisher "leconnn"
#define MyAppURL "https://github.com/leconnn/youtube-dl-extension"
#define NativeHostName "com.leconnn.youtube_dl_extension"
#define ExtensionId "youtube-dl-extension@local"
#define HostDistDir "..\native-host\dist\host"
#define XpiFile "youtube-dl-extension.xpi"

[Setup]
AppId={{B36F1F3E-6B0C-4B8E-9B1A-9C6F6F6B6C31}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\youtube-dl-extension
DisableProgramGroupPage=yes
DisableWelcomePage=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
Compression=lzma2/max
SolidCompression=yes
OutputDir=Output
OutputBaseFilename=youtube-dl-extension-setup
WizardStyle=modern

[Files]
Source: "{#HostDistDir}\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
Source: "{#XpiFile}"; DestDir: "{app}"; Flags: ignoreversion

[Registry]
Root: HKLM; Subkey: "SOFTWARE\Mozilla\NativeMessagingHosts\{#NativeHostName}"; \
  ValueType: string; ValueName: ""; ValueData: "{app}\{#NativeHostName}.json"; \
  Flags: uninsdeletekey

[Run]
Filename: "{code:GetFirefoxExePath}"; Description: "Launch Firefox now"; \
  Flags: postinstall nowait skipifsilent; Check: ShouldOfferLaunchFirefox

[Code]
var
  PoliciesPath: string;
  PoliciesInstalledByUs: Boolean;
  FirefoxExePath: string;

function IsFirefoxRunning(): Boolean;
var
  ResultCode: Integer;
  TempFile: string;
  Lines: TArrayOfString;
  I: Integer;
begin
  Result := False;
  TempFile := ExpandConstant('{tmp}\ff-running-check.txt');
  { Checks the actual process list via tasklist rather than window
    enumeration (FindWindowByClassName), since window enumeration only
    sees the calling process's own window station/session and can miss a
    real, visible Firefox window depending on how the installer itself
    was launched. }
  if Exec(ExpandConstant('{cmd}'), '/C tasklist /FI "IMAGENAME eq firefox.exe" /NH > "' + TempFile + '" 2>&1',
     '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    if LoadStringsFromFile(TempFile, Lines) then
    begin
      for I := 0 to GetArrayLength(Lines) - 1 do
        if Pos('firefox.exe', Lowercase(Lines[I])) > 0 then
        begin
          Result := True;
          break;
        end;
    end;
  end;
  DeleteFile(TempFile);
end;

function CheckFirefoxClosed(): Boolean;
var
  Response: Integer;
begin
  Result := True;
  while IsFirefoxRunning() do
  begin
    Response := MsgBox(
      'Firefox needs to be closed before installing. It only reads its ' +
      'extension configuration at startup, so installing while it''s ' +
      'running would leave the extension not actually installed until a ' +
      'later restart you might not think to make.' + Chr(13) + Chr(10) + Chr(13) + Chr(10) +
      'Close all Firefox windows, then click Retry.',
      mbInformation, MB_RETRYCANCEL);
    if Response = IDCANCEL then
    begin
      Result := False;
      exit;
    end;
  end;
end;

function InitializeSetup(): Boolean;
begin
  Result := CheckFirefoxClosed();
end;

function GetFirefoxExePath(Param: string): string;
begin
  Result := FirefoxExePath;
end;

function ShouldOfferLaunchFirefox(): Boolean;
begin
  Result := FirefoxExePath <> '';
end;

function JsonEscape(const S: string): string;
begin
  Result := S;
  StringChangeEx(Result, '\', '\\', True);
end;

function ToFileUrl(const WindowsPath: string): string;
var
  P: string;
begin
  P := WindowsPath;
  StringChangeEx(P, '\', '/', True);
  StringChangeEx(P, ' ', '%20', True);
  Result := 'file:///' + P;
end;

procedure WriteNativeMessagingManifest();
var
  HostExePath, Json: string;
begin
  HostExePath := ExpandConstant('{app}\host.exe');
  Json :=
    '{' + #13#10 +
    '  "name": "' + '{#NativeHostName}' + '",' + #13#10 +
    '  "description": "Native host for the youtube-dl Downloader Firefox extension",' + #13#10 +
    '  "path": "' + JsonEscape(HostExePath) + '",' + #13#10 +
    '  "type": "stdio",' + #13#10 +
    '  "allowed_extensions": ["' + '{#ExtensionId}' + '"]' + #13#10 +
    '}' + #13#10;
  SaveStringToFile(ExpandConstant('{app}\{#NativeHostName}.json'), Json, False);
end;

function FindFirefoxDir(): string;
var
  ExePath: string;
begin
  Result := '';
  if RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\firefox.exe', '', ExePath) then
    Result := ExtractFileDir(ExePath)
  else if FileExists(ExpandConstant('{commonpf}\Mozilla Firefox\firefox.exe')) then
    Result := ExpandConstant('{commonpf}\Mozilla Firefox')
  else if FileExists(ExpandConstant('{commonpf32}\Mozilla Firefox\firefox.exe')) then
    Result := ExpandConstant('{commonpf32}\Mozilla Firefox');
end;

procedure InstallFirefoxPolicy();
var
  FirefoxDir, DistDir, XpiPath, Json, NL, Msg: string;
begin
  NL := Chr(13) + Chr(10);
  PoliciesInstalledByUs := False;
  FirefoxDir := FindFirefoxDir();
  if FirefoxDir <> '' then
    FirefoxExePath := FirefoxDir + '\firefox.exe';
  if FirefoxDir = '' then
  begin
    Msg := 'Could not find a Firefox installation. The native host was installed, ';
    Msg := Msg + 'but the extension itself was not registered with Firefox. Install ';
    Msg := Msg + 'Firefox and re-run this installer, or load the extension manually ';
    Msg := Msg + 'from ' + ExpandConstant('{app}\{#XpiFile}') + '.';
    MsgBox(Msg, mbInformation, MB_OK);
    exit;
  end;

  DistDir := FirefoxDir + '\distribution';
  PoliciesPath := DistDir + '\policies.json';

  { A policies.json already there that we did NOT create ourselves (no
    marker file) belongs to someone else's configuration (or a previous,
    differently-installed one) -- never overwrite that blind. One we did
    create ourselves (e.g. a re-run of this same installer, or an update)
    is always safe to refresh, since its content only ever depends on
    values fixed by this script (the extension id and install path). }
  if FileExists(PoliciesPath) and not FileExists(ExpandConstant('{app}\.policies-installed-by-us')) then
  begin
    Msg := 'Firefox already has a policies.json file at:' + NL + PoliciesPath + NL + NL;
    Msg := Msg + 'To avoid overwriting an existing configuration, this installer ';
    Msg := Msg + 'did not touch it. To finish installing the extension, add this to ';
    Msg := Msg + 'its "ExtensionSettings" (create that key if it is missing):' + NL + NL;
    Msg := Msg + '"{#ExtensionId}": { "installation_mode": "normal_installed", ';
    Msg := Msg + '"install_url": "' + ToFileUrl(ExpandConstant('{app}\{#XpiFile}')) + '" }';
    MsgBox(Msg, mbInformation, MB_OK);
    exit;
  end;

  if not ForceDirectories(DistDir) then
  begin
    Msg := 'Could not create ' + DistDir + '. The extension was not registered ';
    Msg := Msg + 'with Firefox; load it manually from ' + ExpandConstant('{app}\{#XpiFile}') + '.';
    MsgBox(Msg, mbError, MB_OK);
    exit;
  end;

  XpiPath := ExpandConstant('{app}\{#XpiFile}');
  Json :=
    '{' + #13#10 +
    '  "policies": {' + #13#10 +
    '    "ExtensionSettings": {' + #13#10 +
    '      "{#ExtensionId}": {' + #13#10 +
    '        "installation_mode": "normal_installed",' + #13#10 +
    '        "install_url": "' + ToFileUrl(XpiPath) + '"' + #13#10 +
    '      }' + #13#10 +
    '    }' + #13#10 +
    '  }' + #13#10 +
    '}' + #13#10;

  SaveStringToFile(PoliciesPath, Json, False);
  PoliciesInstalledByUs := True;
  SaveStringToFile(ExpandConstant('{app}\.policies-installed-by-us'), PoliciesPath, False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    WriteNativeMessagingManifest();
    InstallFirefoxPolicy();
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  MarkerPath, RecordedPoliciesPath: string;
  Lines: TArrayOfString;
begin
  if CurUninstallStep = usUninstall then
  begin
    MarkerPath := ExpandConstant('{app}\.policies-installed-by-us');
    if FileExists(MarkerPath) then
    begin
      if LoadStringsFromFile(MarkerPath, Lines) and (GetArrayLength(Lines) > 0) then
      begin
        RecordedPoliciesPath := Lines[0];
        if FileExists(RecordedPoliciesPath) then
          DeleteFile(RecordedPoliciesPath);
        RemoveDir(ExtractFileDir(RecordedPoliciesPath));
      end;
    end;
  end;
end;

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
