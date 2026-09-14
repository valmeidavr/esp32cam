; Instalador Windows (Inno Setup) do Classificador de Pecas ESP32-CAM.
; Empacota a pasta gerada pelo PyInstaller, cria os atalhos e libera a porta
; 8000 no firewall para a banca abrir a pagina pelo celular.
;
; Gerado pelo construir.ps1 — nao precisa compilar na mao.

#define Nome        "Classificador de Peças ESP32-CAM"
#define NomeCurto   "ClassificadorESP32CAM"
; a versao vem de visao/versao.py, passada pelo construir.ps1 como /DVersao=x.y.z
#ifndef Versao
  #define Versao    "0.0.0"
#endif
#define Autor       "ETPC - Escola Técnica"
#define Copyright   "© 2026 ETPC. Matheus Pedrosa, Carlos Eduardo Borges, Maria Eduarda Mazza, Milena Maia, Milena Rodrigues. Apoio: Prof. Vinicius (Tecnologia). Todos os direitos reservados."
#define Site        "https://github.com/valmeidavr/esp32cam"
#define Exe         "ClassificadorESP32CAM.exe"
#define Origem      "..\dist\ClassificadorESP32CAM"

[Setup]
AppId={{7C2F1B7A-3E6D-4B2A-9D7E-51A0C3E8F2D4}
AppName={#Nome}
AppVersion={#Versao}
AppPublisher={#Autor}
AppPublisherURL={#Site}
AppSupportURL={#Site}
AppCopyright={#Copyright}
VersionInfoCompany={#Autor}
VersionInfoCopyright={#Copyright}
VersionInfoVersion={#Versao}
; pagina de creditos exibida no comeco do assistente
InfoBeforeFile=..\COPYRIGHT
DefaultDirName={autopf}\{#NomeCurto}
DefaultGroupName={#Nome}
UninstallDisplayIcon={app}\{#Exe}
OutputDir=..\dist
OutputBaseFilename={#NomeCurto}-Setup-{#Versao}
SetupIconFile=icone.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; a regra de firewall exige administrador
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
; na atualizacao automatica o programa esta aberto: fechar e trocar os arquivos
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"
Name: "firewall"; Description: "Liberar a porta 8000 no firewall (para abrir a página pelo celular)"; GroupDescription: "Rede:"

[Files]
Source: "{#Origem}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#Nome}"; Filename: "{app}\{#Exe}"; WorkingDir: "{app}"
Name: "{group}\Regravar firmware na placa"; Filename: "{app}\{#Exe}"; Parameters: "--gravar"; WorkingDir: "{app}"
Name: "{group}\Driver USB CH340 (site do fabricante)"; Filename: "https://www.wch.cn/downloads/CH341SER_EXE.html"
Name: "{group}\Desinstalar {#Nome}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#Nome}"; Filename: "{app}\{#Exe}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
; regra de firewall: sem ela o Windows bloqueia o celular da banca
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""{#Nome}"""; Flags: runhidden; Tasks: firewall
Filename: "netsh"; Parameters: "advfirewall firewall add rule name=""{#Nome}"" dir=in action=allow protocol=TCP localport=8000 program=""{app}\{#Exe}"" enable=yes profile=any"; Flags: runhidden; Tasks: firewall
; sem "skipifsilent": na atualizacao automatica (instalador rodando em modo
; silencioso) o programa reabre sozinho. "runasoriginaluser" para ele nao
; herdar os privilegios de administrador do instalador.
Filename: "{app}\{#Exe}"; Description: "Abrir o {#Nome} agora"; Flags: nowait postinstall runasoriginaluser

[UninstallRun]
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""{#Nome}"""; Flags: runhidden; RunOnceId: "firewall"
